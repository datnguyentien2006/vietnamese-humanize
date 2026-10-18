"""Test cho tính năng Giảm đạo văn AI (v1.2)."""

from unittest.mock import MagicMock, Mock

from app.config import settings


def test_vocabulary_endpoint_returns_mapping(client):
    response = client.get("/api/vocabulary")
    assert response.status_code == 200
    data = response.json()
    assert "mapping" in data
    assert "tận dụng" in data["mapping"]
    assert "dùng" in data["mapping"]["tận dụng"]


def test_scan_report_disabled_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", False)
    payload = {"text": "Văn bản thử nghiệm."}
    response = client.post("/api/scan-report", json=payload)
    assert response.status_code == 503


def test_scan_report_missing_groq_key(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    payload = {"text": "Văn bản thử nghiệm."}
    response = client.post("/api/scan-report", json=payload)
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_scan_report_empty_text(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    payload = {"text": "   "}
    response = client.post("/api/scan-report", json=payload)
    assert response.status_code == 400


def test_refine_missing_groq_key(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    payload = {
        "paragraph_text": "Đoạn văn thử.",
        "sentence": "Tận dụng nguồn lực.",
        "issue_type": "academic_tone",
        "user_command": "sửa cho tự nhiên hơn",
    }
    response = client.post("/api/refine", json=payload)
    assert response.status_code == 503


def test_refine_invalid_issue_type(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test")
    payload = {
        "paragraph_text": "Đoạn văn thử.",
        "sentence": "Tận dụng nguồn lực.",
        "issue_type": "invalid_type",
        "user_command": "sửa cho tự nhiên hơn",
    }
    response = client.post("/api/refine", json=payload)
    assert response.status_code == 400