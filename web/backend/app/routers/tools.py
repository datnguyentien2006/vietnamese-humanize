"""Router công cụ không cần LLM: /api/vocabulary + /api/diff.

v1.3: hai endpoint này chuyển từ routers/report_refiner.py (v1.2, bị xoá)
sang router công cụ riêng và KHÔNG còn gating capability — chúng là hàm
thuần (chỉ dẫn xáo/AI không), không tiêu token, không lộ bí mật.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from fastapi import APIRouter, Request

from app.limiter import limiter
from app.schemas import DiffResponse, DiffSegment
from app.services.vocabulary_advisor import get_all_formal_phrases

router = APIRouter(
    prefix="/api",
    tags=["Tools"],
)


@router.get("/vocabulary")
@limiter.limit("30/minute")
def get_vocabulary_endpoint(request: Request):
    """Trả về từ điển từ phổ thông để frontend hiển thị."""
    return {"mapping": get_all_formal_phrases()}


@router.post("/diff", response_model=DiffResponse)
@limiter.limit("30/minute")
def diff_endpoint(request: Request, original: str, refined: str):
    """So sánh hai đoạn văn bản và trả về diff."""
    matcher = SequenceMatcher(None, original, refined)
    segments: list[DiffSegment] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segments.append(DiffSegment(type="unchanged", text=original[i1:i2]))
        elif tag == "delete":
            segments.append(DiffSegment(type="removed", text=original[i1:i2]))
        elif tag == "insert":
            segments.append(DiffSegment(type="added", text=refined[j1:j2]))
        elif tag == "replace":
            segments.append(DiffSegment(type="removed", text=original[i1:i2]))
            segments.append(DiffSegment(type="added", text=refined[j1:j2]))

    return DiffResponse(
        original=original,
        refined=refined,
        diff_segments=segments,
    )
