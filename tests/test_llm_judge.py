"""Test cho LLM judge (Nhóm C) với mock hoàn toàn, không gọi API thật."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vietnamese_writing_skills.core import llm_judge
from vietnamese_writing_skills.core.llm_judge import (
    LLM_JUDGED_PATTERN_IDS,
    JudgeResult,
    _parse_judge_json,
    judge_text,
)


def test_llm_judged_ids_are_six() -> None:
    assert len(LLM_JUDGED_PATTERN_IDS) == 6
    for pid in (
        "VI-HUM-D06",
        "VI-HUM-D07",
        "VI-HUM-S13",
        "VI-HUM-L07",
        "VI-HUM-D08",
        "VI-HUM-D09",
    ):
        assert pid in LLM_JUDGED_PATTERN_IDS


def test_unsupported_pattern_returns_error() -> None:
    result = judge_text("text", "VI-HUM-L01")
    assert result.verdict == "error"
    assert "không được hỗ trợ" in (result.error or "")


def test_missing_api_key_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch.object(llm_judge, "is_llm_judge_available", return_value=True):
        result = judge_text("text dài hơn 200 ký tự" * 20, "VI-HUM-D07")
    assert result.verdict == "error"
    assert "GEMINI_API_KEY" in (result.error or "")


def test_missing_dependency_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(llm_judge, "is_llm_judge_available", return_value=False):
        result = judge_text("text", "VI-HUM-D07", api_key="fake")
    assert result.verdict == "error"
    assert "google-genai" in (result.error or "")


def test_parse_valid_json() -> None:
    raw = json.dumps(
        {
            "pattern_id": "VI-HUM-D07",
            "verdict": "flagged",
            "confidence": 5,
            "evidence": ["câu 1", "câu 2"],
            "reasoning": "không nhất quán",
        }
    )
    result = _parse_judge_json(raw, "VI-HUM-D07")
    assert result.verdict == "flagged"
    assert result.confidence == 5
    assert result.evidence == ["câu 1", "câu 2"]


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(ValueError):
        _parse_judge_json("not json", "VI-HUM-D07")


def test_parse_invalid_verdict_raises() -> None:
    raw = json.dumps({"verdict": "maybe", "confidence": 3})
    with pytest.raises(ValueError):
        _parse_judge_json(raw, "VI-HUM-D07")


def test_parse_clamps_confidence() -> None:
    raw = json.dumps({"verdict": "clean", "confidence": 99, "evidence": [], "reasoning": ""})
    result = _parse_judge_json(raw, "VI-HUM-D07")
    assert result.confidence == 5


def test_parse_handles_string_evidence() -> None:
    raw = json.dumps(
        {"verdict": "flagged", "confidence": 4, "evidence": "câu đơn", "reasoning": "x"}
    )
    result = _parse_judge_json(raw, "VI-HUM-D07")
    assert result.evidence == ["câu đơn"]


def test_flagged_below_threshold_downgraded_to_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = MagicMock()
    fake_response.text = json.dumps(
        {
            "verdict": "flagged",
            "confidence": 2,
            "evidence": ["câu nghi ngờ"],
            "reasoning": "có thể",
        }
    )
    with (
        patch.object(llm_judge, "is_llm_judge_available", return_value=True),
        patch.object(llm_judge, "_call_gemini", return_value=fake_response.text),
    ):
        result = judge_text("text" * 100, "VI-HUM-D07", api_key="fake", min_confidence=4)
    assert result.verdict == "clean"
    assert result.confidence == 2


def test_flagged_above_threshold_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = MagicMock()
    fake_response.text = json.dumps(
        {
            "verdict": "flagged",
            "confidence": 5,
            "evidence": ["câu bằng chứng"],
            "reasoning": "rõ ràng",
        }
    )
    with (
        patch.object(llm_judge, "is_llm_judge_available", return_value=True),
        patch.object(llm_judge, "_call_gemini", return_value=fake_response.text),
    ):
        result = judge_text("text" * 100, "VI-HUM-D07", api_key="fake", min_confidence=4)
    assert result.verdict == "flagged"
    assert result.confidence == 5


def test_network_error_returns_error_result(monkeypatch: pytest.MonkeyPatch) -> None:
    with (
        patch.object(llm_judge, "is_llm_judge_available", return_value=True),
        patch.object(llm_judge, "_call_gemini", side_effect=RuntimeError("network down")),
    ):
        result = judge_text("text" * 100, "VI-HUM-D07", api_key="fake")
    assert result.verdict == "error"
    assert "network down" in (result.error or "")


def test_short_text_is_skipped_by_deep_judge() -> None:
    from vietnamese_writing_skills.cli.lint import _deep_judge_issues
    from vietnamese_writing_skills.core.patterns import pattern_index
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    patterns = pattern_index(root / "patterns")
    # Văn bản quá ngắn → skip, không gọi LLM
    with patch.object(llm_judge, "is_llm_judge_available", return_value=True):
        issues = _deep_judge_issues("ngắn", patterns, api_key="fake")
    assert issues == []


def test_lint_text_deep_flag_off_does_not_call_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """lint_text mặc định (deep=False) không được gọi LLM."""
    from vietnamese_writing_skills.cli.lint import lint_text

    called = {"count": 0}

    def fake_judge(*args, **kwargs):
        called["count"] += 1
        return JudgeResult(pattern_id="x", verdict="clean", confidence=1)

    monkeypatch.setattr(
        "vietnamese_writing_skills.cli.lint.judge_text",
        fake_judge,
    )
    lint_text("Văn bản bình thường không cần deep judge.", deep=False)
    assert called["count"] == 0