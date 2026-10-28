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
        setErrorMsg("ÄÃ£ xáº£y ra lá»—i khi gá»­i Ä‘á» xuáº¥t Ä‘Ã³ng gÃ³p.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-2xl shadow-card border border-line p-6 max-w-3xl mx-auto my-6 transition-colors">
      <h2 className="text-xl font-bold text-ink mb-1 flex items-center gap-2">
        <span aria-hidden="true" className="h-1 w-6 rounded-full bg-gradient-to-r from-green-500 to-emerald-500" />
        ÄÃ³ng gÃ³p vÃ­ dá»¥ / Case vÄƒn phong
      </h2>
      <p className="text-xs text-muted mb-6">
        CÃ¡c Ä‘Ã³ng gÃ³p cá»§a báº¡n sáº½ Ä‘Æ°á»£c lÆ°u vÃ o cÆ¡ sá»Ÿ dá»¯ liá»‡u kiá»ƒm duyá»‡t (staging) Ä‘á»ƒ maintainer rÃ  soÃ¡t trÆ°á»›c khi Ä‘Æ°a vÃ o bá»™ corpus dá»¯ liá»‡u chuáº©n.
      </p>

      {response && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100 rounded-xl text-xs mb-6">
          <p className="font-bold text-sm">âœ… {response.message}</p>
          <p className="mt-1">MÃ£ Ä‘á» xuáº¥t Ä‘Ã³ng gÃ³p cá»§a báº¡n: <code className="bg-emerald-100 dark:bg-emerald-900/60 px-1 py-0.5 rounded font-mono">{response.id}</code> (Tráº¡ng thÃ¡i: {response.status})</p>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-100 rounded-xl text-xs mb-6">
          <p className="font-bold">âŒ Gá»­i tháº¥t báº¡i:</p>
          <p className="mt-0.5">{errorMsg}</p>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="skill-select" className="block text-xs font-semibold text-ink mb-1">
            Chá»n ká»¹ nÄƒng liÃªn quan <span className="text-rose-500">*</span>
          </label>
          <select
            id="skill-select"
            value={skill}
            onChange={(e) => setSkill(e.target.value)}
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink focus:ring-2 focus:ring-green-500/30 focus:border-green-500 dark:focus:border-green-400 focus:outline-none transition-all"
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
            VÄƒn báº£n gá»‘c (Input Text) <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="input-text"
            rows={4}
            required
            maxLength={20000}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Nháº­p Ä‘oáº¡n vÄƒn báº£n chá»©a cÃ¢u/tá»« chÆ°a tá»± nhiÃªn..."
            className="w-full p-3 bg-soft border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-green-500/30 focus:border-green-500 dark:focus:border-green-400 focus:outline-none transition-all shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="context-text" className="block text-xs font-semibold text-ink mb-1">
            Ngá»¯ cáº£nh vÄƒn báº£n (Context - KhÃ´ng báº¯t buá»™c)
          </label>
          <input
            id="context-text"
            type="text"
            maxLength={5000}
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="VÃ­ dá»¥: BÃ¡o chÃ­ chÃ­nh luáº­n, thÃ´ng cÃ¡o bÃ¡o chÃ­, email cÃ´ng viá»‡c..."
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-green-500/30 focus:border-green-500 dark:focus:border-green-400 focus:outline-none transition-all"
          />
        </div>

        <div>
          <label htmlFor="suggestion-text" className="block text-xs font-semibold text-ink mb-1">
            Báº£n gá»t giÅ©a Ä‘á» xuáº¥t (Suggestion) <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="suggestion-text"
            rows={4}
            required
            maxLength={20000}
            value={suggestion}
            onChange={(e) => setSuggestion(e.target.value)}
            placeholder="Nháº­p cÃ¡ch diá»…n Ä‘áº¡t sá»­a Ä‘á»•i tá»± nhiÃªn, chuáº©n má»±c hÆ¡n..."
            className="w-full p-3 bg-soft border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-green-500/30 focus:border-green-500 dark:focus:border-green-400 focus:outline-none transition-all shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="note-text" className="block text-xs font-semibold text-ink mb-1">
            Ghi chÃº thÃªm (Note - KhÃ´ng báº¯t buá»™c)
          </label>
          <input
            id="note-text"
            type="text"
            maxLength={5000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="LÃ½ do nÃªn sá»­a, quy chuáº©n tham chiáº¿u..."
            className="w-full p-2.5 bg-card border border-line rounded-lg text-xs text-ink placeholder:text-muted/70 focus:ring-2 focus:ring-green-500/30 focus:border-green-500 dark:focus:border-green-400 focus:outline-none transition-all"
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
              TÃ´i xÃ¡c nháº­n vÄƒn báº£n nÃ y khÃ´ng chá»©a thÃ´ng tin cÃ¡ nhÃ¢n nháº¡y cáº£m (PII) vÃ  tÃ´i cÃ³ quyá»n chia sáº» vÃ­ dá»¥ nÃ y Ä‘á»ƒ phá»¥c vá»¥ nghiÃªn cá»©u cá»™ng Ä‘á»“ng. <span className="text-rose-500">*</span>
            </span>
          </label>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="submit"
          disabled={loading || !consent || !inputText.trim() || !suggestion.trim()}
          className="px-6 py-2.5 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-emerald-500 text-white font-medium text-xs rounded-xl shadow-glow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none active:scale-[0.98] transition-all"
        >
          {loading ? "Äang gá»­i..." : "Gá»­i Ä‘Ã³ng gÃ³p case"}
        </button>
      </div>
    </form>
  );
};
