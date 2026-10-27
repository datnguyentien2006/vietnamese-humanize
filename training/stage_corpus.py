# -*- coding: utf-8 -*-
"""Lấy mẫu cân bằng từ các nguồn corpus vào thư mục staging cho batch teacher.

``raw/`` có thể chứa hàng nghìn tài liệu Wikisource — chạy dirtying trên toàn
bộ sẽ vượt rate limit hằng ngày của teacher endpoint. Script chọn ngẫu nhiên
(seed cố định) tối đa ``--per-source`` tài liệu mỗi nguồn vào
``training/data/raw_staged/`` để batch teacher có tỉ lệ register cân bằng và
số call teacher kiểm soát được.

Nguồn mặc định (đổi bằng --sources):
  news_vntc  — training/data/raw/news_vntc/   (register news)
  wiki_vi    — training/data/raw/wiki_vi/     (register wiki)
  own        — training/data/raw/own/         (văn của bạn, khi có)
  WIKISOURCE — file wikisource_*.txt ngay trong training/data/raw/

File đã staged trước đó được giữ nguyên (không copy đè), nên rerun với
--per-source lớn hơn chỉ mở rộng thêm. Batch synthesize phải chạy với
``--source training/data/raw_staged`` để chỉ dùng các tài liệu đã chọn.

Usage:
  python training/stage_corpus.py --per-source 150
  python training/stage_corpus.py --per-source 300 --sources news_vntc wiki_vi WIKISOURCE
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "training" / "data" / "raw"
STAGED = ROOT / "training" / "data" / "raw_staged"


def docs_in_folder(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.txt") if p.is_file())


def docs_wikisource() -> list[Path]:
    if not RAW.is_dir():
        return []
    return sorted(p for p in RAW.glob("wikisource_*.txt") if p.is_file())


def resolve_source(name: str) -> tuple[str, Path | None, list[Path]]:
    if name == "WIKISOURCE":
        return "WIKISOURCE", None, docs_wikisource()
    folder = RAW / name
    return name, folder, docs_in_folder(folder)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        nargs="*",
        default=["news_vntc", "wiki_vi", "own", "WIKISOURCE"],
        help="tên thư mục con của raw/ (hoặc WIKISOURCE); bỏ nguồn không tồn tại",
    )
    parser.add_argument("--per-source", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    STAGED.mkdir(parents=True, exist_ok=True)
    staged_before = {p.name for p in STAGED.glob("*.txt")}
    summary: dict[str, dict] = {}
    rng = random.Random(args.seed)

    for name in args.sources:
        label, _folder, docs = resolve_source(name)
        if not docs:
            summary[label] = {"available": 0, "staged_now": 0, "note": "nguồn trống hoặc chưa có"}
            continue
        picked = rng.sample(docs, min(args.per_source, len(docs)))
        copied = 0
        for doc in picked:
            target = STAGED / doc.name
            if doc.name in staged_before:
                continue
            shutil.copy2(doc, target)
            staged_before.add(doc.name)
            copied += 1
        summary[label] = {
            "available": len(docs),
            "picked": len(picked),
            "staged_now": copied,
            "staged_total_in_dir": len(list(STAGED.glob("*.txt"))),
        }

    manifest = {
        "staged_dir": STAGED.as_posix(),
        "seed": args.seed,
        "per_source": args.per_source,
        "updated_at": datetime.now(UTC).isoformat(),
        "sources": summary,
        "total_staged": len(list(STAGED.glob("*.txt"))),
    }
    (STAGED / "_staging.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[done] staging dir: {STAGED.as_posix()}")
    print("[hint] chạy batch: python training/prepare_dataset.py --mode synthesize --source training/data/raw_staged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
