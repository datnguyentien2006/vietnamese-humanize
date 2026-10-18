"use client";

import React, { useEffect, useRef, useState } from "react";
import { suggestFix } from "../lib/api";
import { Edit, IssueItem, IssueOccurrence, PatternItem } from "../lib/types";
import { makeIssueKey } from "../lib/edit";
import { useCapabilities } from "./CapabilityNav";

interface IssueCardProps {
  issue: IssueItem;
  pattern?: PatternItem;
  onSelectPattern: (patternId: string) => void;
  edit?: Edit;
  /**
   * Đoạn văn hiện tại của paragraph chứa issue này. Có thể đã bao gồm các
   * thay đổi từ issue khác trong cùng đoạn (nếu user đã accept issue kia).
   * Fallback về issue.paragraph nếu chưa có thay đổi nào.
   */
  effectiveParagraph: string;
  /** Có cho phép hoàn tác edit này không (dựa trên logic latest-in-paragraph). */
  canUndo: boolean;
  onAcceptEdit: (edit: Edit) => void;
  onSkipEdit: (issueKey: string) => void;
  onUndoEdit: (issueKey: string) => void;
}

/**
 * Render paragraph với mọi lần xuất hiện của `matchedText` được tô vàng.
 * Nếu `matchedText` không còn trong paragraph (do đã sửa), trả về paragraph
 * nguyên bản không highlight.
 */
function renderHighlightedParagraph(
  paragraph: string,
  matchedText: string
): React.ReactNode {
  if (!matchedText) return paragraph;
  if (!paragraph.includes(matchedText)) return paragraph;

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  let idx = paragraph.indexOf(matchedText, cursor);
  let key = 0;

  while (idx >= 0) {
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
        {matchedText}
      </mark>
    );
    cursor = idx + matchedText.length;
    idx = paragraph.indexOf(matchedText, cursor);
  }
  if (cursor < paragraph.length) {
    parts.push(<span key={`t-${key++}`}>{paragraph.slice(cursor)}</span>);
  }
  return parts;
}

export const IssueCard: React.FC<IssueCardProps> = ({
  issue,
  pattern,
  onSelectPattern,
  edit,
  effectiveParagraph,
  canUndo,
  onAcceptEdit,
  onSkipEdit,
  onUndoEdit,
}) => {
  const [showOccurrences, setShowOccurrences] = useState(false);
  const [draft, setDraft] = useState<string>(effectiveParagraph);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const prevEffectiveParagraphRef = useRef<string>(effectiveParagraph);

  const capabilities = useCapabilities();
  const canSuggestWithAI = capabilities.rewrite === true;
  const [suggesting, setSuggesting] = useState<boolean>(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const occurrences: IssueOccurrence[] = issue.occurrences?.length
    ? issue.occurrences
    : [
        {
          line: issue.line,
          column: issue.column,
          excerpt: issue.excerpt,
          matched_text: "",
          start: issue.start,
          end: issue.end,
          sentence: issue.sentence,
          sentence_start: issue.sentence_start,
          sentence_end: issue.sentence_end,
          paragraph: issue.paragraph,
          paragraph_start: issue.paragraph_start,
          paragraph_end: issue.paragraph_end,
        },
      ];

  const issueKey = makeIssueKey(issue);
  const isAccepted = edit?.status === "accepted";
  const isSkipped = edit?.status === "skipped";

  /**
   * Khi paragraph hiệu lực thay đổi (do user accept edit khác trong cùng
   * đoạn), cập nhật draft nếu user chưa tự sửa gì. Nếu user đã gõ thay đổi,
   * giữ nguyên draft để không mất công sức của user.
   */
  useEffect(() => {
    const previous = prevEffectiveParagraphRef.current;
    prevEffectiveParagraphRef.current = effectiveParagraph;
    if (previous === effectiveParagraph) return;

    setDraft((current) => {
      if (current === previous) return effectiveParagraph;
      return current;
    });
  }, [effectiveParagraph]);

  // Khi mở edit, focus và chọn đúng đoạn lỗi trong textarea (nếu tìm thấy).
  useEffect(() => {
    if (isAccepted || isSkipped) return;
    const ta = textareaRef.current;
    if (!ta) return;
    if (draft !== effectiveParagraph) return;

    const matched = occurrences[0]?.matched_text || issue.excerpt;
    if (!matched) return;
    const idx = draft.indexOf(matched);
    if (idx < 0) return;
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(idx, idx + matched.length);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "high":
      case "error":
        return "bg-rose-50 text-rose-700 border-rose-200/80";
      case "medium":
      case "warning":
        return "bg-amber-50 text-amber-800 border-amber-200/80";
      default:
        return "bg-sky-50 text-sky-800 border-sky-200/80";
    }
  };

  const getFindingTypeLabel = (type: string) => {
    switch (type) {
      case "error":
        return "Lỗi ngữ pháp & chính tả";
      case "warning":
        return "Cảnh báo văn phong";
      case "preference":
        return "Khuyến nghị từ ngữ";
      case "heuristic":
        return "Lối viết khuôn mẫu";
      default:
        return type;
    }
  };

  const handleAccept = () => {
    if (!draft.trim()) return;
    onAcceptEdit({
      issueKey,
      issue,
      originalParagraph: effectiveParagraph,
      newParagraph: draft,
      paragraphStart: issue.paragraph_start,
      paragraphEnd: issue.paragraph_end,
      status: "accepted",
      acceptedAt: Date.now(),
    });
  };

  const handleSkip = () => onSkipEdit(issueKey);

  const handleUndo = () => {
    if (!canUndo) return;
    onUndoEdit(issueKey);
    setSuggestError(null);
  };

  const handleSuggest = async () => {
    if (!canSuggestWithAI) return;
    setSuggesting(true);
    setSuggestError(null);
    try {
      const res = await suggestFix(effectiveParagraph, [issue.pattern_id]);
      setDraft(res.suggestion);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Không gọi được dịch vụ AI.";
      setSuggestError(message);
    } finally {
      setSuggesting(false);
    }
  };

  const matched = occurrences[0]?.matched_text || "";
  const rows = Math.min(
    16,
    Math.max(4, Math.ceil(effectiveParagraph.length / 70) + 1)
  );

  const undoTitle = canUndo
    ? "Hoàn tác thay đổi"
    : "Không thể hoàn tác vì đã có vấn đề khác được sửa sau đó trong cùng đoạn văn. Hãy hoàn tác vấn đề mới hơn trước.";

  return (
    <div
      className={`border rounded-xl p-4 bg-white shadow-sm transition-all group ${
        isAccepted
          ? "border-emerald-300 ring-1 ring-emerald-200"
          : isSkipped
            ? "border-slate-200 opacity-70"
            : "border-slate-200/80 hover:border-sky-300 hover:shadow"
      }`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center space-x-2 flex-wrap">
          <button
            type="button"
            onClick={() => onSelectPattern(issue.pattern_id)}
            className="font-mono text-[11px] font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 px-2.5 py-1 rounded-md border border-sky-200/80 transition-colors"
          >
            {issue.pattern_id}
          </button>
          <span className="text-xs text-slate-400 font-mono">
            Dòng {issue.line}:{issue.column}
          </span>
          {occurrences.length > 1 && (
            <button
              type="button"
              aria-expanded={showOccurrences}
              onClick={() => setShowOccurrences((v) => !v)}
              className="text-[11px] font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 px-2 py-0.5 rounded-md border border-sky-200/80 transition-colors"
            >
              {occurrences.length} vị trí
            </button>
          )}
          <span className="text-xs text-slate-500 font-medium">
            • {getFindingTypeLabel(issue.finding_type)}
          </span>
        </div>
        <span
          className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono font-bold border uppercase tracking-wider ${getSeverityBadge(
            issue.severity
          )}`}
        >
          {issue.severity}
        </span>
      </div>

      {/* Issue message + suggestion */}
      <p className="text-xs sm:text-sm text-slate-700 font-medium mb-2 leading-relaxed">
        {issue.message}
      </p>

      {issue.suggestion && (
        <div className="mt-2 mb-3 text-xs text-emerald-900 bg-emerald-50/80 p-2.5 rounded-lg border border-emerald-200/70 flex items-start space-x-2">
          <svg
            className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
            />
          </svg>
          <div className="flex-1">
            <span className="font-bold text-emerald-950">Gợi ý sửa: </span>
            <span className="leading-relaxed">{issue.suggestion}</span>
          </div>
        </div>
      )}

      {showOccurrences && occurrences.length > 1 && (
        <ol className="mb-3 space-y-2" aria-label="Các vị trí phát hiện">
          {occurrences.map((occ, index) => (
            <li
              key={`${occ.line}-${occ.column}-${index}`}
              className="rounded-lg border border-slate-200/80 bg-slate-50/60 p-2.5"
            >
              <div className="mb-1 text-[11px] font-mono font-semibold text-slate-500">
                Dòng {occ.line}:{occ.column}
              </div>
              <div className="text-xs sm:text-sm font-mono text-slate-700 leading-relaxed">
                &quot;{occ.excerpt}&quot;
              </div>
            </li>
          ))}
        </ol>
      )}

      {/* === EDIT SECTION === */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        {isAccepted ? (
          <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <svg
                  className="w-4 h-4 text-emerald-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Đã sửa đoạn văn
              </span>
              <button
                type="button"
                onClick={handleUndo}
                disabled={!canUndo}
                title={undoTitle}
                className="text-[11px] text-slate-500 hover:text-rose-600 font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-500"
              >
                Hoàn tác
              </button>
            </div>
            <p className="text-[11px] text-slate-500 font-mono uppercase tracking-wider mb-1">
              Đoạn văn sau khi sửa:
            </p>
            <p className="text-xs sm:text-sm text-emerald-950 leading-relaxed bg-yellow-100/80 border border-yellow-200 rounded-md p-2 whitespace-pre-wrap">
              {edit.newParagraph}
            </p>
          </div>
        ) : isSkipped ? (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex items-center justify-between">
            <span className="text-xs text-slate-500 italic">
              Đã bỏ qua vấn đề này.
            </span>
            <button
              type="button"
              onClick={handleUndo}
              className="text-[11px] text-sky-600 hover:text-sky-700 font-semibold transition-colors"
            >
              Hoàn tác
            </button>
          </div>
        ) : (
          <div>
            <label
              htmlFor={`edit-${issueKey}`}
              className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-mono mb-2"
            >
              <svg
                className="w-3.5 h-3.5 text-sky-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z"
                />
              </svg>
              Sửa đoạn văn (đoạn lỗi được tô vàng bên trên)
            </label>

            {/* Preview paragraph với đoạn lỗi tô vàng */}
            <div className="mb-2 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs sm:text-sm font-mono leading-relaxed whitespace-pre-wrap text-slate-700">
              {renderHighlightedParagraph(effectiveParagraph, matched)}
            </div>

            <textarea
              ref={textareaRef}
              id={`edit-${issueKey}`}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={rows}
              className="w-full p-3 border border-slate-300 rounded-lg text-xs sm:text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 transition-all resize-y"
              spellCheck={false}
            />
            <div className="flex flex-wrap items-center justify-between mt-2 gap-2">
              <span className="text-[10px] text-slate-400 font-mono">
                {draft.length} ký tự
                {draft !== effectiveParagraph && (
                  <span className="text-sky-600 ml-2 font-bold">
                    • đã thay đổi
                  </span>
                )}
              </span>
              <div className="flex items-center gap-2 flex-wrap">
                {canSuggestWithAI && (
                  <button
                    type="button"
                    onClick={handleSuggest}
                    disabled={suggesting}
                    className="px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200/80 rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                  >
                    {suggesting ? (
                      <>
                        <svg
                          className="animate-spin h-3.5 w-3.5"
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
                        <span>Đang gợi ý...</span>
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                          />
                        </svg>
                        <span>Gợi ý sửa bằng AI</span>
                      </>
                    )}
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleSkip}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Bỏ qua
                </button>
                <button
                  type="button"
                  onClick={handleAccept}
                  disabled={!draft.trim() || draft === effectiveParagraph}
                  className="px-3.5 py-1.5 text-xs font-bold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1.5"
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  Chấp nhận
                </button>
              </div>
            </div>
            {canSuggestWithAI && suggestError && (
              <div className="mt-2 text-[11px] text-amber-900 bg-amber-50 border border-amber-200/80 rounded-md px-2.5 py-1.5">
                <div className="font-bold mb-1">Không gọi được dịch vụ AI:</div>
                <pre className="whitespace-pre-wrap break-words font-mono text-[10.5px] leading-relaxed text-amber-900/90 m-0">
                  {suggestError}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {pattern && (
        <div className="mt-3 pt-2.5 border-t border-slate-100 flex justify-between items-center text-xs">
          <span className="text-slate-400 truncate max-w-md italic">
            {pattern.summary}
          </span>
          <button
            type="button"
            onClick={() => onSelectPattern(issue.pattern_id)}
            className="text-sky-600 font-bold hover:text-sky-700 hover:underline flex-shrink-0 ml-2 flex items-center space-x-1"
          >
            <span>Chi tiết quy chuẩn</span>
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};