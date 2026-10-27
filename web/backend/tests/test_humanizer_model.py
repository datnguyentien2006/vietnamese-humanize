"""Tests cho app.services.humanizer_model (mô hình chuyên biệt, httpx)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.config import settings
from app.services.humanizer_model import (
    HumanizerNotConfiguredError,
    HumanizerServerError,
    HumanizerTimeoutError,
    humanize_with_model,
)
from app.services.humanizer_prompts import SYSTEM_PROMPT, build_user_prompt

BASE = "https://humanizer.example.com/v1"
SAMPLE = (
    "Doanh thu quý 3 đạt 1.850 tỷ đồng, tăng 56,7% so với cùng kỳ, "
    "công bố ngày 8/10/2025."
)
CLEAN_REWRITE = (
    "Quý 3, doanh thu lên 1850 tỷ đồng — tăng 56,7% so với cùng kỳ, "
    "công bố ngày 8/10/2025."
)
# Cùng token số nhưng MẤT ngày 8/10/2025.
LOST_REWRITE = (
    "Quý 3, doanh thu lên 1850 tỷ đồng — tăng 56,7% so với cùng kỳ, "
    "phát hành trong tháng 10."
)


def _response(status_code: int, content: str) -> SimpleNamespace:
    return SimpleNamespace(
        status_code=status_code,
        text=content,
        json=lambda: {
            "choices": [{"message": {"content": content}}],
        },
    )


def _mock_client_class():
    """Patch app.services.humanizer_model.httpx.Client; trả (cls, post)."""
    patcher = patch("app.services.humanizer_model.httpx.Client")
    mock_cls = patcher.start()
    post = mock_cls.return_value.__enter__.return_value.post
    return patcher, mock_cls, post


def test_not_configured_raises():
    with pytest.raises(HumanizerNotConfiguredError):
        humanize_with_model("text")


def test_happy_path_single_call_messages_and_headers(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    monkeypatch.setattr(settings, "HUMANIZER_API_KEY", "hk-secret")
    patcher, mock_cls, post = _mock_client_class()
    post.return_value = _response(200, CLEAN_REWRITE)
    try:
        result = humanize_with_model(SAMPLE)
    finally:
        patcher.stop()

    assert result.provider == "humanizer-model"
    assert result.guard_ok is True
    assert result.rewrite == CLEAN_REWRITE
    assert result.fact_check == {"lost_tokens": [], "added_tokens": []}
    assert result.warnings == []
    assert len(result.attempts) == 1
    assert result.attempts[0]["kind"] == "ok"

    post.assert_called_once()
    url = post.call_args.args[0]
    assert url == f"{BASE}/chat/completions"
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == settings.HUMANIZER_MODEL
    assert payload["temperature"] == 0.5
    assert payload["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    # Phase 0: user prompt = template frozen + câu nhắc chống nén/chèn tiêu đề.
    user_content = payload["messages"][1]["content"]
    assert payload["messages"][1]["role"] == "user"
    assert user_content.startswith(build_user_prompt(SAMPLE))
    assert "không đặt tiêu đề" in user_content
    headers = post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer hk-secret"


def test_no_api_key_omits_authorization_header(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    monkeypatch.setattr(settings, "HUMANIZER_API_KEY", None)
    patcher, _, post = _mock_client_class()
    post.return_value = _response(200, CLEAN_REWRITE)
    try:
        humanize_with_model(SAMPLE)
    finally:
        patcher.stop()
    assert "Authorization" not in post.call_args.kwargs["headers"]


def test_retries_once_with_bumped_temperature_when_tokens_lost(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = [_response(200, LOST_REWRITE), _response(200, CLEAN_REWRITE)]
    try:
        result = humanize_with_model(SAMPLE)
    finally:
        patcher.stop()

    assert post.call_count == 2
    assert post.call_args_list[0].kwargs["json"]["temperature"] == 0.5
    assert post.call_args_list[1].kwargs["json"]["temperature"] == 0.6
    assert post.call_args_list[0].kwargs["json"] is not None and post.call_args_list[
        0
    ].kwargs["json"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert result.guard_ok is True
    assert len(result.attempts) == 2
    assert result.attempts[0]["kind"] == "fact_loss"
    assert result.attempts[1]["kind"] == "ok"


def test_guard_failure_after_retry_returns_lost_tokens_and_warning(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = [
        _response(200, LOST_REWRITE),
        _response(200, LOST_REWRITE.replace("1850", "1850")),
    ]
    try:
        result = humanize_with_model(SAMPLE)
    finally:
        patcher.stop()

    assert result.guard_ok is False
    assert result.rewrite.startswith("Quý 3")
    assert "8/10/2025" in result.fact_check["lost_tokens"]
    assert any(tok == "8/10/2025" or tok.isdigit() or "/" in tok
               for tok in result.fact_check["lost_tokens"])
    assert len(result.warnings) == 1
    assert "8/10/2025" not in result.rewrite


def test_timeout_raises_and_records_attempt(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = httpx.ReadTimeout("read timed out")
    try:
        with pytest.raises(HumanizerTimeoutError):
            humanize_with_model(SAMPLE)
    finally:
        patcher.stop()
    assert post.call_count == 1


def test_http_401_raises_server_error(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.return_value = SimpleNamespace(status_code=401, text="unauthorized")
    try:
        with pytest.raises(HumanizerServerError):
            humanize_with_model(SAMPLE)
    finally:
        patcher.stop()


def test_http_500_then_success(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = [
        SimpleNamespace(status_code=500, text="boom"),
        _response(200, CLEAN_REWRITE),
    ]
    try:
        result = humanize_with_model(SAMPLE)
    finally:
        patcher.stop()
    assert result.guard_ok is True
    assert post.call_count == 2


def test_two_http_500s_raise(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = [
        SimpleNamespace(status_code=502, text="bad gateway"),
        SimpleNamespace(status_code=503, text="unavailable"),
    ]
    try:
        with pytest.raises(HumanizerServerError):
            humanize_with_model(SAMPLE)
    finally:
        patcher.stop()


def test_network_error_raises(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.side_effect = httpx.ConnectError("no route to host")
    try:
        with pytest.raises(HumanizerServerError):
            humanize_with_model(SAMPLE)
    finally:
        patcher.stop()


def test_empty_choices_then_success(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    empty = SimpleNamespace(
        status_code=200, text="{}", json=lambda: {"choices": []}
    )
    post.side_effect = [empty, _response(200, CLEAN_REWRITE)]
    try:
        result = humanize_with_model(SAMPLE)
    finally:
        patcher.stop()
    assert result.guard_ok is True
    assert post.call_count == 2


def test_separator_only_change_passes_guard(monkeypatch):
    monkeypatch.setattr(settings, "HUMANIZER_API_BASE", BASE)
    patcher, _, post = _mock_client_class()
    post.return_value = _response(200, CLEAN_REWRITE)
    try:
        result = humanize_with_model("doanh thu 1.850 tỷ")
    finally:
        patcher.stop()
    assert "1850" not in result.fact_check["lost_tokens"]
    assert result.fact_check["lost_tokens"] == []
