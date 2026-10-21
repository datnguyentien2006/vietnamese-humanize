# Vietnamese Humanizer — Automated Evaluation Harness

Automated pipeline to measure how well the web app humanizes AI-style
Vietnamese text, and to catch regressions while we iterate on prompts,
patterns, and the fine-tuned model.

## What it does

1. **Samples** — `samples/*.txt`, eight self-authored paragraphs written in
   a deliberately "AI flavour" across eight genres (business blog, news,
   product description, academic, tech release note, travel, finance
   report, community post). Each contains hard facts (numbers, dates,
   names, acronyms) so fact preservation can be verified.
2. **Humanize** — each sample goes through the *real* production path:
   the backend's `generate_rewrite` (lint → Groq edits → verified apply),
   exactly what the website serves, not a separate prompt.
3. **Score**
   - *Meaning preservation* — regex extraction of numbers, dates,
     acronyms and quoted entities; anything in the original that vanished
     from the rewrite is counted as a loss (`metrics.meaning_preservation`).
   - *Readability* — sentence-length mean/stdev (human prose varies more),
     lexical diversity (TTR), length ratio (`metrics.readability`).
   - *Mechanical style* — robotic-connector density per 100 words and
     linter issue counts before/after (deltas show whether editing
     actually reduced flags).
   - *Naturalness / meaning / tone (LLM-as-judge)* — Groq-hosted judge
     scores each rewrite 0–10 against an explicit rubric
     (`judge.judge_pair`). This is text-quality judging, **not** an
     AI-detector score; see the policy note in `EVALUATION_REPORT.md`.
4. **Results** — one JSON per sample plus `summary.json`, written to
   `results/` (or `results/<tag>/` with `--tag`). Committed results for
   recent rounds live in `results/round2/`.

## Usage

From the repository root (`.venv` activated):

```powershell
python evaluation/run_evaluation.py                # all samples + judge
python evaluation/run_evaluation.py --no-judge     # static metrics only
python evaluation/run_evaluation.py --sample sample03
python evaluation/run_evaluation.py --tag round3   # keep rounds separate
```

Requires `GROQ_API_KEY` in `web/backend/.env` (never committed), and the
`groq` SDK installed in the active environment. Note: free-tier Groq has a
per-day token quota (TPD); a full 8-sample round consumes essentially the
whole day's budget on `gpt-oss-120b`.

## Directory layout

```
evaluation/
├── README.md            # this file
├── metrics.py           # deterministic metrics (no LLM)
├── judge.py             # Groq LLM-as-judge (fail-soft)
├── run_evaluation.py    # orchestrator
├── show_results.py      # per-sample dashboard from saved results
├── samples/             # self-authored test inputs (8 genres)
└── results/             # generated JSON (root layout or results/<tag>/)
```

The findings, sample-by-sample results, and fix history live in
`EVALUATION_REPORT.md` at the repository root.
