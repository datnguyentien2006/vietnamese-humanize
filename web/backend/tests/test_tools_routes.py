"""Tests cho router công cụ không cần LLM: /api/vocabulary + /api/diff."""

from __future__ import annotations


def test_vocabulary_endpoint_returns_mapping(client):
    response = client.get("/api/vocabulary")
    assert response.status_code == 200
    data = response.json()
    assert "mapping" in data
    assert len(data["mapping"]) > 100
    assert "dùng" in data["mapping"]["tận dụng"]


def test_diff_endpoint_returns_segments(client):
    response = client.post(
        "/api/diff",
        params={"original": "cong suat 2200W", "refined": "cong suat 2200W hai vong"},
    )
    assert response.status_code == 200
    segments = response.json()["diff_segments"]
    types = [s["type"] for s in segments]
    assert types == ["unchanged", "added"]
