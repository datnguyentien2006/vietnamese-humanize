from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from vietnamese_writing_skills.core.llm_judge import (
    LLM_JUDGED_PATTERN_IDS,
    is_llm_judge_available,
    judge_text,
)
from vietnamese_writing_skills.core.paths import data_location, repository_root
from vietnamese_writing_skills.core.patterns import iter_patterns, pattern_index

FENCE_RE = re.compile(r"^(\s*)([`~]{3,})(.*)$")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_START_RE = re.compile(r"(?:https?://|www\.)", flags=re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
FILENAME_RE = re.compile(
    r"\b[\w.-]+\.(?:md|txt|yml|yaml|json|py|ts|tsx|js|jsx|mjs|cjs|html|css|"
    r"pdf|docx|xlsx|csv|png|jpg|jpeg|gif|svg|webp|zip|toml|ini|cfg|sh|bat|"
    r"exe|dll|so|rs|go|java|kt|rb|php|xml|env|lock)\b",
    flags=re.IGNORECASE,
)
ABBREV_RE = re.compile(r"\b(?:TP|P|Q|TT|GS|PGS|TS|ThS|BS|CN)\.[A-Za-zÀ-ỹĐđ.]+")
IDENTIFIER_RE = re.compile(r"\b(?:[A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+|[A-Za-z]+::[A-Za-z:]+)\b")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", flags=re.UNICODE)
WORD_RE = re.compile(r"[\wÀ-ỹĐđ]+", flags=re.UNICODE)
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_VIETNAMESE_VOWEL_MARKS_RE = re.compile(
    r"[ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]"
)
SMART_QUOTE_OPEN = "\u201c"
SMART_QUOTE_CLOSE = "\u201d"
URL_STOP_CHARS = frozenset("<>\"'«»") | {SMART_QUOTE_OPEN, SMART_QUOTE_CLOSE}
PRONOUN_GROUPS = (
    ("bạn", "quý khách"),
    ("tôi", "chúng tôi", "chúng ta"),
)
RESULT_AUXILIARIES = {"sẽ", "đã", "đang", "bị", "được", "phải", "là", "chưa"}
RESULT_SUBJECTS = (
    ("công", "ty"),
    ("dữ", "liệu"),
    ("cuộc", "họp"),
)
REPEATED_FUNCTION_WORDS = {
    "sẽ",
    "đã",
    "đang",
    "là",
    "được",
    "bị",
    "của",
    "và",
    "hoặc",
    "nhưng",
    "thì",
    "mà",
    "cho",
    "với",
    "trong",
    "không",
    "có",
    "các",
    "những",
    "một",
    "khi",
    "nếu",
    "để",
    "rằng",
    "vì",
    "rất",
    "cũng",
    "vẫn",
    "phải",
    "cần",
    "nên",
    "hay",
    "này",
    "đó",
    "từ",
    "đến",
    "tại",
    "do",
    "bởi",
}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
FINDING_TYPES = ("error", "warning", "preference", "heuristic")
SPECIAL_PATTERN_IDS = {
    "VI-GRA-C06",
    "VI-GRA-L01",
    "VI-GRA-P04",
    "VI-HUM-D05",
    "VI-HUM-D06",
    "VI-HUM-D07",
    "VI-HUM-D08",
    "VI-HUM-D09",
    "VI-HUM-L07",
    "VI-HUM-S01",
    "VI-HUM-S04",
    "VI-HUM-S07",
    "VI-HUM-S08",
    "VI-HUM-S10",
    "VI-HUM-S13",
    "VI-HUM-S14",
    "VI-STY-C02",
    "VI-STY-N02",
    "VI-STY-P01",
    "VI-STY-T01",
    "VI-STY-T02",
    "VI-TRA-S05",
}

_PRONOUN_PATTERN = re.compile(
    r"(?<!\w)(?:tôi|mình|chúng tôi|chúng ta|chúng mình|bạn|"
    r"anh|chị|em|ông|bà|các bạn|mọi người)(?!\w)",
    flags=re.IGNORECASE,
)
_DIALOGUE_CONNECTORS = (
    "nhưng",
    "và",
    "vì vậy",
    "thế nên",
    "cho nên",
    "bởi vì",
    "tuy nhiên",
    "mặc dù",
    "dù",
    "nếu",
    "khi",
    "rồi",
    "thì",
)

NUMERIC_EXEMPT_KEYWORDS = (
    "theo",
    "nguồn",
    "báo cáo",
    "nghiên cứu",
    "khảo sát",
    "thống kê",
    "ước tính",
    "ước chừng",
    "có lẽ",
    "có thể là",
    "số liệu của",
)

HEDGE_PHRASES = (
    "có lẽ",
    "dường như",
    "có khả năng",
    "có vẻ",
    "phần nào",
)

_SYMMETRY_POSITIVE_RE = re.compile(
    r"\b(\d+)\s+(?:ưu điểm|điểm mạnh|lợi ích|cơ hội)\b",
    flags=re.IGNORECASE,
)
_SYMMETRY_NEGATIVE_RE = re.compile(
    r"\b(\d+)\s+(?:nhược điểm|điểm yếu|hạn chế|thách thức)\b",
    flags=re.IGNORECASE,
)

PROPER_NOUN_WHITELIST = (
    "Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ", "Huế",
    "Bình Dương", "Đồng Nai", "Bà Rịa", "Vũng Tàu", "Long An", "Tiền Giang",
    "Bến Tre", "Vĩnh Long", "An Giang", "Kiên Giang", "Cà Mau", "Bạc Liêu",
    "Sóc Trăng", "Trà Vinh", "Đồng Tháp", "Vĩnh Phúc", "Bắc Ninh", "Hải Dương",
    "Hưng Yên", "Thái Bình", "Nam Định", "Ninh Bình", "Thanh Hóa", "Nghệ An",
    "Hà Tĩnh", "Quảng Bình", "Quảng Trị", "Thừa Thiên", "Quảng Nam", "Quảng Ngãi",
    "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận", "Kon Tum",
    "Gia Lai", "Đắk Lắk", "Đắk Nông", "Lâm Đồng", "Tây Ninh", "Bình Phước",
    "Điện Biên", "Lai Châu", "Sơn La", "Hòa Bình", "Lào Cai", "Yên Bái",
    "Phú Thọ", "Tuyên Quang", "Hà Giang", "Cao Bằng", "Bắc Kạn", "Thái Nguyên",
    "Lạng Sơn", "Quảng Ninh", "Bắc Giang",
    "Việt Nam", "Hoa Kỳ", "Trung Quốc", "Nhật Bản", "Hàn Quốc", "Triều Tiên",
    "Anh Quốc", "Pháp Quốc", "Đức Quốc", "Ý Quốc", "Tây Ban Nha", "Bồ Đào Nha",
    "Nga Quốc", "Ấn Độ", "Thái Lan", "Malaysia", "Indonesia", "Philippines",
    "Singapore", "Campuchia", "Lào Quốc", "Myanmar", "Canada", "Brazil",
    "Mexico", "Argentina", "Ai Cập", "Ả Rập", "Israel", "Iran", "Iraq",
    "Liên Hợp Quốc", "Liên Minh", "Hiệp Hội",
    "Bách Khoa", "Quốc Gia",
)

ORGANIZATION_SUFFIXES = (
    "Công Ty", "Tập Đoàn", "Đại Học", "Cao Đẳng", "Trung Cấp", "Trường",
    "Học Viện", "Viện", "Trung Tâm", "Ủy Ban", "UBND", "HĐND",
    "Bộ", "Sở", "Ban", "Phòng", "Chi Cục", "Cục",
)

_TITLE_CASE_RE = re.compile(
    r"\b[A-ZĐÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZĐÀ-Ỹ][a-zà-ỹ]+){1,4}\b"
)

_ENUMERATION_MARKERS_RE = re.compile(
    r"\b(?:[Tt]hứ\s+(?:nhất|hai|ba|tư|năm|sáu)|"
    r"[Mm]ột là|[Hh]ai là|[Bb]a là|"
    r"[Đđ]iểm thứ\s+(?:nhất|hai|ba))\b",
    flags=re.UNICODE,
)

_ENUMERATION_EXCLUDE_PRECEDING = frozenset({
    "lần", "ngày", "tuần", "hạng", "giải", "vị", "số", "đợt", "kỳ", "bước",
    "tháng", "năm", "quý", "phút", "giây",
})


def _blank_keep_newlines(line: str) -> str:
    return "".join("\n" if char == "\n" else " " for char in line)


def mask_protected(text: str) -> str:
    """Che nội dung không nên lint nhưng giữ nguyên newline và vị trí ký tự."""
    output: list[str] = []
    in_fence = False
    fence_char = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(2)
            info = fence.group(3)
            if not in_fence:
                output.append(_blank_keep_newlines(line))
                in_fence = True
                fence_char = marker[0]
                fence_length = len(marker)
                continue
            if (
                marker[0] == fence_char
                and len(marker) >= fence_length
                and info.strip() == ""
            ):
                output.append(_blank_keep_newlines(line))
                in_fence = False
                fence_char = ""
                fence_length = 0
                continue
        if in_fence:
            output.append(_blank_keep_newlines(line))
            continue
        masked = INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), line)
        masked = _mask_urls(masked)
        for expression in (
            EMAIL_RE,
            FILENAME_RE,
            ABBREV_RE,
            IDENTIFIER_RE,
        ):
            masked = expression.sub(lambda match: " " * len(match.group(0)), masked)
        output.append(masked)
    return "".join(output)


def _url_end(text: str, body_start: int) -> int:
    index = body_start
    depth = 0
    while index < len(text):
        char = text[index]
        if char.isspace() or char in URL_STOP_CHARS:
            break
        if char == "[":
            close = text.find("]", index + 1)
            if close != -1 and ":" in text[index + 1 : close]:
                index = close + 1
                continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        elif char == "]" and depth == 0:
            break
        index += 1
    return index


def _mask_urls(text: str) -> str:
    chars = list(text)
    for match in URL_START_RE.finditer(text):
        end = _url_end(text, match.end())
        for index in range(match.start(), end):
            chars[index] = " "
    return "".join(chars)


def _location(text: str, start: int) -> tuple[int, int]:
    line = text.count("\n", 0, start) + 1
    previous_newline = text.rfind("\n", 0, start)
    return line, start - previous_newline


def _excerpt(text: str, start: int, end: int, limit: int = 100) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    leading = len(line) - len(line.lstrip())
    excerpt = line.strip()
    relative_start = max(0, start - line_start - leading)
    relative_end = min(len(excerpt), end - line_start - leading)
    if len(excerpt) <= limit:
        return excerpt

    matched_length = max(1, relative_end - relative_start)
    if matched_length > limit:
        matched = excerpt[relative_start:relative_end].strip()
        left_length = (limit - 1) // 2
        right_length = limit - 1 - left_length
        return matched[:left_length] + "…" + matched[-right_length:]

    context_budget = max(0, limit - min(matched_length, limit) - 2)
    left_context = min(relative_start, context_budget // 2)
    right_context = min(len(excerpt) - relative_end, context_budget - left_context)
    remaining = context_budget - left_context - right_context
    if remaining:
        extra_left = min(relative_start - left_context, remaining)
        left_context += extra_left
        remaining -= extra_left
        right_context += min(len(excerpt) - relative_end - right_context, remaining)

    clip_start = relative_start - left_context
    clip_end = relative_end + right_context
    prefix = "…" if clip_start > 0 else ""
    suffix = "…" if clip_end < len(excerpt) else ""
    return prefix + excerpt[clip_start:clip_end].strip() + suffix


def _paragraph_bounds(text: str, position: int) -> tuple[int, int]:
    """Trả về (start, end) của đoạn văn chứa `position`.

    Đoạn văn được ngăn cách bởi dòng trống (\\n\\n). Nếu text không có
    dòng trống, toàn bộ text là một đoạn.
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


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Khoảng [start, end) của câu chứa position.

    Không tách tại dấu chấm trong viết tắt kiểu `ĐHQG. HCM` vì dấu chấm
    đó không được theo sau bởi khoảng trắng + chữ hoa mở câu mới. Cụ thể,
    chỉ coi dấu `.` `!` `?` là kết câu khi ngay sau nó là khoảng trắng
    (hoặc hết chuỗi / hết dòng) và ký tự tiếp theo sau khoảng trắng là
    chữ hoa hoặc hết câu.
    """
    if not text:
        return 0, 0
    position = max(0, min(position, len(text)))

    start = position
    while start > 0:
        prev = text[start - 1]
        if prev == "\n":
            break
        if prev in ".!?":
            # Nếu ký tự ngay trước dấu câu là chữ số hoặc viết tắt đơn âm tiết
            # thì không cắt (ví dụ: "3.14", "TP.")
            # Đơn giản: chỉ cắt khi dấu câu được theo sau bởi khoảng trắng
            # và ký tự đầu của câu mới là chữ hoa.
            nxt_index = start
            if nxt_index < len(text) and text[nxt_index] in " \t":
                # tìm ký tự không phải khoảng trắng
                k = nxt_index
                while k < len(text) and text[k] in " \t":
                    k += 1
                if k >= len(text) or text[k].isupper() or text[k] in "“\"'([":
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
                    or text[k] in "“\"'(["
                ):
                    end += 1
                    break
        end += 1

    return start, end


def _occurrence(text: str, start: int, end: int) -> dict[str, Any]:
    line, column = _location(text, start)
    sent_start, sent_end = _sentence_bounds(text, start)
    para_start, para_end = _paragraph_bounds(text, start)
    return {
        "line": line,
        "column": column,
        "excerpt": _excerpt(text, start, end),
        "matched_text": text[start:end],
        "start": start,
        "end": end,
        "sentence": text[sent_start:sent_end],
        "sentence_start": sent_start,
        "sentence_end": sent_end,
        "paragraph": text[para_start:para_end],
        "paragraph_start": para_start,
        "paragraph_end": para_end,
    }


def _issue(
    text: str,
    start: int,
    end: int,
    pattern: dict[str, Any],
    message: str | None = None,
    suggestion: str | None = None,
    occurrence_spans: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    spans = occurrence_spans or [(start, end)]
    occurrences = [_occurrence(text, span_start, span_end) for span_start, span_end in spans]
    first = occurrences[0]
    return {
        "pattern_id": pattern["id"],
        "finding_type": pattern["finding_type"],
        "severity": pattern["severity"],
        "confidence": pattern["confidence"],
        "scope": pattern["scope"],
        "line": first["line"],
        "column": first["column"],
        "excerpt": first["excerpt"],
        "message": message or " ".join(pattern["summary"].split()),
        "suggestion": suggestion or pattern["rewrite_strategy"][0],
        "occurrences": occurrences,
        "start": first["start"],
        "end": first["end"],
        "sentence": first["sentence"],
        "sentence_start": first["sentence_start"],
        "sentence_end": first["sentence_end"],
        "paragraph": first["paragraph"],
        "paragraph_start": first["paragraph_start"],
        "paragraph_end": first["paragraph_end"],
    }


def _signal_matches(masked: str, pattern: dict[str, Any]) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    signals = pattern.get("signals", {})
    flags = 0 if pattern.get("case_sensitive", False) else re.IGNORECASE
    for phrase in signals.get("phrases", []):
        matches.extend(re.finditer(re.escape(phrase), masked, flags=flags))
    for expression in signals.get("regex", []):
        matches.extend(re.finditer(expression, masked, flags=flags))
    excluded = {phrase.casefold() for phrase in signals.get("exclude_phrases", [])}
    matches = [match for match in matches if match.group(0).casefold() not in excluded]
    unique = {(match.start(), match.end()): match for match in matches}
    return [unique[key] for key in sorted(unique)]


def _paragraph_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"\n[ \t]*\n", text):
        ranges.append((start, match.start()))
        start = match.end()
    ranges.append((start, len(text)))
    return [
        (span_start, span_end)
        for span_start, span_end in ranges
        if text[span_start:span_end].strip()
    ]


def _line_at(text: str, index: int) -> str:
    line_start = text.rfind("\n", 0, index) + 1
    line_end = text.find("\n", index)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end]


def _is_list_item(text: str, index: int) -> bool:
    return bool(LIST_PREFIX_RE.match(_line_at(text, index)))


def _emit_catalog_group(
    text: str,
    pattern: dict[str, Any],
    ordered: list[re.Match[str]],
) -> list[dict[str, Any]]:
    threshold = pattern.get("min_occurrences", 1)
    if len(ordered) < threshold:
        return []
    aggregation = pattern.get("aggregation", "single")
    if aggregation == "single":
        return [_issue(text, match.start(), match.end(), pattern) for match in ordered]
    first = ordered[0]
    return [
        _issue(
            text,
            first.start(),
            first.end(),
            pattern,
            occurrence_spans=[(match.start(), match.end()) for match in ordered],
        )
    ]


def _catalog_issues(
    text: str,
    masked: str,
    pattern_dir: Any,
    skills: set[str] | None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    paragraph_ranges = _paragraph_ranges(masked)
    for _, pattern in iter_patterns(pattern_dir):
        if skills and pattern["skill"] not in skills:
            continue
        if pattern["id"] in SPECIAL_PATTERN_IDS:
            continue
        ordered = _signal_matches(masked, pattern)
        if pattern.get("scope") == "paragraph":
            for start, end in paragraph_ranges:
                local = [match for match in ordered if start <= match.start() < end]
                if pattern["id"] in {"VI-HUM-S03", "VI-HUM-S12"}:
                    local = [
                        match
                        for match in local
                        if not _is_list_item(masked, match.start())
                    ]
                issues.extend(_emit_catalog_group(text, pattern, local))
            continue
        issues.extend(_emit_catalog_group(text, pattern, ordered))
    return issues


def _sentences(masked: str) -> list[tuple[re.Match[str], list[str]]]:
    output: list[tuple[re.Match[str], list[str]]] = []
    for match in SENTENCE_RE.finditer(masked):
        words = WORD_RE.findall(match.group(0))
        if words:
            output.append((match, words))
    return output


def _repeated_opening_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    sentences = _sentences(masked)
    issues: list[dict[str, Any]] = []
    for paragraph_start, paragraph_end in _paragraph_ranges(masked):
        local = [
            item
            for item in sentences
            if paragraph_start <= item[0].start() < paragraph_end
        ]
        for index in range(len(local) - 2):
            window = local[index : index + 3]
            if all(_is_list_item(masked, sentence_match.start()) for sentence_match, _ in window):
                continue
            openings = [words[0].casefold() for _, words in window]
            if len(set(openings)) != 1:
                continue
            match = window[0][0]
            issues.append(
                _issue(
                    text,
                    match.start(),
                    match.end(),
                    patterns["VI-HUM-S01"],
                    f"Ba câu liên tiếp cùng mở đầu bằng “{openings[0]}”.",
                    "Đổi chủ thể hoặc gộp câu nếu quan hệ giữa các ý cho phép.",
                    occurrence_spans=[
                        (sentence_match.start(), sentence_match.start() + len(words[0]))
                        for sentence_match, words in window
                    ],
                )
            )
    return issues


def _uniform_length_issue(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    sentences = _sentences(masked)
    lengths = [len(words) for _, words in sentences if len(words) >= 6]
    if len(lengths) < 5:
        return []
    average = sum(lengths) / len(lengths)
    variance = sum((length - average) ** 2 for length in lengths) / len(lengths)
    coefficient = math.sqrt(variance) / average if average else 1.0
    if coefficient >= 0.16:
        return []
    return [
        _issue(
            text,
            sentences[0][0].start(),
            sentences[-1][0].end(),
            patterns["VI-HUM-S04"],
            "Độ dài của ít nhất năm câu gần như đồng đều; đây chỉ là tín hiệu cần đọc lại.",
            "Đọc thành tiếng và chỉ tách hoặc gộp câu khi nhịp đều làm ý khó theo dõi.",
        )
    ]


def _paragraph_uniformity_issue(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-HUM-S07: các đoạn có số câu gần bằng nhau (CV < 0.15, mean 3-7)."""
    pattern = patterns.get("VI-HUM-S07")
    if pattern is None:
        return []
    sentence_counts: list[int] = []
    for para_start, para_end in _paragraph_ranges(masked):
        paragraph = masked[para_start:para_end]
        count = sum(
            1
            for match in SENTENCE_RE.finditer(paragraph)
            if WORD_RE.findall(match.group(0))
        )
        if count > 0:
            sentence_counts.append(count)
    if len(sentence_counts) < 5:
        return []
    mean = statistics.mean(sentence_counts)
    if mean < 3 or mean > 7:
        return []
    stdev = statistics.stdev(sentence_counts)
    cv = stdev / mean if mean else 1.0
    if cv >= 0.15:
        return []
    return [
        _issue(
            text,
            0,
            len(text),
            pattern,
            message=(
                f"Số câu mỗi đoạn đồng đều (CV={cv:.2f}, trung bình {mean:.1f} câu/đoạn). "
                "Đây chỉ là tín hiệu cấu trúc cần đọc lại."
            ),
            suggestion="Xen kẽ đoạn ngắn và đoạn dài nếu cấu trúc ý cho phép.",
        )
    ]


def _hedge_uniformity_issue(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-HUM-S08: hedge rải đều khắp các đoạn (mỗi đoạn có >= 1 hedge)."""
    pattern = patterns.get("VI-HUM-S08")
    if pattern is None:
        return []
    lower = masked.casefold()
    hedge_counts: list[int] = []
    for para_start, para_end in _paragraph_ranges(masked):
        paragraph_lower = lower[para_start:para_end]
        count = 0
        for phrase in HEDGE_PHRASES:
            pattern_re = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            count += len(re.findall(pattern_re, paragraph_lower))
        hedge_counts.append(count)
    if len(hedge_counts) < 5:
        return []
    if any(c == 0 for c in hedge_counts):
        return []
    total = sum(hedge_counts)
    if total < 5:
        return []
    if max(hedge_counts) - min(hedge_counts) > 1:
        return []
    return [
        _issue(
            text,
            0,
            len(text),
            pattern,
            message=(
                f"Hedge rải đều khắp {len(hedge_counts)} đoạn "
                f"(mỗi đoạn {min(hedge_counts)}-{max(hedge_counts)} hedge)."
            ),
            suggestion="Tập trung hedge ở chỗ thật sự cần, không rải đều.",
        )
    ]


def _symmetry_bias_issue(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-HUM-S10: số mục tích cực và tiêu cực bằng nhau."""
    pattern = patterns.get("VI-HUM-S10")
    if pattern is None:
        return []
    positives = {match.group(1) for match in _SYMMETRY_POSITIVE_RE.finditer(masked)}
    negatives = {match.group(1) for match in _SYMMETRY_NEGATIVE_RE.finditer(masked)}
    shared = positives & negatives
    if not shared:
        return []
    first_number = sorted(shared)[0]
    first_match: re.Match[str] | None = None
    for match in _SYMMETRY_POSITIVE_RE.finditer(masked):
        if match.group(1) == first_number:
            first_match = match
            break
    if first_match is None:
        return []
    return [
        _issue(
            text,
            first_match.start(),
            first_match.end(),
            pattern,
            message=(
                f"Số mục tích cực và tiêu cực đối xứng: "
                f"{first_number} và {first_number}."
            ),
            suggestion="Cho phép số mục hai nhánh khác nhau nếu tài liệu không thực sự cân.",
        )
    ]


def _over_enumeration_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-HUM-S14: mật độ 'thứ nhất/thứ hai/thứ ba' và biến thể dày."""
    pattern = patterns.get("VI-HUM-S14")
    if pattern is None:
        return []
    candidates: list[tuple[int, int]] = []
    for match in _ENUMERATION_MARKERS_RE.finditer(masked):
        before = masked[max(0, match.start() - 30):match.start()]
        words_before = WORD_RE.findall(before)
        if words_before and words_before[-1].casefold() in _ENUMERATION_EXCLUDE_PRECEDING:
            continue
        candidates.append((match.start(), match.end()))
    threshold = pattern.get("min_occurrences", 3)
    if len(candidates) < threshold:
        return []
    first_start, first_end = candidates[0]
    return [
        _issue(
            text,
            first_start,
            first_end,
            pattern,
            occurrence_spans=candidates,
        )
    ]


def _burstiness_score(text: str) -> float:
    """Đo độ biến thiên độ dài câu (burstiness)."""
    sentences = _sentences(text)
    if len(sentences) < 5:
        return 1.0

    lengths = [len(words) for _, words in sentences if len(words) > 0]
    if len(lengths) < 5:
        return 1.0

    mean = statistics.mean(lengths)
    if mean == 0:
        return 1.0

    stdev = statistics.stdev(lengths)
    cv = stdev / mean

    return min(1.0, max(0.0, (cv - 0.10) / 0.30))


def _lexical_diversity_score(text: str) -> float:
    """Đo độ đa dạng từ vựng (type-token ratio)."""
    words = WORD_RE.findall(text.casefold())
    if len(words) < 50:
        return 1.0

    window_size = 50
    ttrs: list[float] = []
    for i in range(0, len(words) - window_size + 1, window_size // 2):
        window = words[i : i + window_size]
        ttr = len(set(window)) / len(window)
        ttrs.append(ttr)

    if not ttrs:
        return 1.0

    avg_ttr = statistics.mean(ttrs)
    return min(1.0, max(0.0, (avg_ttr - 0.55) / 0.30))


def _statistical_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Phát hiện các dấu hiệu AI dựa trên thống kê (burstiness, lexical diversity)."""
    issues: list[dict[str, Any]] = []
    pattern = patterns.get("VI-HUM-S05")
    if pattern is None:
        return issues

    burst = _burstiness_score(masked)
    if burst < 0.35:
        issues.append(
            _issue(
                text,
                0,
                len(text),
                pattern,
                message=(
                    f"Burstiness thấp ({burst:.2f}): độ dài câu quá đều, "
                    f"dấu hiệu thống kê của văn AI."
                ),
                suggestion="Đa dạng hóa độ dài câu: tách câu dài, gộp câu ngắn.",
            )
        )

    diversity = _lexical_diversity_score(masked)
    if diversity < 0.30:
        issues.append(
            _issue(
                text,
                0,
                len(text),
                pattern,
                message=(
                    f"Độ đa dạng từ vựng thấp ({diversity:.2f}): "
                    f"lặp từ nhiều, dấu hiệu của văn AI."
                ),
                suggestion="Thay thế từ lặp bằng từ đồng nghĩa hoặc đại từ.",
            )
        )

    return issues


def _missing_pronoun_issues(
    text: str,
    masked: str,
) -> list[dict[str, Any]]:
    """Phát hiện đoạn văn dài nhưng hoàn toàn thiếu đại từ nhân xưng."""
    issues: list[dict[str, Any]] = []
    for para_start, para_end in _paragraph_ranges(masked):
        paragraph = masked[para_start:para_end]
        sentences = [
            match
            for match in SENTENCE_RE.finditer(paragraph)
            if WORD_RE.findall(match.group(0))
        ]
        if len(sentences) < 5:
            continue
        if _PRONOUN_PATTERN.search(paragraph):
            continue
        has_connector = any(
            re.search(rf"(?<!\w){re.escape(c)}(?!\w)", paragraph, re.IGNORECASE)
            for c in _DIALOGUE_CONNECTORS
        )
        if has_connector:
            continue
        para_len = para_end - para_start
        end_for_excerpt = para_start + min(100, para_len)
        line, column = _location(text, para_start)
        issues.append(
            {
                "pattern_id": "VI-HUM-S06",
                "finding_type": "heuristic",
                "severity": "medium",
                "confidence": "medium",
                "scope": "paragraph",
                "line": line,
                "column": column,
                "excerpt": _excerpt(text, para_start, end_for_excerpt),
                "message": (
                    "Đoạn văn dài nhưng không có đại từ nhân xưng hoặc từ nối đối thoại; "
                    "giọng hoàn toàn khách quan, dấu hiệu của văn AI."
                ),
                "suggestion": (
                    "Thêm đại từ phù hợp (chúng tôi, bạn, …) hoặc từ nối đối thoại "
                    "(nhưng, vì vậy, …) nếu giọng văn cho phép."
                ),
                "occurrences": [
                    {
                        "line": line,
                        "column": column,
                        "excerpt": _excerpt(text, para_start, end_for_excerpt),
                        "matched_text": text[para_start:end_for_excerpt],
                        "start": para_start,
                        "end": end_for_excerpt,
                        "sentence": text[para_start:end_for_excerpt],
                        "sentence_start": para_start,
                        "sentence_end": end_for_excerpt,
                        "paragraph": text[para_start:para_end],
                        "paragraph_start": para_start,
                        "paragraph_end": para_end,
                    }
                ],
                "start": para_start,
                "end": end_for_excerpt,
                "sentence": text[para_start:end_for_excerpt],
                "sentence_start": para_start,
                "sentence_end": end_for_excerpt,
                "paragraph": text[para_start:para_end],
                "paragraph_start": para_start,
                "paragraph_end": para_end,
            }
        )
    return issues


def _numeric_without_source_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-HUM-D05: số liệu không nguồn."""
    pattern = patterns.get("VI-HUM-D05")
    if pattern is None:
        return []

    numeric_spans: list[tuple[int, int]] = []
    for regex in (
        r"\b\d+(?:[.,]\d+)?\s*%",
        r"\b\d+(?:[.,]\d+)?\s*(?:triệu|nghìn|ngàn|tỷ)\b",
    ):
        for match in re.finditer(regex, masked, flags=re.IGNORECASE):
            numeric_spans.append((match.start(), match.end()))

    if not numeric_spans:
        return []

    flagged: list[tuple[int, int]] = []
    for sentence_match, _words in _sentences(masked):
        sentence_start = sentence_match.start()
        sentence_end = sentence_match.end()
        local = [
            span for span in numeric_spans
            if sentence_start <= span[0] < sentence_end
        ]
        if not local:
            continue
        sentence_lower = masked[sentence_start:sentence_end].casefold()
        if any(keyword in sentence_lower for keyword in NUMERIC_EXEMPT_KEYWORDS):
            continue
        flagged.extend(local)

    threshold = pattern.get("min_occurrences", 1)
    if len(flagged) < threshold:
        return []

    first_start, first_end = flagged[0]
    return [
        _issue(
            text,
            first_start,
            first_end,
            pattern,
            occurrence_spans=flagged,
        )
    ]


def _pronoun_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    lower = masked.casefold()
    for group in PRONOUN_GROUPS:
        alternatives = "|".join(
            re.escape(pronoun) for pronoun in sorted(group, key=len, reverse=True)
        )
        matches = list(re.finditer(rf"(?<!\w)(?:{alternatives})(?!\w)", lower))
        matched_pronouns = {match.group(0) for match in matches}
        present = [pronoun for pronoun in group if pronoun in matched_pronouns]
        if len(present) < 2 or len(matches) < 3:
            continue
        first = matches[0]
        issues.append(
            _issue(
                text,
                first.start(),
                first.end(),
                patterns["VI-STY-P01"],
                f"Đại từ có thể chưa nhất quán: {', '.join(present)}.",
                "Chọn cách xưng hô theo quan hệ với độc giả rồi rà toàn văn.",
                occurrence_spans=[(match.start(), match.end()) for match in matches],
            )
        )
    return issues


def _terminology_consistency_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-STY-T01"]
    matches = _signal_matches(masked, pattern)
    variants = {" ".join(match.group(0).casefold().split()) for match in matches}
    if len(matches) < pattern.get("min_occurrences", 1) or len(variants) < 2:
        return []
    first = matches[0]
    return [
        _issue(
            text,
            first.start(),
            first.end(),
            pattern,
            f"Thuật ngữ có thể chưa nhất quán: {', '.join(sorted(variants))}.",
            occurrence_spans=[(match.start(), match.end()) for match in matches],
        )
    ]


def _percentage_consistency_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-STY-N02"]
    matches = _signal_matches(masked, pattern)
    spacing_styles = {bool(re.search(r"\s+%$", match.group(0))) for match in matches}
    if len(matches) < pattern.get("min_occurrences", 1) or len(spacing_styles) < 2:
        return []
    first = matches[0]
    return [
        _issue(
            text,
            first.start(),
            first.end(),
            pattern,
            occurrence_spans=[(match.start(), match.end()) for match in matches],
        )
    ]


def _is_emphasis_context(masked: str, match: re.Match[str]) -> bool:
    line_start = masked.rfind("\n", 0, match.start()) + 1
    line_end = masked.find("\n", match.end())
    if line_end < 0:
        line_end = len(masked)
    line = masked[line_start:line_end]

    upper_words = re.findall(r"[A-ZĐÀ-Ỹ]{2,}", line)
    if len(upper_words) < 2:
        return False

    for word in upper_words:
        if word != match.group(0) and _VIETNAMESE_VOWEL_MARKS_RE.search(word):
            return True

    return False


def _is_in_quoted_text(text: str, match: re.Match[str]) -> bool:
    before = text[: match.start()]
    if before.count('"') % 2 == 1:
        return True
    return before.count(SMART_QUOTE_OPEN) > before.count(SMART_QUOTE_CLOSE)


def _acronym_definition_offsets(masked: str) -> dict[str, int]:
    defined: dict[str, int] = {}
    for match in re.finditer(
        r"\b[\wÀ-ỹĐđ]+(?:\s+[\wÀ-ỹĐđ]+){1,12}\s+\(([A-ZĐ]{3,6})\)",
        masked,
    ):
        defined.setdefault(match.group(1), match.start(1))
    for match in re.finditer(
        r"\b([A-ZĐ]{3,6})\s+\((?:[\wÀ-ỹĐđ]+(?:\s+[\wÀ-ỹĐđ]+)+)\)",
        masked,
    ):
        defined.setdefault(match.group(1), match.start(1))
    return defined


def _acronym_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-STY-T02"]
    defined = _acronym_definition_offsets(masked)
    issues: list[dict[str, Any]] = []
    for match in _signal_matches(masked, pattern):
        word = match.group(0)
        if _VIETNAMESE_VOWEL_MARKS_RE.search(word):
            continue
        if _is_emphasis_context(masked, match):
            continue
        if _is_in_quoted_text(text, match):
            continue
        defined_at = defined.get(word)
        if defined_at is not None and match.start() >= defined_at:
            continue
        is_parenthesized = (
            match.start() > 0
            and match.end() < len(masked)
            and masked[match.start() - 1] == "("
            and masked[match.end()] == ")"
        )
        sentence_start = max(
            masked.rfind(".", 0, match.start()),
            masked.rfind("!", 0, match.start()),
            masked.rfind("?", 0, match.start()),
            masked.rfind("\n", 0, match.start()),
        )
        expansion = masked[sentence_start + 1 : match.start() - 1]
        is_first_definition = is_parenthesized and len(WORD_RE.findall(expansion)) >= 2
        if not is_first_definition:
            issues.append(_issue(text, match.start(), match.end(), pattern))
    return issues


def _is_at_sentence_start(masked: str, start: int) -> bool:
    """Kiểm tra vị trí có phải đầu câu không (VI-STY-C02 helper)."""
    before = masked[:start].rstrip()
    if not before:
        return True
    last_char = before[-1]
    if last_char in ".!?":
        return True
    line_start = masked.rfind("\n", 0, start)
    if line_start >= 0:
        segment = masked[line_start + 1 : start]
        if not segment.strip():
            return True
    return False


def _is_in_heading(masked: str, start: int) -> bool:
    """Kiểm tra candidate có nằm trong dòng Markdown heading không (VI-STY-C02 helper)."""
    line_start = masked.rfind("\n", 0, start) + 1
    line = masked[line_start:start]
    return line.lstrip().startswith("#")


def _title_case_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """VI-STY-C02: cụm Title Case giữa câu (dấu hiệu nhiễm quy ước tiếng Anh)."""
    pattern = patterns.get("VI-STY-C02")
    if pattern is None:
        return []
    candidates: list[tuple[int, int]] = []
    for match in _TITLE_CASE_RE.finditer(masked):
        start, end = match.start(), match.end()
        phrase = match.group(0)
        if len(phrase) < 8:
            continue
        if _is_at_sentence_start(masked, start):
            continue
        if _is_in_heading(masked, start):
            continue
        if _is_in_quoted_text(text, match):
            continue
        phrase_cf = phrase.casefold()
        if any(pn.casefold() in phrase_cf for pn in PROPER_NOUN_WHITELIST):
            continue
        if any(suffix.casefold() in phrase_cf for suffix in ORGANIZATION_SUFFIXES):
            continue
        candidates.append((start, end))
    threshold = pattern.get("min_occurrences", 2)
    if len(candidates) < threshold:
        return []
    first_start, first_end = candidates[0]
    return [
        _issue(
            text,
            first_start,
            first_end,
            pattern,
            occurrence_spans=candidates,
        )
    ]


def _sentence_tail(masked: str, start: int) -> str:
    tail = masked[start:]
    cut = len(tail)
    for separator in ".!?\n":
        index = tail.find(separator)
        if 0 <= index < cut:
            cut = index
    return tail[:cut]


def _redundant_connector_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-GRA-C06"]
    issues: list[dict[str, Any]] = []
    for match in re.finditer(r"\bvì vậy\s*,?\s+nên\b", masked, flags=re.IGNORECASE):
        words = WORD_RE.findall(_sentence_tail(masked, match.end()))[:6]
        lowered = [word.casefold() for word in words]
        subject_length = next(
            (
                len(subject)
                for subject in RESULT_SUBJECTS
                if tuple(lowered[: len(subject)]) == subject
            ),
            0,
        )
        if not subject_length:
            continue
        predicate = lowered[subject_length:]
        if not any(word in RESULT_AUXILIARIES for word in predicate[:4]):
            continue
        issues.append(_issue(text, match.start(), match.end(), pattern))
    return issues


def _repeated_word_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-GRA-L01"]
    issues: list[dict[str, Any]] = []
    for match in _signal_matches(masked, pattern):
        word = match.group(1) if match.lastindex else match.group(0).split()[0]
        if word.casefold() not in REPEATED_FUNCTION_WORDS:
            continue
        issues.append(_issue(text, match.start(), match.end(), pattern))
    return issues


def _balance_scan_text(masked: str) -> str:
    lines: list[str] = []
    for line in masked.splitlines(keepends=True):
        match = LIST_PREFIX_RE.match(line)
        if not match:
            lines.append(line)
            continue
        prefix = "".join(" " if char in ".)" else char for char in line[: match.end()])
        lines.append(prefix + line[match.end() :])
    return "".join(lines)


def _first_unbalanced_delimiter(text: str, opener: str, closer: str) -> int:
    if opener == closer:
        stack: list[int] = []
        for index, char in enumerate(text):
            if char != opener:
                continue
            if stack:
                stack.pop()
            else:
                stack.append(index)
        return stack[0] if stack else -1

    stack = []
    extra_closer = -1
    for index, char in enumerate(text):
        if char == opener:
            stack.append(index)
        elif char == closer:
            if stack:
                stack.pop()
            elif extra_closer < 0:
                extra_closer = index
    if stack:
        start = stack[0]
        if extra_closer < 0 or start < extra_closer:
            return start
    return extra_closer


def _unbalanced_delimiter_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-GRA-P04"]
    scanned = _balance_scan_text(masked)
    issues: list[dict[str, Any]] = []
    checks = (
        ('"', '"', 'Ngoặc kép ASCII " không cân.'),
        (SMART_QUOTE_OPEN, SMART_QUOTE_CLOSE, "Ngoặc kép cong “ ” không cân."),
        ("«", "»", "Ngoặc kép « » không cân."),
        ("(", ")", "Ngoặc đơn không cân."),
        ("[", "]", "Ngoặc vuông không cân."),
    )
    for opener, closer, message in checks:
        start = _first_unbalanced_delimiter(scanned, opener, closer)
        if start < 0:
            continue
        issues.append(
            _issue(
                text,
                start,
                start + 1,
                pattern,
                message,
                "Đánh dấu để người viết kiểm tra; không tự thêm dấu đóng.",
            )
        )
    return issues


def _administrative_stack_issues(
    text: str,
    masked: str,
    patterns: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = patterns["VI-TRA-S05"]
    matches = _signal_matches(masked, pattern)
    threshold = pattern.get("min_occurrences", 1)
    issues: list[dict[str, Any]] = []
    for sentence_match, _ in _sentences(masked):
        sentence_matches = [
            match
            for match in matches
            if sentence_match.start() <= match.start() < sentence_match.end()
        ]
        if len(sentence_matches) < threshold:
            continue
        first = sentence_matches[0]
        issues.append(
            _issue(
                text,
                first.start(),
                first.end(),
                pattern,
                occurrence_spans=[
                    (match.start(), match.end()) for match in sentence_matches
                ],
            )
        )
    return issues


def _deep_judge_issues(
    text: str,
    patterns: dict[str, dict[str, Any]],
    *,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
    min_confidence: int = 4,
) -> list[dict[str, Any]]:
    """Chạy LLM judge cho 6 pattern Nhóm C. Chỉ dùng khi --deep."""
    if not is_llm_judge_available():
        return []
    if len(text) < 200:
        return []
    issues: list[dict[str, Any]] = []
    for pattern_id in sorted(LLM_JUDGED_PATTERN_IDS):
        pattern = patterns.get(pattern_id)
        if pattern is None:
            continue
        result = judge_text(
            text,
            pattern_id,
            api_key=api_key,
            model=model,
            min_confidence=min_confidence,
        )
        if result.verdict != "flagged":
            continue
        occurrences: list[dict[str, Any]] = []
        for evidence in result.evidence[:3]:
            idx = text.find(evidence)
            if idx < 0:
                idx = 0
            end = idx + len(evidence)
            occurrences.append(_occurrence(text, idx, end))
        if not occurrences:
            occurrences = [_occurrence(text, 0, min(len(text), 100))]
        first = occurrences[0]
        issues.append(
            {
                "pattern_id": pattern_id,
                "finding_type": pattern["finding_type"],
                "severity": pattern["severity"],
                "confidence": pattern["confidence"],
                "scope": pattern["scope"],
                "line": first["line"],
                "column": first["column"],
                "excerpt": first["excerpt"],
                "message": (
                    f"[LLM judge {result.confidence}/5] {result.reasoning}"
                ),
                "suggestion": pattern["rewrite_strategy"][0],
                "occurrences": occurrences,
                "start": first["start"],
                "end": first["end"],
                "sentence": first["sentence"],
                "sentence_start": first["sentence_start"],
                "sentence_end": first["sentence_end"],
                "paragraph": first["paragraph"],
                "paragraph_start": first["paragraph_start"],
                "paragraph_end": first["paragraph_end"],
            }
        )
    return issues


def lint_text(
    text: str,
    skills: set[str] | None = None,
    pattern_dir: Any | None = None,
    *,
    deep: bool = False,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
    min_confidence: int = 4,
) -> list[dict[str, Any]]:
    directory = pattern_dir or data_location("patterns")
    patterns = pattern_index(directory)
    masked = mask_protected(text)
    issues = _catalog_issues(text, masked, directory, skills)
    if not skills or "humanizer-vi" in skills:
        issues.extend(_repeated_opening_issues(text, masked, patterns))
        issues.extend(_uniform_length_issue(text, masked, patterns))
        issues.extend(_statistical_issues(text, masked, patterns))
        issues.extend(_missing_pronoun_issues(text, masked))
        issues.extend(_numeric_without_source_issues(text, masked, patterns))
        issues.extend(_paragraph_uniformity_issue(text, masked, patterns))
        issues.extend(_hedge_uniformity_issue(text, masked, patterns))
        issues.extend(_symmetry_bias_issue(text, masked, patterns))
        issues.extend(_over_enumeration_issues(text, masked, patterns))
    if not skills or "grammar-checker-vi" in skills:
        issues.extend(_redundant_connector_issues(text, masked, patterns))
        issues.extend(_repeated_word_issues(text, masked, patterns))
        issues.extend(_unbalanced_delimiter_issues(text, masked, patterns))
    if not skills or "style-guide-vi" in skills:
        issues.extend(_pronoun_issues(text, masked, patterns))
        issues.extend(_terminology_consistency_issues(text, masked, patterns))
        issues.extend(_percentage_consistency_issues(text, masked, patterns))
        issues.extend(_acronym_issues(text, masked, patterns))
        issues.extend(_title_case_issues(text, masked, patterns))
    if not skills or "translationese-cleaner-vi" in skills:
        issues.extend(_administrative_stack_issues(text, masked, patterns))
    unique: dict[tuple[str, int, int], dict[str, Any]] = {}
    for issue in issues:
        key = (issue["pattern_id"], issue["line"], issue["column"])
        unique[key] = issue
    if deep and (not skills or "humanizer-vi" in skills):
        deep_issues = _deep_judge_issues(
            text,
            patterns,
            api_key=api_key,
            model=model,
            min_confidence=min_confidence,
        )
        for issue in deep_issues:
            key = (issue["pattern_id"], issue["line"], issue["column"])
            unique[key] = issue
    return sorted(
        unique.values(),
        key=lambda item: (item["line"], item["column"], SEVERITY_ORDER[item["severity"]]),
    )


def lint_file(
    path: Path,
    skills: set[str] | None = None,
    pattern_dir: Any | None = None,
    *,
    deep: bool = False,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
    min_confidence: int = 4,
) -> dict[str, Any]:
    issues = lint_text(
        path.read_text(encoding="utf-8"),
        skills,
        pattern_dir,
        deep=deep,
        api_key=api_key,
        model=model,
        min_confidence=min_confidence,
    )
    counts = Counter(issue["finding_type"] for issue in issues)
    return {
        "file": str(path),
        "summary": {
            "total": len(issues),
            **{finding_type: counts[finding_type] for finding_type in FINDING_TYPES},
            "note": "Số phát hiện cần review, không phải xác suất văn bản do AI tạo.",
        },
        "issues": issues,
    }


def _paths(target: Path, recursive: bool) -> Iterable[Path]:
    if target.is_file():
        yield target
    elif target.is_dir() and recursive:
        for path in sorted(target.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                yield path
    else:
        raise ValueError("đường dẫn phải là file, hoặc dùng --recursive với thư mục")


def _print_text(result: dict[str, Any]) -> None:
    print(f"{result['file']}: {result['summary']['total']} phát hiện cần review")
    for issue in result["issues"]:
        label = issue["finding_type"].upper()
        print(
            f"  {issue['line']}:{issue['column']} {label} {issue['severity']} "
            f"{issue['pattern_id']} {issue['message']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint heuristic bề mặt cho tiếng Việt; không phải công cụ phát hiện AI"
    )
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        help="Repository chứa patterns/; mặc định tự phát hiện",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--skill", action="append", dest="skills")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Bật LLM judge cho 6 pattern Nhóm C (cần GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--deep-model",
        default="gemini-2.5-flash",
        help="Model cho LLM judge",
    )
    parser.add_argument(
        "--deep-min-confidence",
        type=int,
        default=4,
        help="Ngưỡng confidence tối thiểu (1-5)",
    )
    args = parser.parse_args(argv)
    try:
        root = repository_root(args.root)
        pattern_dir = data_location("patterns", root)
        selected_skills = set(args.skills) if args.skills else None
        results = [
            lint_file(
                path,
                selected_skills,
                pattern_dir,
                deep=args.deep,
                model=args.deep_model,
                min_confidence=args.deep_min_confidence,
            )
            for path in _paths(args.path, args.recursive)
        ]
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        payload = results[0] if len(results) == 1 else results
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            _print_text(result)
    return 1 if any(result["summary"]["total"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())