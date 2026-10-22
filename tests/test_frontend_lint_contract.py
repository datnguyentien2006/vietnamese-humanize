"""Frontend v1.3: the single-screen Humanize workflow contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "web" / "frontend"


def read_frontend(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_frontend_supports_the_humanize_workflow() -> None:
    page = read_frontend("app/page.tsx")
    panel = read_frontend("components/SuggestionsPanel.tsx")

    # Paste AI text → humanize → before/after diff + review suggestions.
    assert "Dán văn bản AI cần làm mượt tại đây" in page
    assert "✨ Humanize văn bản" in page
    assert "<CompareView" in page
    assert "Bản đã humanize" in page
    assert "humanizeText(" in page
    assert "Gợi ý rà soát" in page
    assert "<SuggestionsPanel" in page
    assert "✨ Humanize" not in panel

    # Fact warning surface: lost number/date tokens must be listed verbatim.
    assert "fact_check.lost_tokens.length > 0" in page
    assert (
        "Cảnh báo: số liệu/ngày còn thiếu trong bản đã humanize" in page
    )

    # Review suggestion items: badge label map, question, collapse toggle.
    assert "export function issueTypeLabel(type: string): string" in panel
    assert "unverified_data" in panel
    assert panel.count('return type;') >= 1  # unknown types fall back to raw id


def test_frontend_zero_state_does_not_overclaim() -> None:
    page = read_frontend("app/page.tsx")
    disclaimer = read_frontend("components/Disclaimer.tsx")
    panel = read_frontend("components/SuggestionsPanel.tsx")

    assert "Không có gợi ý nào cần rà soát cho văn bản này." in panel
    assert "Giảm đạo văn AI" not in page
    assert "Giảm đạo văn" not in disclaimer
    # The avoidance sentence is split across <strong> tags in JSX, so
    # contract on the contiguous human-readable fragments.
    assert "đo xác suất AI" in disclaimer
    assert "suy đoán tác giả" in disclaimer
    assert "không có tính năng lách kiểm duyệt" in disclaimer
    assert "Mỗi k" in disclaimer and "quả chỉ là" in disclaimer
    assert "đề xuất" in disclaimer
    for overclaim in ("bypass", "detector", "đo lường AI"):
        assert overclaim not in page.lower() and overclaim not in disclaimer.lower()


def test_frontend_manual_edit_and_provider_labels() -> None:
    page = read_frontend("app/page.tsx")

    # One-level undo + copy + manual editing of the humanized text.
    assert "Sửa thủ công" in page
    assert "Hoàn tác" in page
    assert "Sao chép" in page
    assert "navigator.clipboard.writeText(" in page
    assert "lastResultBeforeEdit" in page

    # Provider labels: dedicated model vs temporary Groq fallback.
    assert 'provider === "humanizer-model"' in page
    assert result_provider_labels_ok(page)


def result_provider_labels_ok(page: str) -> bool:
    return "Mô hình chuyên biệt" in page and "Groq (tạm thời)" in page
