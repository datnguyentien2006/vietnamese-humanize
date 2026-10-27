# -*- coding: utf-8 -*-
"""Prepare the SFT dataset for the Vietnamese humanizer fine-tune.

Builds chat-format JSONL samples from human-written Vietnamese text.

Two modes:
  * continuation (default): for each document, sample pairs are formed as
    "user gives one chunk, assistant writes the following chunk". The
    assistant responses are real human Vietnamese prose, so the model is
    trained toward natural human style instead of memorizing a copy task.
  * pairs: reads a curated JSONL file of {"input": ..., "output": ...}
    rewrite pairs (for example from manual edits). Use this once you have
    enough pairs; it teaches the actual rewrite task.

Usage:
  python training/prepare_dataset.py
  python training/prepare_dataset.py --source path/to/corpus.txt --limit 20000
  python training/prepare_dataset.py --mode pairs

Output:
  training/data/sft/train.jsonl
  training/data/sft/val.jsonl
Each line: {"messages": [{"role": "system", ...}, {"role": "user", ...},
{"role": "assistant", ...}]}
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from pair_synthesis import (  # noqa: E402
    Pair,
    Rejection,
    check_pair,
    dirty_rule_based,
    dirty_with_teacher,
    pair_manifest,
    split_by_document,
    word_ngram_overlap,
)
from task_prompts import SYSTEM_PROMPT, build_user_prompt  # noqa: E402

WS_RE = re.compile(r"[ \t]+")
BLANK_RE = re.compile(r"\n{3,}")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
URL_RE = re.compile(r"https?://\S+")
HEADING_RE = re.compile(r"^#{1,6}[ \t]+.*$", re.MULTILINE)
CATEGORY_LINE_RE = re.compile(r"^(Thể loại|Category):.*$", re.MULTILINE)
# Old scans put a space before punctuation ("nay ,"). Normalise so the model
# never learns it; it is a typographic habit, not a prose feature.
SPACE_BEFORE_PUNCT_RE = re.compile(r"[ \t]+([,.!?;:])")


def load_config() -> dict:
    with (ROOT / "training" / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sync_to_config(args: argparse.Namespace, cfg: dict) -> dict:
    ds = cfg["dataset"]
    if args.source:
        ds["source_paths"] = [str(p) for p in args.source]
    if args.mode:
        ds["mode"] = args.mode
    if getattr(args, "dirtying", None):
        cfg.setdefault("synthesize", {})["dirtying"] = args.dirtying
    if args.pairs_file:
        ds["pairs_file"] = str(args.pairs_file)
    if args.limit:
        ds["limit"] = args.limit
    return cfg


def iter_source_files(paths: list[str]) -> Iterable[Path]:
    for raw in paths:
        base = Path(raw)
        if base.is_file():
            yield base
        elif base.is_dir():
            yield from sorted(
                p
                for p in base.rglob("*")
                if p.is_file() and p.name not in {"sources.jsonl", "state.json"}
            )
        else:
            print(f"[skip] not found: {base}")


def read_text_file(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    # BOM sniff: corpus đời đầu (VNTC, file Word export) thường là UTF-16;
    # decode cưỡng bức UTF-8 sẽ giữ lại dãy \x00 xen kẽ mỗi ký tự — model nhìn
    # thấy "văn bản rỗng" và trả lời bừa. Đọc bytes và tự nhận diện BOM.
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="ignore")


def read_documents(
    paths: list[str], text_column: str, limit: int | None
) -> Iterable[tuple[str, str]]:
    """Yield ``(doc_id, text)`` from .txt/.txt.gz, .jsonl or .parquet rows.

    The doc id groups every chunk of one source document, which is what keeps
    the validation split free of adjacent-paragraph leakage.
    """
    count = 0
    for path in iter_source_files(paths):
        if limit and count >= limit:
            return
        suffix = path.suffix
        if suffix == ".jsonl" or path.name.endswith(".jsonl.gz"):
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8", errors="ignore") as fh:  # type: ignore[operator]
                for line in fh:
                    if limit and count >= limit:
                        return
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = row.get(text_column) or row.get("text")
                    if isinstance(text, str) and text.strip():
                        count += 1
                        yield f"{path.name}#{count}", text
        elif suffix == ".parquet":
            try:
                import pandas as pd
            except ImportError:
                print(f"[skip] pandas not installed: {path}")
                continue
            frame = pd.read_parquet(path, columns=[text_column])
            for text in frame[text_column]:
                if limit and count >= limit:
                    return
                if isinstance(text, str) and text.strip():
                    count += 1
                    yield f"{path.name}#{count}", text
        else:  # default: .txt / .txt.gz
            if suffix not in {".txt", ".gz", ".md", ".markdown"}:
                print(f"[skip] unsupported: {path}")
                continue
            text = read_text_file(path)
            if text.strip():
                count += 1
                yield path.stem, text


def clean_text(raw: str) -> str:
    text = raw.replace("\r", "\n")
    text = MD_LINK_RE.sub(r"\1", text)
    text = URL_RE.sub(" ", text)
    text = HEADING_RE.sub("", text)
    text = CATEGORY_LINE_RE.sub("", text)
    text = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = WS_RE.sub(" ", text)
    text = BLANK_RE.sub("\n\n", text)
    return text.strip()


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_document(text: str, min_words: int, max_words: int) -> list[str]:
    """Split a document into paragraph chunks inside [min_words, max_words].

    Short paragraphs are merged into the current chunk instead of being
    dropped, so a corpus of brief paragraphs still yields training data; a
    chunk that stays under ``min_words`` after merging is discarded.
    """
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if current:
            chunks.append("\n\n".join(current))
        current, current_words = [], 0

    for para in paragraphs(text):
        words = len(para.split())
        if current and current_words + words > max_words:
            flush()
        if words > max_words:
            flush()
            chunks.append(para)
            continue
        current.append(para)
        current_words += words
    flush()

    return [chunk for chunk in chunks if len(chunk.split()) >= min_words]


def normalize_for_dedupe(text: str) -> str:
    plain = re.sub(r"[^0-9a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỵỷỹđ\s]", " ", text.lower())
    return " ".join(plain.split())


def make_sample(user_text: str, assistant_text: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(user_text)},
            {"role": "assistant", "content": assistant_text.strip()},
        ]
    }


def collect_samples(cfg: dict) -> list[tuple[str, str]]:
    """Return list of (user_text, assistant_text) pairs."""
    ds = cfg["dataset"]
    limit = ds.get("limit")
    samples: list[tuple[str, str]] = []

    if ds["mode"] == "pairs":
        pairs_path = Path(ROOT / ds["pairs_file"])
        if not pairs_path.is_file():
            sys.exit(f"pairs mode cần file {pairs_path} (mỗi dòng: {{\"input\": ..., \"output\": ...}})")
        with pairs_path.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                output = clean_text(row["output"])
                if ds["min_words"] <= len(output.split()) <= ds["max_words"]:
                    samples.append((row["input"], output))
        return samples

    for _doc_id, doc_text in read_documents(ds["source_paths"], ds["text_column"], limit):
        cleaned = clean_text(doc_text)
        chunks = chunk_document(cleaned, ds["min_words"], ds["max_words"])
        for i in range(1, len(chunks)):
            # user sees the previous chunk (rewrite task prompt), assistant
            # writes the next chunk: real human continuation prose.
            samples.append((chunks[i - 1], chunks[i]))
    return samples


def _lint_fn():
    """Return ``lint_text`` if the package is importable, else ``None``."""
    try:
        from vietnamese_writing_skills.cli.lint import lint_text

        return lint_text
    except ImportError:
        src = str(ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        try:
            from vietnamese_writing_skills.cli.lint import lint_text

            return lint_text
        except ImportError:
            return None


_REGISTER_HINTS = (
    ("academic", ("academic", "hoc-thuat", "luan", "nghien-cuu", "research", "wikibooks")),
    ("literature", ("wikisource", "truyen", "tieu-thuyet", "van-hoc", "tap-but", "vanmau")),
    ("report", ("report", "bao-cao", "finance", "tai-chinh", "business")),
    ("news", ("news", "tin", "thoi-su", "baochi", "bao-chi", "wikinews")),
    ("social", ("social", "community", "cong-dong", "mang-xa-hoi")),
    ("blog", ("blog", "travel", "du-lich", "product", "san-pham", "wikivoyage")),
    ("wiki", ("wiki", "bach-khoa", "encyclopedia")),
)


def infer_register(doc_id: str, override: str | None = None) -> str:
    """Best-effort register label from the file/doc name (P2 uses it to condition)."""
    if override:
        return override
    folded = doc_id.casefold().replace("_", "-").replace(" ", "-")
    for register, hints in _REGISTER_HINTS:
        if any(hint in folded for hint in hints):
            return register
    return "unknown"


def collect_synthesized_pairs(
    cfg: dict,
    *,
    seed: int = 42,
    teacher=None,
    lint_fn=None,
) -> tuple[list[Pair], list[Rejection]]:
    """Build ``(AI-flavoured -> human)`` pairs from the human corpus.

    Human text is the gold target; the AI side is generated by dirtying. Every
    candidate is verified mechanically, so a bad teacher degrades yield instead
    of poisoning the dataset.
    """
    ds = cfg["dataset"]
    syn = cfg.get("synthesize", {}) or {}
    dirtying = syn.get("dirtying", "rule")
    max_gold_errors_per_100 = float(syn.get("max_gold_errors_per_100_words", 1.0))
    per_doc_max_pairs = syn.get("per_doc_max_pairs", 2)
    bounds = tuple(syn.get("length_ratio", (0.85, 1.35)))
    min_ai_hits = int(syn.get("min_ai_hits", 1))
    limit = ds.get("limit")
    rng = random.Random(seed)
    severities = [str(s) for s in (syn.get("teacher_severities") or ["L2"])]
    # Gate chống vẹt chỉ có nghĩa với input do teacher sinh (rule là insert-only).
    llm_gates: dict = {}
    if dirtying == "llm":
        if syn.get("llm_max_5gram_overlap") is not None:
            llm_gates["max_5gram_overlap"] = float(syn["llm_max_5gram_overlap"])
        if syn.get("llm_max_lcs") is not None:
            llm_gates["max_lcs"] = float(syn["llm_max_lcs"])
    include_rule_pairs = bool(syn.get("include_rule_pairs", True)) and dirtying == "llm"

    pairs: list[Pair] = []
    rejections: list[Rejection] = []

    for doc_index, (doc_id, doc_text) in enumerate(
        read_documents(ds["source_paths"], ds["text_column"], limit)
    ):
        # Batch teacher chạy hàng chục phút: log tiến trình để theo dõi log
        # chạy nền thay vì nhìn màn hình im lặng.
        if doc_index and doc_index % 25 == 0:
            print(
                f"  [progress {doc_index} docs] pairs={len(pairs)} rejected={len(rejections)}",
                flush=True,
            )
        cleaned = clean_text(doc_text)
        chunks = chunk_document(cleaned, ds["min_words"], ds["max_words"])
        if per_doc_max_pairs:
            chunks = chunks[: int(per_doc_max_pairs)]
        register = infer_register(doc_id, syn.get("register"))

        for position, human in enumerate(chunks):
            tag = f"{doc_id}|{position}"
            # Gold is rejected for demonstrable errors only. Heuristic findings
            # (sentence length, Hán-Việt density, connector counts) are style
            # signals calibrated for modern prose — real literature trips them
            # constantly, and filtering on them would reject every good chunk.
            if lint_fn is not None:
                errors = sum(
                    1
                    for issue in lint_fn(human)
                    if isinstance(issue, dict) and issue.get("finding_type") == "error"
                )
                rate = errors * 100 / max(len(human.split()), 1)
                if rate > max_gold_errors_per_100:
                    rejections.append(
                        Rejection(tag, "gold_noisy", f"errors_per_100w={rate:.2f}")
                    )
                    continue
            severity = severities[position % len(severities)]
            try:
                if dirtying == "llm":
                    ai_text = dirty_with_teacher(human, teacher, severity=severity)
                else:
                    ai_text = dirty_rule_based(human, rng)
            except Exception as exc:  # noqa: BLE001 - one bad doc must not kill the run
                if str(exc).startswith("QUOTA_EXHAUSTED"):
                    print(
                        f"[stop] teacher hết quota — ghi dataset với {len(pairs)} cặp đã có "
                        "(cache giữ toàn bộ call thành công, chạy lại để tiếp tục).",
                        flush=True,
                    )
                    return pairs, rejections
                rejections.append(
                    Rejection(tag, "teacher_error", f"{type(exc).__name__}: {exc}"[:200])
                )
                continue

            reason = check_pair(
                ai_text,
                human,
                length_ratio_bounds=bounds,
                min_ai_hits=min_ai_hits,
                lint_fn=lint_fn,
                require_lint_hit=bool(syn.get("require_lint_hit", False)),
                **llm_gates,
            )
            if reason:
                rejections.append(Rejection(tag, reason))
                continue
            pairs.append(
                Pair(
                    ai_text,
                    human,
                    doc_id,
                    register,
                    generator="llm" if dirtying == "llm" else "rule",
                    severity=severity if dirtying == "llm" else "",
                )
            )

            # Kèm biến thể rule (L1) cho cùng chunk khi chạy teacher: đa dạng
            # generator để dataset không mang giọng riêng của một teacher duy
            # nhất (rủi ro số 3 trong kế hoạch dataset).
            if include_rule_pairs:
                rule_ai = dirty_rule_based(human, rng)
                rule_reason = check_pair(
                    rule_ai,
                    human,
                    length_ratio_bounds=bounds,
                    min_ai_hits=min_ai_hits,
                    lint_fn=lint_fn,
                    require_lint_hit=bool(syn.get("require_lint_hit", False)),
                )
                if rule_reason:
                    rejections.append(Rejection(f"{tag}|rule", rule_reason))
                else:
                    pairs.append(Pair(rule_ai, human, doc_id, register, generator="rule"))

    return pairs, rejections


def _write_pair_split(path: Path, pairs: list[Pair]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for pair in pairs:
            fh.write(
                json.dumps(
                    make_sample(pair.user_text, pair.assistant_text), ensure_ascii=False
                )
                + "\n"
            )
    print(f"[write] {path.name}: {len(pairs)} mẫu, {path.as_posix()}")


def _cached_teacher(teacher, cache_path: Path):
    """Cache kết quả teacher theo (severity, text) vào JSONL append-only.

    Một batch teacher chạy hàng giờ: rớt giữa chừng hoặc chạm rate limit
    hằng ngày thì rerun sau phải tái sử dụng phần đã gọi, không trả giá lại.
    """
    cache: dict[str, str] = {}
    if cache_path.is_file():
        with cache_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key, ai = row.get("key"), row.get("ai")
                if isinstance(key, str) and isinstance(ai, str) and ai.strip():
                    cache[key] = ai
    hits = [0]

    def cached(text: str, severity: str = "L2") -> str:
        key = hashlib.sha1(f"{severity}|{text}".encode("utf-8")).hexdigest()
        hit = cache.get(key)
        if hit:
            hits[0] += 1
            return hit
        ai = teacher(text, severity=severity)
        cache[key] = ai
        with cache_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps({"key": key, "severity": severity, "ai": ai}, ensure_ascii=False)
                + "\n"
            )
        return ai

    cached.hits = hits  # type: ignore[attr-defined]
    return cached


def run_synthesize(cfg: dict, seed: int = 42, out_dir_arg: str | None = None) -> None:
    """``--mode synthesize``: dirtying pairs, document-level split, manifest."""
    ds = cfg["dataset"]
    syn = cfg.get("synthesize", {}) or {}
    lint_fn = _lint_fn()
    if lint_fn is None:
        print("[warn] không import được lint_text — bỏ qua filter chất lượng gold/AI")

    teacher = None
    if syn.get("dirtying", "rule") == "llm":
        from pair_synthesis import TeacherConfig, make_teacher

        config = TeacherConfig.from_env()
        if config is None:
            sys.exit(
                "dirtying=llm cần TEACHER_API_BASE, TEACHER_MODEL và TEACHER_API_KEY "
                "(hoặc GROQ_API_KEY)."
            )
        print(f"[info] teacher: {config.model} @ {config.base_url}")
        teacher = make_teacher(config)
        if syn.get("teacher_cache", True):
            cache_path = ROOT / "training" / "data" / "sft" / "teacher_cache.jsonl"
            teacher = _cached_teacher(teacher, cache_path)
            print(f"[info] teacher cache: {cache_path.as_posix()} (rerun/crash không tốn call)")

    pairs, rejections = collect_synthesized_pairs(
        cfg, seed=seed, teacher=teacher, lint_fn=lint_fn
    )

    if ds.get("dedupe", True):
        seen: set[str] = set()
        kept: list[Pair] = []
        for pair in pairs:
            key = hashlib.sha1(
                normalize_for_dedupe(pair.assistant_text).encode()
            ).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            kept.append(pair)
        print(f"[info] trùng lặp bỏ đi: {len(pairs) - len(kept)}, còn {len(kept)}")
        pairs = kept

    if not pairs:
        reasons: dict[str, int] = {}
        for rejection in rejections:
            key = rejection.reason.split(":", 1)[0]
            reasons[key] = reasons.get(key, 0) + 1
        print(json.dumps(reasons, ensure_ascii=False, indent=2))
        sys.exit(
            "[error] không tạo được cặp nào. Xem rejection_reasons để biết filter nào chặn."
        )

    # Clobber-guard: batch bị quota abort giữa chừng (hoặc chạy hỏng) có thể
    # chỉ còn vài cặp — KHÔNG được phép ghi đè dataset lớn hơn đang nằm trong
    # data/sft. Ghi sang sft_partial/ để so sánh thủ công, giữ nguyên bản tốt.
    # --out-dir cho phép ghi vào thư mục riêng (vd data/sft_v2) khi thử nghiệm.
    out_dir = ROOT / (out_dir_arg or "training/data/sft")
    existing_manifest = out_dir / "manifest.json"
    if existing_manifest.is_file():
        try:
            existing_pairs = int(
                json.loads(existing_manifest.read_text(encoding="utf-8")).get("pairs", 0)
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            existing_pairs = 0
        if existing_pairs > len(pairs) * 2 and existing_pairs > 50:
            out_dir = ROOT / "training" / "data" / "sft_partial"
            print(
                f"[warn] batch này chỉ có {len(pairs)} cặp < {existing_pairs} cặp hiện có "
                f"— ghi vào {out_dir.as_posix()} thay vì ghi đè data/sft.",
                flush=True,
            )

    train, val = split_by_document(pairs, ds["train_ratio"], seed=seed)
    _write_pair_split(out_dir / "train.jsonl", train)
    _write_pair_split(out_dir / "val.jsonl", val)

    overlap = (
        round(sum(word_ngram_overlap(p.user_text, p.assistant_text) for p in pairs) / len(pairs), 4)
        if pairs
        else 0.0
    )
    manifest = pair_manifest(
        pairs,
        rejections,
        extra={
            "mode": "synthesize",
            "dirtying": syn.get("dirtying", "rule"),
            "train_pairs": len(train),
            "val_pairs": len(val),
            "mean_pair_5gram_overlap": overlap,
            "rejections_sample": [asdict(r) for r in rejections[:20]],
        },
    )
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2)[:1200])
    print(f"[done] manifest: {manifest_path.as_posix()}")


def write_split(path: Path, samples: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for user_text, assistant_text in samples:
            fh.write(json.dumps(make_sample(user_text, assistant_text), ensure_ascii=False) + "\n")
    print(f"[write] {path.name}: {len(samples)} mẫu, {path.as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", help="her/gói file hoặc thư mục dữ liệu (có thể lặp lại)")
    parser.add_argument("--mode", choices=["continuation", "pairs", "synthesize"])
    parser.add_argument("--pairs-file")
    parser.add_argument("--limit", type=int, help="giới hạn số văn bản đọc từ nguồn")
    parser.add_argument(
        "--out-dir",
        default="training/data/sft",
        help="thư mục ghi train/val/manifest (mặc định data/sft; dùng thư mục riêng khi thử nghiệm)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dirtying",
        choices=["rule", "llm"],
        help="ghi đè synthesize.dirtying (rule = offline 0 đồng, llm = teacher endpoint)",
    )
    args = parser.parse_args()

    cfg = sync_to_config(args, load_config())
    ds = cfg["dataset"]

    if ds["mode"] == "synthesize":
        run_synthesize(cfg, seed=args.seed, out_dir_arg=args.out_dir)
        return

    samples = collect_samples(cfg)
    print(f"[info] đội mẫu sau lọc: {len(samples)}")

    seen: set[str] = set()
    if ds["dedupe"]:
        kept: list[tuple[str, str]] = []
        for user_text, assistant_text in samples:
            key = hashlib.sha1(normalize_for_dedupe(assistant_text).encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                kept.append((user_text, assistant_text))
        dropped = len(samples) - len(kept)
        samples = kept
        print(f"[info] trùng lặp bỏ đi: {dropped}, còn {len(samples)}")

    samples.sort(key=lambda s: len(s[1]), reverse=True)
    val_size = max(1, int(len(samples) * (1 - ds["train_ratio"])))
    val, train = samples[:val_size], samples[val_size:]

    write_split(ROOT / "training" / "data" / "sft" / "train.jsonl", train)
    write_split(ROOT / "training" / "data" / "sft" / "val.jsonl", val)
    print("[done] Tập SFT đã sẵn sàng trong training/data/sft/")


if __name__ == "__main__":
    main()
