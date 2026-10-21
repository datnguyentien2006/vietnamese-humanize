# Contributing

Thanks for wanting to contribute. This is a small personal project, so the process is lightweight.

## Report an issue

Open a [GitHub issue](https://github.com/datnguyentien2006/vietnamese-humanize/issues) with:

- What you expected vs. what happened (backend error, lint finding, UI behavior).
- A short Vietnamese sample text that reproduces the problem directly in the prompt, or as a code block.
- If it is a lint/false-positive report: the pattern ID from the finding (`--format json` output) and the structure being flagged.

## Set up a development environment

Python 3.11+ and Node.js 20+.

```bash
# Python package + tests
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # use .venv/bin/ on Linux/macOS
pytest

# Backend
cd web/backend
pip install -r requirements.txt
copy .env.example .env          # set GROQ_API_KEY, REWRITE_ENABLED=true
pytest tests

# Frontend
cd web/frontend
npm ci
npm test
```

Style: run `ruff check .` before committing Python changes. Keep changes consistent with the surrounding code; upstream-era names (`Vietnamese Writing Skills`, `vietnamese_writing_skills`) are kept intentionally.

## Rules

- **Do not commit `.env` files or API keys.** `.gitignore` excludes `web/backend/.env` — verify before pushing.
- **Do not change facts in patterns.** Pattern YAML entries must describe a real, reproducible Vietnamese-language signal. Include one bad example and one good example per pattern.
- **No detector-evasion features.** Contributions that add "AI score", authorship detection, or evasion advice will be rejected.
- Keep Web UI text in Vietnamese (the app's audience is Vietnamese writers); code comments may be English or Vietnamese.

## Contribute human-written Vietnamese text (highest-value contribution)

The fine-tuning pipeline in [`training/`](training/README.md) needs one thing
above all: naturally written Vietnamese prose. If you want to help:

1. Put plain-text files (30–400 word chunks work best) into `training/data/raw/`
   — `.txt`, `.txt.gz`, or `.jsonl`/`.parquet` with a `text` column.
2. Only submit text you have the right to share for training, and note its
   origin in the PR description (site/book/corpus + license).
3. Machine-translated or AI-generated text contaminates the whole corpus —
   write a line about why you believe the text is human-written.
4. Do not commit downloads of large licensed corpora; open an issue with the
   source instead, and we will handle the agreement.

Also valuable: accepted rewrites from the app's review workflow exported as
`{"input", "output"}` pairs for phase 3 (`training/data/pairs/`).

## Pull requests

1. Fork, create a feature branch (`feat/report-refiner-fix`, not `patch-1`).
2. Run `pytest`, `pytest web/backend/tests`, and `npm test` — all green.
3. Describe what changed and why in the PR description.
4. Small, focused PRs are merged faster than large ones.
