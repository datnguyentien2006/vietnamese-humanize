# Vietnamese Humanize

Tools for editing Vietnamese prose without changing its facts. This repository contains:

- **A web application** — a FastAPI backend + Next.js frontend that lints a text, then helps you fix each issue manually or with AI.
- **`viet-writing-lint`, a rule-based linting CLI** for Vietnamese prose (this project's Python package is `vietnamese-writing-skills`, imported as `vietnamese_writing_skills`).
- **`humanize.py`, a standalone CLI** that rewrites a whole document with an LLM using the bundled `skills/humanizer-vi/SKILL.md` prompt.
- **`training/`, a fine-tuning pipeline (under construction)** for a dedicated Vietnamese humanizer model — dataset prep from human-written corpora, QLoRA training, and AWQ export for a self-hosted vLLM endpoint.

The linter does not classify authorship, produce an "AI probability score," or offer detector-evasion advice. It reports surface signals for a person to review.

Based on [longhang2004/vietnamese-humanizer](https://github.com/longhang2004/vietnamese-humanizer) (MIT). This fork keeps the lint/pattern foundation and replaces the original rewrite pipeline with a Groq-powered, issue-oriented editing workflow (see [Changelog of this fork](#fork-changes)).

## Where this is heading: a fine-tuned humanizer model

Per-issue rewrite prompts with Groq plateau around a 15–20% AI-detection
score — good, but not the goal. The next step (tracked in
[ROADMAP.md](ROADMAP.md)) is to train a model dedicated to this task:

- **Training data:** naturally written human Vietnamese text, so the model
  learns how people actually write instead of copying a generic assistant voice.
- **Inference flow on the site:** submit AI-generated text → the fine-tuned
  model rewrites it → you review the humanized result → edit manually if the
  result is not natural enough.
- **Meaning and facts stay put:** numbers, dates, and names are checked
  mechanically after every rewrite, and unclear figures get "explain the
  source" suggestions from the report analyzer.
- Engine: QLoRA fine-tune of Qwen2.5-14B-Instruct, exported to AWQ and served
  from a self-hosted vLLM endpoint. Everything lives under [`training/`](training/README.md).

Until the trained model is ready, the web app keeps the current Groq pipeline.

## How the web app works

1. **Lint** — paste text and select the skills to check against. The frontend shows findings grouped by issue, with occurrences highlighted inside the page.
2. **Edit** — every issue card opens an editable view of its matched text. You rewrite it yourself, or use "Gợi ý sửa bằng AI" to get an AI suggestion per issue.
3. **Refine** — the Report Refiner scans the document paragraph by paragraph (9 issue types: unverified data, academic tone, long sentence, missing evidence, logic gap, repetition, vague reference, passive overuse, register mismatch), then executes your natural-language command on each flagged sentence, shows a before/after diff, and pushes the result back into the editor.

LLM calls go to **Groq** (`openai/gpt-oss-120b` with `openai/gpt-oss-20b` as fallback; configurable via `GROQ_REWRITE_MODELS`). All AI features stay disabled until `GROQ_API_KEY` is set and `REWRITE_ENABLED=true`.

## The four skills

The linter and rewrite prompts are organized into four skills. Select one or more in the UI or on the CLI:

| Skill | Use it for |
| --- | --- |
| `humanizer-vi` | Prose that feels templated, clichéd, flat in rhythm, or uneven in voice |
| `translationese-cleaner-vi` | Vietnamese that copies English word order, metaphors, or nominalization too closely |
| `grammar-checker-vi` | Spelling, punctuation, structure, and ambiguity checks |
| `style-guide-vi` | Consistency of pronouns, terms, numbers, and formatting |

The pattern catalog (69 patterns across `patterns/*.yml`) defines finding type, scope, aggregation, exceptions, and rewrite strategy for each rule:

- `ERROR` — a demonstrable error, such as an accidental repeated word or invalid spacing.
- `WARNING` — a structure that may be ambiguous or inconsistent but requires context.
- `PREFERENCE` — a style choice that should only be applied after a style has been selected.
- `HEURISTIC` — a surface signal such as density or sentence rhythm; a reviewer must inspect the full scope.

A finding does not prove that prose is wrong or AI-generated.

## Run the web app locally

Requires Python 3.11+ and Node.js 20+.

**Backend**

```bash
cd web/backend
python -m venv .venv           # or: uv venv, uv pip install -e ../..
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/ on Linux/macOS
copy .env.example .env         # edit: set GROQ_API_KEY, REWRITE_ENABLED=true
.venv/Scripts/uvicorn app.main:app --reload
```

**Frontend**

```bash
cd web/frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. The frontend reads `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`), and the backend CORS origins come from `FRONTEND_ORIGIN`.

### Backend environment variables

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required for all AI features (rewrite, suggest-fix, report refiner, scan) |
| `GROQ_REWRITE_MODELS` | Comma-separated Groq models, tried in order |
| `REWRITE_ENABLED` | Master switch for AI features (`false` keeps lint-only mode) |
| `DEBUG_ERRORS` | Return verbose per-attempt LLM error details in API errors (dev only — set `false` in production) |
| `FRONTEND_ORIGIN` | CORS origins, comma-separated |
| `CONTRIBUTIONS_ENABLED`, `ADMIN_API_ENABLED`, `ADMIN_API_KEY` | Optional contribution/admin endpoints (add database + postgres driver + `DATABASE_URL` when enabled) |
| `TRUSTED_PROXY_HOSTS`, `TRUST_PRIVATE_PROXIES` | Rate-limit IP resolution behind proxies |

Never commit `.env`. Set `DEBUG_ERRORS=false` in production.

## CLI: `viet-writing-lint`

```bash
python -m pip install .            # from a source checkout, or: pip install -e ".[dev]"
viet-writing-lint article.md
viet-writing-lint article.md --format json
viet-writing-lint docs/ --recursive --root .        # lint a tree of markdown files
```

The CLI exits with `1` when it finds material to review and `2` when it cannot run. Use `--format json` when feeding the report to another program (for example, `humanize.py --lint`).

### Deep (LLM-judged) checks

Six semantic patterns (VI-HUM-D06, D07, S13, L07, D08, D09) cannot be detected with regex — cluttered emotion, self-echo, question-answering reflex, and similar. With `--deep`, the CLI sends candidate passages to an LLM judge and keeps only findings with high confidence:

```bash
python -m pip install "vietnamese-writing-skills[llm]"   # adds google-genai
export GEMINI_API_KEY=...                                # deep checks use Gemini
viet-writing-lint article.md --deep --deep-model gemini-2.5-flash
```

Without `--deep` (the default) the CLI never calls any LLM.

## CLI: `humanize.py`

A two-pass document rewriter: pass 1 rewrites the full text, pass 2 audits the output (lost facts, added claims, leftover AI tells) and repairs it. It loads `skills/humanizer-vi/SKILL.md` as its system prompt.

```bash
python -m pip install google-genai
python humanize.py input.txt output.txt [--lint lint-report.json] [--voice sample.txt] [--no-audit]
```

## Development

```bash
pytest                  # root unit tests (tests/)
pytest web/backend/tests
cd web/frontend && npm test    # vitest
ruff check .
```

Deployment targets kept in the repo: [web/backend/render.yaml](web/backend/render.yaml) (Render: backend service + Postgres) and [web/backend/vercel.json](web/backend/vercel.json) + [web/backend/api/index.py](web/backend/api/index.py) (Vercel serverless entry).

## Project layout

```
patterns/     rule catalog (YAML + JSON Schema), shared by CLI, package, and backend
skills/       skill prompts: <skill>/SKILL.md + references/ (the humanizer prompt is used by humanize.py)
src/          the vietnamese_writing_skills package (lint engine, pattern loader)
tests/        CLI/engine unit tests
web/backend   FastAPI app (lint, patterns, skills, rewrite, suggest-fix, report refiner)
web/frontend  Next.js app (editor, issue cards, compare view, report refiner)
docs/         generated pattern documentation (docs/generated-patterns.md)
humanize.py   standalone document rewriter CLI
training/     fine-tune pipeline for the dedicated humanizer model (see training/README.md)
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[MIT](LICENSE). Original lint engine, patterns, and skill structure are based on [longhang2004/vietnamese-humanizer](https://github.com/longhang2004/vietnamese-humanizer).

## Fork changes

Differences from upstream in this fork:

- Rewrite pipeline moved from Gemini to **Groq** with multi-model fallback and lint-verified retries.
- Replaced the one-shot rewrite panel with a manual, per-issue editing workflow plus an AI "suggest fix" per issue.
- Added the **Report Refiner** scan/refine/diff workflow and the formal→casual vocabulary advisor.
- Linter: added start/end/paragraph/sentence enrichment per occurrence, new heuristic patterns (Chinese-source-word filler density, uniform sentence rhythm, hedge spread, symmetry bias, over-enumeration, title-case abuse), and the `--deep` LLM judge.
- Added `humanize.py` (two-pass document rewriter) and the anti-perfection checklist / signs-of-AI references for the humanizer skill.
- Started the dedicated-model pipeline: `training/` (dataset prep, QLoRA fine-tune, AWQ export, vLLM serving guide) — see [ROADMAP.md](ROADMAP.md).
- Removed upstream's examples corpus, benchmarks, maintainer docs, release tooling, and donation assets that this fork does not use.
