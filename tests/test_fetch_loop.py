# -*- coding: utf-8 -*-
"""Regression: the fetch loop must terminate when every page is a stub.

A stub is a page whose extraction came back empty. Those pages are kept out of
``state.json`` so a later run can retry them — but an earlier version therefore
handed the same stub titles back for ever, producing thousands of identical
"lần thử" lines with no progress.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

import fetch_corpus as fc  # noqa: E402


def test_loop_terminates_when_all_pages_are_stubs(monkeypatch, tmp_path: Path) -> None:
    calls: list[int] = []

    monkeypatch.setattr(fc, "build_literature_pool", lambda *a, **k: ["A", "B", "C"])
    monkeypatch.setattr(fc, "all_pages", lambda *a, **k: ([], None))

    def fake_wikitext(titles):
        calls.append(len(titles))
        return {title: "quá ngắn" for title in titles}  # all stubs

    monkeypatch.setattr(fc, "fetch_wikitext", fake_wikitext)
    monkeypatch.setattr(fc, "fetch_extracts", lambda titles: {})

    code = fc.main(["--max-pages", "5", "--out", str(tmp_path), "--sleep", "0"])

    assert code == 1  # nothing accepted
    # 3 titles / batch of 20 → exactly one request, not one per loop iteration.
    assert calls == [3]


def test_stub_titles_are_tracked_separately_from_seen(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fc, "build_literature_pool", lambda *a, **k: ["A"])
    monkeypatch.setattr(fc, "all_pages", lambda *a, **k: ([], None))
    monkeypatch.setattr(fc, "fetch_wikitext", lambda titles: {t: "ngắn" for t in titles})
    monkeypatch.setattr(fc, "fetch_extracts", lambda titles: {})

    fc.main(["--max-pages", "1", "--out", str(tmp_path), "--sleep", "0"])

    import json

    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert "A" not in state["seen"]  # không phải tài liệu hợp lệ
    assert "A" in state["stubs"]  # nhưng được nhớ để không tải lại mỗi lần chạy


def test_allpages_wraps_once_instead_of_stopping_midway(monkeypatch, tmp_path: Path) -> None:
    """Một lượt chạy bắt đầu giữa bảng chữ cái vẫn phải quét hết namespace."""
    cursors: list[str | None] = []

    def fake_all_pages(cursor, limit=200):
        cursors.append(cursor)
        return (["Truyện B"], None) if cursor is None else ([], None)

    monkeypatch.setattr(fc, "build_literature_pool", lambda *a, **k: [])
    monkeypatch.setattr(fc, "all_pages", fake_all_pages)
    monkeypatch.setattr(fc, "fetch_wikitext", lambda titles: {})
    monkeypatch.setattr(fc, "fetch_extracts", lambda titles: {})

    feeder = fc.TitleFeeder([], cursor="GIUA_BANG_CHU_CAI", strategy="literature")

    titles = feeder.take(5, set())

    assert titles == ["Truyện B"]
    assert feeder.wraps == 1
    assert cursors == ["GIUA_BANG_CHU_CAI", None]


def test_accepted_page_is_persisted_as_seen(monkeypatch, tmp_path: Path) -> None:
    body = (
        "Buổi chiều xuống chậm trên cánh đồng. Gió thổi nhẹ qua rặng tre. "
        "Người trong làng lần lượt gánh nước về nhà. Tiếng trẻ con chạy chơi "
        "vang lên ngoài ngõ. Đèn dầu được thắp lên trong từng căn bếp nhỏ. "
        "Mùi rơm mới cắt còn vương trên sân gạch. Bà cụ ngồi vá lại chiếc áo "
        "cũ bên hiên, tay thoăn thoắt từng mũi kim. Ngoài kia, con sông mùa "
        "này nước đục ngầu, chảy chậm như đang ngủ."
    )
    monkeypatch.setattr(fc, "build_literature_pool", lambda *a, **k: ["Truyện A"])
    monkeypatch.setattr(fc, "all_pages", lambda *a, **k: ([], None))
    monkeypatch.setattr(fc, "fetch_wikitext", lambda titles: {t: body for t in titles})
    monkeypatch.setattr(fc, "fetch_extracts", lambda titles: {})

    code = fc.main(["--max-pages", "1", "--out", str(tmp_path), "--sleep", "0", "--min-words", "20"])

    assert code == 0
    state = (tmp_path / "state.json").read_text(encoding="utf-8")
    assert "Truyện A" in state
    assert len(list(tmp_path.glob("wikisource_*.txt"))) == 1
