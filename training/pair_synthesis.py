# -*- coding: utf-8 -*-
"""Turn human-written Vietnamese text into (AI-flavoured -> human) rewrite pairs.

Why this module exists
----------------------
`prepare_dataset.py --mode continuation` builds samples whose user prompt says
"rewrite this text" while the assistant target is the *next* chunk. Training on
that teaches a continuation model, not a rewriter: the model learns to ignore
the input, which is exactly what destroys fact preservation at inference time.

The pairs we actually need are `(AI-flavoured text A, human text H)` where A and
H carry the *same* facts. We cannot download such a corpus, but we can build it:
take real human prose H and "dirty" it into A by injecting the very tells this
project catalogs (generic connectors, hollow evaluative tails, template
openings). A is then AI-flavoured by construction, H is human by definition,
and because dirtying only inserts phrases without digits the fact-token multiset
is identical on both sides.

Two dirtying engines
--------------------
* ``rule``  - deterministic, offline, zero cost. Insert connectors/openers from
  the project's own catalog. Guarantees fact invariance structurally.
* ``llm``   - a teacher model behind an OpenAI-compatible endpoint (Groq or a
  local vLLM). Produces more realistic A, but every candidate is still checked
  mechanically by :func:`check_pair`; anything that drops or adds a number/date
  is rejected instead of being trained on.

Fact-token definition
---------------------
The canonical implementation lives in ``web/backend/app/services/fact_guard.py``.
This module imports it when the repository layout is available (single source of
truth) and otherwise falls back to :func:`_fallback_fact_tokens`, which mirrors
it exactly; ``tests/test_pair_synthesis.py`` asserts the two agree so they
cannot drift silently.
"""

from __future__ import annotations

import difflib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Groq nằm sau Cloudflare: User-Agent mặc định của urllib bị chặn (error 1010).
USER_AGENT = (
    "vietnamese-humanizer-teacher/0.5 "
    "(training data synthesis; https://github.com/datnguyentien2006/vietnamese-humanize)"
)

# --------------------------------------------------------------------------
# Fact tokens: single source of truth, with a mirrored fallback.
# --------------------------------------------------------------------------

_DATE_TOKEN_RE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
_NUM_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _fallback_fact_tokens(text: str) -> Counter:
    tokens: Counter = Counter()
    for match in _DATE_TOKEN_RE.findall(text):
        tokens[match] += 1
    residue = _DATE_TOKEN_RE.sub(" ", text)
    for match in _NUM_TOKEN_RE.findall(residue):
        tokens[match.replace(".", "").replace(",", "")] += 1
    return tokens


def _load_backend_fact_tokens():
    """Import ``app.services.fact_guard.fact_tokens`` if the repo layout allows."""
    backend = Path(__file__).resolve().parents[1] / "web" / "backend"
    if not backend.is_dir():
        return None
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    try:
        from app.services.fact_guard import fact_tokens  # noqa: PLC0415
    except Exception:  # pragma: no cover - layout/dependency differences
        return None
    return fact_tokens


_BACKEND_FACT_TOKENS = _load_backend_fact_tokens()


def fact_tokens(text: str) -> Counter:
    """Counter of verifiable data tokens (dates + canonical numbers)."""
    if _BACKEND_FACT_TOKENS is not None:
        return _BACKEND_FACT_TOKENS(text)
    return _fallback_fact_tokens(text)


# --------------------------------------------------------------------------
# Dirtying signals (mirrors patterns/humanizer.yml VI-HUM-S15 / S16).
# --------------------------------------------------------------------------

AI_CONNECTORS = (
    "Tổng thể",
    "Bên cạnh đó",
    "Ngoài ra",
    "Điều này cho thấy",
    "Nói cách khác",
    "Nhìn chung",
    "Quan trọng là",
    "Theo đó",
    "Chính vì vậy",
    "Trong bối cảnh đó",
    "Điều này đồng nghĩa với việc",
    "Để đạt được điều này",
)

TEMPLATE_OPENERS = (
    "Trong bối cảnh không ngừng phát triển, ",
    "Trong bối cảnh chuyển đổi số diễn ra mạnh mẽ, ",
)

HOLLOW_CLOSERS = (
    "Điều này cho thấy tầm quan trọng của vấn đề là rất lớn.",
    "Nhìn chung, đây là một yếu tố then chốt cần được quan tâm.",
    "Quan trọng là, vấn đề này cần được nhìn nhận một cách toàn diện.",
)

# Keep proper nouns and acronyms capitalised when a connector is prepended.
_PROPER_NOUN_GUARD = (
    "Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ", "Huế",
    "Việt Nam", "Hoa Kỳ", "Trung Quốc", "Nhật Bản", "Hàn Quốc", "Thái Lan",
)

# Split only after real sentence terminators: whitespace + an opening capital.
# A naive [^.!?]+ split would cut "3.2.1" into three tokens and silently break
# fact preservation, which is the one thing these pairs must guarantee.
_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-ZĐÀ-Ỹ“\"'(\[])", flags=re.UNICODE
)

STRUCTURAL_LINE_RE = re.compile(r"^\s*(?:[#>*+-]|\d+[.)]|```|~~~)")


def _lower_first(text: str, context: str = "") -> str:
    """Lowercase the first letter only when the word is demonstrably common.

    Vietnamese sentences start with a capital, so blindly lowercasing after a
    connector mangles proper nouns ("Liên" -> "liên"). We therefore lowercase
    only when the same word also occurs lowercase somewhere in the surrounding
    paragraph — that is evidence it is a common noun, not a name. Anything
    unproven keeps its capital.
    """
    if not text:
        return text
    stripped = text.lstrip()
    if not stripped:
        return text
    offset = len(text) - len(stripped)
    head = stripped.split(" ", 1)[0]
    if any(stripped.startswith(name) for name in _PROPER_NOUN_GUARD):
        return text
    if len(head) > 1 and head[1].isupper():  # UBND, TP, API ...
        return text
    if not context:
        return text
    lowered = head.lower()
    if not re.search(rf"(?<!\w){re.escape(lowered)}(?!\w)", context):
        return text
    return text[:offset] + stripped[0].lower() + stripped[1:]


def _split_sentences(paragraph: str) -> list[str]:
    return [part for part in _SENTENCE_SPLIT_RE.split(paragraph) if part.strip()]


def _dirty_paragraph(paragraph: str, rng: random.Random, allow_index0: bool = True) -> str:
    sentences = _split_sentences(paragraph)
    if not sentences:
        return paragraph
    # A paragraph with no sentence terminator is a label/heading, not prose:
    # rewriting it produces run-on garbage and poisons the gold pairing.
    if not any(mark in paragraph for mark in ".!?"):
        return paragraph

    # Decide connector positions first so every paragraph gets at least one:
    # a paragraph that stays clean would produce a pair whose input is not
    # AI-flavoured at all, which teaches the model nothing.
    first_allowed = 0 if allow_index0 else 1
    chosen: set[int] = {
        i for i in range(1, len(sentences)) if i >= first_allowed and rng.random() < 0.45
    }
    if not chosen and len(sentences) > first_allowed:
        chosen = {rng.randint(first_allowed, len(sentences) - 1)}

    out: list[str] = []
    used_connectors: set[str] = set()
    for index, sentence in enumerate(sentences):
        sentence = sentence.rstrip()
        stripped = sentence.lstrip()
        prefix = sentence[: len(sentence) - len(stripped)]

        if index in chosen:
            # Never reuse the same connector twice in one paragraph: real AI
            # prose varies its glue, and a repeated "Nhìn chung" right after
            # itself reads like a generator artefact rather than a style.
            options = [c for c in AI_CONNECTORS if c not in used_connectors] or [
                *AI_CONNECTORS
            ]
            connector = rng.choice(options)
            used_connectors.add(connector)
            body = _lower_first(stripped, paragraph)
            sentence = f"{prefix}{connector}, {body}"

        out.append(sentence)

    result = " ".join(part.strip() for part in out if part.strip())
    # Chèn thêm đuôi rỗng nhưng không để đoạn phình quá 40%: nếu phình quá thì
    # cặp sẽ bị loại ở length_ratio, và một bản "AI" dài gấp rưỡi bản người
    # không còn giống văn AI thật nữa.
    base_words = max(len(paragraph.split()), 1)
    if len(sentences) >= 3 and rng.random() < 0.3:
        closer = rng.choice(HOLLOW_CLOSERS)
        if len((result + " " + closer).split()) <= 1.4 * base_words:
            result = result + " " + closer
    return result


def dirty_rule_based(text: str, rng: random.Random | None = None) -> str:
    """Inject catalog tells without touching any digit.

    The result is AI-flavoured by construction: generic connectors, template
    openers, hollow evaluative tails. Because no inserted phrase contains a
    digit, ``fact_tokens(dirty_rule_based(h)) == fact_tokens(h)`` always holds;
    :func:`check_pair` still verifies it.
    """
    rng = rng or random.Random(0)
    paragraphs = [part for part in text.split("\n\n")]
    rendered: list[str] = []

    for position, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            rendered.append(paragraph)
            continue
        if STRUCTURAL_LINE_RE.match(paragraph):
            rendered.append(paragraph)
            continue
        add_opener = position == 0 and rng.random() < 0.6
        dirty = _dirty_paragraph(paragraph, rng, allow_index0=not add_opener)
        if add_opener and dirty != paragraph:
            dirty = rng.choice(TEMPLATE_OPENERS) + _lower_first(dirty, paragraph)
        rendered.append(dirty)

    joined = "\n\n".join(rendered)
    return re.sub(r"[ \t]+", " ", joined).strip()


# --------------------------------------------------------------------------
# Teacher engine (OpenAI-compatible endpoint: Groq or local vLLM).
# --------------------------------------------------------------------------

AI_STYLE_TEACHER_PROMPT = """Bạn viết lại văn bản tiếng Việt theo đúng kiểu "văn AI" của một trợ lý phổ thông.

Quy tắc bắt buộc:
1. Giữ nguyên 100% số liệu, ngày tháng, tên riêng, tên tổ chức, viết tắt và đơn vị. Không thêm, không bớt, không đổi một chữ số nào.
2. Chỉ đổi cách diễn đạt bề mặt: thêm cú nối khuôn mẫu, danh hóa, câu đều nhịp, nhận định rỗng.
3. Dùng các cú nối kiểu: "Tổng thể", "Bên cạnh đó", "Ngoài ra", "Điều này cho thấy", "Nói cách khác", "Nhìn chung", "Quan trọng là", "Theo đó".
4. Câu đều 18-25 từ, hạn chế câu ngắn, tránh khẩu ngữ.
5. Độ dài bắt buộc 90-120% số từ bản gốc (đếm từ). TUYỆT ĐỐI không thêm câu mới, không thêm ý mới — chỉ biến đổi câu có sẵn bằng cách chèn từ nối, danh hóa, nhận định rỗng ngắn cuối đoạn.
6. Chỉ trả về văn bản đã viết lại, không giải thích, không markdown.

Văn bản gốc:
<ORIGINAL>
{text}
</ORIGINAL>"""


# Ba mức độ "văn AI" cho teacher: L2 giữ nguyên prompt chuẩn của project,
# L1 chỉ chèn nối nhẹ (gần bằng engine rule), L3 là văn AI máy móc nhất
# (mở đầu khuôn mẫu, liệt kê đối xứng, đuôi nhận định rỗng). Chạy với
# teacher_severities để corpus có đủ nhiều mức độ AI khác nhau.
AI_STYLE_TEACHER_PROMPTS: dict[str, str] = {
    "L1": """Bạn viết lại văn bản tiếng Việt theo kiểu "văn AI" ở mức nhẹ.

Quy tắc bắt buộc:
1. Giữ nguyên 100% số liệu, ngày tháng, tên riêng, tên tổ chức, viết tắt và đơn vị. Không thêm, không bớt, không đổi một chữ số nào.
2. Chỉ chèn 1-2 từ nối khuôn mẫu mỗi đoạn ("Bên cạnh đó", "Theo đó", "Nói cách khác"). Không đổi cấu trúc câu gốc.
3. Độ dài bắt buộc 95-115% số từ bản gốc. TUYỆT ĐỐI không thêm câu mới, không thêm ý mới — chỉ biến đổi câu có sẵn.
4. Chỉ trả về văn bản đã viết lại, không giải thích, không markdown.

Văn bản gốc:
<ORIGINAL>
{text}
</ORIGINAL>""",
    "L2": AI_STYLE_TEACHER_PROMPT,
    "L3": """Bạn viết lại văn bản tiếng Việt thành văn AI nặng độ máy móc — kiểu content SEO hoặc báo cáo AI generic.

Quy tắc bắt buộc:
1. Giữ nguyên 100% số liệu, ngày tháng, tên riêng, tên tổ chức, viết tắt và đơn vị. Không thêm, không bớt, không đổi một chữ số nào.
2. Chỉ thêm TỐI ĐA MỘT mở đầu khuôn mẫu ở câu đầu tiên: "Trong bối cảnh không ngừng phát triển, ..." hoặc "Trong bối cảnh chuyển đổi số diễn ra mạnh mẽ, ...".
3. Cấu trúc liệt kê đối xứng: "không chỉ ... mà còn", "cả ... lẫn ...".
4. Câu đều 18-25 từ; xen TỐI ĐA MỘT câu hỏi tu từ rồi tự trả lời ("Vậy điều gì tạo nên sự khác biệt? Chính là ...").
5. Chèn từ đệm rỗng: "tính bền vững", "tính hiệu quả", "mang tính chiến lược".
6. Thêm TỐI ĐA MỘT nhận định rỗng ở cuối văn bản kiểu: "Điều này cho thấy tầm quan trọng của vấn đề là rất lớn."
7. Độ dài bắt buộc 100-135% số từ bản gốc; không thêm ý thật mới (số liệu, sự kiện) ngoài các chi tiết khuôn mẫu nêu trên.
8. Chỉ trả về văn bản đã viết lại, không giải thích, không markdown.

Văn bản gốc:
<ORIGINAL>
{text}
</ORIGINAL>""",
}

SEVERITIES: tuple[str, ...] = ("L1", "L2", "L3")


@dataclass(frozen=True)
class TeacherConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "TeacherConfig | None":
        base = (os.environ.get("TEACHER_API_BASE") or "").strip()
        model = (os.environ.get("TEACHER_MODEL") or "").strip()
        key = (os.environ.get("TEACHER_API_KEY") or os.environ.get("GROQ_API_KEY") or "").strip()
        if not base or not model or not key:
            return None
        timeout = float(os.environ.get("TEACHER_TIMEOUT_SECONDS") or 60.0)
        return cls(base_url=base.rstrip("/"), api_key=key, model=model, timeout=timeout)


def make_teacher(config: TeacherConfig):
    """Return ``callable(text, severity=...) -> str`` for the configured endpoint."""
    # Đếm 429 LIÊN TIẾP xuyên suốt các call: free tier hết quota ngày thì mọi
    # call đều 429 — không dừng thì batch chậm rì rì retry từng chunk trong
    # nhiều giờ mà không được gì. Vượt ngưỡng → ném QUOTA_EXHAUSTED để
    # prepare_dataset dừng ĐÚNG CÁCH và ghi dataset với phần đã có.
    consecutive_429 = [0]
    max_429 = int(os.environ.get("TEACHER_MAX_429") or 6)

    def call(text: str, severity: str = "L2") -> str:
        template = AI_STYLE_TEACHER_PROMPTS.get(severity)
        if template is None:
            raise ValueError(f"severity không hợp lệ: {severity} (chọn trong {SEVERITIES})")
        # TEACHER_EXTRA_JSON: tham số body bổ sung tuỳ model — ví dụ với
        # qwen/qwen3.8-27b đặt {"reasoning_effort": "none"} để tắt thinking
        # (thinking mode làm model "sửa văn" thay vì làm bẩn văn theo yêu cầu).
        try:
            extra_body = json.loads(os.environ.get("TEACHER_EXTRA_JSON") or "{}")
        except json.JSONDecodeError:
            extra_body = {}
        payload = json.dumps(
            {
                "model": config.model,
                "temperature": 0.4,
                **extra_body,
                "messages": [
                    {
                        "role": "user",
                        "content": template.format(text=text),
                    }
                ],
            }
        ).encode("utf-8")
        # Retry với backoff: một batch lớn chạy qua free tier sẽ gặp 429/5xx;
        # không retry thì cả batch chết giữa chừng và phải gọi lại từ đầu.
        last_exc: Exception | None = None
        for attempt in range(4):
            if attempt:
                time.sleep(min(2**attempt, 8) + random.random())
            try:
                request = urllib.request.Request(
                    f"{config.base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {config.api_key}",
                        # Cloudflare trước Groq chặn UA mặc định của urllib —
                        # thiếu dòng này mọi request đều 403 error 1010.
                        "User-Agent": USER_AGENT,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=config.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                content = (body.get("choices") or [{}])[0].get("message", {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("teacher trả về nội dung rỗng")
                consecutive_429[0] = 0
                return content.strip()
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    consecutive_429[0] += 1
                    if consecutive_429[0] >= max_429:
                        raise RuntimeError(
                            f"QUOTA_EXHAUSTED:{consecutive_429[0]} lần 429 liên tiếp — "
                            "dừng batch (cache đã lưu), chạy lại sau khi quota reset"
                        ) from exc
                    # 429 của Groq là nhịp throttle TPM (cửa sổ ~60s), không
                    # phải lỗi chết. Chờ Retry-After nếu server báo, ngược lại
                    # đón cửa sổ kế tiếp — backoff ngắn 2-8s chỉ khiến mọi
                    # retry rơi đúng cửa sổ đã cạn và abort oan cả batch.
                    retry_after = None
                    if exc.headers is not None:
                        try:
                            retry_after = float(exc.headers.get("retry-after") or 0)
                        except (TypeError, ValueError):
                            retry_after = None
                    time.sleep(retry_after if retry_after else min(12 * (attempt + 1), 65))
                else:
                    consecutive_429[0] = 0
                last_exc = exc
                if exc.code not in (429, 500, 502, 503, 504):
                    raise
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                last_exc = exc
        assert last_exc is not None
        raise last_exc

    return call


def dirty_with_teacher(text: str, teacher, severity: str = "L2") -> str:
    if teacher is None:
        raise ValueError("dirty_with_teacher cần một teacher callable")
    return teacher(text, severity=severity).strip()


# --------------------------------------------------------------------------
# Acceptance rules + measurement.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Pair:
    """One trainable sample: AI-flavoured input, human-written target."""

    user_text: str
    assistant_text: str
    doc_id: str
    register: str = "unknown"
    generator: str = "rule"  # rule | llm — để manifest phân tích giọng generator
    severity: str = ""       # L1/L2/L3 khi generator="llm"


@dataclass(frozen=True)
class Rejection:
    """Why a candidate pair was thrown away (kept for the audit manifest)."""

    doc_id: str
    reason: str
    detail: str = ""


def word_ngram_overlap(a: str, b: str, n: int = 5) -> float:
    """Jaccard similarity of word n-gram sets (0 = nothing shared, 1 = identical)."""

    def grams(text: str) -> set[tuple[str, ...]]:
        words = re.findall(r"[\wÀ-ỹĐđ]+", text.casefold(), flags=re.UNICODE)
        if len(words) < n:
            return {tuple(words)} if words else set()
        return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}

    left, right = grams(a), grams(b)
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def longest_common_substring_ratio(a: str, b: str) -> float:
    """Share of the shorter text covered by its longest common substring.

    Dùng ``difflib.SequenceMatcher`` (C-backed) thay cho DP O(n*m) thuần Python:
    trên đoạn 400 từ (~2.500 ký tự) DP mất vài giây/cặp, difflib mất vài ms —
    khác biệt sống còn khi chấm hàng nghìn cặp. Kết quả trùng DP cho mọi cặp
    không có autojunk (đã tắt).
    """
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if not short:
        return 0.0
    matcher = difflib.SequenceMatcher(None, long_, short, autojunk=False)
    best = matcher.find_longest_match(0, len(long_), 0, len(short)).size
    return round(best / len(short), 4)


def length_ratio(ai_text: str, human_text: str) -> float:
    human_words = len(human_text.split())
    if not human_words:
        return 0.0
    return round(len(ai_text.split()) / human_words, 3)


def sentence_length_std(text: str) -> float:
    """Độ lệch chuẩn độ dài câu — proxy burstiness (văn AI đều hơn người)."""
    sentences = [
        part
        for part in _SENTENCE_SPLIT_RE.split(re.sub(r"\s+", " ", text.strip()))
        if part.strip()
    ]
    lengths = [len(part.split()) for part in sentences]
    if len(lengths) < 2:
        return 0.0
    mean = sum(lengths) / len(lengths)
    return round((sum((x - mean) ** 2 for x in lengths) / len(lengths)) ** 0.5, 3)


def connector_hits(text: str) -> int:
    """Occurrences of generic AI tells — independent of lint thresholds."""
    lowered = text.casefold()
    phrases = AI_CONNECTORS + TEMPLATE_OPENERS
    return sum(lowered.count(phrase.casefold()) for phrase in phrases)


def check_pair(
    ai_text: str,
    human_text: str,
    *,
    length_ratio_bounds: tuple[float, float] = (0.85, 1.45),
    min_ai_hits: int = 1,
    lint_fn=None,
    require_lint_hit: bool = False,
    max_5gram_overlap: float | None = None,
    max_lcs: float | None = None,
) -> str | None:
    """Return a rejection reason, or ``None`` when the pair is trainable."""
    if not ai_text.strip() or not human_text.strip():
        return "empty_side"
    if ai_text.strip() == human_text.strip():
        return "identical"

    if fact_tokens(ai_text) != fact_tokens(human_text):
        lost = fact_tokens(human_text) - fact_tokens(ai_text)
        added = fact_tokens(ai_text) - fact_tokens(human_text)
        return f"fact_drift:lost={dict(lost)}:added={dict(added)}"

    ratio = length_ratio(ai_text, human_text)
    low, high = length_ratio_bounds
    if ratio and not (low <= ratio <= high):
        return f"length_ratio:{ratio}"

    # Gate chống "vẹt" — chỉ bật cho input do teacher LLM sinh. Engine rule là
    # insert-only nên overlap cao theo thiết kế và vẫn hợp lệ.
    if max_5gram_overlap is not None:
        overlap5 = word_ngram_overlap(ai_text, human_text, 5)
        if overlap5 > max_5gram_overlap:
            return f"reuse_5gram:{overlap5}"
    if max_lcs is not None:
        lcs = longest_common_substring_ratio(ai_text, human_text)
        if lcs > max_lcs:
            return f"reuse_lcs:{lcs}"

    hits = connector_hits(ai_text)
    if hits < min_ai_hits:
        return f"not_ai_flavoured:hits={hits}"
    if require_lint_hit and lint_fn is not None and not lint_fn(ai_text):
        return "not_ai_flavoured:linter_silent"

    return None


def split_by_document(pairs: list, train_ratio: float, seed: int = 42) -> tuple[list, list]:
    """Split whole documents so chunks of one source never straddle the split."""
    doc_ids = sorted({pair.doc_id for pair in pairs})
    rng = random.Random(seed)
    rng.shuffle(doc_ids)
    if len(doc_ids) == 1:
        return pairs, []
    val_docs = min(len(doc_ids) - 1, max(1, round(len(doc_ids) * (1 - train_ratio))))
    val_set = set(doc_ids[:val_docs])
    train = [pair for pair in pairs if pair.doc_id not in val_set]
    val = [pair for pair in pairs if pair.doc_id in val_set]
    return train, val


def pair_manifest(pairs: list, rejections: list, extra: dict | None = None) -> dict:
    """Auditable summary written next to the JSONL splits."""
    by_register: dict[str, int] = {}
    by_generator: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for pair in pairs:
        by_register[pair.register] = by_register.get(pair.register, 0) + 1
        by_generator[pair.generator] = by_generator.get(pair.generator, 0) + 1
        if pair.severity:
            by_severity[pair.severity] = by_severity.get(pair.severity, 0) + 1
    reasons: dict[str, int] = {}
    for rejection in rejections:
        key = rejection.reason.split(":", 1)[0]
        reasons[key] = reasons.get(key, 0) + 1
    manifest = {
        "pairs": len(pairs),
        "rejected": len(rejections),
        "documents": len({pair.doc_id for pair in pairs}),
        "by_register": dict(sorted(by_register.items())),
        "by_generator": dict(sorted(by_generator.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "rejection_reasons": dict(sorted(reasons.items())),
    }
    if extra:
        manifest.update(extra)
    return manifest
