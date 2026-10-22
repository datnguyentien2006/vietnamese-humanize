"""Orchestrator humanize dùng chung cho POST /api/humanize và evaluation.

Thứ tự ưu tiên (theo spec v1.3):

1. Mô hình chuyên biệt (``HUMANIZER_API_BASE``) — toàn văn bản, prompt frozen.
2. Nếu mô hình fail fact guard sai lần hai → thử Groq fallback (nếu bật),
   ưu tiên bản sạch hơn về fact guard.
3.Nếu mô hình không khả dụng (chưa phục vụ / lỗi mạng) → Groq fallback.
4. Không có provider nào → raise (router trả 503/502 thân thiện).

Kết quả luôn đi qua fact guard nguyên văn: bản mất số liệu/ngày không bao
giờ được trả về mà không có ``fact_check.lost_tokens`` + ``warnings``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from app.config import settings
from app.services import fact_guard
from app.services.humanizer_model import (
    HumanizerNotConfiguredError,
    HumanizerServerError,
    HumanizerTimeoutError,
    ModelHumanizeResult,
    humanize_with_model,
)

logger = logging.getLogger(__name__)

WARN_MODEL_GUARD_FAILED = (
    "Kết quả từ mô hình chuyên biệt còn thiếu số liệu/ngay so với bản gốc."
)
WARN_MODEL_SWITCHED_TO_GROQ = (
    "Kết quả mô hình chuyên biệt làm mất số liệu/ngày nên đã chuyển sang "
    "Groq tạm thời."
)
WARN_MODEL_UNAVAILABLE = (
    "Mô hình chuyên biệt không phản hồi nên đã dùng Groq tạm thời."
)
WARN_FALLBACK_ALSO_FAILED = (
    "Fallback Groq cũng lỗi nên hiển thị kết quả mô hình kèm cảnh báo fact."
)
WARN_LOST_FACTS = (
    "Cảnh báo: một số số liệu/ngày trong văn bản gốc không còn xuất hiện "
    "trong bản đã humanize. Kiểm tra lại trước khi dùng."
)


@dataclass
class PipelineResult:
    """Kết quả chuẩn hoá của một lượt humanize (bất kể provider)."""

    rewrite: str
    provider: str
    fact_check: dict[str, list[str]] = field(
        default_factory=lambda: {"lost_tokens": [], "added_tokens": []}
    )
    warnings: list[str] = field(default_factory=list)
    # attempts chỉ được bóc cho client khi DEBUG_ERRORS bật (router lo).
    attempts: list[dict] = field(default_factory=list)
    # Khóa bổ sung cho HumanizeStats (tổng issues/fixed/edits của pipeline
    # Groq; rỗng với mô hình chuyên biệt).
    stats: dict = field(default_factory=dict)


def _fallback_enabled() -> bool:
    return (
        settings.HUMANIZER_FALLBACK_GROQ
        and bool((settings.GROQ_API_KEY or "").strip())
    )


def _stats_from_rewrite_response(groq_response) -> dict:
    stats = groq_response.stats
    if stats is None:
        return {}
    return {
        "total_issues": stats.total_issues,
        "fixed": stats.fixed,
        "edits_applied": stats.edits_applied,
        "edits_rejected": stats.edits_rejected,
        "verification_attempts": stats.verification_attempts,
        "verification_passed": stats.verification_passed,
    }


def _groq_fallback(text: str, extra_warnings: list[str] | None = None) -> PipelineResult:
    """Pipeline Groq hiện có gộp edits thành văn bản toàn văn."""
    from app.services.rewriter import generate_rewrite

    started = time.monotonic()
    response = generate_rewrite(text=text, skill="humanizer-vi", issue_ids=None)
    fact_check = fact_guard.diff_fact_tokens(text, response.rewrite)
    warnings = list(extra_warnings or [])
    if fact_check["lost_tokens"]:
        warnings.append(WARN_LOST_FACTS)
    stats = _stats_from_rewrite_response(response)
    stats["attempts"] = stats.get("verification_attempts", 0) or 0
    stats["fallback_latency_seconds"] = round(time.monotonic() - started, 2)
    return PipelineResult(
        rewrite=response.rewrite,
        provider="groq-fallback",
        fact_check=fact_check,
        warnings=warnings,
        attempts=[],
        stats=stats,
    )


def run_humanize(text: str) -> PipelineResult:
    """Chạy humanize theo cấu hình; luôn qua fact guard nguyên văn."""
    started = time.monotonic()
    if (settings.HUMANIZER_API_BASE or "").strip():
        try:
            model_result = humanize_with_model(text)
        except (HumanizerTimeoutError, HumanizerServerError) as exc:
            if _fallback_enabled():
                logger.warning(
                    "Humanizer model lỗi (%s) — chuyển Groq fallback.",
                    str(exc)[:200],
                )
                result = _groq_fallback(text, [WARN_MODEL_UNAVAILABLE])
                result.attempts = list(exc.attempts)
                return result
            raise
        latency = round(time.monotonic() - started, 2)

        def _model_pipeline(model_result: ModelHumanizeResult) -> PipelineResult:
            return PipelineResult(
                rewrite=model_result.rewrite,
                provider=model_result.provider,
                fact_check=model_result.fact_check,
                warnings=list(model_result.warnings),
                attempts=list(model_result.attempts),
                stats={"attempts": len(model_result.attempts), "latency_seconds": latency},
            )

        if model_result.guard_ok:
            return _model_pipeline(model_result)

        # Guard fail: lần cuối vẫn giữ kết quả nếu fallback không giúp được.
        if not _fallback_enabled():
            if not model_result.warnings:
                model_result.warnings.append(WARN_LOST_FACTS)
            return _model_pipeline(model_result)

        try:
            fallback = _groq_fallback(text, [WARN_MODEL_SWITCHED_TO_GROQ])
        except Exception as exc:
            logger.warning(
                "Groq fallback cũng thất bại (%s) — giữ kết quả model.", str(exc)[:200]
            )
            result = _model_pipeline(model_result)
            result.fact_check = model_result.fact_check
            if not result.warnings:
                result.warnings.append(WARN_LOST_FACTS)
            result.warnings.append(WARN_FALLBACK_ALSO_FAILED)
            return result
        if not fallback.fact_check["lost_tokens"]:
            return fallback
        # Fallback cũng mất fact: trả bản model (đã có lost_tokens + warning).
        return _model_pipeline(model_result)

    if _fallback_enabled():
        return _groq_fallback(text)
    raise HumanizerNotConfiguredError(
        "Chưa cấu hình HUMANIZER_API_BASE và Groq fallback cũng không khả dụng."
    )
