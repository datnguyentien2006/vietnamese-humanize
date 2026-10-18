"use client";

import React, { useMemo, useState } from "react";
import { Edit } from "../lib/types";
import { applyEdits, computeHighlightRanges } from "../lib/edit";

interface CompareViewProps {
  originalText: string;
  edits: Edit[];
}

export const CompareView: React.FC<CompareViewProps> = ({
  originalText,
  edits,
}) => {
  const [copied, setCopied] = useState(false);

  const workingText = useMemo(
    () => applyEdits(originalText, edits),
    [originalText, edits]
  );
  const ranges = useMemo(() => computeHighlightRanges(edits), [edits]);

  const highlighted = useMemo(() => {
    if (ranges.length === 0) return <>{workingText}</>;
    const sorted = [...ranges].sort((a, b) => a.start - b.start);
    const nodes: React.ReactNode[] = [];
    let cursor = 0;
    sorted.forEach((r, idx) => {
      if (r.start > cursor) {
        nodes.push(
          <span key={`t-${idx}`}>{workingText.slice(cursor, r.start)}</span>
        );
      }
      nodes.push(
        <mark
          key={`m-${idx}`}
          className="bg-yellow-200 text-yellow-950 rounded-sm px-0.5"
        >
          {workingText.slice(r.start, r.end)}
        </mark>
      );
      cursor = r.end;
    });
    if (cursor < workingText.length) {
      nodes.push(<span key="tail">{workingText.slice(cursor)}</span>);
    }
    return <>{nodes}</>;
  }, [workingText, ranges]);

  const handleCopy = () => {
    navigator.clipboard.writeText(workingText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const charDelta = workingText.length - originalText.length;
  const charDeltaLabel =
    charDelta === 0 ? "0" : charDelta > 0 ? `+${charDelta}` : `${charDelta}`;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-4 border-b border-slate-100">
        <div>
          <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <svg
              className="w-5 h-5 text-emerald-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z"
              />
            </svg>
            <span>So sánh trước và sau khi sửa</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1 font-mono">
            {ranges.length} đoạn đã sửa • Độ dài: {charDeltaLabel} ký tự
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm shadow-emerald-600/20 transition-all flex items-center gap-1.5"
        >
          {copied ? (
            <>
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={3}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Đã sao chép
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
                  d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 011.927-.184"
                />
              </svg>
              Sao chép văn bản đã sửa
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/80">
          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 font-mono">
            Văn bản gốc
          </span>
          <p className="whitespace-pre-wrap text-xs sm:text-sm text-slate-800 leading-relaxed">
            {originalText}
          </p>
        </div>
        <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200/80">
          <span className="block text-xs font-bold text-emerald-800 uppercase tracking-wider mb-2 font-mono">
            Văn bản đã sửa
          </span>
          <p className="whitespace-pre-wrap text-xs sm:text-sm text-emerald-950 leading-relaxed">
            {highlighted}
          </p>
        </div>
      </div>
    </div>
  );
};