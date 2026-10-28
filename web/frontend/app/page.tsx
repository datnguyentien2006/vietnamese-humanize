"use client";

import React, { useEffect, useRef, useState } from "react";
import { useCapabilitiesStatus } from "../components/CapabilityNav";
import { CompareView } from "../components/CompareView";
import { Disclaimer } from "../components/Disclaimer";
import { SuggestionsPanel } from "../components/SuggestionsPanel";
import { humanizeText } from "../lib/api";
import { HumanizeResponse } from "../lib/types";

const API_LIMIT = 20000;

/**
 * Văn bản mẫu mang phong cách AI: câu dài, số liệu chưa có nguồn,
 * lặp ý và giọng "báo cáo tổng hợp". Tác giả tự viết để thử công cụ.
 */
const SAMPLE_TEXT = `Trong bối cảnh chuyển đổi số không ngừng phát triển, việc triển khai các giải pháp công nghệ hiện đại được xác định là một trong những yếu tố cốt lõi nhằm nâng cao năng lực cạnh tranh của doanh nghiệp trong krajina thị trường đầy biến động hiện nay. Theo số liệu tổng hợp, doanh thu của nhóm ngành tăng 1.850 tỷ đồng trong năm qua, cho thấy xu hướng tăng trưởng tích cực. Nền tảng này không chỉ giúp tối ưu quy trình vận hành mà còn mở ra nhiều cơ hội hợp tác chiến lược, đồng thời đặt ra những yêu cầu mới về quản trị rủi ro mà doanh nghiệp cần nghiên cứu, đánh giá và áp dụng một cách toàn diện.`;

type Phase = "idle" | "humanizing" | "review";

const DISABLED_BANNER =
  "Chưa bật tính năng Humanize trên server. Đặt HUMANIZER_API_BASE hoặc GROQ_API_KEY rồi thử lại.";

function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export default function HomePage() {
  const { capabilities, loaded } = useCapabilitiesStatus();
  const [text, setText] = useState<string>("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [result, setResult] = useState<HumanizeResponse | null>(null);
  const [originalText, setOriginalText] = useState<string>("");
  const [currentText, setCurrentText] = useState<string>("");
  const [lastResultBeforeEdit, setLastResultBeforeEdit] = useState<
    string | null
  >(null);

  const [editing, setEditing] = useState<boolean>(false);
  const [draftText, setDraftText] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const copyTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current !== null) {
        window.clearTimeout(copyTimerRef.current);
      }
    };
  }, []);

  const humanizing = phase === "humanizing";
  const humanizeEnabled = capabilities.humanize === true;
  const canSubmit =
    !humanizing &&
    text.trim().length > 0 &&
    (!loaded || humanizeEnabled);

  const handleHumanize = async () => {
    const submitted = text.trim();
    if (!submitted) return;

    setPhase("humanizing");
    setErrorMsg(null);

    try {
      const res = await humanizeText(submitted);
      setResult(res);
      setOriginalText(submitted);
      setCurrentText(res.rewrite);
      setLastResultBeforeEdit(res.rewrite);
      setDraftText(res.rewrite);
      setEditing(false);
      setCopied(false);
      setPhase("review");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Đã xảy ra lỗi không xác định khi humanize.");
      }
      setPhase("idle");
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(currentText).then(
      () => {
        setCopied(true);
        if (copyTimerRef.current !== null) {
          window.clearTimeout(copyTimerRef.current);
        }
        copyTimerRef.current = window.setTimeout(() => setCopied(false), 2000);
      },
      () => {
        // Clipboard có thể bị chặn — không hiển thị "Đã sao chép ✓".
      }
    );
  };

  const handleStartEdit = () => {
    setDraftText(currentText);
    setEditing(true);
  };

  const handleSaveEdit = () => {
    setLastResultBeforeEdit(currentText);
    setCurrentText(draftText);
    setEditing(false);
  };

  const handleUndo = () => {
    if (lastResultBeforeEdit === null) return;
    setCurrentText(lastResultBeforeEdit);
    setEditing(false);
    setLastResultBeforeEdit(null);
  };

  const resetToIdle = () => {
    setPhase("idle");
    setResult(null);
    setErrorMsg(null);
    setEditing(false);
    setCopied(false);
    setLastResultBeforeEdit(null);
  };

  const providerLabel =
    result === null
      ? ""
      : result.provider === "humanizer-model"
        ? "Mô hình chuyên biệt"
        : "Groq (tạm thời)";

  return (
    <div className="space-y-6">
      {/* ===== Hero ===== */}
      <div className="animate-fade-up">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">
            Humanize Text v1.3
          </h1>
          <span
            aria-hidden="true"
            className="hidden sm:inline-block accent-bar"
          />
        </div>
        <p className="text-sm text-muted mt-1.5 max-w-2xl leading-relaxed">
          Chuyển văn bản phong cách AI thành văn viết tự nhiên, giữ nguyên 100%
          số liệu và ý.
        </p>
      </div>

      <Disclaimer />

      {loaded && !(capabilities.humanize === true) && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800/60 text-amber-950 dark:text-amber-100 p-4 rounded-xl text-xs sm:text-sm shadow-card flex items-start space-x-3 animate-fade-up">
          <div className="flex-shrink-0 w-6 h-6 text-amber-600 dark:text-amber-400 mt-0.5">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
          </div>
          <p className="leading-relaxed">{DISABLED_BANNER}</p>
        </div>
      )}

      {/* Ô nhập văn bản — luôn hiển thị để humanize lại với văn bản mới */}
      <div className="bg-card rounded-2xl shadow-card border border-line p-5 sm:p-6 transition-colors">
        <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
          <label
            htmlFor="humanize-input"
            className="block text-sm font-bold text-ink tracking-tight flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-sky-600 dark:text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
            <span>Văn bản AI cần humanize</span>
          </label>

          <div className="flex items-center space-x-3 text-xs">
            {text.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setText("");
                  resetToIdle();
                }}
                className="text-muted hover:text-rose-600 dark:hover:text-rose-400 font-medium transition-colors"
              >
                Xóa văn bản
              </button>
            )}
            <button
              type="button"
              onClick={() => setText(SAMPLE_TEXT)}
              className="inline-flex items-center space-x-1 text-sky-700 dark:text-sky-300 hover:text-sky-800 dark:hover:text-sky-200 font-semibold transition-colors bg-sky-50 dark:bg-sky-950/50 px-2.5 py-1 rounded-md border border-sky-100 dark:border-sky-900 hover:border-sky-300 dark:hover:border-sky-700"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <span>Thử văn bản mẫu</span>
            </button>
          </div>
        </div>

        <div className="relative group">
          <textarea
            id="humanize-input"
            rows={8}
            maxLength={API_LIMIT}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Dán văn bản AI cần làm mượt tại đây"
            className="w-full p-4 bg-soft border border-line rounded-xl text-sm leading-relaxed text-ink placeholder:text-muted/80 focus:outline-none focus:ring-2 focus:ring-sky-500/30 dark:focus:ring-sky-400/30 focus:border-sky-500 dark:focus:border-sky-400 font-sans transition-all resize-y min-h-[160px] shadow-inner"
          />

          <div className="flex justify-between items-center text-xs text-muted mt-1.5 px-1 font-mono">
            <div className="flex items-center space-x-3">
              <span className="inline-flex items-center gap-1">
                Ký tự:{" "}
                <strong className="text-ink">{text.length.toLocaleString()}</strong>
                <span className="text-muted/70">/ 20.000</span>
              </span>
              <span className="inline-flex items-center gap-1">
                Từ: <strong className="text-ink">{countWords(text).toLocaleString()}</strong>
              </span>
            </div>
            {text.length >= API_LIMIT && (
              <span className="text-rose-600 dark:text-rose-400 font-semibold animate-pulse-soft">
                Đã đạt giới hạn tối đa
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-line mt-4">
          {humanizing && (
            <span className="text-xs text-sky-700 dark:text-sky-300 flex items-center gap-2 mr-auto animate-fade-in">
              <svg className="animate-spin h-4 w-4 text-sky-600 dark:text-sky-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Đang humanize... có thể mất khoảng 20 giây.
            </span>
          )}

          <button
            type="button"
            onClick={handleHumanize}
            disabled={!canSubmit}
            className="px-7 py-3 bg-gradient-to-r from-sky-600 to-sky-500 hover:from-sky-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-glow disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none dark:disabled:opacity-40 active:scale-[0.98] transition-all flex items-center space-x-2"
          >
            {humanizing ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Đang humanize...</span>
              </>
            ) : (
              <span>✨ Humanize văn bản</span>
            )}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-50 dark:bg-rose-950/40 border border-rose-200/80 dark:border-rose-800/60 text-rose-950 dark:text-rose-100 p-4 rounded-xl text-xs sm:text-sm flex items-start space-x-3 shadow-card animate-fade-up">
          <div className="flex-shrink-0 w-6 h-6 text-rose-600 dark:text-rose-400 mt-0.5">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="font-bold text-rose-950 dark:text-rose-100">Lỗi khi humanize:</p>
            <p className="mt-0.5 text-rose-800 dark:text-rose-200 leading-relaxed whitespace-pre-wrap break-words">
              {errorMsg}
            </p>
            <button
              type="button"
              onClick={handleHumanize}
              disabled={!canSubmit}
              className="mt-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl shadow-glow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              Thử lại
            </button>
          </div>
        </div>
      )}

      {phase === "review" && result !== null && originalText && (
        <div className="space-y-6 animate-fade-up">
          {/* Cảnh báo số liệu/giữ nguyên fact */}
          {result.fact_check.lost_tokens.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300/80 dark:border-amber-700/60 text-amber-950 dark:text-amber-100 p-4 rounded-xl text-xs sm:text-sm shadow-card flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 text-amber-600 dark:text-amber-400 mt-0.5">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="font-bold text-amber-950 dark:text-amber-100">
                  Cảnh báo: số liệu/ngày còn thiếu trong bản đã humanize
                </p>
                <p className="mt-1 text-amber-900 dark:text-amber-200 leading-relaxed break-words">
                  {result.fact_check.lost_tokens.join(", ")}
                </p>
              </div>
            </div>
          )}

          {result.warnings.length > 0 && (
            <div className="bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800/50 text-amber-950 dark:text-amber-100 p-4 rounded-xl text-xs sm:text-sm shadow-card">
              <p className="font-bold text-amber-900 dark:text-amber-200 mb-1.5">
                Ghi chú từ server:
              </p>
              <ul className="list-disc pl-4 space-y-1">
                {result.warnings.map((w, idx) => (
                  <li key={idx} className="text-amber-900 dark:text-amber-200 leading-relaxed">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* So sánh trước / sau */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-ink tracking-tight flex items-center gap-2">
              <span aria-hidden="true" className="h-1 w-6 rounded-full bg-gradient-to-r from-sky-500 to-emerald-500" />
              Bản đã humanize
            </h2>

            <div className="bg-card rounded-2xl border border-line shadow-card p-3.5 transition-colors">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-muted">Nguồn kết quả:</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full font-semibold bg-gradient-to-r from-sky-100 to-emerald-100 dark:from-sky-950/60 dark:to-emerald-950/60 text-sky-900 dark:text-sky-200 border border-sky-200 dark:border-sky-800">
                    {providerLabel}
                  </span>
                  {typeof result.stats?.latency_seconds === "number" && (
                    <span className="text-muted font-mono">
                      {result.stats.latency_seconds.toLocaleString("vi-VN")} giây
                    </span>
                  )}
                  {typeof result.stats?.attempts === "number" &&
                    result.stats.attempts > 1 && (
                      <span className="text-muted font-mono">
                        {result.stats.attempts} lần thử
                      </span>
                    )}
                  {typeof result.stats?.total_issues === "number" && (
                    <span className="text-muted font-mono">
                      {result.stats.total_issues} vấn đề phát hiện
                      {typeof result.stats.fixed === "number" && `, đã sửa ${result.stats.fixed}`}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {editing ? (
                    <button
                      type="button"
                      onClick={handleSaveEdit}
                      className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-xs font-bold rounded-xl shadow-glow-sm transition-all active:scale-[0.98]"
                    >
                      Lưu chỉnh sửa
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleStartEdit}
                      className="px-4 py-2 bg-card hover:bg-soft border border-line text-ink text-xs font-bold rounded-xl shadow-sm transition-all active:scale-[0.98]"
                    >
                      Sửa thủ công
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleUndo}
                    disabled={lastResultBeforeEdit === null}
                    title={
                      lastResultBeforeEdit === null
                        ? "Không có gì để hoàn tác"
                        : "Khôi phục giá trị trước đó"
                    }
                    className="px-4 py-2 bg-card hover:bg-soft border border-line text-ink text-xs font-bold rounded-xl shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
                  >
                    Hoàn tác
                  </button>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="px-4 py-2 bg-slate-900 dark:bg-slate-700 hover:bg-slate-800 dark:hover:bg-slate-600 text-white text-xs font-bold rounded-xl shadow-sm transition-all active:scale-[0.98]"
                  >
                    {copied ? "Đã sao chép ✓" : "Sao chép"}
                  </button>
                </div>
              </div>

              {editing && (
                <div className="mt-3.5 bg-soft rounded-xl border border-sky-200/80 dark:border-sky-800/60 p-3.5 animate-fade-in">
                  <label
                    htmlFor="manual-edit-input"
                    className="block text-xs font-bold text-muted uppercase tracking-wider font-mono mb-2"
                  >
                    Sửa trực tiếp bản đã humanize
                  </label>
                  <textarea
                    id="manual-edit-input"
                    rows={10}
                    value={draftText}
                    onChange={(e) => setDraftText(e.target.value)}
                    className="w-full p-4 bg-card border border-line rounded-xl text-sm leading-relaxed text-ink focus:outline-none focus:ring-2 focus:ring-sky-500/30 dark:focus:ring-sky-400/30 focus:border-sky-500 dark:focus:border-sky-400 font-sans transition-all resize-y shadow-inner"
                  />
                </div>
              )}
            </div>

            <CompareView originalText={originalText} currentText={currentText} />
          </section>

          {/* Gợi ý rà soát */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-ink tracking-tight flex items-center gap-2">
              <span aria-hidden="true" className="h-1 w-6 rounded-full bg-gradient-to-r from-sky-500 to-emerald-500" />
              Gợi ý rà soát
            </h2>
            <SuggestionsPanel suggestions={result.suggestions} />
          </section>
        </div>
      )}
    </div>
  );
}
