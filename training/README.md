# Fine-tuning pipeline — dedicated Vietnamese humanizer

The current rewrite pipeline (Groq + per-issue edit prompts + manual editing)
reduces AI-detection scores to roughly 15–20%. The plan here replaces the
engine with a **model fine-tuned specifically for Vietnamese humanization**,
trained on naturally written human Vietnamese so it learns how people actually
write — then the site becomes: submit AI text → model rewrites → review →
optionally edit manually, with fact-preservation and source-suggestion checks
around it.

**Current status:** scaffold prepared. Nothing has been trained yet; the
existing Groq web app stays live while this pipeline is under construction.

## Method

Two-phase training on a Qwen2.5-14B-Instruct base (4-bit QLoRA):

1. **Phase 1 — task SFT (synthesize mode, the default).** Build
   `(AI-flavoured input, human target)` pairs: take human-written prose and
   "dirty" it into AI-flavoured Vietnamese by injecting the project's own
   catalog tells (generic connectors, template openers, hollow evaluative
   tails). Dirtying only inserts phrases without digits, so both sides carry
   the same fact tokens; every candidate is re-verified mechanically before it
   is written to disk. This is the only mode that teaches the actual
   "rewrite this text, keep the numbers" mapping, because the prompt and the
   target describe the same content.
2. **Phase 2 — curated pairs (pairs mode).** Assemble rewrite pairs from your
   own work — manual edits from the current app's review workflow, accepted
   suggestions, and earlier pipeline fixes — saved as
   `training/data/pairs/humanized_pairs.jsonl`, one
   `{"input": ..., "output": ...}` per line.

`--mode continuation` still exists as a style-prior experiment, but it is no
longer the default and it does **not** teach the rewrite task: it pairs a
"rewrite this" prompt with the *next* chunk as the target, so the model learns
to ignore the input — which is exactly what breaks fact preservation at
inference time.

Base model choice:

| Checkpoint | Role | Notes |
| --- | --- | --- |
| `Qwen/Qwen2.5-14B-Instruct` | QLoRA training base | Real fp16 weights are required for training; AWQ checkpoints are not trainable |
| `Qwen/Qwen2.5-7B-Instruct` | fallback base | Use when a free T4 (16 GB) runs out of memory |
| `Qwen/Qwen2.5-14B-Instruct-AWQ` | serving format | Produced by `merge_and_export.py --export-awq` from the merged model |

Prompt templates live in `training/task_prompts.py` — the web backend must use
the exact same template at inference time or quality drops.

## Corpus guidance (phase 1 data)

Target: tens of thousands of cleaned human-written Vietnamese chunks of
30–400 words. Candidate source families (verify each for license + access
yourself; do not commit downloaded corpora):

- Vietnamese news article datasets whose terms allow study use.
- Public-domain Vietnamese literature (e-books / digitized texts).
- Open web-crawl subsets of Vietnamese (e.g. filtered MC4-vi) with obvious
  boilerplate removed.
- Your own writing and other contributors' writing (with permission).

Rules:

- **License matters.** Only use texts you have the right to study/train on;
  prefer public domain or clearly licensed corpora.
- **No AI contamination.** Prefer corpora published before generative-AI
  output dominated the web, and remove obvious machine-translated prose.
- Wikipedia dumps are fine for punctuation/grammar but their style is
  encyclopedic; balance them with essays, blogs, and narrative prose.

## Before you train: `doctor.py`

```bash
python training/doctor.py
```

It prints the Python/package state, **which provider `/api/humanize` would
actually answer today** (mirroring `app.capabilities.humanize_enabled`), the
dataset row counts and manifest summary, and which training-only dependencies
are missing. If it reports `groq-fallback`, every result you are reviewing came
from Groq — not from a local model.

## How to run (Colab free / Kaggle T4)

1. Put human text files into `training/data/raw/` (`.txt`, `.txt.gz`,
   `.jsonl` with a `text` column, or `.parquet`; set `text_column` in
   `training/config.yaml`). On Colab, keep raw data + outputs in Google Drive
   and symlink:
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   ```
2. Clone the repo, then:
   ```bash
   pip install -r training/requirements.txt
   python training/fetch_corpus.py --max-pages 800   # nếu chưa có corpus (xem CORPUS.md)
   python training/prepare_dataset.py --mode synthesize --source training/data/raw --limit 20000
   python training/train_qlora.py
   ```
   `--mode synthesize` writes `training/data/sft/{train,val}.jsonl` plus a
   `manifest.json` (pair counts, register mix, rejection reasons, mean surface
   overlap). Splits are made **per source document**, so chunks of one document
   never straddle train/val.

   `synthesize.dirtying: llm` uses a teacher endpoint instead of the rule
   engine and needs `TEACHER_API_BASE`, `TEACHER_MODEL`, `TEACHER_API_KEY`
   (or `GROQ_API_KEY`). Candidates that drop or add a number/date are rejected
   by the same guard, so a weak teacher lowers yield instead of poisoning the
   dataset.
3. If VRAM runs out (`CUDA out of memory`), rerun with:
   ```bash
   python training/train_qlora.py --model Qwen/Qwen2.5-7B-Instruct
   ```
   The 14B NF4 model needs ~10 GB + LoRA/optimizer states; with batch size 1
   and 16 accumulation steps it usually fits on a T4, but sequences beyond
   ~1024 tokens push it over.
4. Merge + export (AWQ needs a CUDA GPU; ~20–40 min on a T4):
   ```bash
   python training/merge_and_export.py --export-awq
   ```
5. Serve locally/self-hosted — see [`serve/runpod_vllm.md`](serve/runpod_vllm.md).

Parameters live in [`config.yaml`](config.yaml) (LoRA rank/alpha, lr, epochs,
length filters); `--model`, `--epochs`, `--batch-size`, `--grad-accum` CLI
flags override for a single run.

## Fact-preservation protocol

The system prompt forbids inventing or dropping facts, but prompts are not
guarantees. Enforce it mechanically:

1. Before serving a rewrite, extract numbers, dates, and capitalized proper
   names from the original and check they appear in the rewrite; on a miss,
   retry once, else decline and keep the manual editor as the path forward.
2. Keep `viet-writing-lint` running on the rewritten text (the patterns that
   flag templated openings, empty Hán-Việt filler, uniform rhythm are still
   the cheapest regression check).
3. The reuse target for "explain your figures" suggestions is
   `report_analyzer.py`'s `unverified_data` / `missing_evidence` issue types,
   shown after the rewrite for the user's own review.

## Evaluation (what "good" means here)

- **Fact preservation:** automated number/date/name diff review over a held-out
  set — zero regressions allowed.
- **Human review:** a small blind panel of reviewers comparing rewritten vs.
  original for fluency, tone, and correctness.
- Conversational-style spot checks against templated/AI-flavored patterns
  using the project's own pattern catalog.

We deliberately frame quality as writing quality and fact accuracy — reviews
and data regression — rather than chasing AI-detector score targets.

## Layout

```
training/
  config.yaml          hyperparams, model ids, dataset paths
  task_prompts.py      the ONE prompt template used for training + serving
  prepare_dataset.py   raw human text -> SFT JSONL (synthesize / pairs / continuation)
  pair_synthesis.py    dirtying engine + fact-token guard for synthesize pairs
  fetch_corpus.py      collect PD/CC Vietnamese prose from Wikisource (provenance kept)
  CORPUS.md            nguồn dữ liệu, license, tỉ lệ trộn, cách kiểm tra nhiễm
  doctor.py            readiness: live provider, dataset state, missing deps
  train_qlora.py       4-bit QLoRA fine-tune (TRL + PEFT + bitsandbytes)
  merge_and_export.py  merge LoRA into base; optional AWQ export for vLLM
  serve/runpod_vllm.md self-hosting guide + future backend contract
  remote/              generated Colab/Kaggle notebook + running instructions
  data/raw/            put corpora here (gitignored)
  data/pairs/          curated {"input","output"} rewrite pairs (gitignored)
  data/sft/            generated train/val JSONL (gitignored)
  output/              checkpoints, adapters, merged + AWQ exports (gitignored)
```
