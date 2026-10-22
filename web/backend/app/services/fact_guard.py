"""Mechanical fact-preservation guard, shared by the web LLM pipelines.

`rewriter.py` uses the per-edit compare (`fact_losses`) while the v1.3
whole-text humanizer (`humanizer_model.py`) uses the whole-text diff
(`diff_fact_tokens`). Both share one definition of a "fact token" so a
dropped number or date is caught the same way on every path.
"""

from __future__ import annotations

import re
from collections import Counter

# Date tokens like 22/10/2025 must survive edits verbatim.
_DATE_TOKEN_RE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
# Plain numeric tokens: canonical compare ignores thousand/decimal separators
# so "1.850" == "1,850" == "1850", but a dropped number is caught.
_NUM_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)*")


def fact_tokens(text: str) -> Counter:
    """Counter of verifiable data tokens (dates + canonical numbers) in text."""
    tokens: Counter = Counter()
    for match in _DATE_TOKEN_RE.findall(text):
        tokens[match] += 1
    residue = _DATE_TOKEN_RE.sub(" ", text)
    for match in _NUM_TOKEN_RE.findall(residue):
        canonical = match.replace(".", "").replace(",", "")
        tokens[canonical] += 1
    return tokens


def _ordered_unique_tokens(text: str) -> list[str]:
    """Tokens of `text`, each once, in first-occurrence order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for date_match in _DATE_TOKEN_RE.finditer(text):
        token = date_match.group()
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    residue = _DATE_TOKEN_RE.sub(" ", text)
    for num_match in _NUM_TOKEN_RE.finditer(residue):
        canonical = num_match.group().replace(".", "").replace(",", "")
        if canonical not in seen:
            seen.add(canonical)
            ordered.append(canonical)
    return ordered


def fact_losses(find: str, replace: str) -> list[str]:
    """Data tokens present in `find` that vanished in `replace`."""
    before = fact_tokens(find)
    before.subtract(fact_tokens(replace))
    return [token for token, deficit in before.items() if deficit > 0]


def diff_fact_tokens(original: str, rewritten: str) -> dict[str, list[str]]:
    """Whole-text fact compare for model rewrites.

    Returns lost tokens (in first-occurrence order in `original`) and added
    tokens (in first-occurrence order in `rewritten`). Lost tokens are a hard
    signal that the rewrite dropped data.
    """
    before = fact_tokens(original)
    after = fact_tokens(rewritten)
    lost: list[str] = []
    for token in _ordered_unique_tokens(original):
        if after[token] < before[token]:
            lost.append(token)
    original_set = set(_ordered_unique_tokens(original))
    added: list[str] = []
    for token in _ordered_unique_tokens(rewritten):
        if before[token] < after[token] and token not in original_set:
            added.append(token)
    return {"lost_tokens": lost, "added_tokens": added}
