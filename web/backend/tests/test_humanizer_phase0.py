"""Phase 0 (28/10/2026): chống chèn tiêu đề, chống nén quá tay, chia văn bản dài.

Ba hành vi này là hậu kỳ thuần tuý (không đổi prompt frozen), nên test trực
tiếp các helper — không cần mock HTTP.
"""

from __future__ import annotations

from app.services.humanizer_model import (
    _MIN_LENGTH_RATIO,
    _length_ratio,
    _looks_like_heading,
    _split_into_chunks,
    _strip_spurious_heading,
)

BODY = (
    "Thành phố Đà Nẵng đã triển khai thí điểm hệ thống giám sát giao thông "
    "thông minh tại 45 nút giao từ tháng 3/2025, giúp giảm 27% thời gian chờ "
    "đèn đỏ vào giờ cao điểm. Tổng kinh phí giai đoạn một là 1.850 tỷ đồng."
)
ORIGINAL = (
    "Trong bối cảnh chuyển đổi số diễn ra mạnh mẽ, việc áp dụng trí tuệ nhân "
    "tạo vào quản lý đô thị đang được nhiều địa phương quan tâm. " + BODY
)


# ---------------------------------------------------------------- tiêu đề


def test_heading_detected_for_short_line_without_sentence_end():
    assert _looks_like_heading("Áp dụng trí tuệ nhân tạo vào quản lý đô thị") is True


def test_heading_not_detected_for_real_sentence():
    assert _looks_like_heading(BODY.split(". ")[0] + ".") is False


def test_strip_removes_model_inserted_title():
    rewrite = "Áp dụng trí tuệ nhân tạo vào quản lý đô thị\n\n" + BODY
    cleaned = _strip_spurious_heading(rewrite, ORIGINAL)

    assert cleaned == BODY
    assert not cleaned.startswith("Áp dụng trí tuệ nhân tạo vào quản lý đô thị\n")


def test_strip_keeps_title_when_original_had_one():
    original = "Báo cáo quý III\n\n" + BODY
    rewrite = "Báo cáo quý III\n\n" + BODY

    assert _strip_spurious_heading(rewrite, original) == rewrite


def test_strip_keeps_short_body():
    # Thân quá ngắn: bóc tiêu đề sẽ làm mất gần hết nội dung → giữ nguyên.
    rewrite = "Tiêu đề ngắn\n\nMột câu."
    assert _strip_spurious_heading(rewrite, ORIGINAL) == rewrite


# ---------------------------------------------------------------- độ dài


def test_length_ratio_and_threshold():
    assert _length_ratio(BODY, BODY) == 1.0
    assert _MIN_LENGTH_RATIO == 0.70
    half = " ".join(BODY.split()[: len(BODY.split()) // 2])
    assert _length_ratio(half, BODY) < _MIN_LENGTH_RATIO


# ---------------------------------------------------------------- chia phần


def _paragraph(words: int, index: int) -> str:
    sentence = f"Đoạn {index} nói về số liệu {index}00 và mốc thời gian tháng {index}/2025."
    out = []
    while len(" ".join(out).split()) < words:
        out.append(sentence)
    return " ".join(out)


def test_split_keeps_short_text_whole():
    text = "Đoạn một ngắn.\n\nĐoạn hai cũng ngắn."
    assert _split_into_chunks(text) == [text]


def test_split_respects_max_words():
    text = "\n\n".join(_paragraph(300, i) for i in range(1, 4))
    chunks = _split_into_chunks(text, max_words=650)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.split()) <= 660  # sai số 10 từ cho ranh giới đoạn


def test_split_breaks_long_paragraph_at_sentence_boundary():
    long_paragraph = " ".join(f"Câu số {i} có nội dung kiểm tra." for i in range(1, 200))
    chunks = _split_into_chunks(long_paragraph, max_words=200)

    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.strip().endswith(".")  # không cắt giữa câu
