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


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    skill: str = "humanizer-vi"
    issue_ids: list[str] | None = None


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


class SuggestFixRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    pattern_ids: list[str] = Field(default_factory=list)
    skill: str = "humanizer-vi"


class SuggestFixResponse(BaseModel):
    suggestion: str
    review_status: str = "unreviewed"
    disclaimer: str = "Gợi ý do model sinh, cần người đọc kiểm chứng bảo toàn dữ kiện."


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
# v1.2 — Giảm đạo văn AI (Interactive Report Refiner)
# ============================================================


class ScanReportIssue(BaseModel):
    """Một vấn đề được AI phát hiện trong báo cáo."""

    paragraph_index: int
    paragraph_text: str
    issue_type: str
    sentence: str
    reason: str
    question: str
    suggestions: list[str] = []
    confidence: int = 3


class ScanReportRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class ScanReportResponse(BaseModel):
    issues: list[ScanReportIssue]
    total_paragraphs: int
    total_issues: int


class RefineRequest(BaseModel):
    """User gửi câu lệnh để AI sửa một câu cụ thể.

    v1.2.1: nhận list issue_types để xử lý nhiều vấn đề trên cùng một câu
    trong 1 lần gọi duy nhất.
    """

    paragraph_text: str = Field(..., min_length=1, max_length=10000)
    sentence: str = Field(..., min_length=1, max_length=5000)
    issue_types: list[str] = Field(..., min_length=1)
    user_command: str = Field(..., min_length=1, max_length=2000)


class RefineResponse(BaseModel):
    refined_sentence: str
    refined_paragraph: str
    change_summary: str
    review_status: str = "unreviewed"


class DiffSegment(BaseModel):
    """Một đoạn trong diff."""

    type: str  # "unchanged" | "removed" | "added"
    text: str


class DiffResponse(BaseModel):
    original: str
    refined: str
    diff_segments: list[DiffSegment]