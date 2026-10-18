import {
  ContributionRequest,
  ContributionResponse,
  HealthResponse,
  LintResponse,
  PatternsResponse,
  RefineResponse,
  RewriteResponse,
  ScanReportResponse,
  SkillsResponse,
  SuggestFixResponse,
  VocabularyResponse,
} from "./types";

const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_BASE = rawBase.replace(/\/+$/, "");
let healthRequest: Promise<HealthResponse> | null = null;

interface ErrorAttempt {
  model?: string;
  kind?: string;
  http_status?: number | null;
  raw?: string;
  retry_attempt?: number;
}

interface ErrorDetailObject {
  message?: string;
  exception_type?: string;
  exception_str?: string;
  attempts?: ErrorAttempt[];
}

function formatErrorDetail(detail: unknown, fallbackStatus: number): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === "object") {
    const obj = detail as ErrorDetailObject;
    const lines: string[] = [];
    if (obj.message) {
      lines.push(obj.message);
    } else {
      lines.push(`Yêu cầu thất bại với mã lỗi HTTP ${fallbackStatus}`);
    }
    if (obj.attempts && obj.attempts.length > 0) {
      lines.push("");
      lines.push("Chi tiết từng lần gọi Groq:");
      for (const a of obj.attempts) {
        const status =
          a.http_status === null || a.http_status === undefined
            ? "?"
            : String(a.http_status);
        const kind = a.kind || "unknown";
        const model = a.model || "(unknown model)";
        const retry =
          a.retry_attempt && a.retry_attempt > 0
            ? ` (retry #${a.retry_attempt})`
            : "";
        lines.push(`  • ${model}${retry} — HTTP ${status} / ${kind}`);
        if (a.raw) {
          lines.push(`    ${a.raw}`);
        }
      }
    }
    if (obj.exception_type) {
      lines.push("");
      lines.push(`Loại lỗi: ${obj.exception_type}`);
    }
    if (obj.exception_str && !obj.attempts?.length) {
      lines.push("");
      lines.push(`Chi tiết: ${obj.exception_str}`);
    }
    return lines.join("\n");
  }
  return `Yêu cầu thất bại với mã lỗi HTTP ${fallbackStatus}`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Yêu cầu thất bại với mã lỗi HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && "detail" in data) {
        errorDetail = formatErrorDetail(data.detail, res.status);
      }
    } catch {
      // JSON parse error fallback
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  if (!healthRequest) {
    healthRequest = fetch(`${API_BASE}/api/health`).then((res) =>
      handleResponse<HealthResponse>(res)
    );
  }
  return healthRequest;
}

export async function lintText(text: string, skills?: string[]): Promise<LintResponse> {
  const res = await fetch(`${API_BASE}/api/lint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, skills }),
  });
  return handleResponse<LintResponse>(res);
}

export async function fetchPatterns(): Promise<PatternsResponse> {
  const res = await fetch(`${API_BASE}/api/patterns`);
  return handleResponse<PatternsResponse>(res);
}

export async function fetchSkills(): Promise<SkillsResponse> {
  const res = await fetch(`${API_BASE}/api/skills`);
  return handleResponse<SkillsResponse>(res);
}

export async function rewriteText(
  text: string,
  skill: string = "humanizer-vi",
  issueIds?: string[]
): Promise<RewriteResponse> {
  const res = await fetch(`${API_BASE}/api/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, skill, issue_ids: issueIds }),
  });
  return handleResponse<RewriteResponse>(res);
}

export async function suggestFix(
  text: string,
  patternIds: string[],
  skill: string = "humanizer-vi"
): Promise<SuggestFixResponse> {
  const res = await fetch(`${API_BASE}/api/suggest-fix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, pattern_ids: patternIds, skill }),
  });
  return handleResponse<SuggestFixResponse>(res);
}

export async function submitContribution(
  data: ContributionRequest
): Promise<ContributionResponse> {
  const res = await fetch(`${API_BASE}/api/contributions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ContributionResponse>(res);
}

// ===== v1.2: Report Refiner =====

export async function scanReport(text: string): Promise<ScanReportResponse> {
  const res = await fetch(`${API_BASE}/api/scan-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return handleResponse<ScanReportResponse>(res);
}

export async function refineSentence(
  paragraphText: string,
  sentence: string,
  issueTypes: string[],
  userCommand: string
): Promise<RefineResponse> {
  const res = await fetch(`${API_BASE}/api/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paragraph_text: paragraphText,
      sentence,
      issue_types: issueTypes,
      user_command: userCommand,
    }),
  });
  return handleResponse<RefineResponse>(res);
}

export async function fetchVocabulary(): Promise<VocabularyResponse> {
  const res = await fetch(`${API_BASE}/api/vocabulary`);
  return handleResponse<VocabularyResponse>(res);
}