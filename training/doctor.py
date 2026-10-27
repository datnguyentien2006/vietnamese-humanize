# -*- coding: utf-8 -*-
"""Readiness check for the humanizer pipeline (P0).

Answers the questions that decide whether you are looking at the fine-tuned
model or at the Groq fallback, without printing any secret:

    python training/doctor.py

Reports, in order: environment, which provider `/api/humanize` would actually
use today (mirroring ``app.capabilities.humanize_enabled``), the state of the
training dataset, and which training-only dependencies are missing.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "web" / "backend" / ".env"


def parse_env_file(path: Path) -> dict[str, str]:
    """Minimal ``KEY=VALUE`` parser; quoting and comments handled, no expansion."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        values[key.strip()] = value
    return values


def effective_settings() -> tuple[dict[str, str], str]:
    """Environment wins over .env, same as pydantic-settings."""
    file_values = parse_env_file(ENV_FILE)
    merged = dict(file_values)
    source = ".env"
    for key in (
        "HUMANIZER_API_BASE",
        "HUMANIZER_API_KEY",
        "HUMANIZER_MODEL",
        "HUMANIZER_FALLBACK_GROQ",
        "GROQ_API_KEY",
        "DEBUG_ERRORS",
    ):
        if os.environ.get(key):
            merged[key] = os.environ[key]
            source = "env + .env"
    return merged, source


def mask(secret: str | None) -> str:
    if not secret:
        return "(trống)"
    secret = secret.strip()
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}…{secret[-4:]} (dài {len(secret)})"


def provider_verdict(settings: dict[str, str]) -> tuple[str, str]:
    """Mirror app.capabilities.humanize_enabled() to predict the live provider."""
    base = (settings.get("HUMANIZER_API_BASE") or "").strip()
    fallback = (settings.get("HUMANIZER_FALLBACK_GROQ") or "true").strip().lower()
    fallback_on = fallback not in {"false", "0", "no", "off"}
    key = (settings.get("GROQ_API_KEY") or "").strip()

    if base:
        return "humanizer-model", f"HUMANIZER_API_BASE = {base}"
    if fallback_on and key:
        return "groq-fallback", "chưa có HUMANIZER_API_BASE → Groq trả lời mọi request"
    return "none (503)", "thiếu cả HUMANIZER_API_BASE và Groq fallback khả dụng"


def package_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("vietnamese-writing-skills")
    except Exception:  # noqa: BLE001 - metadata may be absent in a bare checkout
        return None


def pattern_count() -> int | None:
    try:
        import yaml

        total = 0
        for path in sorted((ROOT / "patterns").glob("*.yml")):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            total += len(document.get("patterns", []))
        return total
    except Exception:  # noqa: BLE001
        return None


def jsonl_stats(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def main() -> int:
    print("=" * 62)
    print(" Vietnamese Humanizer — doctor (P0)")
    print("=" * 62)
    print(f"python      : {sys.version.split()[0]} ({platform.system()} {platform.machine()})")
    print(f"repo root   : {ROOT}")
    print(f"package     : {package_version() or 'chưa cài (pip install -e .)'}")
    count = pattern_count()
    print(f"patterns    : {count if count is not None else 'không đọc được patterns/*.yml'}")

    settings, source = effective_settings()
    provider, reason = provider_verdict(settings)
    print("")
    print("-- Provider thực tế của /api/humanize " + "-" * 22)
    print(f"nguồn cấu hình : {source if ENV_FILE.is_file() else 'env (không có .env)'}")
    print(f"HUMANIZER_API_BASE : {settings.get('HUMANIZER_API_BASE') or '(trống)'}")
    print(f"HUMANIZER_MODEL    : {settings.get('HUMANIZER_MODEL') or 'humanizer-vi (mặc định)'}")
    print(f"HUMANIZER_API_KEY  : {mask(settings.get('HUMANIZER_API_KEY'))}")
    print(f"GROQ_API_KEY       : {mask(settings.get('GROQ_API_KEY'))}")
    print(f"HUMANIZER_FALLBACK_GROQ : {settings.get('HUMANIZER_FALLBACK_GROQ') or 'true (mặc định)'}")
    print(f"DEBUG_ERRORS       : {settings.get('DEBUG_ERRORS') or 'true (mặc định)'}")
    print(f"→ provider dự kiến : {provider}   ({reason})")

    print("")
    print("-- Dataset -------------------------------")
    sft = ROOT / "training" / "data" / "sft"
    train_rows = jsonl_stats(sft / "train.jsonl")
    val_rows = jsonl_stats(sft / "val.jsonl")
    print(f"train.jsonl : {train_rows} mẫu")
    print(f"val.jsonl   : {val_rows} mẫu")
    manifest_path = sft / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key in ("mode", "dirtying", "pairs", "rejected", "documents", "by_register"):
                if key in manifest:
                    print(f"  {key:12s}: {manifest[key]}")
        except Exception:  # noqa: BLE001
            print("  manifest.json không đọc được")

    print("")
    print("-- Dependency train (chỉ cần khi train) ---")
    for module, hint in (
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("peft", "peft"),
        ("trl", "trl"),
        ("datasets", "datasets"),
        ("bitsandbytes", "bitsandbytes"),
    ):
        installed = importlib.util.find_spec(module) is not None
        print(f"{module:14s}: {'ok' if installed else 'thiếu — pip install ' + hint}")

    warnings: list[str] = []
    if provider != "humanizer-model":
        warnings.append(
            "Chưa phục vụ model local: mọi kết quả hiện do Groq trả lời, "
            "nên đánh giá 'chưa tự nhiên' đang nói về pipeline Groq."
        )
    if train_rows == 0:
        warnings.append("Chưa có train.jsonl → chưa train được gì (chạy --mode synthesize).")
    if (settings.get("DEBUG_ERRORS") or "true").strip().lower() in {"true", "1", "yes"}:
        warnings.append("DEBUG_ERRORS đang bật — chỉ dùng khi dev, tắt khi deploy.")
    if warnings:
        print("")
        print("-- Cảnh báo ------------------------------")
        for warning in warnings:
            print(f"  • {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
