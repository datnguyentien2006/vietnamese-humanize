"use client";

import React, { useEffect, useMemo, useState } from "react";
import { refineSentence, scanReport } from "../lib/api";
import {
  RefineHistoryEntry,
  ReportIssueGroup,
  ScanReportIssue,
} from "../lib/types";

interface ReportRefinerProps {
  originalText: string;
  originalTextBeforeAll: string;
  onComplete: (refinedText: string) => void;
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
  unverified_data: "Số liệu chưa kiểm chứng",
  academic_tone: "Từ ngữ quá academic",
  long_sentence: "Câu quá dài",
  missing_evidence: "Thiếu minh chứng",
  logic_gap: "Khoảng trống logic",
  repetition: "Lặp ý",
  vague_reference: "Tham chiếu mơ hồ",
  passive_overuse: "Lạm dụng bị động",
  register_mismatch: "Giọng văn không phù hợp",
};

/**
 * Render đoạn văn với câu cần xem xét được bôi vàng.
 */
function renderParagraphWithHighlight(
  paragraph: string,
  sentence: string
): React.ReactNode {
  if (!sentence || !paragraph.includes(sentence)) {
    return paragraph;
  }

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  let key = 0;

  while (cursor < paragraph.length) {
    const idx = paragraph.indexOf(sentence, cursor);
    if (idx < 0) {
      parts.push(
        <span key={`t-${key++}`}>{paragraph.slice(cursor)}</span>
      );
      break;
    }
    if (idx > cursor) {
      parts.push(
        <span key={`t-${key++}`}>{paragraph.slice(cursor, idx)}</span>
      );
    }
    parts.push(
      <mark
        key={`m-${key++}`}
        className="bg-yellow-200 text-yellow-950 rounded-sm px-0.5"
      >
        {sentence}
      </mark>
    );
    cursor = idx + sentence.length;
  }
  return parts;
}

/**
 * Group các issue cùng (paragraph_index, sentence) lại.
 */
function groupIssues(issues: ScanReportIssue[]): ReportIssueGroup[] {
  const map = new Map<string, ReportIssueGroup>();

  for (const issue of issues) {
    const key = `${issue.paragraph_index}::${issue.sentence}`;
    const existing = map.get(key);
    if (existing) {
      if (!existing.issue_types.includes(issue.issue_type)) {
        existing.issue_types.push(issue.issue_type);
      }
      if (!existing.reasons.includes(issue.reason)) {
        existing.reasons.push(issue.reason);
      }
      for (const s of issue.suggestions) {
        if (!existing.suggestions.includes(s)) {
          existing.suggestions.push(s);
        }
      }
      if (issue.confidence > existing.confidence) {
        existing.confidence = issue.confidence;
        existing.question = issue.question;
      }
      existing.raw_issues.push(issue);
    } else {
      map.set(key, {
        paragraph_index: issue.paragraph_index,
        paragraph_text: issue.paragraph_text,
        sentence: issue.sentence,
        issue_types: [issue.issue_type],
        reasons: [issue.reason],
        question: issue.question,
        suggestions: [...issue.suggestions],
        confidence: issue.confidence,
        raw_issues: [issue],
      });
    }
  }

  const groups = Array.from(map.values());
  groups.sort((a, b) => {
    if (a.paragraph_index !== b.paragraph_index) {
      return a.paragraph_index - b.paragraph_index;
    }
    return (
      a.paragraph_text.indexOf(a.sentence) -
      b.paragraph_text.indexOf(b.sentence)
    );
  });
  return groups;
}

export const ReportRefiner: React.FC<ReportRefinerProps> = ({
  originalText,
  originalTextBeforeAll,
  onComplete,
}) => {
  const [phase, setPhase] = useState<"idle" | "scanning" | "refining" | "done">(
    "idle"
  );
  const [groups, setGroups] = useState<ReportIssueGroup[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentText, setCurrentText] = useState(originalText);
  const [userCommand, setUserCommand] = useState("");
  const [refining, setRefining] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewParagraph, setPreviewParagraph] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<RefineHistoryEntry[]>([]);
  const [showOriginalBeforeAll, setShowOriginalBeforeAll] = useState(false);

  // Reset khi prop originalText thay đổi (remount từ page.tsx)
  useEffect(() => {
    setGroups([]);
    setCurrentIndex(0);
    setCurrentText(originalText);
    setUserCommand("");
    setPreview(null);
    setPreviewParagraph(null);
    setError(null);
    setHistory([]);
    setPhase("idle");
  }, [originalText]);

  const currentGroup = groups[currentIndex];
  const totalIssuesRaw = useMemo(
    () => groups.reduce((sum, g) => sum + g.raw_issues.length, 0),
    [groups]
  );

  const handleScan = async () => {
    setPhase("scanning");
    setError(null);
    try {
      const res = await scanReport(currentText);
      const grouped = groupIssues(res.issues);
      setGroups(grouped);
      setCurrentIndex(0);
      setPreview(null);
      setPreviewParagraph(null);
      setHistory([]);
      setUserCommand("");
      setPhase(grouped.length > 0 ? "refining" : "done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không quét được văn bản");
      setPhase("idle");
    }
  };

  const handleRefine = async () => {
    if (!currentGroup || !userCommand.trim()) return;
    setRefining(true);
    setError(null);
    try {
      const res = await refineSentence(
        currentGroup.paragraph_text,
        currentGroup.sentence,
        currentGroup.issue_types,
        userCommand
      );
      setPreview(res.refined_sentence);
      setPreviewParagraph(res.refined_paragraph);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không sửa được câu");
    } finally {
      setRefining(false);
    }
  };

  const handleAccept = () => {
    if (!currentGroup || !preview || !previewParagraph) return;

    const oldPara = currentGroup.paragraph_text;
    const newPara = previewParagraph;

    // 1. Update currentText
    const newText = currentText.includes(oldPara)
      ? currentText.replace(oldPara, newPara)
      : currentText;
    setCurrentText(newText);

    // 2. Update paragraph_text của TẤT CẢ group cùng paragraph gốc.
    //    Với group khác: nếu sentence còn trong newPara → giữ; ngược lại
    //    → đánh dấu stale để user bỏ qua.
    setGroups((prev) =>
      prev.map((g, idx) => {
        if (g.paragraph_text !== oldPara) return g;

        if (idx === currentIndex) {
          // Group hiện tại đã xử lý xong
          return { ...g, paragraph_text: newPara };
        }

        const stillHasSentence = newPara.includes(g.sentence);
        return {
          ...g,
          paragraph_text: newPara,
          is_stale: !stillHasSentence,
          stale_reason: stillHasSentence
            ? undefined
            : "Câu này đã thay đổi do chỉnh sửa khác trong cùng đoạn văn. Không cần xử lý lại.",
        };
      })
    );

    // 3. Push history
    setHistory([
      ...history,
      {
        group: { ...currentGroup },
        refinedSentence: preview,
        refinedParagraph: previewParagraph,
        changeSummary: "",
        userCommand,
        oldParagraphText: oldPara,
      },
    ]);

    // 4. Reset preview và chuyển group tiếp theo
    setPreview(null);
    setPreviewParagraph(null);
    setUserCommand("");

    if (currentIndex < groups.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setPhase("done");
    }
  };

  const handleSkip = () => {
    setPreview(null);
    setPreviewParagraph(null);
    setUserCommand("");
    if (currentIndex < groups.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setPhase("done");
    }
  };

  const handleUndo = () => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    const { oldParagraphText, refinedParagraph } = last;

    // 1. Revert currentText
    const revertedText = currentText.includes(refinedParagraph)
      ? currentText.replace(refinedParagraph, oldParagraphText)
      : currentText;
    setCurrentText(revertedText);

    // 2. Revert paragraph_text + clear stale flag cho tất cả group cùng paragraph
    setGroups((prev) =>
      prev.map((g) => {
        if (g.paragraph_text !== refinedParagraph) return g;
        return {
          ...g,
          paragraph_text: oldParagraphText,
          is_stale: false,
          stale_reason: undefined,
        };
      })
    );

    // 3. Pop history và lùi con trỏ
    setHistory(history.slice(0, -1));
    setCurrentIndex(Math.max(0, currentIndex - 1));
    setPreview(null);
    setPreviewParagraph(null);
    setUserCommand("");
  };

  const handleRevertOne = (entry: RefineHistoryEntry, index: number) => {
    // Chỉ cho revert entry cuối cùng để tránh conflict paragraph
    if (index !== history.length - 1) return;
    handleUndo();
  };

  const handleResetAll = () => {
    setPhase("idle");
    setGroups([]);
    setCurrentIndex(0);
    setCurrentText(originalText);
    setUserCommand("");
    setPreview(null);
    setPreviewParagraph(null);
    setError(null);
    setHistory([]);
  };

  const handleApplyToEditor = () => {
    onComplete(currentText);
  };

  // ============================================================
  // PHASE: IDLE
  // ============================================================
  if (phase === "idle") {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center text-sm">
            🔍
          </span>
          Giảm đạo văn AI
        </h2>
        <p className="text-sm text-slate-600 mb-4">
          AI sẽ đọc văn bản bạn đã soát văn phong và tìm những chỗ có thể khiến
          người đọc cảm thấy &quot;máy móc&quot;. Sau đó bạn và AI cùng sửa
          từng chỗ một.
        </p>

        <div className="mb-4 bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center justify-between">
            <span>Văn bản sẽ được AI quét</span>
            <span className="text-slate-400 normal-case font-normal">
              ({currentText.length} ký tự)
            </span>
          </div>
          <div className="max-h-32 overflow-y-auto text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">
            {currentText || (
              <span className="text-slate-400 italic">
                (Chưa có văn bản — hãy quay lại soát văn phong trước)
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={handleScan}
          disabled={!currentText.trim()}
          className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-sm rounded-xl shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          Bắt đầu quét
        </button>
      </div>
    );
  }

  // ============================================================
  // PHASE: SCANNING
  // ============================================================
  if (phase === "scanning") {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center">
        <div className="w-10 h-10 mx-auto mb-3">
          <svg
            className="animate-spin text-amber-600"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
        <p className="text-sm font-bold text-slate-700">
          Đang phân tích văn bản...
        </p>
        <p className="text-xs text-slate-500 mt-1">
          AI đang đọc từng đoạn để tìm vấn đề phong cách.
        </p>
      </div>
    );
  }

  // ============================================================
  // PHASE: DONE
  // ============================================================
  if (phase === "done") {
    const processedCount = history.length;
    const skippedCount = groups.length - processedCount;

    return (
      <div className="bg-white rounded-2xl border border-emerald-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-slate-100">
          <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xl">
            ✓
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Đã hoàn tất giảm đạo văn AI
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Bạn đã sửa {processedCount} vấn đề
              {skippedCount > 0 && `, bỏ qua ${skippedCount}`}
            </p>
          </div>
        </div>

        {history.length > 0 && (
          <div className="mb-5">
            <div className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider mb-2">
              Các thay đổi đã thực hiện ({history.length})
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {history.map((entry, idx) => (
                <div
                  key={idx}
                  className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs"
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex flex-wrap gap-1">
                      {entry.group.issue_types.map((t) => (
                        <span
                          key={t}
                          className="text-[10px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200"
                        >
                          {ISSUE_TYPE_LABELS[t] || t}
                        </span>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRevertOne(entry, idx)}
                      disabled={idx !== history.length - 1}
                      title={
                        idx !== history.length - 1
                          ? "Chỉ có thể hoàn tác thay đổi mới nhất"
                          : "Hoàn tác thay đổi này"
                      }
                      className="text-[10px] text-slate-500 hover:text-rose-600 font-semibold flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-500"
                    >
                      Hoàn tác
                    </button>
                  </div>
                  <div className="text-slate-500 line-through mb-1">
                    {entry.group.sentence}
                  </div>
                  <div className="text-emerald-800 font-medium">
                    → {entry.refinedSentence}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
              So sánh văn bản
            </div>
            <button
              type="button"
              onClick={() => setShowOriginalBeforeAll((v) => !v)}
              className="text-[11px] font-semibold text-sky-700 hover:text-sky-800 bg-sky-50 hover:bg-sky-100 px-2 py-1 rounded-md border border-sky-200 transition-colors"
            >
              {showOriginalBeforeAll
                ? "Ẩn văn bản gốc ban đầu"
                : "So sánh với văn bản gốc ban đầu"}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 font-mono">
                {showOriginalBeforeAll
                  ? "Văn bản gốc ban đầu"
                  : "Sau khi soát văn phong"}
              </div>
              <p className="whitespace-pre-wrap text-xs text-slate-800 leading-relaxed">
                {showOriginalBeforeAll
                  ? originalTextBeforeAll
                  : originalText}
              </p>
            </div>
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200">
              <div className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider mb-2 font-mono">
                Sau khi giảm đạo văn AI (v1.2)
              </div>
              <p className="whitespace-pre-wrap text-xs text-emerald-950 leading-relaxed">
                {currentText}
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={handleResetAll}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition-colors"
          >
            Làm lại từ đầu
          </button>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(currentText);
            }}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition-colors"
          >
            Sao chép văn bản cuối
          </button>
          <button
            type="button"
            onClick={handleApplyToEditor}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors"
          >
            Áp dụng vào Editor
          </button>
        </div>
      </div>
    );
  }

  // ============================================================
  // PHASE: REFINING
  // ============================================================
  if (!currentGroup) {
    return null;
  }

  // Nếu group hiện tại stale → hiển thị thông báo, chỉ cho bỏ qua
  if (currentGroup.is_stale) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Giảm đạo văn AI
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Vấn đề {currentIndex + 1} / {groups.length}
            </p>
          </div>
          {history.length > 0 && (
            <button
              type="button"
              onClick={handleUndo}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg"
            >
              Hoàn tác
            </button>
          )}
        </div>

        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-amber-500 transition-all duration-300"
            style={{
              width: `${((currentIndex + 0.5) / groups.length) * 100}%`,
            }}
          />
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="text-sm font-bold text-amber-900 mb-1.5">
            ⚠️ Vấn đề này đã thay đổi do chỉnh sửa khác trong cùng đoạn văn
          </div>
          <p className="text-xs text-amber-800 leading-relaxed">
            {currentGroup.stale_reason ||
              "Câu gốc của vấn đề này không còn tồn tại trong đoạn văn hiện tại."}
          </p>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={handleSkip}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-sm rounded-lg shadow-sm transition-colors"
          >
            Bỏ qua và tiếp tục
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Giảm đạo văn AI</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Vấn đề {currentIndex + 1} / {groups.length}
            {totalIssuesRaw > groups.length && (
              <span className="text-slate-400">
                {" "}
                (gộp {totalIssuesRaw} phát hiện)
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {history.length > 0 && (
            <button
              type="button"
              onClick={handleUndo}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg"
            >
              Hoàn tác
            </button>
          )}
          <button
            type="button"
            onClick={handleSkip}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg"
          >
            Bỏ qua
          </button>
        </div>
      </div>

      <div className="mb-4 w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-amber-500 transition-all duration-300"
          style={{
            width: `${((currentIndex + (preview ? 0.5 : 0)) / groups.length) * 100}%`,
          }}
        />
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {currentGroup.issue_types.map((t) => (
            <span
              key={t}
              className="text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-1 rounded-md border border-amber-200"
            >
              {ISSUE_TYPE_LABELS[t] || t}
            </span>
          ))}
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <p className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider mb-2">
            Đoạn văn (câu cần xem xét được bôi vàng):
          </p>
          <p className="text-sm text-slate-800 leading-relaxed">
            {renderParagraphWithHighlight(
              currentGroup.paragraph_text,
              currentGroup.sentence
            )}
          </p>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-[11px] font-bold text-amber-900 uppercase tracking-wider mb-1.5">
            {currentGroup.reasons.length > 1 ? "Các lý do:" : "Lý do:"}
          </p>
          <ul className="space-y-1">
            {currentGroup.reasons.map((reason, idx) => (
              <li key={idx} className="text-xs text-amber-900 flex gap-2">
                <span className="text-amber-500 flex-shrink-0">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-sky-50 border border-sky-200 rounded-lg p-3">
          <p className="text-xs text-sky-900 font-medium">
            <span className="font-bold">AI hỏi: </span>
            {currentGroup.question}
          </p>
          {currentGroup.suggestions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {currentGroup.suggestions.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setUserCommand(s)}
                  className="text-[11px] font-medium text-sky-700 bg-white border border-sky-200 hover:bg-sky-100 px-2 py-1 rounded-md"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {preview && previewParagraph && (
        <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
          <p className="text-[11px] font-mono font-bold text-emerald-800 uppercase tracking-wider mb-2">
            Đoạn văn sau khi sửa:
          </p>
          <p className="text-sm text-emerald-950 leading-relaxed whitespace-pre-wrap">
            {renderParagraphWithHighlight(previewParagraph, preview)}
          </p>
        </div>
      )}

      {error && (
        <div className="mt-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      <div className="mt-4">
        <label
          htmlFor="user-command"
          className="block text-xs font-bold text-slate-600 mb-1.5"
        >
          Bạn muốn sửa thế nào? (câu lệnh của bạn)
        </label>
        <textarea
          id="user-command"
          value={userCommand}
          onChange={(e) => setUserCommand(e.target.value)}
          placeholder='Ví dụ: "sửa cho tự nhiên hơn", "ngắn hơn", "bỏ từ tận dụng đi", "viết lại thành văn nói"'
          rows={3}
          className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 resize-y"
        />

        <div className="flex justify-end gap-2 mt-2">
          {!preview ? (
            <button
              type="button"
              onClick={handleRefine}
              disabled={refining || !userCommand.trim()}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-sm rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {refining ? "Đang sửa..." : "Sửa câu này"}
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => {
                  setPreview(null);
                  setPreviewParagraph(null);
                }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-sm rounded-lg"
              >
                Sửa lại
              </button>
              <button
                type="button"
                onClick={handleAccept}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-lg shadow-sm"
              >
                ✓ Chấp nhận
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};