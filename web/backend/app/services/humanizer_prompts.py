# ruff: noqa: E501 - frozen prompt lines must not be wrapped.
"""Frozen copy of training/task_prompts.py, carried by the web backend.

Deployment packages ship only web/backend/, so the repo-root training
package is not importable there. tests/test_humanizer_prompts_lock.py
(repo root) asserts these strings stay identical to training/task_prompts.py.
When the training prompts change, update this copy in the same commit.
"""

SYSTEM_PROMPT = 'Bạn là một trợ lý biên tập tiếng Việt. Viết lại văn bản theo văn phong tự nhiên của người Việt. Bắt buộc giữ nguyên 100% thông tin: số liệu, mốc thời gian, tên riêng, địa danh, thuật ngữ chuyên môn và các điều kiện kèm theo. Không thêm ý mới, không bỏ ý cũ, không đưa nhận định nằm ngoài văn bản gốc. Chỉ trả về văn bản đã viết lại, không giải thích.'

USER_TEMPLATE = 'Viết lại đoạn văn sau sao cho tự nhiên như chính người Việt viết ra. Giữ nguyên ý nghĩa, số liệu, mốc thời gian và tên riêng của văn bản gốc.\n\n<ORIGINAL>\n{text}\n</ORIGINAL>'

def build_user_prompt(text: str) -> str:
    """Render the user prompt for one whole-text rewrite."""
    return USER_TEMPLATE.format(text=text)
