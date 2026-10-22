export interface CapabilityFlags {
  humanize: boolean;
  contributions: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  capabilities: CapabilityFlags;
}

// ===== v1.3: Humanize =====

export interface FactCheck {
  lost_tokens: string[];
  added_tokens: string[];
}

export interface Suggestion {
  issue_type: string;
  excerpt: string;
  reason: string;
  question: string;
  suggestions: string[];
  confidence: number;
}

/**
 * Thống kê lần humanize. `total_issues`, `fixed`, `edits_applied`,
 * `edits_rejected`, `verification_attempts`, `verification_passed` có thể là
 * null khi server dùng mô hình chuyên biệt (không chạy pipeline lint/verify).
 */
export interface HumanizeStats {
  attempts: number;
  latency_seconds: number;
  total_issues?: number | null;
  fixed?: number | null;
  edits_applied?: number | null;
  edits_rejected?: number | null;
  verification_attempts?: number | null;
  verification_passed?: boolean | null;
}

export interface HumanizeResponse {
  rewrite: string;
  stats?: HumanizeStats;
  provider: "humanizer-model" | "groq-fallback";
  fact_check: FactCheck;
  suggestions: Suggestion[];
  warnings: string[];
}

// ===== Contributor flow (vẫn dùng ở /contribute) =====

export interface SkillItem {
  id: string;
  name: string;
  when_to_use: string;
  when_not_to_use: string;
}

export interface SkillsResponse {
  skills: SkillItem[];
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
