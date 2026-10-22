# Roadmap — dedicated humanizer model

The tool's mission: rewrite AI-generated Vietnamese text to read naturally,
preserving meaning and facts (numbers, dates, names), with an interactive
review-and-edit experience. The first version went through a per-issue Groq
pipeline (lint → manual editing → AI suggest-fix → report refiner) which
plateaued: manual-style rewrites still left the result detectably templated.
The next step is a model fine-tuned on naturally written human Vietnamese,
behind a single-screen "Humanize văn bản" workflow.

Phase order is deliberate: data first, then training, serving, and only then
switching the live web app.

## Phase 0 — Done (baseline)

- Groq rewrite pipeline + manual per-issue editing + compare view + report
  refiner (live app).
- Lint engine: 70 patterns (including VI-HUM-S15/S16, generic AI-connector
  overload at paragraph and document scope), `--deep` LLM judge.
- Repository cleanup separating this fork from the upstream project.
- `evaluation/` automated harness: eight self-authored AI-style samples,
  per-sample JSON results, static metrics + Groq LLM-as-judge; findings
  recorded in [EVALUATION_REPORT.md](EVALUATION_REPORT.md).

## Phase 1 — Corpus (in progress)

- Collect human-written Vietnamese text; apply the license and
  no-AI-contamination rules in [training/README.md](training/README.md).
- Run `prepare_dataset.py` in continuation mode; target 20k+ chunks
  (30–400 words) after dedupe.
- **Exit criteria:** ≥ a few thousand training chunks in
  `training/data/sft/train.jsonl`; validation split frozen.

## Phase 2 — QLoRA fine-tune

- Train `Qwen/Qwen2.5-14B-Instruct` (NF4) with `train_qlora.py` on Colab/Kaggle
  T4; drop to 7B if OOM.
- **Exit criteria:** validation loss plateaus; spot-check outputs read like
  natural Vietnamese and beat the Groq pipeline in the blind review checklist.

## Phase 3 — Curated task pairs

- Export the manual edits accumulated in the app's review workflow as
  `{"input","output"}` pairs (`prepare_dataset.py --mode pairs`), fine-tune
  further.
- **Exit criteria:** instruct-following improves; fact-preservation check
  (numbers/dates/names) passes ≥98% on the held-out set.

## Phase 4 — Serving

- Merge adapter, export AWQ, host behind vLLM (Runpod or own GPU) — see
  [training/serve/runpod_vllm.md](training/serve/runpod_vllm.md).
- **Exit criteria:** OpenAI-compatible endpoint responds in scope; latency
  <20 s for a 400-word paragraph.

## Phase 5 — Backend swap (shipped in v1.3)

- Rewrite service points at `HUMANIZER_API_BASE` (env-only, no SDK); keep
  Groq as a fallback flag initially.
- Fact-preservation validator (number/date/name set extraction, a diff view
  of it in the compare UI) wraps every model call.
- "Where does this figure come from" suggestions stay powered by the existing
  report-analyzer issue types (`unverified_data`, `missing_evidence`), now
  shown attached to the final rewrite.
- **Status (v1.3):** backend done — `POST /api/humanize` (5/min) replaced the
  v1.2 endpoints (`/api/rewrite` and friends removed); the v1.2 per-issue
  frontend was rebuilt into the single-screen workflow (`Humanize Text v1.3`);
  the inference prompt is locked to `training/task_prompts.py` by a test.
  Remaining: serve the fine-tuned checkpoint and set `HUMANIZER_API_BASE` —
  until then the Groq fallback answers every request.

## Phase 6 — Evaluation & iteration

- Held-out fact-preservation suite + small blind human review panel as the
  regression baseline for every future adapter.
- Iterate dataset composition (more pairs, more registers: blogs, essays,
  reports) based on real user edits — the manual-edit workflow remains the
  data collection flywheel for pairs.

Non-goals (unchanged from project scope): no authorship classification, no
"AI probability score" product features, no detector-evasion tooling. Quality
is measured as writing quality and fact accuracy, not detector score targets.
