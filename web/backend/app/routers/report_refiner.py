"""Router cho tính năng giảm đạo văn AI (v1.2)."""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.capabilities import capability_route_class, require_rewrite_enabled
from app.config import settings
from app.limiter import limiter
from app.schemas import (
    DiffResponse,
    DiffSegment,
    RefineRequest,
    RefineResponse,
    ScanReportRequest,
    ScanReportResponse,
)
from app.services.report_analyzer import ISSUE_TYPES, analyze_report
from app.services.refiner import refine_sentence
from app.services.vocabulary_advisor import get_all_formal_phrases

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Report Refiner"],
    route_class=capability_route_class(require_rewrite_enabled),
)


@router.get("/vocabulary")
@limiter.limit("30/minute")
def get_vocabulary_endpoint(request: Request):
    """Trả về từ điển từ phổ thông để frontend hiển thị."""
    return {"mapping": get_all_formal_phrases()}


@router.post("/scan-report", response_model=ScanReportResponse)
@limiter.limit("5/minute")
def scan_report_endpoint(request: Request, body: ScanReportRequest):
    """Quét toàn văn bản để tìm các vấn đề phong cách báo cáo."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY chưa được cấu hình.",
        )

    try:
        issues = analyze_report(body.text, api_key=api_key)
    except Exception as exc:
        logger.exception("Lỗi khi quét báo cáo")
        raise HTTPException(
            status_code=500,
            detail=f"Không thể quét báo cáo: {str(exc)[:200]}",
        ) from exc

    # Đếm số paragraph: chia theo dòng trống
    paragraphs = [p for p in body.text.split("\n\n") if p.strip()]

    return ScanReportResponse(
        issues=[
            {
                "paragraph_index": i.paragraph_index,
                "paragraph_text": i.paragraph_text,
                "issue_type": i.issue_type,
                "sentence": i.sentence,
                "reason": i.reason,
                "question": i.question,
                "suggestions": i.suggestions,
                "confidence": i.confidence,
            }
            for i in issues
        ],
        total_paragraphs=len(paragraphs),
        total_issues=len(issues),
    )


@router.post("/refine", response_model=RefineResponse)
@limiter.limit("10/minute")
def refine_endpoint(request: Request, body: RefineRequest):
    """User gửi câu lệnh, AI sửa câu theo yêu cầu."""
    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY chưa được cấu hình.",
        )

    # Validate issue_types
    invalid = [t for t in body.issue_types if t not in ISSUE_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"issue_types không hợp lệ: {', '.join(invalid)}",
        )

    try:
        result = refine_sentence(
            paragraph_text=body.paragraph_text,
            sentence=body.sentence,
            issue_types=body.issue_types,
            user_command=body.user_command,
            api_key=api_key,
        )
    except Exception as exc:
        logger.exception("Lỗi khi refine câu")
        raise HTTPException(
            status_code=500,
            detail=f"Không thể sửa câu: {str(exc)[:200]}",
        ) from exc

    return RefineResponse(**result)


@router.post("/diff", response_model=DiffResponse)
@limiter.limit("30/minute")
def diff_endpoint(request: Request, original: str, refined: str):
    """So sánh hai đoạn văn bản và trả về diff."""
    from difflib import SequenceMatcher

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