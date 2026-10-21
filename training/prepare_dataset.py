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
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from task_prompts import SYSTEM_PROMPT, build_user_prompt  # noqa: E402

WS_RE = re.compile(r"[ \t]+")
BLANK_RE = re.compile(r"\n{3,}")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
URL_RE = re.compile(r"https?://\S+")
HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def load_config() -> dict:
    with (ROOT / "training" / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sync_to_config(args: argparse.Namespace, cfg: dict) -> dict:
    ds = cfg["dataset"]
    if args.source:
        ds["source_paths"] = [str(p) for p in args.source]
    if args.mode:
        ds["mode"] = args.mode
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
            yield from sorted(p for p in base.rglob("*") if p.is_file())
        else:
            print(f"[skip] not found: {base}")


def read_text_file(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="ignore")


def read_documents(paths: list[str], text_column: str, limit: int | None) -> Iterable[str]:
    """Yield document texts, from .txt/.txt.gz (whole file), .jsonl or .parquet rows."""
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
                        yield text
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
                    yield text
        else:  # default: .txt / .txt.gz
            if suffix not in {".txt", ".gz"}:
                print(f"[skip] unsupported: {path}")
                continue
            text = read_text_file(path)
            if text.strip():
                count += 1
                yield text


def clean_text(raw: str) -> str:
    text = raw.replace("\r", "\n")
    text = MD_LINK_RE.sub(r"\1", text)
    text = URL_RE.sub(" ", text)
    text = HEADING_RE.sub("", text)
    text = WS_RE.sub(" ", text)
    text = BLANK_RE.sub("\n\n", text)
    return text.strip()


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_document(text: str, min_words: int, max_words: int) -> list[str]:
    """Split a document into paragraph chunks inside [min_words, max_words]."""
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for para in paragraphs(text):
        words = len(para.split())
        if words < min_words:
            continue
        if current_words + words > max_words and current:
            chunks.append("\n\n".join(current))
            current, current_words = [], 0
        current.append(para)
        current_words += words
    if current:
        chunks.append("\n\n".join(current))
    return chunks


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

    for doc_text in read_documents(ds["source_paths"], ds["text_column"], limit):
        cleaned = clean_text(doc_text)
        chunks = chunk_document(cleaned, ds["min_words"], ds["max_words"])
        for i in range(1, len(chunks)):
            # user sees the previous chunk (rewrite task prompt), assistant
            # writes the next chunk: real human continuation prose.
            samples.append((chunks[i - 1], chunks[i]))
    return samples


def write_split(path: Path, samples: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for user_text, assistant_text in samples:
            fh.write(json.dumps(make_sample(user_text, assistant_text), ensure_ascii=False) + "\n")
    print(f"[write] {path.name}: {len(samples)} mẫu, {path.as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", help="her/gói file hoặc thư mục dữ liệu (có thể lặp lại)")
    parser.add_argument("--mode", choices=["continuation", "pairs"])
    parser.add_argument("--pairs-file")
    parser.add_argument("--limit", type=int, help="giới hạn số văn bản đọc từ nguồn")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = sync_to_config(args, load_config())
    ds = cfg["dataset"]

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
