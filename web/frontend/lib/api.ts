import {
  ContributionRequest,
  ContributionResponse,
  HealthResponse,
  HumanizeResponse,
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
      lines.push("Chi tiết từng lần gọi mô hình:");
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

// ===== v1.3: Humanize =====

export async function humanizeText(text: string): Promise<HumanizeResponse> {
  const res = await fetch(`${API_BASE}/api/humanize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return handleResponse<HumanizeResponse>(res);
}

// ===== Contributor flow =====

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
