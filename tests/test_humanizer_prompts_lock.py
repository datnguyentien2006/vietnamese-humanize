"""Lock: humanizer inference prompts MUST equal training/task_prompts.py.

The web backend carries a frozen copy (app/services/humanizer_prompts.py)
because deployment packages ship only web/backend/, but a mismatch between
the training prompt and the inference prompt collapses generation quality.
This test imports both and fails if they ever diverge — change them together.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "web" / "backend"

sys.path.insert(0, str(BACKEND))

from app.services.humanizer_prompts import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    build_user_prompt,
)


def _training_module():
    sys.path.insert(0, str(ROOT))
    return importlib.import_module("training.task_prompts")


def test_system_prompt_matches_training() -> None:
    training = _training_module()

    assert SYSTEM_PROMPT == training.SYSTEM_PROMPT


def test_user_template_matches_training() -> None:
    training = _training_module()

    assert USER_TEMPLATE == training.USER_TEMPLATE


def test_user_template_wraps_the_text_in_original_tags() -> None:
    assert USER_TEMPLATE.endswith("<ORIGINAL>\n{text}\n</ORIGINAL>")
    assert USER_TEMPLATE.count("{text}") == 1

    rendered = build_user_prompt("Giá cổ phiếu tăng 12%.")
    assert "<ORIGINAL>\nGiá cổ phiếu tăng 12%.\n</ORIGINAL>" in rendered
    assert "12%" in rendered  # verbatim passthrough, no % escaping


def test_prompts_are_nonempty_and_single_sourced() -> None:
    # Guard against an empty-string regression that would silently degrade
    # the served model's task definition.
    assert SYSTEM_PROMPT.strip() != ""
    assert "100%" in SYSTEM_PROMPT
    assert "trả về" in SYSTEM_PROMPT and "không giải thích" in SYSTEM_PROMPT
