from pydantic import BaseModel, Field

VALID_SKILLS = {
    "humanizer-vi",
    "translationese-cleaner-vi",
    "grammar-checker-vi",
    "style-guide-vi",
}


class LintRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    skills: list[str] | None = None


class IssueOccurrence(BaseModel):
    line: int
    column: int
    excerpt: str
    matched_text: str
    start: int = 0
    end: int = 0
    sentence: str = ""
    sentence_start: int = 0
    sentence_end: int = 0
    paragraph: str = ""
    paragraph_start: int = 0
    paragraph_end: int = 0


class IssueItem(BaseModel):
    pattern_id: str
    finding_type: str
    severity: str
    confidence: str
    scope: str
    line: int
    column: int
    excerpt: str
    message: str
    suggestion: str
    occurrences: list[IssueOccurrence]
    start: int = 0
    end: int = 0
    sentence: str = ""
    sentence_start: int = 0
    sentence_end: int = 0
    paragraph: str = ""
    paragraph_start: int = 0
    paragraph_end: int = 0


class LintSummary(BaseModel):
    total: int
    error: int
    warning: int
    preference: int
    heuristic: int
    note: str = "Số phát hiện cần review, không phải xác suất văn bản do AI tạo."


class LintResponse(BaseModel):
    version: str
    summary: LintSummary
    issues: list[IssueItem]


class PatternItem(BaseModel):
    id: str
    name: str
    skill: str
    category: str
    finding_type: str
    severity: str
    summary: str
    why_it_matters: str
    rewrite_strategy: str


class PatternsResponse(BaseModel):
    patterns: list[PatternItem]


class SkillItem(BaseModel):
    id: str
    name: str
    when_to_use: str
    when_not_to_use: str


class SkillsResponse(BaseModel):
    skills: list[SkillItem]


class RewriteEdit(BaseModel):
    issue_pattern_id: str
    find_preview: str
    replace_preview: str
    reason: str


class RewriteStats(BaseModel):
    total_issues: int
    fixed: int
    skipped: int
    edits_applied: int
    edits_rejected: int
    verification_attempts: int
    verification_passed: bool


class UnresolvedIssue(BaseModel):
    pattern_id: str
    line: int
    column: int
    message: str


class RewriteResponse(BaseModel):
    rewrite: str
    review_status: str = "unreviewed"
    disclaimer: str = "Gợi ý do model sinh, cần người đọc kiểm chứng bảo toàn dữ kiện."
    stats: RewriteStats | None = None
    applied_edits: list[RewriteEdit] = []
    unresolved_issues: list[UnresolvedIssue] = []


class ContributionCreate(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=20000)
    context: str | None = Field(None, max_length=5000)
    suggestion: str = Field(..., min_length=1, max_length=20000)
    skill: str = "humanizer-vi"
    pattern_ids: list[str] | None = None
    note: str | None = Field(None, max_length=5000)
    consent: bool


class ContributionResponse(BaseModel):
    id: str
    status: str
    message: str


class AdminContributionItem(BaseModel):
    id: str
    created_at: str
    input_text: str
    context: str | None = None
    suggestion: str
    skill: str
    pattern_ids: list[str] | None = None
    note: str | None = None
    consent: bool
    status: str
    review_note: str | None = None
    reviewed_at: str | None = None


class AdminContributionPatch(BaseModel):
    status: str
    review_note: str | None = None


# ============================================================
# v1.3 - Humanize văn bản (mô hình chuyên biệt + Groq fallback)
# ============================================================


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)


class FactCheck(BaseModel):
    lost_tokens: list[str] = []
    added_tokens: list[str] = []


class ReviewSuggestion(BaseModel):
    issue_type: str
    excerpt: str
    reason: str
    question: str
    suggestions: list[str] = []
    confidence: int = 3


class HumanizeStats(BaseModel):
    attempts: int = 0
    latency_seconds: float = 0.0
    total_issues: int | None = None
    fixed: int | None = None
    edits_applied: int | None = None
    edits_rejected: int | None = None
    verification_attempts: int | None = None
    verification_passed: bool | None = None


class HumanizeResponse(BaseModel):
    rewrite: str
    stats: HumanizeStats
    # "humanizer-model" | "groq-fallback"
    provider: str
    fact_check: FactCheck
    suggestions: list[ReviewSuggestion] = []
    warnings: list[str] = []

class DiffSegment(BaseModel):
    """Một đoạn trong diff."""

    type: str  # "unchanged" | "removed" | "added"
    text: str


class DiffResponse(BaseModel):
    original: str
    refined: str
    diff_segments: list[DiffSegment]