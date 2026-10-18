import { Edit, HighlightRange, IssueItem } from "./types";

export function makeIssueKey(issue: IssueItem): string {
  return `${issue.pattern_id}|${issue.line}|${issue.column}`;
}

/**
 * Từ danh sách edits, chọn ra edit "có hiệu lực" cho mỗi paragraph.
 *
 * Nếu có nhiều edit cùng `paragraphStart` (do user sửa nhiều issue trong
 * cùng một đoạn), chỉ giữ lại edit có `acceptedAt` mới nhất. Điều này
 * đảm bảo áp dụng đúng trạng thái cuối cùng của đoạn văn.
 */
function pickLatestAcceptedPerParagraph(edits: Edit[]): Edit[] {
  const accepted = edits.filter((e) => e.status === "accepted");
  const latest = new Map<number, Edit>();
  for (const edit of accepted) {
    const existing = latest.get(edit.paragraphStart);
    if (!existing) {
      latest.set(edit.paragraphStart, edit);
      continue;
    }
    const existingTime = existing.acceptedAt ?? 0;
    const editTime = edit.acceptedAt ?? 0;
    if (editTime >= existingTime) {
      latest.set(edit.paragraphStart, edit);
    }
  }
  return Array.from(latest.values());
}

/**
 * Apply tất cả edit có status='accepted' vào originalText.
 *
 * Mỗi edit thay thế một đoạn văn (paragraph). Sắp xếp theo paragraphStart
 * giảm dần (phải → trái) để offset của các edit bên trái không bị lệch.
 * Với mỗi paragraph, chỉ apply edit mới nhất (theo acceptedAt).
 */
export function applyEdits(originalText: string, edits: Edit[]): string {
  const effective = pickLatestAcceptedPerParagraph(edits);
  const sorted = effective.sort(
    (a, b) => b.paragraphStart - a.paragraphStart
  );

  let result = originalText;
  for (const edit of sorted) {
    if (
      edit.paragraphStart < 0 ||
      edit.paragraphEnd > result.length ||
      edit.paragraphStart > edit.paragraphEnd
    ) {
      continue;
    }
    result =
      result.slice(0, edit.paragraphStart) +
      edit.newParagraph +
      result.slice(edit.paragraphEnd);
  }
  return result;
}

/**
 * Tính vị trí highlight trong workingText (sau khi applyEdits).
 * Delta tích lũy từ trái sang phải, mỗi paragraph chỉ tính một edit mới nhất.
 */
export function computeHighlightRanges(edits: Edit[]): HighlightRange[] {
  const effective = pickLatestAcceptedPerParagraph(edits);
  const sorted = effective.sort(
    (a, b) => a.paragraphStart - b.paragraphStart
  );

  const ranges: HighlightRange[] = [];
  let delta = 0;

  for (const edit of sorted) {
    const start = edit.paragraphStart + delta;
    const end = start + edit.newParagraph.length;
    ranges.push({ start, end, issueKey: edit.issueKey });
    delta += edit.newParagraph.length - edit.originalParagraph.length;
  }
  return ranges;
}

/** Hai edit cùng paragraph thì coi là overlap. */
export function editsOverlap(a: Edit, b: Edit): boolean {
  return a.paragraphStart === b.paragraphStart;
}

/**
 * Cho biết edit có thể undo được không.
 *
 * Chỉ cho undo edit MỚI NHẤT trong đoạn văn (theo acceptedAt). Nếu user đã
 * accept nhiều edit trong cùng một đoạn, các edit cũ hơn không thể undo
 * trực tiếp — phải undo edit mới nhất trước, tránh phải rollback phức tạp.
 *
 * - Edit status = "skipped": luôn cho undo.
 * - Edit status = "accepted": cho undo nếu là edit mới nhất trong đoạn.
 */
export function canUndoEdit(
  targetEdit: Edit,
  allEdits: Map<string, Edit>
): boolean {
  if (targetEdit.status === "skipped") return true;
  if (targetEdit.status !== "accepted") return false;

  const acceptedInParagraph = Array.from(allEdits.values())
    .filter(
      (e) =>
        e.paragraphStart === targetEdit.paragraphStart &&
        e.status === "accepted"
    )
    .sort((a, b) => (b.acceptedAt ?? 0) - (a.acceptedAt ?? 0));

  if (acceptedInParagraph.length === 0) return false;
  return acceptedInParagraph[0].issueKey === targetEdit.issueKey;
}