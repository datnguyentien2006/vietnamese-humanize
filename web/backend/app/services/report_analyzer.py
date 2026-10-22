"""AI quét toàn văn bản để tìm các vấn đề phong cách báo cáo."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from groq import Groq

from app.config import settings
from app.services.vocabulary_advisor import get_casual_suggestions

logger = logging.getLogger(__name__)


ISSUE_TYPES = {
    "unverified_data": "Số liệu chưa có nguồn hoặc chưa kiểm chứng",
    "academic_tone": "Từ ngữ quá academic, xa cách với tiếng Việt thông thường",
    "long_sentence": "Câu quá dài, khó theo dõi",
    "missing_evidence": "Có nhận định nhưng thiếu minh chứng",
    "logic_gap": "Có khoảng trống logic giữa các ý",
    "repetition": "Lặp ý hoặc lặp từ không cần thiết",
    "vague_reference": "Tham chiếu mơ hồ (điều này, vấn đề đó...)",
    "passive_overuse": "Lạm dụng câu bị động",
    "register_mismatch": "Giọng văn không phù hợp với loại báo cáo",
}

MIN_CONFIDENCE = 3
MAX_PARAGRAPHS_PER_BATCH = 10


@dataclass
class ReportIssue:
    paragraph_index: int
    paragraph_text: str
    issue_type: str
    sentence: str
    reason: str
    question: str
    suggestions: list[str] = field(default_factory=list)
    confidence: int = 3


# QUAN TRỌNG: Không dùng str.format() cho prompt này vì prompt chứa
# nhiều dấu { } trong ví dụ JSON. Ta sẽ dùng replace() thủ công.
REPORT_ANALYZER_PROMPT = """Bạn là biên tập viên báo cáo tiếng Việt có kinh
nghiệm. Nhiệm vụ: đọc đoạn văn sau và tìm những chỗ có thể khiến người đọc
cảm thấy văn bản "máy móc", "xa cách", hoặc "thiếu tự nhiên".

## Các loại vấn đề cần tìm

1. **unverified_data**: Số liệu được đưa ra nhưng không có nguồn hoặc không có cơ sở.
   Ví dụ: "70% người dùng hài lòng" mà không nói khảo sát nào, ai khảo sát.

2. **academic_tone**: Dùng từ Hán-Việt trang trọng khi từ phổ thông sẽ tự nhiên hơn.
   Ví dụ: "tận dụng" thay vì "dùng", "tối ưu hóa" thay vì "cải thiện".

3. **long_sentence**: Câu quá dài (trên 40 từ), nhiều mệnh đề, khó theo dõi.

4. **missing_evidence**: Có nhận định, đánh giá nhưng không có số liệu hoặc dẫn chứng đi kèm.

5. **logic_gap**: Hai ý liền nhau nhưng không có kết nối logic rõ ràng.

6. **repetition**: Lặp lại cùng một ý bằng từ khác, hoặc lặp từ quá nhiều lần.

7. **vague_reference**: Dùng "điều này", "vấn đề đó", "điều đó" mà không rõ đang nói đến cái gì.

8. **passive_overuse**: Nhiều câu bị động liên tiếp, che mất người thực hiện.

9. **register_mismatch**: Giọng văn không phù hợp với loại báo cáo.

## Yêu cầu

- Chỉ đánh dấu những chỗ thực sự đáng để user xem xét, không đánh dấu mọi câu.
- Với mỗi chỗ, đưa ra câu hỏi gợi ý để user suy nghĩ.
- Câu hỏi phải cụ thể, gắn với nội dung, không chung chung.
- Nếu không có vấn đề gì, trả về danh sách rỗng.

## Đoạn văn cần phân tích

<PARAGRAPH>
__PARAGRAPH__
</PARAGRAPH>

## Trả về JSON

{
  "issues": [
    {
      "issue_type": "academic_tone",
      "sentence": "câu cụ thể bị đánh dấu",
      "reason": "lý do ngắn gọn",
      "question": "câu hỏi gợi ý cho user",
      "suggestions": ["dùng", "sử dụng"],
      "confidence": 4
    }
  ]
}

Nếu không có vấn đề: {"issues": []}
"""


def _call_analyzer(paragraph: str, api_key: str) -> list[dict]:
    """Gọi Groq để phân tích một đoạn văn."""
    client = Groq(api_key=api_key)
    # Dùng replace() thủ công, KHÔNG dùng .format() vì prompt có nhiều { }
    prompt = REPORT_ANALYZER_PROMPT.replace("__PARAGRAPH__", paragraph)

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là biên tập viên báo cáo tiếng Việt. "
                    "Trả về JSON duy nhất, không markdown, không text khác."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        model="openai/gpt-oss-120b",
        temperature=0.2,
        max_tokens=2048,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown code fences nếu có
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Tìm JSON object trong content (đề phòng Groq thêm text trước/sau)
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        content = content[start : end + 1]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("Groq trả JSON không hợp lệ: %s | content=%r", exc, content[:300])
        return []

    if not isinstance(data, dict):
        logger.warning("Groq trả JSON không phải object: %r", type(data))
        return []

    issues = data.get("issues", [])
    if not isinstance(issues, list):
        return []
    return issues


def analyze_report(
    text: str,
    api_key: str | None = None,
) -> list[ReportIssue]:
    """Quét toàn bộ văn bản và trả về danh sách các vấn đề."""
    active_key = (api_key if api_key else (settings.GROQ_API_KEY or "")).strip()
    if not active_key:
        raise ValueError("GROQ_API_KEY chưa được cấu hình.")

    paragraphs: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("\n".join(current))

    all_issues: list[ReportIssue] = []

    for idx, para in enumerate(paragraphs):
        if not para.strip():
            continue

        try:
            raw_issues = _call_analyzer(para, active_key)
        except Exception as exc:
            logger.warning("Không phân tích được đoạn %d: %s", idx, exc)
            continue

        for raw in raw_issues:
            if not isinstance(raw, dict):
                continue

            confidence = raw.get("confidence", 3)
            try:
                confidence = int(confidence)
            except (TypeError, ValueError):
                confidence = 3
            if confidence < MIN_CONFIDENCE:
                continue

            issue_type = raw.get("issue_type", "academic_tone")
            if issue_type not in ISSUE_TYPES:
                issue_type = "academic_tone"

            sentence = str(raw.get("sentence", "")).strip()
            if not sentence:
                continue

            suggestions = raw.get("suggestions", [])
            if not isinstance(suggestions, list):
                suggestions = []
            suggestions = [str(s) for s in suggestions if isinstance(s, str)]

            if not suggestions and sentence:
                for phrase in sentence.split():
                    casual = get_casual_suggestions(phrase)
                    if casual:
                        suggestions.extend(casual)
                        break
                suggestions = list(dict.fromkeys(suggestions))[:3]

            all_issues.append(
                ReportIssue(
                    paragraph_index=idx,
                    paragraph_text=para,
                    issue_type=issue_type,
                    sentence=sentence,
                    reason=str(raw.get("reason", "")),
                    question=str(raw.get("question", "")),
                    suggestions=suggestions,
                    confidence=confidence,
                )
            )

    return all_issues