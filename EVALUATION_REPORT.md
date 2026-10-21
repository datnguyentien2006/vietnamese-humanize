# Evaluation Report — Vietnamese Humanizer

**Status:** rounds 1–2 complete; round-3 fixes queued (§4.4) · **Harness:** [`evaluation/`](evaluation/README.md) · **Results:** `evaluation/results/round2/*.json`

This report documents the automated evaluation of the web app's humanization
core: methodology, test samples, per-round results, identified weaknesses,
fixes applied, and conclusions. All sample texts are self-authored for this
harness (no copyrighted material).

## 1. Policy note on AI-detection scores

The original task called for measuring "changes in AI-detection scores where
suitable." We deliberately **excluded detector scores as an optimization
target or recorded metric**. Reasons:

- This project's mission (see [README.md](README.md)) is writing quality with
  fact fidelity — not detector evasion. The README states outright that the
  linter does not classify authorship or offer detector-evasion advice.
- Optimizing against a detector score trains the pipeline to "beat" a moving,
  proprietary target instead of producing genuinely good Vietnamese prose.
- Our quality proxies correlate with what detectors react to (sentence-length
  variance, template connectors, uniform cadence) without gaming a specific
  detector.

If a detector measurement is ever wanted for information-only purposes, it can
be added as a side-read that must never feed back into prompts or training.

## 2. Methodology

### 2.1 Test samples

Eight self-authored paragraphs, each written in a deliberately "AI flavour"
(uniform sentence cadence, mechanical connectors, hollow hedges) and seeded
with hard facts (numbers, dates, proper names, acronyms) so fact preservation
can be verified mechanically:

| Sample | Flavour | Facts seeded |
|---|---|---|
| sample01_information_technology | business blog | project name, budget 8.5 tỷ, 72% progress, quarter |
| sample02_news_flood | news | 480 mm rainfall, date 22/10/2025, 1.250 households, river level |
| sample03_product_desc | product / e-commerce | model HIT-220B, 2200W, 45%, 99-minute timer, warranty 30 months, 12.400 units |
| sample04_academic_elearning | academic | 1.050 students, 63.5%, GPA 6.8 vs 7.2, dropout +1.8% |
| sample05_tech_release | tech release note | version 3.2.1, date 8/10/2025, −38% boot time, 27 bugs |
| sample06_travel_hoian | travel review | opening hours, 25.000 VAT incl. bread price, ticket 120.000, policy date |
| sample07_finance_report | finance report | 1.850 tỷ profit, +9.2%, NPL 1.15%, CAR 12.8%, date 30/9/2025 |
| sample08_social_community | community post | 845 books, 32 donors, 2.150.000 VND, delivery date |

### 2.2 Pipeline under test

Each sample goes through the **real production path**, not a stub:
backend `generate_rewrite()` → `lint_text` (70 patterns) → Groq-hosted model
(`openai/gpt-oss-120b`, fallback `gpt-oss-20b`) proposes surgical
find/replace edits against the flagged issues → edits applied with
verification, one retry loop.

### 2.3 Scoring dimensions

1. **Meaning preservation (static, deterministic)** — regex extraction of
   numbers, dates, acronyms, quoted entities; anything in the original that
   vanishes from the rewrite is counted as a loss. Score 1.0 = no loss.
2. **Readability** — sentence-length mean/stdev. Human prose varies sentence
   length; a positive stdev delta vs. the original indicates the rewrite
   "de-uniforms" the cadence.
3. **Mechanical style** — robotic-connector density per 100 words (20-phrase
   list) and linter issue counts before/after.
4. **Naturalness / meaning / tone (LLM-as-judge)** — Groq-hosted judge scores
   each rewrite 0–10 against an explicit rubric and lists factual losses and
   unnatural phrases. This is text-quality judging, **not** a detector score.
5. **Rewrite stats** — edits applied vs. rejected, verification attempts.

Every run writes per-sample JSON + `summary.json` to `evaluation/results/`.

## 3. Round 1 — baseline

### 3.1 Aggregate results (8 samples)

| Metric | Value |
|---|---|
| meaning score (static) | **0.99** |
| sentence-length stdev delta | **+1.35** (cadence diversified) |
| robotic density | **5.65 → 4.01** per 100 words |
| lint issues | **2.75 → 1.12** per sample |
| judge naturalness | **8.14 / 10** |
| judge meaning preserved | **9.43 / 10** |
| judge tone preserved | **9.0 / 10** |
| failures | 0 (all 8 humanized) |

### 3.2 Per-sample weaknesses discovered

| Sample | Symptom | Root cause |
|---|---|---|
| 02 (news), 08 (community) | **No-op rewrite** (density unchanged, 0 edits) | generic connectors ("Tổng thể", "Bên cạnh đó", "Ngoài ra"…) were covered by *no* lint pattern, so the issue-driven rewriter had nothing to act on |
| 05 (tech) | date `8/10/2025` missing after rewrite (meaning 0.889) | an edit silently dropped the date; there was **no mechanical guard** on entity preservation inside `_apply_edits` |
| 01 (business) | judge flagged added hedges: "khoảng 72%", "(ước tính)" | model added uncertainty language around solid figures — certainty drift |
| 07 (finance) | "TMCP" expanded into a bogus "Tài chính và Mua bán" | abbreviation hallucination; 3 edits additionally rejected on `find` mismatches |
| 08 (community) | the one proposed edit was rejected (`find` not verbatim) | model mis-extracted the exact source phrase |
| 04 (academic) | connectors survived (density 4.58 → 4.24) | connector count split across two paragraphs, each just below the per-paragraph threshold |
| 06 (travel) | judge call failed to parse (both models), fail-soft recorded | judge JSON parsing had no raw-capture diagnostics |

### 3.3 Fixes applied (round 1 → 2)

1. **New lint pattern VI-HUM-S15** (`patterns/humanizer.yml`) — per-paragraph
   overload of 14 generic AI connectors, threshold 4. Catches paragraph-level
   accumulation on samples 01/03/05/06/07/08.
2. **New lint pattern VI-HUM-S16** — document-scope connector overload,
   threshold 6. Catches text that keeps *each* paragraph just under the
   per-paragraph threshold but is connector-saturated overall
   (sample02, sample04, sample08).
3. **Fact-loss guard in `_apply_edits`** (`web/backend/app/services/rewriter.py`)
   — before applying an edit, mechanical diff of number/date tokens between
   `find` and `replace`: any dropped figure rejects the edit with reason
   "edit làm mất số liệu/ngày: …". Separator style changes (1.850 ↔ 1850) are
   normalized so pure re-formatting passes.
4. **Prompt hardening** (`ANTI_AI_SYSTEM_PROMPT` + `PARAGRAPH_FIX_SYSTEM_PROMPT`)
   — rule: never expand established abbreviations (TMCP, NHNN, UBND…);
   never add hedges ("khoảng", "ước tính") to solid figures; data in `find`
   must reappear in `replace`.
5. **Judge hardening** (`evaluation/judge.py`) — raw response captured on
   parse failure for diagnosis.
6. **Regression tests** — `web/backend/tests/test_fact_guard.py` (6 cases for
   the guard) and `tests/test_evaluation_metrics.py` (13 cases for the
   harness metrics). Full suites stay green: root 100, backend 88.

## 4. Round 2 — after fixes

Re-run of all 8 samples with identical samples and scoring (fixes from
§3.3 applied; the pattern baseline is recomputed with the new 70-pattern
set, so "issues before" is higher than round 1 by construction). Raw
records: `evaluation/results/round2/` (per-sample JSON + `summary.json`).

### 4.1 Aggregate comparison

| Metric | Round 1 (baseline) | Round 2 (after fixes) |
|---|---|---|
| meaning score (static) | 0.99 (one lost date) | **1.00 (8/8 perfect)** |
| sentence-length stdev delta | +1.35 | **+2.08** |
| robotic density per 100 words | 5.65 → 4.01 | 5.65 → **2.86** |
| lint issues per sample | 2.75 → 1.12 | 3.62 → **1.88**¹ |
| judge naturalness | 8.14 (n=7) | **8.50** (n=6)² |
| judge meaning preserved | 9.43 | **10.00** |
| judge tone preserved | 9.00 | **9.33** |
| failures | 0 | 0 (all 8 humanized) |

¹ *Issues-before rises because the two new patterns (S15/S16) detect connector
overload that round 1 was blind to; the model must now clear a harder bar.*
² *The judge failed to parse on samples 06/07 (see 4.3) and is excluded; 6
samples scored.*

### 4.2 Per-sample results (round 2)

| S# | density before → after | stdev Δ | meaning | lint b → a | judge (nat/mp/tp) |
|---|---|---|---|---|---|
| 01 business blog | 4.83 → **0.75** | +4.75 | 1.0 | 5 → 1 | 8.0/10.0/9.0 |
| 02 news | 6.25 → **0.93** | +0.33 | 1.0 | 1 → 1 | 9.0/10.0/8.0 |
| 03 product | 4.51 → 4.23 | +1.89 | 1.0 | 5 → 6 | 9.0/10.0/10.0 |
| 04 academic | 4.58 → 4.43 | +1.07 | 1.0 | 1 → 0 | 9.0/10.0/10.0 |
| 05 tech release | 6.25 → **1.65** | +0.06 | 1.0 | 3 → 1 | 8.0/10.0/9.0 |
| 06 travel | 6.34 → **0.82** | +6.76 | 1.0 | 4 → 1 | — (judge fail) |
| 07 finance report | 5.80 → 3.47 | +1.78 | 1.0 | 7 → 2 | — (judge fail) |
| 08 community | 6.62 → 6.62 (no-op) | 0.00 | 1.0 | 3 → 3 | 8.0/10.0/10.0 |

**Confirmed improvements over round 1:**

- **Fact preservation is now airtight**: previously lost `8/10/2025` (05)
  and hedge/abbreviation drift (01: "khoảng 72%", 07: expanded TMCP) are
  gone; every numerical/date token survives in all 8 rewrites, as a
  property of the mechanical guard rather than model luck.
- **No-op rewrites eliminated at the detector level**: S15/S16 now flag
  sample02/sample08 (round 1: neither was flagged at all), and 02 went
  from density 6.25 → **0.93** with 7 applied edits.
- **Connector cleanup roughly doubles** in strength: total robotic density
  dropped to 2.86 vs 4.01; samples 01/02/05/06 each land below 1.7.

### 4.3 Remaining weaknesses (round 2 → next round)

| Sample | Symptom | Root cause (diagnosed) |
|---|---|---|
| 03 (product), 04 (academic), 08 (community) | Model applies only 0–2 cosmetic edits; density barely moves (4.51→4.23 / 4.58→4.43 / no-op on 08); 03 even **added** a redundant "(mã sản phẩm HIT-220B, một mẫu bếp từ)" | Pass 1 is a **single shot for `heuristic`-type findings**: the model returned a *valid* JSON body with an empty `edits` array (08) or cosmetic edits only (03/04), and `_remaining_retryable` excludes `heuristic`, so no second pass was attempted |
| 06 (travel), 07 (finance) | Judge soft-failed on both models | Judge `max_tokens=900` was below the gpt-oss-20b reasoning budget: output came back truncated (06, raw JSON cut mid-note) or empty (07). The round-1 raw-capture fix made this diagnosable |
| 02 (news) | stdev Δ only +0.33 (still evenly paced) | The rewrite shortens sentences rather than mixing long/short; judge saw no tone damage (8.0) but cadence variance is unimproved |

### 4.4 Fixes applied after round 2 (validated by tests, pending round-3 metrics)

1. **`heuristic` finding type is now retryable** (`RETRYABLE_FINDING_TYPES`
   in `web/backend/app/services/rewriter.py`) — heuristic findings from
   S15/S16 get up to 2 more edit passes instead of silently no-oping.
2. **Prompt forbids empty edit replies** (`_build_user_prompt`): the model
   must propose at least one edit for every listed issue instead of
   returning an empty `edits` array; pairs with fix 1 so pass 2 sees the
   still-flagged text.
3. **Judge token budget 900 → 3000** (`evaluation/judge.py`) — gpt-oss
   reasoning tokens no longer truncate the score JSON.

Round 3 re-validation is deferred until the Groq free-tier daily token
quota (TPD 200k, consumed by rounds 1–2) and the Colab GPU quota reset;
the round-2 dataset/results above are the committed baseline in the
meantime.

## 5. Conclusions (updated per round)

- The core humanization loop is **functional end-to-end** on the real web
  path: issue detection → targeted LLM edits → verified application →
  meaning preservation verified mechanically.
- Fact preservation after the guard is **deterministic**: a dropped
  number/date can no longer reach the output even when the model
  misbehaves (round 2 measured meaning 1.00 across all samples, vs 0.99
  before the guard).
- Rounds 1–2 confirm that rewrite quality follows pattern coverage
  directly: the two connector-overload patterns (S15/S16) turned samples
  that were previously unflagged into the two strongest rewrites
  (01: 4.83→0.75, 02: 6.25→0.93).
- The residual weakness is concentrated in "model abstinence" on
  heuristic-only issue sets (03/04/08). The round-2→3 fixes (retryable
  heuristics + no-empty-array prompt) target exactly this; round 3 will
  re-measure and update the tables above.
- Known remaining limitation: the connector vocabulary is a fixed list;
  discovering *new* mechanical phrasings requires periodically extending
  `patterns/humanizer.yml` (or the `-deep` LLM judge for semantic cases).
