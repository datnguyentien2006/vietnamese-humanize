# -*- coding: utf-8 -*-
"""Benchmark teacher LLM local trên mẫu nhỏ trước khi chạy toàn bộ corpus.

Chạy trên chính máy (6 GB VRAM / 16 GB RAM) qua server OpenAI-compatible
(Ollama: http://127.0.0.1:11434/v1). Với mỗi model, chấm trên một mẫu nhỏ
cân bằng register:

  * tốc độ: thời gian/call, token/s sinh
  * bộ nhớ: VRAM sử dụng trong lúc model resident (nvidia-smi)
  * chất lượng: tỷ lệ qua gate ``check_pair`` (fact-token + length + reuse),
    số fact_drift, và 1 mẫu input/output để người đọc tự thẩm định

Kết quả ghi ra ``training/data/bench_local_report.md`` + in stdout.

Usage (sau khi `ollama pull` model):
  python training/bench_local_teacher.py --models qwen3:4b-instruct-2507,qwen2.5:7b-instruct-q4_K_M
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from pair_synthesis import AI_STYLE_TEACHER_PROMPTS, check_pair  # noqa: E402
from prepare_dataset import (  # noqa: E402
    _lint_fn,
    chunk_document,
    clean_text,
    infer_register,
    read_documents,
)


def call_local(base: str, model: str, prompt: str, timeout: float = 600.0) -> tuple[str, dict]:
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0.4,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    usage = body.get("usage", {}) or {}
    return content.strip(), usage


def vram_used_mib() -> float | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        return float(out.splitlines()[0])
    except Exception:  # noqa: BLE001 - không có nvidia-smi thì bỏ qua
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", required=True, help="tag ollama, phân tách bằng dấu phẩy")
    parser.add_argument("--base", default=os.environ.get("TEACHER_API_BASE", "http://127.0.0.1:11434/v1"))
    parser.add_argument("--source", default="training/data/raw_staged")
    parser.add_argument("--chunks-per-register", type=int, default=2)
    parser.add_argument("--max-words", type=int, default=250, help="cắt chunk ngắn hơn để benchmark nhanh")
    parser.add_argument("--out", default="training/data/bench_local_report.md")
    args = parser.parse_args()

    base = os.environ.get("TEACHER_API_BASE") or args.base
    lint_fn = _lint_fn()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    # Gom chunk theo register: chọn docs xen kẽ nguồn cho đến khi đủ số lượng.
    want = args.chunks_per_register
    by_register: dict[str, list[tuple[str, str]]] = {}
    for doc_id, doc_text in read_documents([args.source], "text", None):
        register = infer_register(doc_id)
        if register == "unknown":
            continue
        if len(by_register.get(register, [])) >= want:
            if all(len(v) >= want for v in by_register.values()) and len(by_register) >= 4:
                break
            continue
        chunks = chunk_document(clean_text(doc_text), 30, args.max_words)
        if chunks:
            by_register.setdefault(register, []).append((f"{doc_id}|0", chunks[0]))

    bench_chunks: list[tuple[str, str]] = []
    for register, items in sorted(by_register.items()):
        bench_chunks.extend(items[:want])
    total_words = sum(len(text.split()) for _, text in bench_chunks)
    print(f"[info] benchmark {len(bench_chunks)} chunk ({total_words} từ) trên {len(by_register)} register: {sorted(by_register)}")

    lines = [
        "# Benchmark teacher local",
        f"- Thời điểm: {datetime.now(UTC).isoformat()}",
        f"- Số chunk: {len(bench_chunks)} ({total_words} từ) — register: {', '.join(sorted(by_register))}",
        f"- Endpoint: {base}",
        "",
        "| Model | Call OK | Gate pass | fact_drift | s/call | tok/s sinh | VRAM (MiB) |",
        "|---|---|---|---|---|---|---|",
    ]
    samples: list[str] = []

    for model in models:
        # Warmup: nạp model vào VRAM, không tính thời gian.
        try:
            call_local(base, model, "Trả về đúng một chữ: OK")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"| **{model}** | LỖI: {type(exc).__name__}: {str(exc)[:80]} | | | | | |")
            print(f"[fail] {model}: {exc}")
            continue
        vram = vram_used_mib()

        gate_pass = 0
        fact_drift = 0
        wall_times: list[float] = []
        gen_tokens = 0
        sample_saved = False
        for tag, human in bench_chunks:
            prompt = AI_STYLE_TEACHER_PROMPTS["L2"].format(text=human)
            started = time.time()
            try:
                ai_text, usage = call_local(base, model, prompt)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] {model} {tag}: {type(exc).__name__}: {str(exc)[:100]}")
                continue
            wall_times.append(time.time() - started)
            gen_tokens += int(usage.get("completion_tokens") or len(ai_text.split()) * 1.3)
            reason = check_pair(
                ai_text,
                human,
                length_ratio_bounds=(0.85, 1.45),
                min_ai_hits=1,
                lint_fn=lint_fn,
                max_5gram_overlap=0.65,
                max_lcs=0.75,
            )
            if reason:
                if reason.startswith("fact_drift"):
                    fact_drift += 1
            else:
                gate_pass += 1
            if not sample_saved and not reason:
                samples.append(
                    "\n## Mẫu đầu ra đạt gate — "
                    + model
                    + "\n\n**GOLD (văn người):**\n\n> "
                    + human[:400].replace("\n", " ")
                    + "…\n\n**OUTPUT (văn AI):**\n\n> "
                    + ai_text[:400].replace("\n", " ")
                    + "…\n"
                )
                sample_saved = True

        n = len(wall_times) or 1
        avg_wall = sum(wall_times) / n
        tok_s = (gen_tokens / sum(wall_times)) if wall_times else 0
        lines.append(
            f"| {model} | {len(wall_times)}/{len(bench_chunks)} | {gate_pass}/{len(wall_times)} "
            f"| {fact_drift} | {avg_wall:.1f} | {tok_s:.0f} | {vram if vram else '—'} |"
        )
        print(f"[done] {model}: pass {gate_pass}/{len(wall_times)}, {avg_wall:.1f}s/call, {tok_s:.0f} tok/s")

    report = "\n".join(lines) + "\n\n" + "\n".join(samples) + "\n"
    out_path = ROOT / args.out
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"[done] report: {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
