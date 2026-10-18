import logging

from fastapi import APIRouter, HTTPException, Request
from vietnamese_writing_skills.core.patterns import pattern_index

from app.capabilities import capability_route_class, require_rewrite_enabled
from app.config import settings
from app.limiter import limiter
from app.schemas import (
    VALID_SKILLS,
    RewriteRequest,
    RewriteResponse,
    SuggestFixRequest,
    SuggestFixResponse,
)
from app.services.rewriter import (
    GroqKeyMissingError,
    GroqNoEditError,
    GroqNoModelError,
    GroqPermissionDeniedError,
    GroqQuotaExceededError,
    generate_rewrite,
    suggest_paragraph_fix,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Rewrite"],
    route_class=capability_route_class(require_rewrite_enabled),
)


def _error_detail(message: str, exc: Exception) -> str | dict:
    """Nếu DEBUG_ERRORS bật, trả dict có attempts list để client debug.

    Ngược lại trả string ngắn gọn như cũ.
    """
    if not settings.DEBUG_ERRORS:
        return message
    attempts = getattr(exc, "attempts", None) or []
    return {
        "message": message,
        "exception_type": type(exc).__name__,
        "exception_str": str(exc)[:500],
        "attempts": attempts,
    }


@router.post("/rewrite", response_model=RewriteResponse)
@limiter.limit("5/minute")
def rewrite_endpoint(request: Request, body: RewriteRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    if body.skill not in VALID_SKILLS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Kỹ năng không hợp lệ: {body.skill}. "
                f"Các kỹ năng hợp lệ: {', '.join(sorted(VALID_SKILLS))}"
            ),
        )

    try:
        return generate_rewrite(text=body.text, skill=body.skill, issue_ids=body.issue_ids)
    except GroqKeyMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GroqPermissionDeniedError as exc:
        logger.warning("Groq permission denied: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Dịch vụ Groq từ chối yêu cầu. "
                "Kiểm tra lại API key hoặc liên hệ maintainer.",
                exc,
            ),
        ) from exc
    except GroqQuotaExceededError as exc:
        logger.warning("Groq quota exceeded: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Groq API đã hết quota. "
                "Thử lại sau vài phút, hoặc dùng API key khác.",
                exc,
            ),
        ) from exc
    except GroqNoModelError as exc:
        logger.error("Groq no model available: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Không có model Groq nào khả dụng. Liên hệ maintainer.",
                exc,
            ),
        ) from exc
    except GroqNoEditError as exc:
        logger.error("Groq edit generation failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Không tạo được gợi ý chỉnh sửa. Thử lại sau.",
                exc,
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /api/rewrite")
        raise HTTPException(
            status_code=500,
            detail=_error_detail("Không thể xử lý yêu cầu viết lại.", exc),
        ) from exc


@router.post("/suggest-fix", response_model=SuggestFixResponse)
@limiter.limit("5/minute")
def suggest_fix_endpoint(request: Request, body: SuggestFixRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    if body.skill not in VALID_SKILLS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Kỹ năng không hợp lệ: {body.skill}. "
                f"Các kỹ năng hợp lệ: {', '.join(sorted(VALID_SKILLS))}"
            ),
        )

    known_patterns = pattern_index()
    for pid in body.pattern_ids:
        if pid not in known_patterns:
            raise HTTPException(
                status_code=400,
                detail=f"Pattern ID không tồn tại: {pid}",
            )

    try:
        suggestion = suggest_paragraph_fix(
            text=body.text,
            pattern_ids=body.pattern_ids,
            skill=body.skill,
        )
    except GroqKeyMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GroqPermissionDeniedError as exc:
        logger.warning("Groq permission denied (suggest-fix): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Dịch vụ Groq từ chối yêu cầu. "
                "Kiểm tra lại API key hoặc liên hệ maintainer.",
                exc,
            ),
        ) from exc
    except GroqQuotaExceededError as exc:
        logger.warning("Groq quota exceeded (suggest-fix): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Groq API đã hết quota. "
                "Thử lại sau vài phút, hoặc dùng API key khác.",
                exc,
            ),
        ) from exc
    except GroqNoModelError as exc:
        logger.error("Groq no model available (suggest-fix): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Không có model Groq nào khả dụng. Liên hệ maintainer.",
                exc,
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /api/suggest-fix")
        raise HTTPException(
            status_code=500,
            detail=_error_detail("Không thể xử lý yêu cầu gợi ý sửa.", exc),
        ) from exc

    return SuggestFixResponse(suggestion=suggestion)