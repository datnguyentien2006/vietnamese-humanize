"use client";

import React, { useState } from "react";
import { Suggestion } from "../lib/types";

/**
 * Map issue_type từ backend sang nhãn ngắn tiếng Việt.
 * Loại không nằm trong danh sách thì trả về nguyên chuỗi gốc.
 */
export function issueTypeLabel(type: string): string {
  switch (type) {
    case "unverified_data":
      return "Số liệu chưa xác thực";
    case "missing_evidence":
      return "Thiếu dẫn chứng";
    case "long_sentence":
      return "Câu quá dài";
    case "logic_gap":
      return "Hở logic";
    case "repetition":
      return "Lặp ý";
    case "vague_reference":
      return "Tham chiếu mơ hồ";
    case "passive_overuse":
      return "Thụ động quá nhiều";
    case "register_mismatch":
      return "Sai sổ tiếng/register: giọng văn lệch";
    case "academic_tone":
      return "Giọng academic";
    default:
      return type;
  }
}

const BADGE_STYLES: Record<string, string> = {
  unverified_data: "bg-amber-100 text-amber-900 border-amber-200 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-800",
  missing_evidence: "bg-orange-100 text-orange-900 border-orange-200 dark:bg-orange-950/60 dark:text-orange-200 dark:border-orange-800",
  long_sentence: "bg-sky-100 text-sky-900 border-sky-200 dark:bg-sky-950/60 dark:text-sky-200 dark:border-sky-800",
  logic_gap: "bg-violet-100 text-violet-900 border-violet-200 dark:bg-violet-950/60 dark:text-violet-200 dark:border-violet-800",
  repetition: "bg-pink-100 text-pink-900 border-pink-200 dark:bg-pink-950/60 dark:text-pink-200 dark:border-pink-800",
  vague_reference: "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800/60 dark:text-slate-200 dark:border-slate-700",
  passive_overuse: "bg-teal-100 text-teal-900 border-teal-200 dark:bg-teal-950/60 dark:text-teal-200 dark:border-teal-800",
  register_mismatch: "bg-rose-100 text-rose-900 border-rose-200 dark:bg-rose-950/60 dark:text-rose-200 dark:border-rose-800",
  academic_tone: "bg-indigo-100 text-indigo-900 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-200 dark:border-indigo-800",
};

const DEFAULT_BADGE_STYLE = "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800/60 dark:text-slate-200 dark:border-slate-700";

/** Chấm màu nhỏ trước badge, phân biệt nhanh nhóm vấn đề. */
const STATUS_DOTS: Record<string, string> = {
  unverified_data: "bg-amber-500 dark:bg-amber-400",
  missing_evidence: "bg-orange-500 dark:bg-orange-400",
  long_sentence: "bg-sky-500 dark:bg-sky-400",
  logic_gap: "bg-violet-500 dark:bg-violet-400",
  repetition: "bg-pink-500 dark:bg-pink-400",
  vague_reference: "bg-slate-500 dark:bg-slate-400",
  passive_overuse: "bg-teal-500 dark:bg-teal-400",
  register_mismatch: "bg-rose-500 dark:bg-rose-400",
  academic_tone: "bg-indigo-500 dark:bg-indigo-400",
};

const DEFAULT_STATUS_DOT = "bg-slate-400";

interface SuggestionItemProps {
  suggestion: Suggestion;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({ suggestion }) => {
  const [open, setOpen] = useState<boolean>(true);
  const badgeStyle = BADGE_STYLES[suggestion.issue_type] || DEFAULT_BADGE_STYLE;
  const dotStyle = STATUS_DOTS[suggestion.issue_type] || DEFAULT_STATUS_DOT;

  return (
    <li className="bg-card rounded-xl border border-line p-3.5 shadow-sm hover:shadow-card transition-all">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeStyle}`}
        >
          <span
            aria-hidden="true"
            className={`h-1.5 w-1.5 rounded-full ${dotStyle}`}
          />
          {issueTypeLabel(suggestion.issue_type)}
        </span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="inline-flex items-center gap-1 text-[11px] text-muted hover:text-ink font-semibold transition-colors"
        >
          <svg
            className="w-3 h-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            )}
          </svg>
          {open ? "Ẩn" : "Hiện"}
        </button>
      </div>

      {suggestion.excerpt && (
        <p className="mt-2 text-xs sm:text-sm text-ink leading-relaxed">
          <mark className="bg-yellow-200 dark:bg-yellow-600/50 text-yellow-950 dark:text-yellow-50 rounded-sm px-1">
            {suggestion.excerpt.trim()}
          </mark>
        </p>
      )}

      {open && (
        <div className="mt-2 space-y-1.5 animate-fade-in">
          {suggestion.reason && (
            <p className="text-xs text-muted leading-relaxed">
              {suggestion.reason}
            </p>
          )}
          {suggestion.question && (
            <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
              ❓ {suggestion.question}
            </p>
          )}
          {suggestion.suggestions.length > 0 && (
            <ul className="list-disc pl-4 space-y-1">
              {suggestion.suggestions.map((s, idx) => (
                <li key={idx} className="text-xs text-muted leading-relaxed">
                  {s}
                </li>
              ))}
            </ul>
          )}
          <p className="flex items-center gap-2 text-[10px] text-muted font-mono">
            <span aria-hidden="true" className="inline-flex items-center gap-0.5">
              {Array.from({ length: 5 }, (_, i) => (
                <span
                  key={i}
                  className={
                    i < suggestion.confidence
                      ? "h-1.5 w-1.5 rounded-full bg-green-500 dark:bg-green-400"
                      : "h-1.5 w-1.5 rounded-full bg-line"
                  }
                />
              ))}
            </span>
            Độ tự tin: {suggestion.confidence}/5
          </p>
        </div>
      )}
    </li>
  );
};

interface SuggestionsPanelProps {
  suggestions: Suggestion[];
}

export const SuggestionsPanel: React.FC<SuggestionsPanelProps> = ({
  suggestions,
}) => {
  return (
    <div className="bg-card rounded-2xl shadow-card border border-line p-5 sm:p-6 transition-colors">
      <p className="text-xs text-muted mb-3">
        Những chỗ tác giả nên tự kiểm tra lại trước khi dùng bản đã humanize.
      </p>

      {suggestions.length === 0 ? (
        <p className="text-xs text-muted leading-relaxed bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-800/60 rounded-xl p-3">
          Không có gợi ý nào cần rà soát cho văn bản này.
        </p>
      ) : (
        <ul className="space-y-3">
          {suggestions.map((s, idx) => (
            <SuggestionItem key={idx} suggestion={s} />
          ))}
        </ul>
      )}
    </div>
  );
};
