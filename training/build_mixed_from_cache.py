# -*- coding: utf-8 -*-
"""Build dataset mixed cuối cùng từ rule engine + cache teacher (0 call API).

Batch teacher có thể bị quota cắt giữa chừng — nhưng mọi call thành công đều
nằm trong ``teacher_cache.jsonl``. Script này dựng dataset hoàn chỉnh:

  * MỌI chunk của corpus staged → biến thể rule (L1) như ``--dirtying rule``.
  * Chunk nào có output teacher trong cache (đúng severity theo chu kỳ
    ``teacher_severities``) → thêm biến thể LLM tương ứng.

Kết quả: dataset lớn hơn và đa dạng generator hơn v0, không phụ thuộc việc
teacher đã chạy được bao xa. Chạy lại sau khi teacher tích thêm cache để
nâng độ phủ L2/L3.

Usage:
  python training/build_mixed_from_cache.py
  python training/build_mixed_from_cache.py --source training/data/raw_staged --out-dir training/data/sft
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from pair_synthesis import (  # noqa: E402
    Pair,
    Rejection,
    check_pair,
    dirty_rule_based,
    pair_manifest,
    split_by_document,
    word_ngram_overlap,
)
from prepare_dataset import (  # noqa: E402
    _lint_fn,
    _write_pair_split,
    chunk_document,
    clean_text,
    infer_register,
    load_config,
    normalize_for_dedupe,
    read_documents,
)


def load_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.is_file():
        print(f"[warn] không có cache teacher: {path} — dataset sẽ chỉ có cặp rule")
        return cache
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            key, ai = row.get("key"), row.get("ai")
            if isinstance(key, str) and isinstance(ai, str) and ai.strip():
                cache[key] = ai
    print(f"[info] cache teacher: {len(cache)} output khả dụng")
    return cache


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=None)
    parser.add_argument("--out-dir", default="training/data/sft")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = load_config()
    ds = cfg["dataset"]
    syn = cfg.get("synthesize", {}) or {}
    if args.source:
        ds["source_paths"] = list(args.source)
    severities = [str(s) for s in (syn.get("teacher_severities") or ["L2"])]
    bounds = tuple(syn.get("length_ratio", (0.85, 1.45)))
    min_ai_hits = int(syn.get("min_ai_hits", 1))
    per_doc_max_pairs = int(syn.get("per_doc_max_pairs", 3))
    llm_gates: dict = {}
    if syn.get("llm_max_5gram_overlap") is not None:
        llm_gates["max_5gram_overlap"] = float(syn["llm_max_5gram_overlap"])
    if syn.get("llm_max_lcs") is not None:
        llm_gates["max_lcs"] = float(syn["llm_max_lcs"])

    cache = load_cache(ROOT / "training" / "data" / "sft" / "teacher_cache.jsonl")
    lint_fn = _lint_fn()
    if lint_fn is None:
        print("[warn] không import được lint_text — bỏ qua filter chất lượng gold")
    rng = random.Random(args.seed)
    max_gold_errors_per_100 = float(syn.get("max_gold_errors_per_100_words", 1.0))

    pairs: list[Pair] = []
    rejections: list[Rejection] = []
    cache_hits = 0
    teacher_attempts = 0

    for doc_index, (doc_id, doc_text) in enumerate(
        read_documents(ds["source_paths"], ds["text_column"], ds.get("limit"))
    ):
        if doc_index and doc_index % 200 == 0:
            print(
                f"  [progress {doc_index} docs] pairs={len(pairs)} "
                f"(llm={sum(1 for p in pairs if p.generator == 'llm')})",
                flush=True,
            )
        cleaned = clean_text(doc_text)
        chunks = chunk_document(cleaned, ds["min_words"], ds["max_words"])
        if per_doc_max_pairs:
            chunks = chunks[:per_doc_max_pairs]
        register = infer_register(doc_id, syn.get("register"))

        for position, human in enumerate(chunks):
            tag = f"{doc_id}|{position}"
            if lint_fn is not None:
                errors = sum(
                    1
                    for issue in lint_fn(human)
                    if isinstance(issue, dict) and issue.get("finding_type") == "error"
                )
                rate = errors * 100 / max(len(human.split()), 1)
                if rate > max_gold_errors_per_100:
                    rejections.append(Rejection(tag, "gold_noisy", f"errors_per_100w={rate:.2f}"))
                    continue

            # 1) Biến thể LLM từ cache (severity theo đúng chu kỳ batch teacher).
            severity = severities[position % len(severities)]
            key = hashlib.sha1(f"{severity}|{human}".encode("utf-8")).hexdigest()
            cached_ai = cache.get(key)
            if cached_ai:
                teacher_attempts += 1
                reason = check_pair(
                    cached_ai,
                    human,
                    length_ratio_bounds=bounds,
                    min_ai_hits=min_ai_hits,
                    lint_fn=lint_fn,
                    require_lint_hit=bool(syn.get("require_lint_hit", False)),
                    **llm_gates,
                )
                if reason:
                    rejections.append(Rejection(tag, reason))
                else:
                    cache_hits += 1
                    pairs.append(Pair(cached_ai, human, doc_id, register, generator="llm", severity=severity))

            # 2) Biến thể rule (L1) — luôn sinh, offline, deterministic.
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

    # Dedupe gold trùng lặp (giống prepare_dataset).
    seen: set[str] = set()
    kept: list[Pair] = []
    for pair in pairs:
        key = hashlib.sha1(normalize_for_dedupe(pair.assistant_text).encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        kept.append(pair)
    dropped = len(pairs) - len(kept)
    pairs = kept
    print(f"[info] trùng lặp bỏ đi: {dropped}, còn {len(pairs)}")

    if not pairs:
        sys.exit("[error] không tạo được cặp nào — kiểm tra corpus/cache.")

    out_dir = ROOT / args.out_dir
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
                f"[warn] dataset mới ({len(pairs)} cặp) nhỏ hơn bản hiện có "
                f"({existing_pairs}) quá nhiều — ghi vào {out_dir.as_posix()}."
            )

    train, val = split_by_document(pairs, ds["train_ratio"], seed=args.seed)
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
            "mode": "mixed-from-cache",
            "train_pairs": len(train),
            "val_pairs": len(val),
            "cache_hits": cache_hits,
            "cache_attempts": teacher_attempts,
            "cache_coverage": round(cache_hits / teacher_attempts, 4) if teacher_attempts else 0.0,
            "mean_pair_5gram_overlap": overlap,
            "rejections_sample": [r.__dict__ for r in rejections[:20]],
        },
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: manifest[k] for k in ("pairs", "by_register", "by_generator", "by_severity", "cache_coverage")}, ensure_ascii=False, indent=2))
    print(f"[done] dataset mixed: {out_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
