# -*- coding: utf-8 -*-
"""Tests for the evaluation harness metrics (no network calls)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from metrics import (  # noqa: E402
    extract_entities,
    meaning_preservation,
    readability,
    robotic_density,
    sentences,
    static_report,
    word_count,
)


def test_entity_extraction_keeps_numbers_dates_acronyms() -> None:
    text = "Doanh thu đạt 1.850 tỷ đồng, tăng 9,2% vào Q3/2025 (20/10/2025), theo NHNN."
    entities = extract_entities(text)
    assert any(e.startswith("1.850") for e in entities)
    assert "9,2" in entities
    assert "Q3" in entities
    assert "20/10/2025" in entities
    assert "NHNN" in entities


def test_quoted_phrase_is_entity() -> None:
    entities = extract_entities("Dự án “Chuyển đổi số 2025” khởi động tháng 3.")
    assert any("chuyển đổi số" in e.lower() for e in entities)


def test_missing_number_is_flagged() -> None:
    original = "Lợi nhuận đạt 1.850 tỷ đồng, tăng 9,2% so với cùng kỳ."
    # The rewrite changed 9,2% -> ~10% and dropped nothing else.
    rewritten = "Lợi nhuận đạt 1.850 tỷ đồng, tăng gần 10% so với cùng kỳ."
    report = meaning_preservation(original, rewritten)
    ids = [e for e in report.entities_missing if "9" in e or "2" in e]
    assert len(report.entities_missing) >= 1
    assert report.score < 1.0


def test_canonical_number_diff_ignores_separator_style() -> None:
    original = "Giá vé 120.000 đồng/du khách."
    rewritten = "Giá vé 120000 đồng/du khách."
    report = meaning_preservation(original, rewritten)
    assert report.entities_missing == []
    assert report.score == 1.0


def test_added_entity_is_reported() -> None:
    original = "Sông Thu Bồn vượt báo động cấp 3."
    rewritten = "Sông Thu Bồn vượt báo động cấp 3, theo NHNN."
    report = meaning_preservation(original, rewritten)
    assert "nhnn" in [e.lower() for e in report.entities_added]


def test_sentence_splitting() -> None:
    assert len(sentences("Câu một. Câu hai! Câu ba?")) == 3
    # A plain newline is also a sentence boundary in this harness.
    assert len(sentences("Một dòng\nhai dòng.")) == 2


def test_readability_shape() -> None:
    report = readability("Câu ngắn. Đây là câu dài hơn hẳn một chút xíu nữa.")
    assert report.sentence_count == 2
    assert report.sentence_len_stdev > 0
    assert report.type_token_ratio <= 1.0


def test_robotic_density_counts_connectors() -> None:
    robotic = "Tổng thể, kết quả tốt. Bên cạnh đó, chi phí giảm. Điều này cho thấy tiến bộ."
    clean = "Kết quả tốt, chi phí giảm - đó là tiến bộ thật sự."
    assert robotic_density(robotic) > robotic_density(clean)


def test_word_count_skips_pure_punctuation() -> None:
    assert word_count("Một hai ba.") == 3
    assert word_count("!!!") == 0


def test_static_report_freshness_ok() -> None:
    original = "Tổng thể, doanh thu tăng 12%. Bên cạnh đó, chi phí giảm."
    rewritten = "Doanh thu tăng 12%, chi phí giảm."
    report = static_report(original, rewritten, 1, 0)
    assert report["meaning"]["score"] == 1.0
    assert report["robotic_density_after"] < report["robotic_density_before"]
    assert report["lint_issues_after"] < report["lint_issues_before"]


@pytest.mark.parametrize(
    ("text", "minimum"),
    [
        ("12%", 1),
        ("Q3/2025", 1),
        ("", 0),
    ],
)
def test_extract_entities_edge_cases(text: str, minimum: int) -> None:
    assert len(extract_entities(text)) >= minimum
