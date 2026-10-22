/**
 * API dùng riêng cho luồng góp mẫu văn bản (/contribute).
 *
 * tách khỏi lib/api.ts trong refactor v1.3 vì luồng humanize chính không
 * còn dùng skills — nhưng app/contribute/page.tsx (ngoài phạm vi refactor)
 * vẫn cần fetchSkills, nên hàm này được re-export từ lib/api.ts.
 */
import { SkillsResponse } from "./types";

const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const CONTRIB_API_BASE = rawBase.replace(/\/+$/, "");

export async function fetchSkills(): Promise<SkillsResponse> {
  const res = await fetch(`${CONTRIB_API_BASE}/api/skills`);
  return handleContribResponse<SkillsResponse>(res);
}

async function handleContribResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Yêu cầu thất bại với mã lỗi HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && "detail" in data && typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // JSON parse error fallback
    }
    throw new Error(message);
  }
  return res.json();
}
