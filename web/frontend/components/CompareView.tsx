"use client";

import React, { useMemo } from "react";

interface CompareViewProps {
  originalText: string;
  currentText: string;
}

/** Tokenize giữ nguyên khoảng trắng để render đúng whitespace. */
function tokenize(text: string): string[] {
  return text.split(/(\s+)/);
}

interface DiffSide {
  tokens: string[];
  /** true = token khác phía bên kia (chỉ tính token không phải khoảng trắng). */
  changed: boolean[];
}

function diffTokens(original: string, current: string): {
  original: DiffSide;
  current: DiffSide;
} {
  const build = (text: string): DiffSide => {
    const tokens = tokenize(text);
    return { tokens, changed: tokens.map(() => false) };
  };
  const a = build(original);
  const b = build(current);

  // Chỉ diff trên token có nội dung (token chỉ toàn khoảng trắng coi như không đổi).
  const aIdx: number[] = [];
  const bIdx: number[] = [];
  const A: string[] = [];
  const B: string[] = [];
  a.tokens.forEach((t, i) => {
    if (t.trim()) {
      aIdx.push(i);
      A.push(t);
    }
  });
  b.tokens.forEach((t, i) => {
    if (t.trim()) {
      bIdx.push(i);
      B.push(t);
    }
  });

  const n = A.length;
  const m = B.length;
  // Va chất văn bản quá dài thì bỏ highlight (tránh tốn bộ nhớ LCS quá lớn)
  if (n > 2000 || m > 2000) {
    return { original: a, current: b };
  }

  const width = m + 1;
  const dp = new Int32Array((n + 1) * width);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * width + j] =
        A[i] === B[j]
          ? dp[(i + 1) * width + j + 1] + 1
          : Math.max(dp[(i + 1) * width + j], dp[i * width + j + 1]);
    }
  }

  const aMatched = new Array<boolean>(n).fill(false);
  const bMatched = new Array<boolean>(m).fill(false);
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) {
      aMatched[i] = true;
      bMatched[j] = true;
      i++;
      j++;
    } else if (dp[(i + 1) * width + j] >= dp[i * width + j + 1]) {
      i++;
    } else {
      j++;
    }
  }

  for (let k = 0; k < n; k++) {
    if (!aMatched[k]) a.changed[aIdx[k]] = true;
  }
  for (let k = 0; k < m; k++) {
    if (!bMatched[k]) b.changed[bIdx[k]] = true;
  }

  return { original: a, current: b };
}

/** Gom token liền kề cùng trạng thái để giảm số node render. */
interface Segment {
  text: string;
  changed: boolean;
}

function groupSegments(side: DiffSide): Segment[] {
  const segments: Segment[] = [];
  side.tokens.forEach((token, idx) => {
    const changed = side.changed[idx] && Boolean(token.trim());
    const last = segments[segments.length - 1];
    if (last && last.changed === changed) {
      last.text += token;
    } else {
      segments.push({ text: token, changed });
    }
  });
  return segments;
}

function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export const CompareView: React.FC<CompareViewProps> = ({
  originalText,
  currentText,
}) => {
  const { original, current } = useMemo(
    () => diffTokens(originalText, currentText),
    [originalText, currentText]
  );

  const originalSegments = useMemo(() => groupSegments(original), [original]);
  const currentSegments = useMemo(() => groupSegments(current), [current]);

  const charDelta = currentText.length - originalText.length;
  const wordDelta = countWords(currentText) - countWords(originalText);
  const formatDelta = (delta: number, unit: string) => {
    const label = delta === 0 ? "0" : delta > 0 ? `+${delta}` : `${delta}`;
    return `${label} ${unit}`;
  };
  const changedCount = currentSegments.filter((s) => s.changed).length;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
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
                d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 011.043 3.296A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z"
              />
            </svg>
            <span>So sánh trước và sau khi humanize</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-mono">
            {changedCount} chỗ đã đổi • Ký tự:{" "}
            {formatDelta(charDelta, "kt")} • Từ:{" "}
            {formatDelta(wordDelta, "từ")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/80">
          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 font-mono">
            Văn bản gốc
          </span>
          <p className="whitespace-pre-wrap text-xs sm:text-sm text-slate-800 leading-relaxed">
            {originalSegments.map((s, idx) =>
              s.changed ? (
                <span
                  key={idx}
                  className="bg-rose-100 text-slate-700 rounded-sm px-0.5"
                >
                  {s.text}
                </span>
              ) : (
                <span key={idx}>{s.text}</span>
              )
            )}
          </p>
        </div>
        <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200/80">
          <span className="block text-xs font-bold text-emerald-800 uppercase tracking-wider mb-2 font-mono">
            Văn bản đã humanize
          </span>
          <p className="whitespace-pre-wrap text-xs sm:text-sm text-emerald-950 leading-relaxed">
            {currentSegments.map((s, idx) =>
              s.changed ? (
                <mark
                  key={idx}
                  className="bg-yellow-200 text-yellow-950 rounded-sm px-0.5"
                >
                  {s.text}
                </mark>
              ) : (
                <span key={idx}>{s.text}</span>
              )
            )}
          </p>
        </div>
      </div>
    </div>
  );
};
