"""Client cho mô hình humanizer chuyên biệt (vLLM, tương thích OpenAI).

Khác với pipeline Groq (trả về JSON edits), mô hình chuyên biệt được huấn
luyện để trả về VĂN BẢN HOÀN CHỈNH ở dạng plain text. Do đó đường dùng này:

1. Gọi ``POST {HUMANIZER_API_BASE}/chat/completions`` bằng httpx (KHÔNG dùng
   Groq SDK).
2. Prompt lấy cứng từ ``app.services.humanizer_prompts`` — bản冻结 copy của
   ``training/task_prompts.py`` (lock bởi tests/test_humanizer_prompts_lock.py).
   Không được đổi prompt ở đây, nếu không mô hình nhận nhiệm vụ khác lúc
   huấn luyện → chất lượng sụp đổ.
3. Fact guard nguyên văn: so từng token số liệu/ngày giữa bản gốc và bản
   đã viết lại; nếu thiếu → thử lại một lần (temperature +0.1); vẫn thiếu →
   trả kết quả kèm fact_check.lost_tokens + warnings (không bao giờ nuốt
   lỗi fact vì hiệu năng).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.services import fact_guard
from app.services.humanizer_prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Lần đầu dùng temperature "chuẩn"; lần thử lại tăng nhẹ để mô hình rời khỏi
# vùng bước cùng một lỗi.
_TEMPERATURES = (0.5, 0.6)

WARN_LOST_FACTS = (
    "Cảnh báo: một số số liệu/ngày trong văn bản gốc không còn xuất hiện "
    "trong bản đã humanize. Kiểm tra lại trước khi dùng."
)


class HumanizerNotConfiguredError(Exception):
    """HUMANIZER_API_BASE chưa được cấu hình."""


class HumanizerServerError(Exception):
    """Gọi endpoint humanizer thất bại (mạng, HTTP, phản hồi rỗng)."""

    def __init__(self, message: str, attempts: list[dict] | None = None):
        super().__init__(message)
        self.attempts: list[dict] = attempts or []


class HumanizerTimeoutError(HumanizerServerError):
    """Endpoint humanizer quá HUMANIZER_TIMEOUT_SECONDS."""


@dataclass
class ModelHumanizeResult:
    """Kết quả một lượt chạy humanizer model (có thể fail fact guard)."""

    rewrite: str
    provider: str = "humanizer-model"
    fact_check: dict[str, list[str]] = field(
        default_factory=lambda: {"lost_tokens": [], "added_tokens": []}
    )
    warnings: list[str] = field(default_factory=list)
    # attempts[] chỉ được bóc ra cho client khi DEBUG_ERRORS bật (router lo).
    attempts: list[dict] = field(default_factory=list)
    guard_ok: bool = True


def _request_payload(text: str, temperature: float) -> dict:
    return {
        "model": settings.HUMANIZER_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(text)},
        ],
    }


def _extract_content(data: dict) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def humanize_with_model(text: str) -> ModelHumanizeResult:
    """Gọi humanizer model, trả văn bản viết lại + fact guard nguyên văn."""
    base = (settings.HUMANIZER_API_BASE or "").strip().rstrip("/")
    if not base:
        raise HumanizerNotConfiguredError(
            "HUMANIZER_API_BASE chưa được cấu hình — không gọi được mô hình."
        )

    url = f"{base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = (settings.HUMANIZER_API_KEY or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    attempts: list[dict] = []
    last_rewrite: str | None = None
    last_fact_check: dict[str, list[str]] = {"lost_tokens": [], "added_tokens": []}

    for attempt_index, temperature in enumerate(_TEMPERATURES, start=1):
        started = time.monotonic()
        payload = _request_payload(text, temperature)
        try:
            with httpx.Client(timeout=settings.HUMANIZER_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            elapsed = round(time.monotonic() - started, 2)
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "timeout",
                    "detail": str(exc)[:300],
                    "latency_seconds": elapsed,
                }
            )
            raise HumanizerTimeoutError(
                f"Humanizer endpoint vượt {settings.HUMANIZER_TIMEOUT_SECONDS:g}s timeout.",
                attempts=attempts,
            ) from exc
        except httpx.HTTPError as exc:
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "network_error",
                    "detail": str(exc)[:300],
                }
            )
            raise HumanizerServerError(
                "Không kết nối được humanizer endpoint.",
                attempts=attempts,
            ) from exc

        if response.status_code in (401, 403):
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "auth_error",
                    "status": response.status_code,
                }
            )
            raise HumanizerServerError(
                "Humanizer endpoint từ chối API key (HTTP "
                f"{response.status_code}). Kiểm tra HUMANIZER_API_KEY.",
                attempts=attempts,
            )
        if 400 <= response.status_code < 500:
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "http_error",
                    "status": response.status_code,
                    "detail": response.text[:200],
                }
            )
            raise HumanizerServerError(
                f"Humanizer endpoint trả HTTP {response.status_code}.",
                attempts=attempts,
            )
        if response.status_code >= 500:
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "server_error",
                    "status": response.status_code,
                    "detail": response.text[:200],
                }
            )
            continue

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "bad_json",
                    "detail": response.text[:200],
                }
            )
            continue

        content = _extract_content(data)
        if content is None:
            attempts.append(
                {
                    "attempt": attempt_index,
                    "temperature": temperature,
                    "kind": "empty_response",
                }
            )
            continue

        attempt_record = {
            "attempt": attempt_index,
            "temperature": temperature,
            "latency_seconds": round(time.monotonic() - started, 2),
        }
        fact_check = fact_guard.diff_fact_tokens(text, content)
        if not fact_check["lost_tokens"]:
            attempt_record["kind"] = "ok"
            attempts.append(attempt_record)
            return ModelHumanizeResult(
                rewrite=content,
                fact_check=fact_check,
                warnings=[],
                attempts=attempts,
                guard_ok=True,
            )
        attempt_record["kind"] = "fact_loss"
        attempt_record["lost_tokens"] = fact_check["lost_tokens"]
        attempts.append(attempt_record)
        last_rewrite = content
        last_fact_check = fact_check

    if last_rewrite is None:
        raise HumanizerServerError(
            "Humanizer endpoint không trả được văn bản nào. "
            "Thử lại sau hoặc kiểm tra endpoint.",
            attempts=attempts,
        )

    # Guard fail sau cả hai lượt: KHÔNG nuốt lỗi — trả kèm lost_tokens.
    return ModelHumanizeResult(
        rewrite=last_rewrite,
        fact_check=last_fact_check,
        warnings=[WARN_LOST_FACTS],
        attempts=attempts,
        guard_ok=False,
    )
