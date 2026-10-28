import React, { useState } from "react";
import { submitContribution } from "../lib/api";
import { ContributionResponse, SkillItem } from "../lib/types";

interface ContributeFormProps {
  skills: SkillItem[];
}

export const ContributeForm: React.FC<ContributeFormProps> = ({ skills }) => {
  const [inputText, setInputText] = useState("");
  const [context, setContext] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [skill, setSkill] = useState("humanizer-vi");
  const [note, setNote] = useState("");
  const [consent, setConsent] = useState(false);

  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ContributionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;
    setLoading(true);
    setErrorMsg(null);
    setResponse(null);

    try {
      const res = await submitContribution({
        input_text: inputText,
        context: context || undefined,
        suggestion,
        skill,
        note: note || undefined,
        consent,
      });
      setResponse(res);
      // Reset form fields
      setInputText("");
      setContext("");
      setSuggestion("");
      setNote("");
      setConsent(false);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Đã xảy ra lỗi khi gửi đề xuất đóng góp.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-2xl shadow-card border border-line p-6 max-w-3xl mx-auto my-6 transition-colors">
      <h2 className="text-xl font-bold text-ink mb-1 flex items-center gap-2">
        <span aria-hidden="true" className="h-1 w-6 rounded-full bg-gradient-to-r from-sky-500 to-emerald-500" />
        Đóng góp ví dụ / Case văn phong
      </h2>
      <p className="text-xs text-muted mb-6">
        Các đóng góp của bạn sẽ được lưu vào cơ sở dữ liệu kiểm duyệt (staging) để maintainer rà soát trước khi đưa vào bộ corpus dữ liệu chuẩn.
      </p>

      {response && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100 rounded-xl text-xs mb-6">
          <p className="font-bold text-sm">✅ {response.message}</p>
          <p className="mt-1">Mã đề xuất đóng góp của bạn: <code className="bg-emerald-100 dark:bg-emerald-900/60 px-1 py-0.5 rounded font-mono">{response.id}</code> (Trạng thái: {response.status})</p>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-100 rounded-xl text-xs mb-6">
          <p className="font-bold">❌ Gửi thất bại:</p>
          <p className="mt-0.5">{errorMsg}</p>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="skill-select" className="block text-xs font-semibold text-ink mb-1">
            Chọn kỹ năng liên quan <span className="text-rose-500">*</span>
          </label>
          <select
            id="skill-select"
            value={skill}
            onChange={(e) => setSkill(e.target.value)}
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 dark:focus:border-sky-400 focus:outline-none transition-all"
          >
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="input-text" className="block text-xs font-semibold text-ink mb-1">
            Văn bản gốc (Input Text) <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="input-text"
            rows={4}
            required
            maxLength={20000}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Nhập đoạn văn bản chứa câu/từ chưa tự nhiên..."
            className="w-full p-3 bg-soft border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 dark:focus:border-sky-400 focus:outline-none transition-all shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="context-text" className="block text-xs font-semibold text-ink mb-1">
            Ngữ cảnh văn bản (Context - Không bắt buộc)
          </label>
          <input
            id="context-text"
            type="text"
            maxLength={5000}
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Ví dụ: Báo chí chính luận, thông cáo báo chí, email công việc..."
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 dark:focus:border-sky-400 focus:outline-none transition-all"
          />
        </div>

        <div>
          <label htmlFor="suggestion-text" className="block text-xs font-semibold text-ink mb-1">
            Bản gọt giũa đề xuất (Suggestion) <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="suggestion-text"
            rows={4}
            required
            maxLength={20000}
            value={suggestion}
            onChange={(e) => setSuggestion(e.target.value)}
            placeholder="Nhập cách diễn đạt sửa đổi tự nhiên, chuẩn mực hơn..."
            className="w-full p-3 bg-soft border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 dark:focus:border-sky-400 focus:outline-none transition-all shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="note-text" className="block text-xs font-semibold text-ink mb-1">
            Ghi chú thêm (Note - Không bắt buộc)
          </label>
          <input
            id="note-text"
            type="text"
            maxLength={5000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Lý do nên sửa, quy chuẩn tham chiếu..."
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 dark:focus:border-sky-400 focus:outline-none transition-all"
          />
        </div>

        <div className="pt-2 border-t border-line">
          <label className="flex items-start cursor-pointer text-xs text-ink font-medium">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 mr-2.5 rounded text-brand-600 focus:ring-brand-500"
            />
            <span>
              Tôi xác nhận văn bản này không chứa thông tin cá nhân nhạy cảm (PII) và tôi có quyền chia sẻ ví dụ này để phục vụ nghiên cứu cộng đồng. <span className="text-rose-500">*</span>
            </span>
          </label>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="submit"
          disabled={loading || !consent || !inputText.trim() || !suggestion.trim()}
          className="px-6 py-2.5 bg-gradient-to-r from-sky-600 to-sky-500 hover:from-sky-500 hover:to-emerald-500 text-white font-medium text-xs rounded-xl shadow-glow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none active:scale-[0.98] transition-all"
        >
          {loading ? "Đang gửi..." : "Gửi đóng góp case"}
        </button>
      </div>
    </form>
  );
};
