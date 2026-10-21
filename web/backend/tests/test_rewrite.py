from unittest.mock import Mock

from app.config import settings


def test_rewrite_disabled_returns_503_before_provider_call(client, monkeypatch):
    provider = Mock(
        return_value={
            "rewrite": "sentinel rewrite",
            "review_status": "unreviewed",
            "disclaimer": "sentinel disclaimer",
        }
    )
    monkeypatch.setattr("app.routers.rewrite.generate_rewrite", provider)
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "skill": "humanizer-vi",
    }

    response = client.post("/api/rewrite", json=payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Capability is disabled."}
    provider.assert_not_called()


def test_rewrite_disabled_rejects_malformed_json_before_parsing_or_provider_call(
    client, monkeypatch
):
    provider = Mock()
    monkeypatch.setattr("app.routers.rewrite.generate_rewrite", provider)

    response = client.post(
        "/api/rewrite",
        content=b'{"text":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Capability is disabled."}
    provider.assert_not_called()


def test_rewrite_missing_groq_key(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "skill": "humanizer-vi",
    }
    response = client.post("/api/rewrite", json=payload)
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_rewrite_with_groq_key_returns_new_response_shape(
    client, monkeypatch, mock_groq
):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    payload = {
        "text": (
            "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới. "
            "Thứ nhất, thị trường yêu cầu linh hoạt. Thứ hai, khách hàng đòi hỏi cao hơn."
        ),
        "skill": "humanizer-vi",
    }
    response = client.post("/api/rewrite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "rewrite",
        "review_status",
        "disclaimer",
        "stats",
        "applied_edits",
        "unresolved_issues",
    }
    assert data["review_status"] == "unreviewed"
    assert data["stats"]["verification_passed"] in (True, False)
    assert isinstance(data["applied_edits"], list)
    assert isinstance(data["unresolved_issues"], list)


def test_rewrite_sends_structured_prompt_to_groq(monkeypatch, mock_groq):
    from app.services.rewriter import generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    generate_rewrite(
        "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "humanizer-vi",
    )

    kwargs = mock_groq.chat.completions.create.call_args.kwargs
    messages = kwargs["messages"]
    assert kwargs["model"] == "openai/gpt-oss-120b"

    system_msg = next(m for m in messages if m["role"] == "system")
    user_msg = next(m for m in messages if m["role"] == "user")

    assert "QUY TẮC BẮT BUỘC" in system_msg["content"]
    assert "find" in system_msg["content"]
    assert "replace" in system_msg["content"]

    assert "Hướng dẫn skill" in user_msg["content"]
    assert "Chiến lược sửa" in user_msg["content"]
    assert "Danh sách issue cần sửa" in user_msg["content"]
    assert "<ORIGINAL>" in user_msg["content"]
    assert "</ORIGINAL>" in user_msg["content"]
    assert "Trong bối cảnh không ngừng phát triển" in user_msg["content"]


def test_rewrite_applies_valid_edit(monkeypatch, mock_groq):
    from app.services.rewriter import generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    original = "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới."
    mock_groq.chat.completions.create.return_value.choices[0].message.content = (
        '{"edits": ['
        '{"issue_pattern_id": "VI-HUM-L02",'
        f'"find": "{original}",'
        '"replace": "Doanh nghiệp cần đổi mới.",'
        '"reason": "Bỏ lời dẫn chung chung"}'
        "]}"
    )

    result = generate_rewrite(original, "humanizer-vi")
    assert "Doanh nghiệp cần đổi mới." in result.rewrite
    assert "Trong bối cảnh không ngừng phát triển" not in result.rewrite
    assert result.stats is not None
    assert result.stats.edits_applied >= 1
    assert len(result.applied_edits) >= 1


def test_rewrite_rejects_mismatched_find(monkeypatch, mock_groq):
    from app.services.rewriter import generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    mock_groq.chat.completions.create.return_value.choices[0].message.content = (
        '{"edits": ['
        '{"issue_pattern_id": "VI-HUM-L02",'
        '"find": "Đoạn văn không có trong văn bản gốc",'
        '"replace": "Đoạn thay thế",'
        '"reason": "Test reject"}'
        "]}"
    )

    result = generate_rewrite(
        "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "humanizer-vi",
    )
    assert result.stats is not None
    assert result.stats.edits_applied == 0
    assert result.stats.edits_rejected >= 1


def test_rewrite_handles_empty_edits_response(monkeypatch, mock_groq):
    from app.services.rewriter import generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    original = "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới."
    result = generate_rewrite(original, "humanizer-vi")
    assert result.rewrite == original
    assert result.stats is not None
    assert result.stats.edits_applied == 0


def test_rewrite_no_issues_returns_unchanged_without_calling_groq(
    monkeypatch, mock_groq
):
    from app.services.rewriter import generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    clean_text = "Nhóm hoàn thành báo cáo hôm nay."
    result = generate_rewrite(clean_text, "humanizer-vi")
    assert result.rewrite == clean_text
    assert result.stats is not None
    assert result.stats.total_issues == 0
    assert result.stats.edits_applied == 0
    mock_groq.chat.completions.create.assert_not_called()


def test_rewrite_provider_failure_does_not_expose_exception_details(
    client, monkeypatch
):
    secret = "groq-secret-token"
    raw_fragment = "[Original Text] confidential customer fragment"
    provider = Mock(side_effect=RuntimeError(f"{secret}: {raw_fragment}"))
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    monkeypatch.setattr(settings, "DEBUG_ERRORS", False)
    monkeypatch.setattr("app.routers.rewrite.generate_rewrite", provider)
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "skill": "humanizer-vi",
    }

    response = client.post("/api/rewrite", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Không thể xử lý yêu cầu viết lại."
    assert secret not in response.text
    assert raw_fragment not in response.text


def test_rewrite_parse_invalid_json_raises(monkeypatch, mock_groq):
    from app.services.rewriter import GroqNoEditError, generate_rewrite

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    mock_groq.chat.completions.create.return_value.choices[0].message.content = "not json"

    try:
        generate_rewrite(
            "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
            "humanizer-vi",
        )
    except GroqNoEditError as exc:
        assert "pass 1" in str(exc).lower() or "json" in str(exc).lower()
    else:
        raise AssertionError("Phải raise GroqNoEditError khi Groq trả JSON lỗi")


# ============================================================
# Tests cho /api/suggest-fix
# ============================================================


def test_suggest_fix_disabled_returns_503_before_provider_call(
    client, monkeypatch
):
    provider = Mock(return_value="sentinel suggestion")
    monkeypatch.setattr(
        "app.routers.rewrite.suggest_paragraph_fix", provider
    )
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "pattern_ids": ["VI-HUM-L02"],
        "skill": "humanizer-vi",
    }

    response = client.post("/api/suggest-fix", json=payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Capability is disabled."}
    provider.assert_not_called()


def test_suggest_fix_missing_groq_key(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "pattern_ids": ["VI-HUM-L02"],
        "skill": "humanizer-vi",
    }
    response = client.post("/api/suggest-fix", json=payload)
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_suggest_fix_rejects_unknown_pattern_id(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    payload = {
        "text": "Văn bản thử.",
        "pattern_ids": ["VI-FAKE-999"],
        "skill": "humanizer-vi",
    }
    response = client.post("/api/suggest-fix", json=payload)
    assert response.status_code == 400
    assert "VI-FAKE-999" in response.json()["detail"]


def test_suggest_fix_rejects_invalid_skill(client, monkeypatch):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    payload = {
        "text": "Văn bản thử.",
        "pattern_ids": [],
        "skill": "invalid-skill",
    }
    response = client.post("/api/suggest-fix", json=payload)
    assert response.status_code == 400
    assert "Kỹ năng không hợp lệ" in response.json()["detail"]


def test_suggest_fix_returns_suggestion(client, monkeypatch, mock_groq):
    monkeypatch.setattr(settings, "REWRITE_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    mock_groq.chat.completions.create.return_value.choices[0].message.content = (
        "Doanh nghiệp cần đổi mới vì thị trường yêu cầu linh hoạt."
    )
    payload = {
        "text": "Trong bối cảnh không ngừng phát triển, doanh nghiệp cần đổi mới.",
        "pattern_ids": ["VI-HUM-L02"],
        "skill": "humanizer-vi",
    }

    response = client.post("/api/suggest-fix", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"suggestion", "review_status", "disclaimer"}
    assert "Doanh nghiệp cần đổi mới" in data["suggestion"]
    assert data["review_status"] == "unreviewed"
    assert data["disclaimer"]


def test_suggest_fix_uses_settings_api_key(monkeypatch, mock_groq):
    """suggest-fix phải dùng settings.GROQ_API_KEY, không dùng hard-coded key."""
    from app.services.rewriter import suggest_paragraph_fix

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_settings_key_value")
    mock_groq.chat.completions.create.return_value.choices[0].message.content = "Đã sửa."

    result = suggest_paragraph_fix("Văn bản cần sửa.", [], "humanizer-vi")
    assert result == "Đã sửa."

    from app.services import rewriter

    client_cls = rewriter.Groq
    client_cls.assert_called()
    call_kwargs = client_cls.call_args.kwargs
    assert call_kwargs.get("api_key") == "gsk_settings_key_value"