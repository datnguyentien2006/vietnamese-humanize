"""LLM-as-judge cho các pattern Nhóm C.

Các pattern Nhóm C không thể phát hiện bằng regex hay thống kê — chúng đòi hỏi
đọc hiểu ngữ nghĩa (semantic comprehension) ở tầng diễn ngôn. Module này dùng
LLM (mặc định Gemini) làm judge cho 6 pattern:

- VI-HUM-D06: cảm xúc phẳng (emotional flatness)
- VI-HUM-D07: cảm xúc không nhất quán (affective incoherence)
- VI-HUM-S13: đóng kín ngữ nghĩa (semantic closure)
- VI-HUM-L07: độ tinh vi mồ côi (orphaned sophistication)
- VI-HUM-D08: echo nội dung (self-echo)
- VI-HUM-D09: phản xạ trả lời trọn vẹn (question answering reflex)

Thiết kế bảo thủ:
- Chỉ gọi khi `--deep` flag được bật (CLI) hoặc web API yêu cầu rõ.
- Confidence threshold mặc định 4/5.
- Fail-safe: nếu thiếu `google-genai`, thiếu API key, lỗi mạng, hoặc lỗi parse
  JSON, module trả về JudgeResult với verdict="error" thay vì crash.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

# 6 pattern ID được LLM judge xử lý
LLM_JUDGED_PATTERN_IDS: frozenset[str] = frozenset(
    {
        "VI-HUM-D06",
        "VI-HUM-D07",
        "VI-HUM-S13",
        "VI-HUM-L07",
        "VI-HUM-D08",
        "VI-HUM-D09",
    }
)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MIN_CONFIDENCE = 4
DEFAULT_MAX_INPUT_CHARS = 12000


@dataclass
class JudgeResult:
    """Kết quả đánh giá từ LLM cho một pattern."""

    pattern_id: str
    verdict: str  # "flagged" | "clean" | "error"
    confidence: int  # 1-5
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""
    error: str | None = None


def is_llm_judge_available() -> bool:
    """Kiểm tra google-genai có cài đặt không."""
    try:
        from google import genai  # noqa: F401
        from google.genai import types  # noqa: F401
    except ImportError:
        return False
    return True


def _truncate(text: str, limit: int = DEFAULT_MAX_INPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n[... văn bản được cắt bớt ...]"


def _build_prompt(pattern_id: str, text: str) -> str | None:
    """Sinh prompt cho pattern_id. Trả về None nếu pattern không hỗ trợ."""
    template = _JUDGE_PROMPTS.get(pattern_id)
    if template is None:
        return None
    return template.replace("{TEXT}", _truncate(text))


def _call_gemini(
    prompt: str,
    api_key: str,
    model: str,
    temperature: float = 0.0,
) -> str:
    """Gọi Gemini và trả về text. Raise exception nếu lỗi."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=1500,
            response_mime_type="application/json",
        ),
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini trả về response rỗng")
    return text


def _parse_judge_json(raw: str, pattern_id: str) -> JudgeResult:
    """Parse JSON từ LLM thành JudgeResult. Raise ValueError nếu không parse được."""
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM trả về JSON không hợp lệ: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM trả về JSON không phải object")
    verdict = data.get("verdict")
    if verdict not in ("flagged", "clean"):
        raise ValueError(f"verdict không hợp lệ: {verdict!r}")
    try:
        confidence = int(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    confidence = max(1, min(5, confidence))
    evidence_raw = data.get("evidence", [])
    if isinstance(evidence_raw, str):
        evidence = [evidence_raw]
    elif isinstance(evidence_raw, list):
        evidence = [str(item) for item in evidence_raw if isinstance(item, (str, int, float))]
    else:
        evidence = []
    reasoning = str(data.get("reasoning", "")).strip()
    return JudgeResult(
        pattern_id=pattern_id,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence,
        reasoning=reasoning,
    )


def judge_text(
    text: str,
    pattern_id: str,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    min_confidence: int = DEFAULT_MIN_CONFIDENCE,
) -> JudgeResult:
    """Đánh giá văn bản với pattern_id.

    Trả về JudgeResult với verdict:
    - "flagged": pattern được phát hiện, confidence >= min_confidence
    - "clean": pattern không được phát hiện, hoặc confidence < min_confidence
    - "error": có lỗi (thiếu dependency, thiếu key, network, JSON parse)
    """
    if pattern_id not in LLM_JUDGED_PATTERN_IDS:
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="error",
            confidence=1,
            error=f"Pattern {pattern_id} không được hỗ trợ bởi LLM judge",
        )
    if not is_llm_judge_available():
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="error",
            confidence=1,
            error=(
                "google-genai chưa cài. Chạy: "
                "pip install 'vietnamese-writing-skills[llm]'"
            ),
        )
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not resolved_key or not resolved_key.strip():
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="error",
            confidence=1,
            error="GEMINI_API_KEY chưa được cấu hình",
        )
    prompt = _build_prompt(pattern_id, text)
    if prompt is None:
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="error",
            confidence=1,
            error=f"Không có prompt cho pattern {pattern_id}",
        )
    try:
        raw = _call_gemini(prompt, resolved_key, model, temperature=0.0)
        result = _parse_judge_json(raw, pattern_id)
    except Exception as exc:  # noqa: BLE001 - fail-safe, không crash lint
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="error",
            confidence=1,
            error=f"{type(exc).__name__}: {str(exc)[:200]}",
        )
    # Ngưỡng bảo thủ: confidence thấp hơn ngưỡng → downgrade thành clean
    if result.verdict == "flagged" and result.confidence < min_confidence:
        return JudgeResult(
            pattern_id=pattern_id,
            verdict="clean",
            confidence=result.confidence,
            evidence=result.evidence,
            reasoning=(
                f"LLM nghi ngờ ({result.confidence}/5) nhưng dưới ngưỡng "
                f"{min_confidence}. {result.reasoning}"
            ),
        )
    return result


# ============================================================================
# Prompt templates cho 6 pattern
# ============================================================================

_JUDGE_PROMPTS: dict[str, str] = {
    "VI-HUM-D06": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: đánh giá xem văn bản nói về chủ đề cảm xúc mạnh có giọng điệu thay đổi theo cảm xúc không.

## Tiêu chí
- Chủ đề cảm xúc mạnh: mất mát, khó khăn, thành công, thất bại, đau khổ, hạnh phúc, xúc động.
- Giọng điệu thay đổi: có câu ngắn đột ngột, câu cụt, dấu ba chấm, từ ngữ đời thường, hoặc sự im lặng khi cảm xúc lên cao.
- Nếu chủ đề cảm xúc mạnh nhưng giọng điệu đều đều như văn báo cáo → flagged.
- Nếu chủ đề trung tính → clean.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Tôi đã trải qua một giai đoạn khó khăn trong sự nghiệp. Mọi thứ diễn ra không như mong đợi. Tuy nhiên, tôi đã học được nhiều bài học quý giá. Những bài học này đã giúp tôi trưởng thành."
→ Chủ đề khó khăn nhưng giọng đều và tích cực máy móc.

### Ví dụ 2 (ĐẠT - clean)
"Tôi vừa mất việc. Mấy hôm đầu tôi không biết làm gì. Sau đó tôi bắt đầu gửi CV, và dần thấy nhẹ hơn."
→ Chủ đề tiêu cực, giọng chuyển dần, có câu ngắn đột ngột.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất (không có text khác):
{
  "pattern_id": "VI-HUM-D06",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn câu cụ thể"],
  "reasoning": "1-2 câu giải thích"
}""",
    "VI-HUM-D07": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: đánh giá xem cảm xúc của NỘI DUNG và cảm xúc của GIỌNG VĂN có nhất quán không.

## Tiêu chí
- Nội dung là điều đang được nói tới (mất mát, thành công, khó khăn, bình thường).
- Giọng văn là cách viết thể hiện cảm xúc (buồn, vui, trung tính, mỉa mai).
- Nếu nội dung buồn nhưng giọng văn vui (hoặc ngược lại) → flagged.
- Nếu cả hai đều trung tính → clean.
- Nếu nội dung tiêu cực và giọng chuyển dần sang tích cực hợp lý → clean.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Tôi vừa mất việc và điều này thật tuyệt vời! Đây là cơ hội vàng để tôi khám phá những con đường mới."
→ Mất việc (buồn) nhưng giọng hào hứng.

### Ví dụ 2 (ĐẠT - clean)
"Tôi vừa mất việc. Tôi chưa biết phải làm gì tiếp theo."
→ Giọng văn khớp với nội dung tiêu cực.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất:
{
  "pattern_id": "VI-HUM-D07",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn câu cụ thể"],
  "reasoning": "1-2 câu giải thích"
}""",
    "VI-HUM-S13": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: đánh giá xem hầu hết các đoạn có kết bằng câu tóm tắt hoặc kết luận không.

## Tiêu chí
- Đếm số đoạn có nội dung (bỏ qua đoạn trắng).
- Với mỗi đoạn, xem câu cuối cùng:
  - Closure ending: tóm tắt, kết luận, lời khuyên, "vì vậy", "tóm lại", "như vậy".
  - Opening ending: câu hỏi, câu bỏ lửng, chi tiết cụ thể không giải thích, dấu ba chấm.
- Nếu closure_ratio > 0.8 và số đoạn >= 4 → flagged.
- Nếu có ít nhất 2 đoạn kết bằng opening → clean.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Đoạn một bàn về A. Chúng ta có thể thấy rằng vấn đề này rất quan trọng.
Đoạn hai phân tích B. Tóm lại, B cần được xử lý.
Đoạn ba đề cập C. Vì vậy, cần có giải pháp cho C."
→ Cả ba đoạn đều closure.

### Ví dụ 2 (ĐẠT - clean)
"Đoạn một bàn về A.
Đoạn hai phân tích B. Tại sao B lại quan trọng hơn A?
Đoạn ba đề cập C."
→ Có đoạn kết bằng câu hỏi.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất:
{
  "pattern_id": "VI-HUM-S13",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn câu kết đoạn"],
  "reasoning": "1-2 câu giải thích, kèm tỉ lệ closure/tổng"
}""",
    "VI-HUM-L07": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: tìm ẩn dụ, so sánh, hoặc hình ảnh "mồ côi" — bị bỏ rơi bởi các câu xung quanh.

## Tiêu chí
- Tìm tất cả ẩn dụ, so sánh, hoặc hình ảnh trong văn bản.
- Với mỗi ẩn dụ, đọc 2 câu trước và 2 câu sau.
- Nếu các câu xung quanh mở rộng hoặc khai thác ẩn dụ → supported.
- Nếu các câu xung quanh hoàn toàn không liên quan → orphaned.
- Nếu orphaned_count >= 2 → flagged.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Dự án này là một con thuyền nhỏ giữa biển lớn. Ngân sách đã được phê duyệt. Đội ngũ có mười thành viên."
→ Ẩn dụ con thuyền bị bỏ rơi.

### Ví dụ 2 (ĐẠT - clean)
"Dự án như con thuyền nhỏ giữa biển lớn: ngân sách là nhiên liệu, đội ngũ là thủy thủ, và sáu tháng là khoảng cách bờ."
→ Cả đoạn xoay quanh ẩn dụ.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất:
{
  "pattern_id": "VI-HUM-L07",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn ẩn dụ mồ côi"],
  "reasoning": "1-2 câu giải thích, kèm số orphaned"
}""",
    "VI-HUM-D08": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: tìm các cặp câu/đoạn có CÙNG Ý nhưng khác từ ngữ (echo nội dung).

## Tiêu chí
- Echo: hai câu nói cùng một ý, chỉ khác cách diễn đạt.
- Không phải echo: hai câu nói hai ý khác nhau, hoặc một câu mở rộng ý kia bằng chi tiết mới.
- Nếu echo_count >= 3 → flagged.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Dự án cần thêm ngân sách để hoàn thành.
Chúng tôi đang thiếu nguồn lực tài chính cho dự án.
Vấn đề chính là dự án chưa có đủ tiền."
→ Ba câu cùng ý, khác từ ngữ.

### Ví dụ 2 (ĐẠT - clean)
"Dự án cần thêm ngân sách để hoàn thành.
Đội ngũ cũng cần thêm hai kỹ sư."
→ Hai ý khác nhau.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất:
{
  "pattern_id": "VI-HUM-D08",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn cặp câu echo"],
  "reasoning": "1-2 câu giải thích, kèm echo_count"
}""",
    "VI-HUM-D09": """Bạn là chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ: đánh giá xem văn bản trả lời câu hỏi/nhiệm vụ một cách trọn vẹn máy móc không.

## Tiêu chí
- Nếu văn bản không bắt đầu bằng câu hỏi/nhiệm vụ → clean.
- Nếu có, đếm các phần "thêm": giải thích, ví dụ, kết luận.
- Nếu extra_sections >= 3 và không có phần nào lệch khỏi câu hỏi → flagged.
- Nếu trả lời cụt hoặc lệch → clean.

## Ví dụ
### Ví dụ 1 (KHÔNG ĐẠT - flagged)
"Câu hỏi: Tại sao dự án thất bại?
Dự án thất bại vì ba lý do. Thứ nhất, thiếu ngân sách. Thứ hai, nhân sự yếu. Thứ ba, kế hoạch không rõ. Ví dụ, giai đoạn hai không có người phụ trách. Như vậy, có thể kết luận rằng thất bại là do nhiều yếu tố."
→ Trả lời + giải thích + ví dụ + kết luận.

### Ví dụ 2 (ĐẠT - clean)
"Dự án thất bại vì thiếu ngân sách cho giai đoạn hai."
→ Trả lời trực tiếp, không mở rộng.

## Văn bản cần đánh giá
{TEXT}

## Yêu cầu
Trả về JSON duy nhất:
{
  "pattern_id": "VI-HUM-D09",
  "verdict": "flagged" hoặc "clean",
  "confidence": 1-5,
  "evidence": ["trích dẫn phần thêm"],
  "reasoning": "1-2 câu giải thích, kèm extra_sections"
}""",
}