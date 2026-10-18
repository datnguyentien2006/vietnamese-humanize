export interface IssueOccurrence {
  line: number;
  column: number;
  excerpt: string;
  matched_text: string;
  start: number;
  end: number;
  sentence: string;
  sentence_start: number;
  sentence_end: number;
  paragraph: string;
  paragraph_start: number;
  paragraph_end: number;
}

export interface IssueItem {
  pattern_id: string;
  finding_type: "error" | "warning" | "preference" | "heuristic" | string;
  severity: "high" | "medium" | "low" | string;
  confidence: string;
  scope: string;
  line: number;
  column: number;
  excerpt: string;
  message: string;
  suggestion: string;
  occurrences: IssueOccurrence[];
  start: number;
  end: number;
  sentence: string;
  sentence_start: number;
  sentence_end: number;
  paragraph: string;
  paragraph_start: number;
  paragraph_end: number;
}

export interface LintSummary {
  total: number;
  error: number;
  warning: number;
  preference: number;
  heuristic: number;
  note: string;
}

export interface LintResponse {
  version: string;
  summary: LintSummary;
  issues: IssueItem[];
}

export interface HealthResponse {
  status: string;
  version: string;
  capabilities: {
    rewrite: boolean;
    contributions: boolean;
  };
}

export interface PatternItem {
  id: string;
  name: string;
  skill: string;
  category: string;
  finding_type: string;
  severity: string;
  summary: string;
  why_it_matters: string;
  rewrite_strategy: string;
}

export interface PatternsResponse {
  patterns: PatternItem[];
}

export interface SkillItem {
  id: string;
  name: string;
  when_to_use: string;
  when_not_to_use: string;
}

export interface SkillsResponse {
  skills: SkillItem[];
}

export interface RewriteEdit {
  issue_pattern_id: string;
  find_preview: string;
  replace_preview: string;
  reason: string;
}

export interface RewriteStats {
  total_issues: number;
  fixed: number;
  skipped: number;
  edits_applied: number;
  edits_rejected: number;
  verification_attempts: number;
  verification_passed: boolean;
}

export interface UnresolvedIssue {
  pattern_id: string;
  line: number;
  column: number;
  message: string;
}

export interface RewriteResponse {
  rewrite: string;
  review_status: string;
  disclaimer: string;
  stats: RewriteStats | null;
  applied_edits: RewriteEdit[];
  unresolved_issues: UnresolvedIssue[];
}

export interface SuggestFixResponse {
  suggestion: string;
  review_status: string;
  disclaimer: string;
}

export interface ContributionRequest {
  input_text: string;
  context?: string;
  suggestion: string;
  skill: string;
  pattern_ids?: string[];
  note?: string;
  consent: boolean;
}

export interface ContributionResponse {
  id: string;
  status: string;
  message: string;
}

// ===== Manual edit feature =====

export type EditStatus = "editing" | "accepted" | "skipped";

export interface Edit {
  issueKey: string;
  issue: IssueItem;
  originalParagraph: string;
  newParagraph: string;
  paragraphStart: number;
  paragraphEnd: number;
  status: EditStatus;
  acceptedAt?: number;
}

export interface HighlightRange {
  start: number;
  end: number;
  issueKey: string;
}

// ===== v1.2: Report Refiner =====

export interface ScanReportIssue {
  paragraph_index: number;
  paragraph_text: string;
  issue_type: string;
  sentence: string;
  reason: string;
  question: string;
  suggestions: string[];
  confidence: number;
}

export interface ScanReportResponse {
  issues: ScanReportIssue[];
  total_paragraphs: number;
  total_issues: number;
}

/**
 * Nhóm nhiều ScanReportIssue cùng (paragraph_index, sentence).
 *
 * `paragraph_text` là đoạn văn hiện tại (có thể đã được cập nhật bởi các
 * accept trước đó trong cùng đoạn). Khi `is_stale = true`, nghĩa là câu
 * gốc của group này không còn tồn tại trong paragraph_text mới — cần bỏ
 * qua hoặc xử lý riêng.
 */
export interface ReportIssueGroup {
  paragraph_index: number;
  paragraph_text: string;
  sentence: string;
  issue_types: string[];
  reasons: string[];
  question: string;
  suggestions: string[];
  confidence: number;
  raw_issues: ScanReportIssue[];
  is_stale?: boolean;
  stale_reason?: string;
}

export interface RefineResponse {
  refined_sentence: string;
  refined_paragraph: string;
  change_summary: string;
  review_status: string;
}

export interface VocabularyResponse {
  mapping: Record<string, string[]>;
}

export interface IssueTypeInfo {
  key: string;
  label: string;
  description: string;
}

export interface RefineHistoryEntry {
  group: ReportIssueGroup;
  refinedSentence: string;
  refinedParagraph: string;
  changeSummary: string;
  userCommand: string;
  /** Đoạn văn trước khi user sửa (dùng để revert). */
  oldParagraphText: string;
}