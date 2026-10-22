"""Tests cho POST /api/humanize (v1.3)."""

from __future__ import annotations

import httpx

import app.services.humanizer_model as humanizer_model
from app.config import settings
from app.limiter import limiter

SAMPLE = (
    "Doanh thu quý 3 đạt 1.850 tỷ đồng, tăng 56,7% so với cùng kỳ, "
    "công bố ngày 8/10/2025. Ban lãnh đạo cho biết điều này thể hiện "
    "sự tăng trưởng bền vững một cách rõ rệt."
)

HUMANIZER_BASE = "https://humanizer.example.com/v1"
CLEAN_REWRITE = (
    "Quý 3, doanh thu lên 1850 tỷ đồng — tăng 56,7% so với cùng kỳ, "
    "công bố ngày 8/10/2025. Ban lãnh đạo nhận xét mức tăng này là lành."
)


def _response(status_code: int, content: str):
    from types import SimpleNamespace

    return SimpleNamespace(
        status_code=status_code,
        text=content,
        json=lambda: {"choices": [{"message": {"content": content}}]},
    )


def test_humanize_disabled_returns_503(client):
    response = client.post("/api/humanize", json={"text": SAMPLE})
    assert response.status_code == 503


def test_humanize_empty_text_returns_400(client, monkeypatch, mock_groq):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    response = client.post("/api/humanize", json={"text": "   "})
    assert response.status_code == 400


def test_humanize_text_over_limit_returns_422(client, monkeypatch, mock_groq):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    response = client.post("/api/humanize", json={"text": "a" * 20001})
    assert response.status_code == 422


def test_groq_fallback_happy_path(client, monkeypatch, mock_groq, mock_groq_analyzer):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq-fallback"
    assert isinstance(data["rewrite"], str)
    assert data["stats"]["total_issues"] is not None
    assert data["fact_check"]["lost_tokens"] == []
    assert isinstance(data["suggestions"], list)
    assert isinstance(data["warnings"], list)


def test_dedicated_model_happy_path(
    client, monkeypatch, mock_groq_analyzer
):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    import unittest.mock as um

    with um.patch.object(humanizer_model.httpx, "Client") as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.return_value = _response(200, CLEAN_REWRITE)
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "humanizer-model"
    assert data["rewrite"] == CLEAN_REWRITE
    assert data["fact_check"]["lost_tokens"] == []
    assert data["stats"]["attempts"] == 1
    assert data["stats"]["latency_seconds"] >= 0
    mock_groq_analyzer.chat.completions.create.assert_called()


def test_model_failure_falls_back_to_groq(
    client, monkeypatch, mock_groq, mock_groq_analyzer
):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    import unittest.mock as um

    with um.patch.object(
        humanizer_model.httpx, "Client"
    ) as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.side_effect = httpx.ConnectError("no route")
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq-fallback"
    assert any("Groq tạm thời" in warning for warning in data["warnings"])


def test_model_failure_without_fallback_returns_502(client, monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "HUMANIZER_FALLBACK_GROQ", False)
    import unittest.mock as um

    with um.patch.object(humanizer_model.httpx, "Client") as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.side_effect = httpx.ConnectError("no route")
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 502


def test_model_guard_failure_prefers_clean_fallback(
    client, monkeypatch, mock_groq, mock_groq_analyzer
):
    lost_rewrite = CLEAN_REWRITE.replace("8/10/2025", "tháng 10")
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    import unittest.mock as um

    with um.patch.object(humanizer_model.httpx, "Client") as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.side_effect = [_response(200, lost_rewrite), _response(200, lost_rewrite)]
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq-fallback"
    assert "8/10/2025" in data["rewrite"]
    assert data["fact_check"]["lost_tokens"] == []


def test_model_guard_failure_without_working_fallback_warns(
    client, monkeypatch, mock_groq_analyzer
):
    # mock_groq fixture absent: Groq sẽ raise GroqKeyMissingError vì key None
    # (fallback bị vô hiệu ở mức pipeline) — bỏ qua: đặt fallback vô hiệu.
    lost_rewrite = CLEAN_REWRITE.replace("8/10/2025", "tháng 10")
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "HUMANIZER_FALLBACK_GROQ", False)
    import unittest.mock as um

    with um.patch.object(humanizer_model.httpx, "Client") as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.side_effect = [_response(200, lost_rewrite), _response(200, lost_rewrite)]
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "humanizer-model"
    assert "8/10/2025" in data["fact_check"]["lost_tokens"]
    assert len(data["warnings"]) >= 1


def test_suggestions_fail_soft(client, monkeypatch, mock_groq):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    import unittest.mock as um

    with (
        um.patch.object(humanizer_model.httpx, "Client") as mock_cls,
        um.patch(
            "app.routers.humanize.analyze_report", side_effect=RuntimeError("boom")
        ),
    ):
        post = mock_cls.return_value.__enter__.return_value.post
        post.return_value = _response(200, CLEAN_REWRITE)
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []
    assert any("rà soát" in warning for warning in data["warnings"])


def test_suggestions_skipped_without_groq_key(
    client, monkeypatch, mock_groq_analyzer
):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", HUMANIZER_BASE)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    import unittest.mock as um

    with um.patch.object(humanizer_model.httpx, "Client") as mock_cls:
        post = mock_cls.return_value.__enter__.return_value.post
        post.return_value = _response(200, CLEAN_REWRITE)
        response = client.post("/api/humanize", json={"text": SAMPLE})

    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []
    assert any("GROQ_API_KEY" in warning for warning in data["warnings"])


def test_rate_limit_five_per_minute(client, monkeypatch, mock_groq, mock_groq_analyzer):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    limiter.enabled = True
    try:
        statuses = [
            client.post("/api/humanize", json={"text": SAMPLE}).status_code
            for _ in range(6)
        ]
    finally:
        limiter.enabled = False
    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429
