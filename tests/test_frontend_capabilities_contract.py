"""Frontend optional features must follow the backend capability contract (v1.3)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "web" / "frontend"


def read_frontend(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_frontend_defines_and_fetches_the_health_capability_contract() -> None:
    types = read_frontend("lib/types.ts")
    api = read_frontend("lib/api.ts")

    assert "export interface HealthResponse" in types
    assert "capabilities:" in types
    assert "humanize: boolean" in types
    assert "contributions: boolean" in types
    assert "export async function fetchHealth()" in api
    assert "`${API_BASE}/api/health`" in api
    assert "handleResponse<HealthResponse>(res)" in api
    # v1.3: the humanize API is the primary POST path.
    assert "export async function humanizeText(text: string): Promise<HumanizeResponse>" in api
    assert "`${API_BASE}/api/humanize`" in api


def test_optional_frontend_features_fail_closed_without_blocking_humanize() -> None:
    capability_nav = read_frontend("components/CapabilityNav.tsx")
    layout = read_frontend("app/layout.tsx")
    home = read_frontend("app/page.tsx")
    contribute = read_frontend("app/contribute/page.tsx")
    api = read_frontend("lib/api.ts")

    assert '"use client"' in capability_nav
    assert "{ humanize: false, contributions: false }" in capability_nav
    assert "fetchHealth()" in capability_nav
    assert "health.capabilities.humanize === true" in capability_nav
    assert "health.capabilities.contributions === true" in capability_nav
    assert "capabilities.contributions &&" in capability_nav

    assert "<CapabilityProvider>" in layout
    assert "<CapabilityNav />" in layout
    assert "<Analytics />" in layout

    # Fail-closed: banner + disabled submit while health says humanize is off.
    assert (
        "Chưa bật tính năng Humanize trên server. "
        "Đặt HUMANIZER_API_BASE hoặc GROQ_API_KEY rồi thử lại." in home
    )
    assert "capabilities.humanize === true" in home
    assert "Đang humanize... có thể mất khoảng 20 giây." in home

    # The v1.2 lint-first flow is gone from the homepage and API client.
    for forbidden in (
        "ReportRefiner",
        "RewritePanel",
        "IssueCard",
        "IssueList",
        "scanReport",
        "refineSentence",
        "suggestFix(",
        "rewriteText",
        "Giảm đạo văn AI",
    ):
        assert forbidden not in home
    for forbidden_api in (
        "rewriteText(",
        "suggestFix(",
        "scanReport",
        "refineSentence",
        "fetchVocabulary(",
        "fetchPatterns(",
        "fetchSkills",
    ):
        assert forbidden_api not in api

    # The untouched contribute page keeps its own capability gate and
    # imports fetchSkills from the dedicated contribute API module.
    assert "const capabilities = useCapabilities()" in contribute
    assert "if (!capabilities.contributions)" in contribute
    assert "<ContributeForm skills={skills} />" in contribute
    assert 'fetchSkills } from "../../lib/contributeApi"' in contribute


def test_frontend_keeps_analytics_root_only_without_custom_events() -> None:
    frontend_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in FRONTEND.rglob("*")
        if path.suffix in {".ts", ".tsx"}
        and ".next" not in path.parts
        and "node_modules" not in path.parts
    )
    layout = read_frontend("app/layout.tsx")

    assert 'import { Analytics } from "@vercel/analytics/react";' in layout
    assert layout.count("<Analytics />") == 1
    assert "track(" not in frontend_sources
    assert "event(" not in frontend_sources
