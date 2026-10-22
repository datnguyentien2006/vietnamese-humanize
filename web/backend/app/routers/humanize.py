"""Router v1.3: POST /api/humanize (5/min, ≤20.000 ký tự).

Đường dùng duy nhất cho tính năng "Humanize văn bản": mô hình chuyên biệt
(ưu tiên) hoặc Groq fallback + fact guard nguyên văn + gợi ý rà soát fail-soft.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request

from app.capabilities import capability_route_class, require_humanize_enabled
from app.config import settings
from app.limiter import limiter
from app.schemas import (
    FactCheck,
    HumanizeRequest,
    HumanizeResponse,
    HumanizeStats,
    ReviewSuggestion,
)
from app.services.humanize_pipeline import run_humanize
from app.services.humanizer_model import (
    HumanizerNotConfiguredError,
    HumanizerServerError,
    HumanizerTimeoutError,
)
from app.services.report_analyzer import analyze_report
from app.services.rewriter import (
    GroqKeyMissingError,
    GroqNoModelError,
    GroqPermissionDeniedError,
    GroqQuotaExceededError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Humanize"],
    route_class=capability_route_class(require_humanize_enabled),
)

WARN_SUGGESTIONS_UNAVAILABLE = (
    "Gợi ý rà soát không khả dụng trong lần này (lỗi khi phân tích bản đã "
    "humanize). Kết quả humanize vẫn nguyên vẹn."
)


def _error_detail(message: str, exc: Exception) -> str | dict:
    """Nếu DEBUG_ERRORS bật, trả dict kèm attempts list cho client debug.

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


def _collect_suggestions(text: str) -> tuple[list[ReviewSuggestion], list[str]]:
    """Gợi ý rà soát trên KẾT QUẢ humanize. Luôn fail-soft.

    Trả về (suggestions, warnings): phân tích lỗi không bao giờ làm hỏng
    kết quả humanize chính.
    """
    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key:
        return [], [
            "Gợi ý rà soát cần GROQ_API_KEY nên bỏ qua trong lần này."
        ]
    try:
        issues = analyze_report(text, api_key=api_key)
    except Exception as exc:
        logger.warning("Gợi ý rà soát thất bại (fail-soft): %s", str(exc)[:300])
        return [], [WARN_SUGGESTIONS_UNAVAILABLE]
    suggestions = [
        ReviewSuggestion(
            issue_type=issue.issue_type,
            excerpt=issue.sentence,
            reason=issue.reason,
            question=issue.question,
            suggestions=issue.suggestions,
            confidence=issue.confidence,
        )
        for issue in issues
    ]
    return suggestions, []


@router.post("/humanize", response_model=HumanizeResponse)
@limiter.limit("5/minute")
def humanize_endpoint(request: Request, body: HumanizeRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    started = time.monotonic()
    try:
        pipeline = run_humanize(body.text)
    except HumanizerNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GroqKeyMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GroqPermissionDeniedError as exc:
        logger.warning("Groq permission denied (humanize): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Dịch vụ Groq từ chối yêu cầu. Kiểm tra lại API key hoặc "
                "liên hệ maintainer.",
                exc,
            ),
        ) from exc
    except GroqQuotaExceededError as exc:
        logger.warning("Groq quota exceeded (humanize): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Groq API đã hết quota. Thử lại sau vài phút, hoặc dùng API "
                "key khác.",
                exc,
            ),
        ) from exc
    except GroqNoModelError as exc:
        logger.error("Groq no model available (humanize): %s", exc)
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                "Không có model Groq nào khả dụng. Liên hệ maintainer.", exc
            ),
        ) from exc
    except HumanizerTimeoutError as exc:
        logger.error("Humanizer model timeout: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=_error_detail(
                "Humanizer endpoint quá thời gian phản hồi. Thử lại sau.",
                exc,
            ),
        ) from exc
    except HumanizerServerError as exc:
        logger.error("Humanizer model server error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=_error_detail(
                "Không gọi được humanizer endpoint. Thử lại sau.",
                exc,
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Lỗi bất thường trong /api/humanize")
        raise HTTPException(
            status_code=500,
            detail=_error_detail("Không thể xử lý yêu cầu humanize.", exc),
        ) from exc

    suggestions, suggestion_warnings = _collect_suggestions(pipeline.rewrite)

    latency_seconds = round(time.monotonic() - started, 2)
    stats = HumanizeStats(
        attempts=pipeline.stats.get("attempts", 0),
        latency_seconds=latency_seconds,
        total_issues=pipeline.stats.get("total_issues"),
        fixed=pipeline.stats.get("fixed"),
        edits_applied=pipeline.stats.get("edits_applied"),
        edits_rejected=pipeline.stats.get("edits_rejected"),
        verification_attempts=pipeline.stats.get("verification_attempts"),
        verification_passed=pipeline.stats.get("verification_passed"),
    )

    return HumanizeResponse(
        rewrite=pipeline.rewrite,
        stats=stats,
        provider=pipeline.provider,
        fact_check=FactCheck(
            lost_tokens=pipeline.fact_check.get("lost_tokens", []),
            added_tokens=pipeline.fact_check.get("added_tokens", []),
        ),
        suggestions=suggestions,
        warnings=pipeline.warnings + suggestion_warnings,
    )
