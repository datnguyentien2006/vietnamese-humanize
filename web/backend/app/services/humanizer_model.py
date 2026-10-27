"""Client cho mô hình humanizer chuyên biệt (Ollama/vLLM, tương thích OpenAI).

Phase 0 (28/10/2026) — ba nâng cấp không cần train lại:

1. **Chia văn bản dài**: context của model là 4096 token; văn bản dài hơn bị
   cắt cụt và mất ý. Văn bản > ~650 từ được chia theo ranh giới đoạn/câu, gọi
   model từng phần rồi ghép — fact guard chạy trên TOÀN văn bản sau khi ghép.
2. **Chặn chèn tiêu đề**: model đôi khi mở đầu bằng một "dòng tiêu đề" ngắn
   (học lẫn từ chunk wiki/báo trong dataset). Dòng đó bị bóc nếu bản gốc không
   có dòng tương tự.
3. **Chặn nén quá tay**: nếu bản viết lại ngắn hơn 70% số từ bản gốc thì coi
   như lượt hỏng (mất ý) và thử lại với temperature cao hơn.

Prompt vẫn giữ nguyên bản frozen (lock bởi tests/test_humanizer_prompts_lock.py)
— mọi thay đổi nằm ở hậu kỳ, không đổi nhiệm vụ model đã được huấn luyện.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.services import fact_guard
from app.services.humanizer_prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Lần đầu dùng temperature "chuẩn"; lần thử lại tăng nhẹ để mô hình rời khỏi
# vùng bước cùng một lỗi.
_TEMPERATURES = (0.5, 0.6)

# Văn bản dài hơn ngưỡng này được chia phần (context 4096 token ≈ 900 từ tiếng Việt).
_MAX_CHUNK_WORDS = 650
# Bản viết lại ngắn hơn tỉ lệ này = nén quá tay (mất ý) → thử lại.
_MIN_LENGTH_RATIO = 0.70
# Dòng đầu ngắn hơn ngưỡng này và không có dấu kết câu → nghi là tiêu đề chèn.
_TITLE_MAX_WORDS = 14

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_SENTENCE_END = re.compile(r"[.!?…:;]$")

# Nhắc thêm ở cuối user prompt (inference-time; KHÔNG đổi template frozen đã
# huấn luyện): model có xu hướng nén quá tay và chèn dòng tiêu đề.
# Đo thực tế: ratio 0.65 → 0.73, hết chèn tiêu đề, giữ thêm một ý.
_NUDGE = (
    "\n\nLưu ý: giữ đủ mọi ý và chi tiết của bản gốc; không tóm tắt, "
    "không lược bớt câu nào; không đặt tiêu đề."
)

WARN_LOST_FACTS = (
    "Cảnh báo: một số số liệu/ngày trong văn bản gốc không còn xuất hiện "
    "trong bản đã humanize. Kiểm tra lại trước khi dùng."
)
WARN_OVER_COMPRESSED = (
    "Cảnh báo: bản viết lại ngắn hơn đáng kể so với bản gốc — kiểm tra lại "
    "xem có bị bỏ ý nào không."
)
WARN_CHUNKED = (
    "Văn bản dài đã được chia thành nhiều phần để humanize, sau đó ghép lại."
)


class HumanizerNotConfiguredError(Exception):
    """HUMANIZER_API_BASE chưa được cấu hình."""


class HumanizerServerError(Exception):
    """Gọi endpoint humanizer thất bại (mạng, HTTP, phản hồi rỗng)."""

    def __init__(self, message: str, attempts: list[dict] | None = None):
        super().__init__(message)
        self.attempts: list[dict] = attempts or []


class HumanizerTimeoutError(HumanizerServerError):
    """Endpoint humanizer quá HUMANIZER_TIMEOUT_SECONDS."""


@dataclass
class ModelHumanizeResult:
    """Kết quả một lượt chạy humanizer model (có thể fail fact guard)."""

    rewrite: str
    provider: str = "humanizer-model"
    fact_check: dict[str, list[str]] = field(
        default_factory=lambda: {"lost_tokens": [], "added_tokens": []}
    )
    warnings: list[str] = field(default_factory=list)
    # attempts[] chỉ được bóc ra cho client khi DEBUG_ERRORS bật (router lo).
    attempts: list[dict] = field(default_factory=list)
    guard_ok: bool = True


# ---------------------------------------------------------------------------
# Tiền/hậu xử lý văn bản
# ---------------------------------------------------------------------------


def _looks_like_heading(line: str) -> bool:
    """Dòng ngắn, không có dấu kết câu → giống tiêu đề/mục hơn là câu văn."""
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped.split()) > _TITLE_MAX_WORDS:
        return False
    return _SENTENCE_END.search(stripped) is None


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _strip_spurious_heading(rewrite: str, original: str) -> str:
    """Bóc dòng tiêu đề model tự chèn (chỉ khi bản gốc không có dòng như vậy)."""
    lines = rewrite.strip().splitlines()
    if len(lines) < 2:
        return rewrite.strip()
    if not _looks_like_heading(lines[0]):
        return rewrite.strip()
    if _looks_like_heading(_first_line(original)):
        return rewrite.strip()
    rest = "\n".join(lines[1:]).lstrip("\n")
    if not rest.strip():
        return rewrite.strip()
    # Chỉ bóc khi phần thân thật sự có câu văn (tránh bóc nhầm khi model chỉ
    # trả về đúng một dòng ngắn).
    if len(rest.split()) < 12:
        return rewrite.strip()
    logger.info("Bóc dòng tiêu đề model chèn: %r", lines[0].strip()[:60])
    return rest.strip()


def _split_into_chunks(text: str, max_words: int = _MAX_CHUNK_WORDS) -> list[str]:
    """Chia văn bản theo đoạn, giữ nguyên thứ tự và ranh giới câu.

    Đoạn nào dài hơn ``max_words`` được cắt tiếp theo câu để không vượt context
    của model (4096 token) — cắt giữa câu là nguyên nhân mất ý.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        words = len(paragraph.split())
        if words <= max_words:
            units.append(paragraph)
            continue
        current: list[str] = []
        current_words = 0
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            count = len(sentence.split())
            if current and current_words + count > max_words:
                units.append(" ".join(current))
                current, current_words = [], 0
            current.append(sentence)
            current_words += count
        if current:
            units.append(" ".join(current))

    chunks: list[str] = []
    buffer: list[str] = []
    buffer_words = 0
    for unit in units:
        count = len(unit.split())
        if buffer and buffer_words + count > max_words:
            chunks.append("\n\n".join(buffer))
            buffer, buffer_words = [], 0
        buffer.append(unit)
        buffer_words += count
    if buffer:
        chunks.append("\n\n".join(buffer))
    return chunks or [text]


def _request_payload(text: str, temperature: float) -> dict:
    return {
        "model": settings.HUMANIZER_MODEL,
        "temperature": temperature,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(text) + _NUDGE},
        ],
    }


def _extract_content(data: dict) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def _length_ratio(rewrite: str, original: str) -> float:
    original_words = len(original.split())
    if not original_words:
        return 1.0
    return len(rewrite.split()) / original_words


def _call_piece(
    url: str,
    headers: dict[str, str],
    piece: str,
    attempts: list[dict],
    label: str,
    chunk_index: int | None = None,
) -> tuple[str | None, bool]:
    """Gọi model cho MỘT phần văn bản, trả (bản tốt nhất, guard_ok)."""
    best: str | None = None
    best_ok = False
    for attempt_index, temperature in enumerate(_TEMPERATURES, start=1):
        started = time.monotonic()
        payload = _request_payload(piece, temperature)
        try:
            with httpx.Client(timeout=settings.HUMANIZER_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "timeout",
                    "detail": str(exc)[:300],
                    "latency_seconds": round(time.monotonic() - started, 2),
                    "piece": label,
                }
            )
            raise HumanizerTimeoutError(
                f"Humanizer endpoint vượt {settings.HUMANIZER_TIMEOUT_SECONDS:g}s timeout.",
                attempts=attempts,
            ) from exc
        except httpx.HTTPError as exc:
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "network_error",
                    "detail": str(exc)[:300],
                    "piece": label,
                }
            )
            raise HumanizerServerError(
                "Không kết nối được humanizer endpoint.", attempts=attempts
            ) from exc

        if response.status_code in (401, 403):
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "auth_error",
                    "status": response.status_code,
                    "piece": label,
                }
            )
            raise HumanizerServerError(
                "Humanizer endpoint từ chối API key (HTTP "
                f"{response.status_code}). Kiểm tra HUMANIZER_API_KEY.",
                attempts=attempts,
            )
        if 400 <= response.status_code < 500:
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "http_error",
                    "status": response.status_code,
                    "detail": response.text[:200],
                    "piece": label,
                }
            )
            raise HumanizerServerError(
                f"Humanizer endpoint trả HTTP {response.status_code}.",
                attempts=attempts,
            )
        if response.status_code >= 500:
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "server_error",
                    "status": response.status_code,
                    "detail": response.text[:200],
                    "piece": label,
                }
            )
            continue

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "bad_json",
                    "detail": response.text[:200],
                    "piece": label,
                }
            )
            continue

        content = _extract_content(data)
        if content is None:
            attempts.append(
                {
                    "attempt": len(attempts) + 1,
                    "temperature": temperature,
                    "kind": "empty_response",
                    "piece": label,
                }
            )
            continue

        content = _strip_spurious_heading(content, piece)
        record = {
            "attempt": len(attempts) + 1,
            "temperature": temperature,
            "latency_seconds": round(time.monotonic() - started, 2),
            "piece": label,
        }
        if chunk_index is not None:
            record["chunk"] = chunk_index

        piece_fact = fact_guard.diff_fact_tokens(piece, content)
        ratio = _length_ratio(content, piece)
        if piece_fact["lost_tokens"]:
            record["kind"] = "fact_loss"
            record["lost_tokens"] = piece_fact["lost_tokens"]
            attempts.append(record)
            best, best_ok = content, False
            continue
        if ratio < _MIN_LENGTH_RATIO:
            record["kind"] = "over_compressed"
            record["length_ratio"] = round(ratio, 3)
            attempts.append(record)
            best, best_ok = content, False
            continue

        record["kind"] = "ok"
        attempts.append(record)
        return content, True

    return best, best_ok


def humanize_with_model(text: str) -> ModelHumanizeResult:
    """Gọi humanizer model, trả văn bản viết lại + fact guard nguyên văn."""
    base = (settings.HUMANIZER_API_BASE or "").strip().rstrip("/")
    if not base:
        raise HumanizerNotConfiguredError(
            "HUMANIZER_API_BASE chưa được cấu hình — không gọi được mô hình."
        )

    url = f"{base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = (settings.HUMANIZER_API_KEY or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    attempts: list[dict] = []
    warnings: list[str] = []
    pieces = _split_into_chunks(text)
    chunked = len(pieces) > 1

    outputs: list[str] = []
    all_ok = True
    succeeded = 0
    for index, piece in enumerate(pieces, start=1):
        label = f"{index}/{len(pieces)}" if chunked else "whole"
        content, ok = _call_piece(
            url, headers, piece, attempts, label, chunk_index=index if chunked else None
        )
        all_ok = all_ok and ok and content is not None
        if content is None:
            outputs.append(piece)  # giữ nguyên phần không xử lý được
        else:
            succeeded += 1
            outputs.append(content)

    # Không phần nào xử lý được → coi như endpoint hỏng (hành vi cũ: raise).
    if succeeded == 0:
        raise HumanizerServerError(
            "Humanizer endpoint không trả được văn bản nào. "
            "Thử lại sau hoặc kiểm tra endpoint.",
            attempts=attempts,
        )

    rewrite = "\n\n".join(part.strip() for part in outputs if part.strip()).strip()
    if not rewrite:
        raise HumanizerServerError(
            "Humanizer endpoint không trả được văn bản nào. "
            "Thử lại sau hoặc kiểm tra endpoint.",
            attempts=attempts,
        )

    if chunked:
        warnings.append(WARN_CHUNKED)

    fact_check = fact_guard.diff_fact_tokens(text, rewrite)
    guard_ok = all_ok and not fact_check["lost_tokens"]
    if fact_check["lost_tokens"]:
        warnings.append(WARN_LOST_FACTS)
    elif not all_ok:
        warnings.append(WARN_OVER_COMPRESSED)

    return ModelHumanizeResult(
        rewrite=rewrite,
        fact_check=fact_check,
        warnings=warnings,
        attempts=attempts,
        guard_ok=guard_ok,
    )
