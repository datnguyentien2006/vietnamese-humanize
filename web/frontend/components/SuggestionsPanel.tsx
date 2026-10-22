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
  unverified_data: "bg-amber-100 text-amber-900 border-amber-200",
  missing_evidence: "bg-orange-100 text-orange-900 border-orange-200",
  long_sentence: "bg-sky-100 text-sky-900 border-sky-200",
  logic_gap: "bg-violet-100 text-violet-900 border-violet-200",
  repetition: "bg-pink-100 text-pink-900 border-pink-200",
  vague_reference: "bg-slate-100 text-slate-800 border-slate-200",
  passive_overuse: "bg-teal-100 text-teal-900 border-teal-200",
  register_mismatch: "bg-rose-100 text-rose-900 border-rose-200",
  academic_tone: "bg-indigo-100 text-indigo-900 border-indigo-200",
};

const DEFAULT_BADGE_STYLE = "bg-slate-100 text-slate-800 border-slate-200";

interface SuggestionItemProps {
  suggestion: Suggestion;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({ suggestion }) => {
  const [open, setOpen] = useState<boolean>(true);
  const badgeStyle = BADGE_STYLES[suggestion.issue_type] || DEFAULT_BADGE_STYLE;

  return (
    <li className="bg-white rounded-xl border border-slate-200/80 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeStyle}`}
        >
          {issueTypeLabel(suggestion.issue_type)}
        </span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="text-[11px] text-slate-400 hover:text-slate-600 font-semibold transition-colors"
        >
          {open ? "Ẩn" : "Hiện"}
        </button>
      </div>

      {suggestion.excerpt && (
        <p className="mt-2 text-xs sm:text-sm text-slate-800 leading-relaxed">
          <mark className="bg-yellow-200 text-yellow-950 rounded-sm px-1">
            {suggestion.excerpt.trim()}
          </mark>
        </p>
      )}

      {open && (
        <div className="mt-2 space-y-1.5">
          {suggestion.reason && (
            <p className="text-xs text-slate-600 leading-relaxed">
              {suggestion.reason}
            </p>
          )}
          {suggestion.question && (
            <p className="text-xs text-amber-800 leading-relaxed">
              ❓ {suggestion.question}
            </p>
          )}
          {suggestion.suggestions.length > 0 && (
            <ul className="list-disc pl-4 space-y-1">
              {suggestion.suggestions.map((s, idx) => (
                <li key={idx} className="text-xs text-slate-600 leading-relaxed">
                  {s}
                </li>
              ))}
            </ul>
          )}
          <p className="text-[10px] text-slate-400 font-mono">
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
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6">
      <p className="text-xs text-slate-500 mb-3">
        Những chỗ tác giả nên tự kiểm tra lại trước khi dùng bản đã humanize.
      </p>

      {suggestions.length === 0 ? (
        <p className="text-xs text-slate-500 leading-relaxed bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-3">
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
