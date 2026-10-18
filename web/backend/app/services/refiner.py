"""AI sửa câu theo câu lệnh của user.

Module này triển khai Tầng 2: user ra lệnh, AI thực thi.
Điểm quan trọng: AI KHÔNG được tự ý sáng tạo, chỉ được:
1. Hiểu câu lệnh của user
2. Sửa câu theo đúng yêu cầu
3. Giữ nguyên logic và dữ kiện

v1.2.1: nhận list issue_types để xử lý nhiều vấn đề trên cùng một câu
trong 1 lần gọi duy nhất.
"""

from __future__ import annotations

import json
import logging

from groq import Groq

from app.config import settings
from app.services.report_analyzer import ISSUE_TYPES

logger = logging.getLogger(__name__)


REFINER_SYSTEM_PROMPT = """Bạn là biên tập viên tiếng Việt. Nhiệm vụ: sửa một câu văn theo yêu cầu của tác giả.

## Nguyên tắc bất di bất dịch

1. **Giữ nguyên ý của tác giả.** Không thêm ý mới, không bớt ý cũ.
2. **Giữ nguyên dữ kiện.** Số liệu, tên riêng, ngày tháng, điều kiện — không được thay đổi.
3. **Chỉ sửa những gì tác giả yêu cầu.** Không "sáng tạo" thêm.
4. **Nếu câu lệnh mơ hồ**, hãy chọn cách sửa an toàn nhất (thay đổi ít nhất).
5. **Không dùng từ Hán-Việt trang trọng** nếu không cần thiết. Ưu tiên từ phổ thông.
6. **Trả về CHỈ câu đã sửa.** Không giải thích, không markdown.

## Ví dụ

Câu gốc: "Tận dụng nguồn lực sẵn có để tối ưu hóa quy trình."
Câu lệnh: "sửa cho tự nhiên hơn"
→ "Dùng nguồn lực sẵn có để cải thiện quy trình."

Câu gốc: "Dự án này đóng vai trò quan trọng trong việc nâng cao hiệu suất."
Câu lệnh: "ngắn hơn"
→ "Dự án này rất quan trọng để tăng hiệu suất."

Câu gốc: "Chúng tôi tin rằng giải pháp này sẽ mang lại lợi ích lâu dài."
Câu lệnh: "bỏ 'chúng tôi tin rằng', viết trực tiếp"
→ "Giải pháp này sẽ mang lại lợi ích lâu dài."
"""


def refine_sentence(
    paragraph_text: str,
    sentence: str,
    issue_types: list[str],
    user_command: str,
    api_key: str | None = None,
) -> dict:
    """Sửa một câu theo câu lệnh của user, có thể cho nhiều issue_type.

    Returns:
        Dict với keys: refined_sentence, refined_paragraph, change_summary
    """
    active_key = (api_key if api_key else (settings.GROQ_API_KEY or "")).strip()
    if not active_key:
        raise ValueError("GROQ_API_KEY chưa được cấu hình.")

    # Lọc và chuẩn hóa issue_types
    valid_issue_types = [t for t in issue_types if t in ISSUE_TYPES]
    if not valid_issue_types:
        valid_issue_types = ["academic_tone"]

    issue_descriptions = "\n".join(
        f"- {t}: {ISSUE_TYPES[t]}" for t in valid_issue_types
    )

    client = Groq(api_key=active_key)

    prompt = f"""## Ngữ cảnh

Đoạn văn gốc:
<PARAGRAPH>
{paragraph_text}
</PARAGRAPH>

Câu cần sửa:
<SENTENCE>
{sentence}
</SENTENCE>

Các vấn đề AI đã phát hiện ở câu này:
{issue_descriptions}

## Câu lệnh của tác giả

<COMMAND>
{user_command}
</COMMAND>

## Nhiệm vụ

Sửa câu trên theo đúng câu lệnh của tác giả. Giải quyết TẤT CẢ các vấn đề đã liệt kê nếu có thể, nhưng ưu tiên tuyệt đối câu lệnh của tác giả.
Giữ nguyên ý và dữ kiện.
Trả về JSON:
{{
  "refined_sentence": "câu đã sửa",
  "change_summary": "mô tả ngắn những gì đã thay đổi"
}}
"""

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": REFINER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model="openai/gpt-oss-120b",
        temperature=0.3,
        max_tokens=1024,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown nếu có
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Tìm JSON object
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        content = content[start : end + 1]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Groq trả JSON không hợp lệ trong refine: %s | content=%r",
            exc,
            content[:300],
        )
        # Fallback: coi như AI trả về text thuần là câu đã sửa
        data = {
            "refined_sentence": content or sentence,
            "change_summary": "Không parse được JSON, dùng text trả về",
        }

    if not isinstance(data, dict):
        data = {"refined_sentence": sentence, "change_summary": ""}

    refined_sentence = str(data.get("refined_sentence", sentence)).strip() or sentence
    change_summary = str(data.get("change_summary", "")).strip()

    # Thay câu đã sửa vào đoạn văn
    if sentence and sentence in paragraph_text:
        refined_paragraph = paragraph_text.replace(sentence, refined_sentence, 1)
    else:
        refined_paragraph = paragraph_text

    return {
        "refined_sentence": refined_sentence,
        "refined_paragraph": refined_paragraph,
        "change_summary": change_summary,
        "review_status": "unreviewed",
    }