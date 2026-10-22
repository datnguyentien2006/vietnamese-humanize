from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings, settings

_DISABLED_DETAIL = "Capability is disabled."
_ADMIN_KEY_PLACEHOLDER_MARKERS = (
    "changethis",
    "changeme",
    "placeholder",
    "replaceme",
    "replacewith",
    "youradminapikey",
)


def _has_value(value: str | None) -> bool:
    return bool(value and value.strip())


def humanize_enabled(config: Settings | None = None) -> bool:
    """True khi `/api/humanize` có ít nhất một provider dùng được.

    Ưu tiên mô hình chuyên biệt (HUMANIZER_API_BASE); nếu chưa phục vụ mô hình
    thì pipeline Groq fallback đảm nhiệm, nhưng chỉ khi HUMANIZER_FALLBACK_GROQ
    và GROQ_API_KEY cùng bật. Fail-closed: thiếu cả hai → False → 503.
    """
    if config is None:
        config = settings
    if _has_value(config.HUMANIZER_API_BASE):
        return True
    return bool(config.HUMANIZER_FALLBACK_GROQ) and _has_value(config.GROQ_API_KEY)


def validate_capability_settings(config: Settings | None = None) -> None:
    if config is None:
        config = settings

    if config.REWRITE_ENABLED and not _has_value(config.GROQ_API_KEY):
        raise ValueError("GROQ_API_KEY is required when REWRITE_ENABLED is true.")

    if _has_value(config.HUMANIZER_API_BASE) and config.HUMANIZER_TIMEOUT_SECONDS <= 0:
        raise ValueError(
            "HUMANIZER_TIMEOUT_SECONDS must be positive when HUMANIZER_API_BASE "
            "is configured."
        )

    if config.ADMIN_API_ENABLED:
        admin_key = (config.ADMIN_API_KEY or "").strip()
        normalized_key = "".join(
            character for character in admin_key.lower() if character.isalnum()
        )
        is_placeholder = any(
            marker in normalized_key for marker in _ADMIN_KEY_PLACEHOLDER_MARKERS
        )
        if len(admin_key) < 32 or is_placeholder:
            raise ValueError(
                "ADMIN_API_KEY must be non-placeholder and at least 32 characters "
                "when ADMIN_API_ENABLED is true."
            )


def require_humanize_enabled() -> None:
    if not humanize_enabled():
        raise HTTPException(status_code=503, detail=_DISABLED_DETAIL)


def require_contributions_enabled() -> None:
    if not settings.CONTRIBUTIONS_ENABLED:
        raise HTTPException(status_code=503, detail=_DISABLED_DETAIL)


def require_admin_enabled() -> None:
    if not settings.ADMIN_API_ENABLED:
        raise HTTPException(status_code=503, detail=_DISABLED_DETAIL)


def capability_route_class(check: Callable[[], None]) -> type[APIRoute]:
    class CapabilityRoute(APIRoute):
        def get_route_handler(
            self,
        ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
            route_handler = super().get_route_handler()

            async def gated_route_handler(request: Request) -> Response:
                check()
                return await route_handler(request)

            return gated_route_handler

    return CapabilityRoute


def public_capabilities() -> dict[str, bool]:
    return {
        "humanize": humanize_enabled(),
        "contributions": settings.CONTRIBUTIONS_ENABLED,
    }
