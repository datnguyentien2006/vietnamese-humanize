"use client";

import React, { useEffect, useMemo, useState } from "react";
import { CompareView } from "../components/CompareView";
import { Disclaimer } from "../components/Disclaimer";
import { Editor } from "../components/Editor";
import { IssueList } from "../components/IssueList";
import { ReportRefiner } from "../components/ReportRefiner";
import { fetchPatterns, fetchSkills, lintText } from "../lib/api";
import { makeIssueKey } from "../lib/edit";
import { Edit, LintResponse, PatternItem, SkillItem } from "../lib/types";

export default function HomePage() {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [patterns, setPatterns] = useState<PatternItem[]>([]);
  const [currentText, setCurrentText] = useState<string>("");
  const [originalTextBeforeLint, setOriginalTextBeforeLint] = useState<string>("");
  const [lintResult, setLintResult] = useState<LintResponse | null>(null);
  const [edits, setEdits] = useState<Map<string, Edit>>(new Map());
  /**
   * Với mỗi paragraph (key = paragraph_start), đây là đoạn văn hiện tại sau
   * khi áp dụng tất cả accepted edits trong paragraph đó. Giúp user khi mở
   * issue khác trong cùng đoạn sẽ thấy đoạn văn đã cập nhật, không bị
   * "vòng lặp sửa lỗi cũ".
   */
  const [paragraphDrafts, setParagraphDrafts] = useState<Map<number, string>>(
    new Map()
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showCompare, setShowCompare] = useState<boolean>(false);
  const [showRefiner, setShowRefiner] = useState<boolean>(false);

  useEffect(() => {
    async function loadMetadata() {
      try {
        const [skillsRes, patternsRes] = await Promise.all([
          fetchSkills(),
          fetchPatterns(),
        ]);
        setSkills(skillsRes.skills);
        setPatterns(patternsRes.patterns);
      } catch (err: unknown) {
        console.error("Failed to load metadata:", err);
      }
    }
    loadMetadata();
  }, []);

  const resetSessionState = () => {
    setEdits(new Map());
    setParagraphDrafts(new Map());
    setShowCompare(false);
    setShowRefiner(false);
  };

  const handleLint = async (text: string, selectedSkills: string[]) => {
    setCurrentText(text);
    setOriginalTextBeforeLint(text);
    resetSessionState();
    setLoading(true);
    setErrorMsg(null);
    setLintResult(null);
    try {
      const res = await lintText(text, selectedSkills);
      setLintResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Đã xảy ra lỗi không xác định khi kiểm tra văn bản.");
      }
      setLintResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptEdit = (edit: Edit) => {
    // Bổ sung acceptedAt nếu chưa có
    const acceptedEdit: Edit = {
      ...edit,
      acceptedAt: edit.acceptedAt ?? Date.now(),
    };

    setEdits((prev) => {
      const next = new Map(prev);
      next.set(acceptedEdit.issueKey, acceptedEdit);
      return next;
    });

    // Cập nhật paragraphDrafts cho paragraph này
    setParagraphDrafts((prev) => {
      const next = new Map(prev);
      next.set(acceptedEdit.paragraphStart, acceptedEdit.newParagraph);
      return next;
    });
  };

  const handleSkipEdit = (issueKey: string) => {
    const issue = lintResult?.issues.find((i) => makeIssueKey(i) === issueKey);
    if (!issue) return;
    setEdits((prev) => {
      const next = new Map(prev);
      next.set(issueKey, {
        issueKey,
        issue,
        originalParagraph: issue.paragraph,
        newParagraph: issue.paragraph,
        paragraphStart: issue.paragraph_start,
        paragraphEnd: issue.paragraph_end,
        status: "skipped",
      });
      return next;
    });
  };

  const handleUndoEdit = (issueKey: string) => {
    const edit = edits.get(issueKey);
    if (!edit) return;

    // Kiểm tra nếu là accepted: chỉ cho undo nếu là edit mới nhất trong paragraph
    if (edit.status === "accepted") {
      const acceptedInParagraph = Array.from(edits.values())
        .filter(
          (e) =>
            e.paragraphStart === edit.paragraphStart &&
            e.status === "accepted"
        )
        .sort((a, b) => (b.acceptedAt ?? 0) - (a.acceptedAt ?? 0));

      if (
        acceptedInParagraph.length > 0 &&
        acceptedInParagraph[0].issueKey !== issueKey
      ) {
        // Không phải edit mới nhất → từ chối undo để tránh rollback phức tạp
        return;
      }
    }

    setEdits((prev) => {
      const next = new Map(prev);
      next.delete(issueKey);
      return next;
    });

    // Nếu là accepted: cập nhật paragraphDrafts cho paragraph tương ứng
    if (edit.status === "accepted") {
      const remaining = Array.from(edits.values())
        .filter(
          (e) =>
            e.paragraphStart === edit.paragraphStart &&
            e.status === "accepted" &&
            e.issueKey !== issueKey
        )
        .sort((a, b) => (b.acceptedAt ?? 0) - (a.acceptedAt ?? 0));

      setParagraphDrafts((prev) => {
        const next = new Map(prev);
        if (remaining.length > 0) {
          next.set(edit.paragraphStart, remaining[0].newParagraph);
        } else {
          next.delete(edit.paragraphStart);
        }
        return next;
      });
    }
  };

  const acceptedEdits = useMemo(
    () => Array.from(edits.values()).filter((e) => e.status === "accepted"),
    [edits]
  );

  const acceptedParagraphCount = useMemo(() => {
    const set = new Set<number>();
    acceptedEdits.forEach((e) => set.add(e.paragraphStart));
    return set.size;
  }, [acceptedEdits]);

  /**
   * Văn bản đã áp dụng tất cả các accepted edits (mỗi paragraph chỉ lấy
   * draft mới nhất từ paragraphDrafts, không cộng dồn giữa các edit).
   */
  const manuallyEditedText = useMemo(() => {
    if (paragraphDrafts.size === 0) return currentText;

    // Cần paragraphEnd cho mỗi paragraph → lấy từ bất kỳ edit nào cùng paragraph.
    const entries: Array<{ start: number; end: number; text: string }> = [];
    for (const [paraStart, draftText] of paragraphDrafts.entries()) {
      const relatedEdit = Array.from(edits.values()).find(
        (e) => e.paragraphStart === paraStart
      );
      if (!relatedEdit) continue;
      entries.push({
        start: paraStart,
        end: relatedEdit.paragraphEnd,
        text: draftText,
      });
    }

    // Apply từ phải sang trái để offset không bị lệch
    entries.sort((a, b) => b.start - a.start);

    let result = currentText;
    for (const entry of entries) {
      if (
        entry.start < 0 ||
        entry.end > result.length ||
        entry.start > entry.end
      ) {
        continue;
      }
      result =
        result.slice(0, entry.start) + entry.text + result.slice(entry.end);
    }
    return result;
  }, [currentText, paragraphDrafts, edits]);

  const unprocessedIssueCount = useMemo(() => {
    if (!lintResult) return 0;
    let count = 0;
    for (const issue of lintResult.issues) {
      const key = makeIssueKey(issue);
      if (!edits.has(key)) count += 1;
    }
    return count;
  }, [lintResult, edits]);

  const totalIssueCount = lintResult?.issues.length ?? 0;
  const processedCount = totalIssueCount - unprocessedIssueCount;
  const canProceedToRefiner =
    totalIssueCount > 0 && unprocessedIssueCount === 0;

  const handleRefinerComplete = async (refinedText: string) => {
    // currentText = văn bản AI scan vừa xong, dùng làm văn bản gốc mới để lint lại
    setCurrentText(refinedText);
    setShowRefiner(false);
    // Re-lint để hiển thị issues mới sau khi AI scan sửa
    setLoading(true);
    setErrorMsg(null);
    setLintResult(null);
    setEdits(new Map());
    setParagraphDrafts(new Map());
    setShowCompare(false);
    try {
      const res = await lintText(refinedText, skills.map((s) => s.id));
      setLintResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Đã xảy ra lỗi không xác định khi kiểm tra văn bản.");
      }
      setLintResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Disclaimer />

      <div className="grid grid-cols-1 gap-6">
        <Editor skills={skills} onLint={handleLint} loading={loading} />

        {errorMsg && (
          <div className="bg-rose-50 border border-rose-200/80 text-rose-950 p-4 rounded-xl text-xs sm:text-sm flex items-start space-x-3 shadow-sm">
            <div className="flex-shrink-0 w-6 h-6 text-rose-600 mt-0.5">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                />
              </svg>
            </div>
            <div>
              <p className="font-bold text-rose-950">Lỗi kiểm tra văn phong:</p>
              <p className="mt-0.5 text-rose-800 leading-relaxed">{errorMsg}</p>
            </div>
          </div>
        )}

        {lintResult && (
          <div className="space-y-6 animate-in fade-in duration-300">
            <IssueList
              summary={lintResult.summary}
              issues={lintResult.issues}
              patterns={patterns}
              edits={edits}
              paragraphDrafts={paragraphDrafts}
              onAcceptEdit={handleAcceptEdit}
              onSkipEdit={handleSkipEdit}
              onUndoEdit={handleUndoEdit}
            />

            {totalIssueCount > 0 && (
              <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-slate-600">
                    <span className="font-bold text-slate-800">
                      Tiến độ soát văn phong:
                    </span>{" "}
                    {processedCount} / {totalIssueCount} vấn đề đã xử lý
                    {unprocessedIssueCount > 0 && (
                      <span className="text-amber-700 ml-1">
                        (còn {unprocessedIssueCount} chưa xử lý)
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setShowCompare((v) => !v)}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
                    >
                      {showCompare ? "Ẩn so sánh" : "Xem so sánh"}
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowRefiner((v) => !v)}
                      disabled={!canProceedToRefiner}
                      title={
                        !canProceedToRefiner
                          ? `Còn ${unprocessedIssueCount} vấn đề chưa xử lý. Hãy xử lý hết trước khi dùng AI scan.`
                          : "Bắt đầu giảm đạo văn AI trên văn bản đã soát"
                      }
                      className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {showRefiner
                        ? "Ẩn phần giảm đạo văn AI"
                        : "🔍 Giảm đạo văn AI (v1.2)"}
                    </button>
                  </div>
                </div>

                {!canProceedToRefiner && unprocessedIssueCount > 0 && (
                  <p className="text-[11px] text-amber-700 mt-2">
                    💡 Hãy xử lý hết {unprocessedIssueCount} vấn đề ở trên
                    (Chấp nhận hoặc Bỏ qua) trước khi chạy AI scan.
                  </p>
                )}
              </div>
            )}

            {showCompare && acceptedParagraphCount > 0 && (
              <CompareView
                originalText={currentText}
                edits={acceptedEdits}
              />
            )}

            {showRefiner && canProceedToRefiner && (
              <ReportRefiner
                key={manuallyEditedText}
                originalText={manuallyEditedText}
                originalTextBeforeAll={originalTextBeforeLint}
                onComplete={handleRefinerComplete}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}