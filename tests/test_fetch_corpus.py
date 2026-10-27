# -*- coding: utf-8 -*-
"""P1: corpus cleaning rules (no network — API calls are mocked out)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

import fetch_corpus as fc  # noqa: E402


def test_strip_metadata_drops_wikisource_category_lines() -> None:
    raw = "Một câu văn.\nThể loại:Hát nói\nThể loại:Thơ Việt Nam\nCâu cuối."

    cleaned = fc.strip_metadata(raw)

    assert "Thể loại" not in cleaned
    assert cleaned.startswith("Một câu văn.")


def test_strip_metadata_normalises_old_space_before_punctuation() -> None:
    raw = "Trời Đông Phố vận ra Sóc Cảnh , trải bao phen gian hiểm ."

    cleaned = fc.strip_metadata(raw)

    assert "Cảnh, trải" in cleaned
    assert "hiểm." in cleaned
    assert " ," not in cleaned


def test_legal_title_detection() -> None:
    assert fc._LEGAL_TITLE.match("Luật Sở hữu trí tuệ nước Cộng hòa")
    assert fc._LEGAL_TITLE.match("Nghị định 12/2020/NĐ-CP")
    assert not fc._LEGAL_TITLE.match("Truyện ngắn Việt Nam")
    assert not fc._LEGAL_TITLE.match("Đói")


def test_legal_body_is_rejected_even_with_innocent_title() -> None:
    body = " ".join(f"Điều {i}. Nội dung quy định chi tiết." for i in range(1, 30))
    reasons = fc.quality_reasons(body, min_words=10, title="Văn bản số 12")

    assert "legal_document" in reasons


def test_quality_reasons_accepts_a_normal_prose_page() -> None:
    body = (
        "Buổi chiều xuống chậm trên cánh đồng. Gió thổi nhẹ qua rặng tre. "
        "Người trong làng lần lượt gánh nước về nhà. Tiếng trẻ con chạy chơi "
        "vang lên ngoài ngõ. Đèn dầu được thắp lên trong từng căn bếp nhỏ. "
        "Mùi rơm mới cắt còn vương trên sân gạch. Bà cụ ngồi vá lại chiếc áo "
        "cũ bên hiên, tay thoăn thoắt từng mũi kim. Ngoài kia, con sông mùa "
        "này nước đục ngầu, chảy chậm như đang ngủ."
    )

    assert fc.quality_reasons(body, min_words=20) == []


def test_title_feeder_uses_category_pool_first() -> None:
    feeder = fc.TitleFeeder(["A", "B", "C"], cursor=None, strategy="literature")

    assert feeder.take(2, set()) == ["A", "B"]
    assert feeder.take(2, {"A"}) == ["B", "C"]
    assert feeder.source == "categories"


def test_title_feeder_falls_through_to_allpages(monkeypatch) -> None:
    calls: list[str | None] = []

    def fake_all_pages(cursor, limit=200):
        calls.append(cursor)
        return ["Luật Đất đai 2024", "Truyện ngắn hay"], "NEXT"

    monkeypatch.setattr(fc, "all_pages", fake_all_pages)
    feeder = fc.TitleFeeder([], cursor=None, strategy="literature")

    titles = feeder.take(5, set())

    assert titles == ["Truyện ngắn hay"]  # legal title filtered before fetching
    assert feeder.source == "allpages"
    assert feeder.cursor == "NEXT"
    assert calls == [None]
