# -*- coding: utf-8 -*-
"""QC judge — Gate 4: LLM-as-a-Judge chấm lại dataset SFT đã sinh.

Đọc train/val JSONL do prepare_dataset.py sinh ra, chạy lại các gate cơ khí
(fact token, length ratio, overlap) và chấm 3 tiêu chí bằng các LLM judge
độc lập:

  * ai_ness     — input giống "văn AI máy móc" đến đâu        (>= --min-score)
  * naturalness — gold tự nhiên như người Việt thật viết đến đâu (>= --min-score)
  * fidelity    — input truyền tải đủ và đúng ý của gold đến đâu (>= --min-score)

Judges (mặc định 2 model Groq; thêm Gemini khi có key trong web/backend/.env):
  groq:openai/gpt-oss-120b, groq:openai/gpt-oss-20b, gemini:gemini-2.5-flash

--verify-only: bỏ LLM, chỉ chạy gate cơ khí + đo metric trên toàn bộ dataset
(nhanh, offline, không tốn call).

Kết quả:
  <sft-dir>/qc_report.json   — tổng hợp pass/fail, lý do, điểm trung bình judges
  <sft-dir>/qc_rejects.jsonl — các dòng bị loại (kèm file + số dòng để lọc sau)

Usage:
  python training/qc_judge.py --verify-only
  python training/qc_judge.py --sample 60
  python training/qc_judge.py --sample 0 --judges groq:openai/gpt-oss-20b
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from pair_synthesis import (  # noqa: E402
    connector_hits,
    fact_tokens,
    length_ratio,
    longest_common_substring_ratio,
    sentence_length_std,
    word_ngram_overlap,
)

ORIGINAL_RE = re.compile(r"<ORIGINAL>\n?(.*?)\n?</ORIGINAL>", re.DOTALL)
FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

DEFAULT_JUDGES = ("groq:qwen/qwen3.8-27b", "groq:openai/gpt-oss-120b")

# Groq nằm sau Cloudflare: UA mặc định của urllib bị chặn (error 1010).
QC_USER_AGENT = "vietnamese-humanizer-qc-judge/0.5 (dataset QC)"

JUDGE_PROMPT = """Bạn là chuyên gia đánh giá văn bản tiếng Việt. Chấm cặp văn bản sau trên thang điểm 1-5.

- ai_ness: văn bản INPUT giống "văn AI máy móc" đến đâu (5 = điển hình: từ nối khuôn mẫu, câu đều nhịp, nhận định rỗng; 1 = hoàn toàn tự nhiên).
- naturalness: văn bản GOLD tự nhiên như một người Việt thật viết đến đâu (5 = hoàn toàn tự nhiên; 3 = gượng ép; 1 = máy móc).
- fidelity: INPUT truyền tải đủ và đúng ý của GOLD đến đâu (5 = trọn vẹn, không thêm bớt ý; 3 = mất hoặc khác ý đáng kể; 1 = khác hoàn toàn).

INPUT:
<INPUT>
{ai_text}
</INPUT>

GOLD (văn người viết):
<GOLD>
{gold_text}
</GOLD>

Chỉ trả về JSON một dòng: {{"ai_ness": n, "naturalness": n, "fidelity": n, "ly_do": "một câu ngắn"}}"""


def load_env() -> dict[str, str]:
    """Đọc KEY=VALUE từ web/backend/.env (không in giá trị ra anywhere)."""
    env: dict[str, str] = {}
    for path in (ROOT / "web" / "backend" / ".env", ROOT / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env.setdefault(key.strip(), value.strip())
    env.setdefault("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    env.setdefault("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    env.setdefault("QC_LOCAL_BASE", os.environ.get("QC_LOCAL_BASE", "http://127.0.0.1:11434/v1"))
    return env


def parse_verdict(text: str) -> dict | None:
    text = (text or "").strip()
    match = FENCE_RE.search(text)
    if match:
        text = match.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
        return {
            "ai_ness": int(data["ai_ness"]),
            "naturalness": int(data["naturalness"]),
            "fidelity": int(data["fidelity"]),
            "ly_do": str(data.get("ly_do", ""))[:300],
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def call_judge(judge: str, prompt: str, env: dict[str, str], timeout: float = 90.0) -> str:
    provider, _, model = judge.partition(":")
    if provider == "local":
        # Teacher/judge chạy trên máy (Ollama/llama.cpp/vLLM) — đúng nguyên tắc
        # pipeline local: không tốn API, không quota. Key là placeholder.
        base = env.get("QC_LOCAL_BASE") or "http://127.0.0.1:11434/v1"
        payload = json.dumps(
            {
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
            method="POST",
        )
    elif provider == "groq":
        key = env.get("GROQ_API_KEY", "")
        if not key:
            raise RuntimeError("thiếu GROQ_API_KEY (web/backend/.env hoặc env)")
        # qwen3.8 bật thinking mặc định: tắt để judge nhanh và không "sửa văn"
        # thay vì chấm. gpt-oss giữ reasoning mặc định.
        extra = {"reasoning_effort": "none"} if model.startswith("qwen/") else {}
        payload = json.dumps(
            {
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
                **extra,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": QC_USER_AGENT,
            },
            method="POST",
        )
    elif provider == "gemini":
        key = env.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("thiếu GEMINI_API_KEY — thêm vào web/backend/.env nếu muốn judge Gemini")
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": QC_USER_AGENT},
            method="POST",
        )
    else:
        raise ValueError(f"judge không hỗ trợ: {judge}")

    # Request bytes dùng lại được qua các lần thử; chỉ retry lỗi tạm thời.
    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(min(2**attempt, 8))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            if provider in ("groq", "local"):
                return (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            parts = (body.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            return " ".join(part.get("text", "") for part in parts)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def load_rows(sft_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for name in ("train.jsonl", "val.jsonl"):
        path = sft_dir / name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            for index, line in enumerate(fh):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows.append({"file": name, "row": index, "messages": data.get("messages", [])})
    return rows


def extract_input(user_content: str) -> str:
    match = ORIGINAL_RE.search(user_content)
    return match.group(1).strip() if match else user_content.strip()


def mechanical_check(ai_text: str, gold: str, bounds: tuple[float, float]) -> dict:
    issues: list[str] = []
    if fact_tokens(ai_text) != fact_tokens(gold):
        lost = fact_tokens(gold) - fact_tokens(ai_text)
        added = fact_tokens(ai_text) - fact_tokens(gold)
        issues.append(f"fact_drift:lost={dict(lost)}:added={dict(added)}")
    ratio = length_ratio(ai_text, gold)
    low, high = bounds
    if ratio and not (low <= ratio <= high):
        issues.append(f"length_ratio:{ratio}")
    if connector_hits(ai_text) < 1:
        issues.append("not_ai_flavoured")
    metrics = {
        "words_gold": len(gold.split()),
        "length_ratio": ratio,
        "overlap_5gram": word_ngram_overlap(ai_text, gold, 5),
        "lcs": longest_common_substring_ratio(ai_text, gold),
        "connector_hits_input": connector_hits(ai_text),
        "sentence_std_input": sentence_length_std(ai_text),
        "sentence_std_gold": sentence_length_std(gold),
    }
    return {"issues": issues, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sft-dir", default="training/data/sft")
    parser.add_argument("--sample", type=int, default=60, help="0 = chấm toàn bộ")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-score", type=int, default=4)
    parser.add_argument("--max-chars", type=int, default=2400)
    parser.add_argument("--judges", nargs="*", default=list(DEFAULT_JUDGES))
    parser.add_argument("--verify-only", action="store_true", help="bỏ LLM judge, chỉ gate cơ khí")
    parser.add_argument("--call-gap", type=float, default=0.6, help="giây nghỉ giữa 2 call judge")
    args = parser.parse_args()

    sft_dir = (ROOT / args.sft_dir).resolve() if not Path(args.sft_dir).is_absolute() else Path(args.sft_dir)
    rows = load_rows(sft_dir)
    if not rows:
        print(f"[error] không có train/val JSONL trong {sft_dir}")
        return 2
    rng = random.Random(args.seed)
    if args.sample and args.sample < len(rows):
        rows = rng.sample(rows, args.sample)
    print(f"[info] chấm {len(rows)} cặp · judges={'cơ khí' if args.verify_only else ', '.join(args.judges)}")

    env = load_env() if not args.verify_only else {}
    active_judges: list[str] = []
    if not args.verify_only:
        for judge in args.judges:
            provider = judge.partition(":")[0]
            if provider == "local":
                active_judges.append(judge)  # server local, không cần key
                continue
            key_name = "GROQ_API_KEY" if provider == "groq" else "GEMINI_API_KEY"
            if env.get(key_name):
                active_judges.append(judge)
            else:
                print(f"[warn] bỏ judge {judge} — thiếu {key_name}")
        if not active_judges:
            print("[error] không còn judge nào khả dụng — dùng --verify-only hoặc bổ sung key")
            return 2

    results: list[dict] = []
    for position, row in enumerate(rows):
        messages = row.get("messages", [])
        try:
            user_content = next(m["content"] for m in messages if m.get("role") == "user")
            gold = next(m["content"] for m in messages if m.get("role") == "assistant")
        except StopIteration:
            continue
        ai_text = extract_input(user_content)
        mech = mechanical_check(ai_text, gold, bounds=(0.85, 1.45))
        entry: dict = {
            "file": row["file"],
            "row": row["row"],
            # BẢN SAO, không phải reference: judge_error sẽ được append vào
            # list này về sau — dùng chung reference khiến verdict lệch nhãn
            # reject_mechanical cho mọi cặp bị judge lỗi (bug đã gặp).
            "issues": list(mech["issues"]),
            "metrics": mech["metrics"],
            "scores": {},
            "verdict": "",
        }

        if not mech["issues"] and not args.verify_only:
            prompt = JUDGE_PROMPT.format(
                ai_text=ai_text[: args.max_chars], gold_text=gold[: args.max_chars]
            )
            for judge in active_judges:
                try:
                    verdict = parse_verdict(call_judge(judge, prompt, env))
                except Exception as exc:  # noqa: BLE001 - judge lỗi không được giết cả run
                    entry["issues"].append(f"judge_error:{judge}:{type(exc).__name__}")
                    verdict = None
                if verdict is None:
                    entry["issues"].append(f"judge_unparseable:{judge}")
                    continue
                entry["scores"][judge] = verdict
                time.sleep(args.call_gap)

        # Quyết định: cơ khí fail = loại ngay; judges phải đồng ý đạt trên 3 tiêu chí.
        score_failures: list[str] = []
        for judge, verdict in entry["scores"].items():
            for metric in ("ai_ness", "naturalness", "fidelity"):
                if verdict[metric] < args.min_score:
                    score_failures.append(f"{judge}:{metric}={verdict[metric]}")
        values = [v[m] for v in entry["scores"].values() for m in ("ai_ness", "naturalness", "fidelity")]
        if values and max(values) - min(values) >= 2:
            score_failures.append("phan_quan")

        if mech["issues"]:
            entry["verdict"] = "reject_mechanical"
        elif not entry["scores"]:
            entry["verdict"] = "unscored"
        elif score_failures:
            entry["verdict"] = "reject_judge"
        else:
            entry["verdict"] = "pass"
        entry["score_failures"] = score_failures
        results.append(entry)
        if (position + 1) % 20 == 0:
            passed = sum(1 for r in results if r["verdict"] == "pass")
            print(f"  [{position + 1}/{len(rows)}] pass={passed}")

    passed = [r for r in results if r["verdict"] == "pass"]
    report = {
        "pairs_checked": len(results),
        "pass": len(passed),
        "reject_mechanical": sum(1 for r in results if r["verdict"] == "reject_mechanical"),
        "reject_judge": sum(1 for r in results if r["verdict"] == "reject_judge"),
        "unscored": sum(1 for r in results if r["verdict"] == "unscored"),
        "issue_counts": {},
        "score_failures": {},
        "metric_means": {},
        "judges": active_judges,
        "min_score": args.min_score,
        "verify_only": args.verify_only,
    }
    for r in results:
        for issue in r["issues"]:
            key = issue.split(":", 1)[0]
            report["issue_counts"][key] = report["issue_counts"].get(key, 0) + 1
        for failure in r["score_failures"]:
            key = failure.split("=", 1)[0] if "=" in failure else failure
            report["score_failures"][key] = report["score_failures"].get(key, 0) + 1
    for metric in ("length_ratio", "overlap_5gram", "lcs", "connector_hits_input", "sentence_std_input"):
        values = [r["metrics"][metric] for r in results if metric in r["metrics"]]
        if values:
            report["metric_means"][metric] = round(sum(values) / len(values), 4)

    report_path = sft_dir / "qc_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rejects_path = sft_dir / "qc_rejects.jsonl"
    with rejects_path.open("w", encoding="utf-8") as fh:
        for r in results:
            if r["verdict"] != "pass":
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[done] report: {report_path.as_posix()} · rejects: {rejects_path.as_posix()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[dừng] QC judge bị ngắt giữa chừng.")
        raise SystemExit(130)
