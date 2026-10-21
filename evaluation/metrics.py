# -*- coding: utf-8 -*-
"""Static (deterministic) metrics for the humanizer evaluation harness.

Three metric families, all computed without any LLM call:

1. Meaning preservation  -- constrain to verifiable surface facts: numbers,
   dates, quoted titles and other entity-like tokens. The humanizer's hard
   rule is "keep 100% of the information", so any missing or altered
   number/date/entity is a defect, not a style choice.
2. Readability           -- sentence-length distribution, lexical diversity
   and length change. Human Vietnamese prose tends to vary sentence length
   more (higher stdev) and to lean on shorter sentences than AI prose.
3. Mechanical-style      -- the project's own linter issue counts on the
   original vs. the rewritten text, plus the density of known
   "robotic connector" phrases per 100 words.

All functions are pure and UTF-8 in / UTF-8 out.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import asdict, dataclass, field

# ---------------------------------------------------------------- words

_WORD_RE = re.compile(r"[^\W\d_]+(?:-\d+)?", re.UNICODE)


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def word_count(text: str) -> int:
    return len(words(text))


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------- sentences

_SENT_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)|\n+")


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(_norm(text)) if p.strip()]
    return parts


# ---------------------------------------------------------------- entities

# Numbers: percentages, decimals with Vietnamese separators, canon digits.
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
# Dates / periods.
_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    re.compile(r"\b(?:Q[1-4])\b"),
    re.compile(r"năm \d{4}"),
    re.compile(r"tháng \d{1,2}"),
    re.compile(r"\d{4}-\d{4}"),
]
# Acronyms and straight uppercase code-like tokens.
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:\d+)?\b")

# Quoted phrases (Vietnamese or latin quotes) often carry names/titles.
# All quote characters are written as unicode escapes so the Python string
# delimiters stay unambiguous.
_Q_CHARS = "\u201c\u201d\u2018\u2019\u0022\u0027"
_QUOTED_RE = re.compile(
    "[" + _Q_CHARS + "]([^" + _Q_CHARS + "]{2,60})[" + _Q_CHARS + "]"
)


def extract_entities(text: str) -> list[str]:
    """Collect verifiable surface facts as a sorted list of normalised strings."""
    t = _norm(text)
    found: list[str] = []
    found.extend(m.group(0) for m in _NUM_RE.finditer(t))
    for pat in _DATE_PATTERNS:
        found.extend(m.group(0) for m in pat.finditer(t))
    found.extend(m.group(0) for m in _ACRONYM_RE.finditer(t))
    found.extend(m.group(1) for m in _QUOTED_RE.finditer(t))
    # De-duplicate; keep case for quoted/NEs (they are data).
    return sorted(set(found))


@dataclass
class MeaningReport:
    entities_total: int
    entities_missing: list[str] = field(default_factory=list)
    entities_added: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        if self.entities_total == 0:
            return 1.0
        return max(0.0, 1.0 - len(self.entities_missing) / self.entities_total)


def meaning_preservation(original: str, rewritten: str) -> MeaningReport:
    """Missing = an entity in the original that vanished; added = new entity."""
    before = extract_entities(original)
    after = set(extract_entities(rewritten))
    # Numbers like 1,5 vs 1.5 vs 1500 are canonicalised numerically for diff.
    after_norm = {_canon(e) for e in after}
    missing = [e for e in before if _canon(e) not in after_norm]
    before_norm = {_canon(e) for e in before}
    added = sorted(_canon(e) for e in after if _canon(e) not in before_norm)
    return MeaningReport(
        entities_total=len(set(before)),
        entities_missing=sorted(set(missing)),
        entities_added=added,
    )


def _canon(entity: str) -> str:
    """Plain digits stay plain (separator-insensitive); text keeps letters."""
    plain = entity.replace(".", "").replace(",", "")
    if plain.isdigit():
        return plain
    return entity.lower()


# ---------------------------------------------------------------- readability


@dataclass
class ReadabilityReport:
    word_count: int
    sentence_count: int
    sentence_len_mean: float
    sentence_len_stdev: float
    type_token_ratio: float


def readability(text: str) -> ReadabilityReport:
    sents = sentences(text)
    lens = [word_count(s) for s in sents if word_count(s) > 0]
    toks = [w.lower() for w in words(text)]
    return ReadabilityReport(
        word_count=len(toks),
        sentence_count=len(lens),
        sentence_len_mean=round(statistics.fmean(lens), 2) if lens else 0.0,
        sentence_len_stdev=round(statistics.pstdev(lens), 2) if len(lens) > 1 else 0.0,
        type_token_ratio=round(len(set(toks)) / len(toks), 3) if toks else 0.0,
    )


# ---------------------------------------------------------------- mechanical style

ROBOTIC_CONNECTORS = [
    "tổng thể",
    "trong bối cảnh đó",
    "bên cạnh đó",
    "điều này cho thấy",
    "nói cách khác",
    "để đạt được điều này",
    "quan trọng là",
    "nhìn chung",
    "từ đó cho thấy",
    "chính vì vậy",
    "như vậy có thể thấy",
    "ngoài ra",
    "đồng thời",
    "theo đó",
    "dựa trên cơ sở",
    "một cách đáng kể",
    "có thể khẳng định",
    "điều này đồng nghĩa",
    "trong thực tế",
    "đáng chú ý",
]


def robotic_density(text: str) -> float:
    """Mechanical-connector hits per 100 words (case-insensitive)."""
    t = _norm(text).lower()
    wc = word_count(t)
    if wc == 0:
        return 0.0
    hits = sum(t.count(" " + p) + (1 if t.startswith(p) else 0) for p in ROBOTIC_CONNECTORS)
    return round(hits * 100.0 / wc, 2)


# ---------------------------------------------------------------- overall


def static_report(
    original: str, rewritten: str, issue_count_before: int, issue_count_after: int
) -> dict:
    before = readability(original)
    after = readability(rewritten)
    meaning = meaning_preservation(original, rewritten)
    return {
        "meaning": asdict(meaning) | {"score": round(meaning.score, 3)},
        "readability_before": asdict(before),
        "readability_after": asdict(after),
        "sentence_len_stdev_delta": round(
            after.sentence_len_stdev - before.sentence_len_stdev, 2
        ),
        "length_ratio": round(after.word_count / before.word_count, 3)
        if before.word_count
        else 0.0,
        "robotic_density_before": robotic_density(original),
        "robotic_density_after": robotic_density(rewritten),
        "lint_issues_before": issue_count_before,
        "lint_issues_after": issue_count_after,
    }
