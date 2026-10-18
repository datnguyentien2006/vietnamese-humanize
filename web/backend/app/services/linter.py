from __future__ import annotations

from vietnamese_writing_skills import __version__
from vietnamese_writing_skills.cli.lint import lint_text
from vietnamese_writing_skills.core.patterns import pattern_index

from app.schemas import (
    IssueItem,
    IssueOccurrence,
    LintResponse,
    LintSummary,
    PatternItem,
)


# ============================================================
# Fallback helpers: tự tính paragraph/sentence/position từ text
# khi package không trả về đủ dữ liệu (bug v1.2).
# ============================================================


def _compute_paragraph_bounds(text: str, position: int) -> tuple[int, int]:
    """Tính (start, end) của đoạn văn chứa position.

    Đoạn văn được ngăn cách bởi dòng trống (\\n\\n).
    """
    if not text:
        return 0, 0
    position = max(0, min(position, len(text)))

    prev_sep = text.rfind("\n\n", 0, position)
    start = prev_sep + 2 if prev_sep >= 0 else 0

    next_sep = text.find("\n\n", position)
    end = next_sep if next_sep >= 0 else len(text)

    while start < position and text[start] in " \t\n":
        start += 1
    while end > position and text[end - 1] in " \t\n":
        end -= 1

    return start, end


def _compute_sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Tính (start, end) của câu chứa position."""
    if not text:
        return 0, 0
    position = max(0, min(position, len(text)))

    start = position
    while start > 0:
        prev = text[start - 1]
        if prev == "\n":
            break
        if prev in ".!?":
            nxt_index = start
            if nxt_index < len(text) and text[nxt_index] in " \t":
                k = nxt_index
                while k < len(text) and text[k] in " \t":
                    k += 1
                if k >= len(text) or text[k].isupper() or text[k] in '"\'([“‘':
                    break
            elif nxt_index >= len(text) or text[nxt_index] == "\n":
                break
        start -= 1
    while start < position and text[start] in " \t":
        start += 1

    end = max(start, position)
    while end < len(text):
        c = text[end]
        if c == "\n":
            break
        if c in ".!?":
            nxt_index = end + 1
            if nxt_index >= len(text) or text[nxt_index] == "\n":
                end += 1
                break
            if text[nxt_index] in " \t":
                k = nxt_index
                while k < len(text) and text[k] in " \t":
                    k += 1
                if (
                    k >= len(text)
                    or text[k] == "\n"
                    or text[k].isupper()
                    or text[k] in '"\'([“‘'
                ):
                    end += 1
                    break
        end += 1

    return start, end


def _position_from_line_column(text: str, line: int, column: int) -> int:
    """Chuyển (line, column) 1-indexed thành position 0-indexed."""
    if line < 1 or column < 1:
        return -1
    pos = 0
    current_line = 1
    while current_line < line and pos < len(text):
        next_nl = text.find("\n", pos)
        if next_nl < 0:
            return -1
        pos = next_nl + 1
        current_line += 1
    if current_line != line:
        return -1
    result = pos + column - 1
    if result < 0 or result > len(text):
        return -1
    return result


def _find_position(text: str, item: dict) -> int:
    """Tìm position của issue trong text gốc.

    Chiến lược ưu tiên:
    1. item.start (nếu có và hợp lệ)
    2. occurrence[0].start
    3. occurrence[0].matched_text (tìm trong text)
    4. line/column (tính position)
    5. excerpt (tìm trong text)
    """
    # 1. item.start
    start = item.get("start", 0)
    end = item.get("end", 0)
    if start and end and 0 < start < end <= len(text):
        return start

    # 2. occurrence[0].start
    occurrences = item.get("occurrences", [])
    if occurrences:
        occ = occurrences[0]
        occ_start = occ.get("start", 0)
        occ_end = occ.get("end", 0)
        if occ_start and occ_end and 0 < occ_start < occ_end <= len(text):
            return occ_start

        # 3. matched_text
        matched = occ.get("matched_text", "")
        if matched:
            idx = text.find(matched)
            if idx >= 0:
                return idx

    # 4. line/column
    line = item.get("line", 0)
    column = item.get("column", 0)
    if line and column:
        pos = _position_from_line_column(text, line, column)
        if pos >= 0:
            return pos

    # 5. excerpt
    excerpt = item.get("excerpt", "")
    if excerpt:
        clean = excerpt.strip("… ")
        if clean:
            idx = text.find(clean)
            if idx >= 0:
                return idx

    return -1


def _occurrence_from_dict(item: dict) -> IssueOccurrence:
    return IssueOccurrence(
        line=item.get("line", 1),
        column=item.get("column", 1),
        excerpt=item.get("excerpt", ""),
        matched_text=item.get("matched_text", ""),
        start=item.get("start", 0),
        end=item.get("end", 0),
        sentence=item.get("sentence", ""),
        sentence_start=item.get("sentence_start", 0),
        sentence_end=item.get("sentence_end", 0),
        paragraph=item.get("paragraph", ""),
        paragraph_start=item.get("paragraph_start", 0),
        paragraph_end=item.get("paragraph_end", 0),
    )


def _enrich_occurrence(occ: dict, text: str, fallback_position: int) -> dict:
    """Bổ sung paragraph/start/end/sentence cho một occurrence nếu thiếu."""
    enriched = dict(occ)

    # Tìm position
    position = -1
    occ_start = enriched.get("start", 0)
    occ_end = enriched.get("end", 0)
    if occ_start and occ_end and 0 < occ_start < occ_end <= len(text):
        position = occ_start
    else:
        matched = enriched.get("matched_text", "")
        if matched:
            idx = text.find(matched, max(0, fallback_position))
            if idx < 0:
                idx = text.find(matched)
            if idx >= 0:
                position = idx
        if position < 0:
            position = fallback_position

    if position < 0:
        return enriched

    # Paragraph
    para = enriched.get("paragraph", "")
    if not para:
        p_start, p_end = _compute_paragraph_bounds(text, position)
        enriched["paragraph"] = text[p_start:p_end]
        enriched["paragraph_start"] = p_start
        enriched["paragraph_end"] = p_end

    # Sentence
    sent = enriched.get("sentence", "")
    if not sent:
        s_start, s_end = _compute_sentence_bounds(text, position)
        enriched["sentence"] = text[s_start:s_end]
        enriched["sentence_start"] = s_start
        enriched["sentence_end"] = s_end

    # Start/end
    if not enriched.get("start") or not enriched.get("end"):
        matched = enriched.get("matched_text", "")
        if matched:
            idx = text.find(matched, max(0, position))
            if idx < 0:
                idx = text.find(matched)
            if idx >= 0:
                enriched["start"] = idx
                enriched["end"] = idx + len(matched)
        if not enriched.get("start"):
            enriched["start"] = position
            enriched["end"] = position

    return enriched


def run_linter(text: str, skills: list[str] | None = None) -> LintResponse:
    skills_set = set(skills) if skills else None
    raw_issues = lint_text(text, skills=skills_set)

    issues: list[IssueItem] = []
    finding_counts = {"error": 0, "warning": 0, "preference": 0, "heuristic": 0}

    for item in raw_issues:
        # Tìm position của issue trong text gốc
        position = _find_position(text, item)

        # Enrich occurrences
        raw_occurrences = item.get("occurrences", [])
        enriched_occurrences = [
            _enrich_occurrence(occ, text, position if position >= 0 else 0)
            for occ in raw_occurrences
        ]

        # Item-level fields
        para = item.get("paragraph", "")
        para_start = item.get("paragraph_start", 0)
        para_end = item.get("paragraph_end", 0)
        sent = item.get("sentence", "")
        sent_start = item.get("sentence_start", 0)
        sent_end = item.get("sentence_end", 0)
        start = item.get("start", 0)
        end = item.get("end", 0)

        if position >= 0:
            if not para:
                para_start, para_end = _compute_paragraph_bounds(text, position)
                para = text[para_start:para_end]
            if not sent:
                sent_start, sent_end = _compute_sentence_bounds(text, position)
                sent = text[sent_start:sent_end]
            if not start or not end:
                # Thử matched_text của occurrence đầu tiên
                # FIX: enriched_occurrences là list các dict, không phải Pydantic object
                matched = ""
                if enriched_occurrences:
                    matched = enriched_occurrences[0].get("matched_text", "")
                if matched:
                    idx = text.find(matched, position)
                    if idx < 0:
                        idx = text.find(matched)
                    if idx >= 0:
                        start = idx
                        end = idx + len(matched)
                if not start:
                    start = position
                    end = position

        issue = IssueItem(
            pattern_id=item["pattern_id"],
            finding_type=item["finding_type"],
            severity=item["severity"],
            confidence=item["confidence"],
            scope=item["scope"],
            line=item["line"],
            column=item["column"],
            excerpt=item["excerpt"],
            message=item["message"],
            suggestion=item["suggestion"],
            occurrences=[_occurrence_from_dict(o) for o in enriched_occurrences],
            start=start,
            end=end,
            sentence=sent,
            sentence_start=sent_start,
            sentence_end=sent_end,
            paragraph=para,
            paragraph_start=para_start,
            paragraph_end=para_end,
        )
        issues.append(issue)

        ftype = item["finding_type"]
        if ftype in finding_counts:
            finding_counts[ftype] += 1

    summary = LintSummary(
        total=len(issues),
        error=finding_counts["error"],
        warning=finding_counts["warning"],
        preference=finding_counts["preference"],
        heuristic=finding_counts["heuristic"],
    )

    return LintResponse(version=__version__, summary=summary, issues=issues)


def get_patterns_list() -> list[PatternItem]:
    index = pattern_index()
    patterns: list[PatternItem] = []

    for pat in index.values():
        strategies = pat.get("rewrite_strategy", [])
        if isinstance(strategies, list):
            strategy = strategies[0] if strategies else ""
        else:
            strategy = str(strategies)

        item = PatternItem(
            id=pat["id"],
            name=pat.get("name", ""),
            skill=pat.get("skill", ""),
            category=pat.get("category", ""),
            finding_type=pat.get("finding_type", "heuristic"),
            severity=pat.get("severity", "low"),
            summary=pat.get("summary", ""),
            why_it_matters=pat.get("why_it_matters", ""),
            rewrite_strategy=strategy,
        )
        patterns.append(item)

    return patterns