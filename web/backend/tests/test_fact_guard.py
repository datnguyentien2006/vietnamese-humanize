# -*- coding: utf-8 -*-
"""Tests for the fact-preservation guard in _apply_edits."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "web" / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.rewriter import _apply_edits, _fact_losses  # noqa: E402


def test_fact_losses_detects_dropped_number() -> None:
    assert _fact_losses("doanh thu 12% tăng", "doanh thu tăng mạnh") == ["12"]


def test_fact_losses_separator_canonical() -> None:
    # 1.850 == 1850: NOT a loss, only separator style changed.
    assert _fact_losses("1.850 tỷ đồng", "1850 tỷ đồng") == []


def test_fact_losses_detects_dropped_date() -> None:
    assert _fact_losses("ngày 8/10/2025 phát hành", "giữa tháng 10 phát hành") == [
        "8/10/2025"
    ]


def test_fact_losses_allows_moving_number() -> None:
    # Same token count moved around: numbers kept -> no loss.
    assert _fact_losses("chỉ có 45% tiết kiệm điện", "tiết kiệm tới 45% điện") == []


def test_apply_edits_rejects_fact_dropping_edit() -> None:
    text = "Bếp có công suất 2200W, hai vùng nấu."
    edits = [
        {
            "issue_pattern_id": "VI-HUM-S15",
            "find": "Bếp có công suất 2200W, hai vùng nấu.",
            "replace": "Bếp có hai vùng nấu tiện dụng.",
            "reason": "dọn câu",
        }
    ]
    new_text, applied, rejected = _apply_edits(text, edits)
    assert applied == []
    assert rejected[0]["reject_reason"].startswith("edit làm mất số liệu/ngày: 2200")
    assert new_text == text  # nothing changed


def test_apply_edits_still_applies_clean_edit() -> None:
    text = "Tổng thể, doanh thu tăng 12%."
    edits = [
        {
            "issue_pattern_id": "VI-HUM-S15",
            "find": "Tổng thể, doanh thu tăng 12%.",
            "replace": "Doanh thu tăng 12%.",
            "reason": "bỏ cú nối",
        }
    ]
    new_text, applied, rejected = _apply_edits(text, edits)
    assert new_text == "Doanh thu tăng 12%."
    assert applied and not rejected
