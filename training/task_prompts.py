# -*- coding: utf-8 -*-
"""Shared prompt templates for the Vietnamese humanizer fine-tune.

Single source of truth: the training scripts and (later) the web backend
must use the same system/user template, otherwise the served model sees a
different task than the one it was trained on.
"""

"""System prompt used at training and inference time."""
SYSTEM_PROMPT = (
    "Bạn là một trợ lý biên tập tiếng Việt. Viết lại văn bản theo văn phong "
    "tự nhiên của người Việt. Bắt buộc giữ nguyên 100% thông tin: số liệu, "
    "mốc thời gian, tên riêng, địa danh, thuật ngữ chuyên môn và các điều "
    "kiện kèm theo. Không thêm ý mới, không bỏ ý cũ, không đưa nhận định "
    "nằm ngoài văn bản gốc. Chỉ trả về văn bản đã viết lại, không giải thích."
)

"""User prompt template. {text} is replaced with the paragraph to rewrite."""
USER_TEMPLATE = (
    "Viết lại đoạn văn sau sao cho tự nhiên như chính người Việt viết ra. "
    "Giữ nguyên ý nghĩa, số liệu, mốc thời gian và tên riêng của văn bản gốc.\n\n"
    "<ORIGINAL>\n{text}\n</ORIGINAL>"
)


def build_user_prompt(text: str) -> str:
    """Render the user prompt for one rewrite sample."""
    return USER_TEMPLATE.format(text=text)
