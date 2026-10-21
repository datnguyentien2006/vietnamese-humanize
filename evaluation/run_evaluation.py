# -*- coding: utf-8 -*-
"""Runner for the Vietnamese humanizer evaluation harness.

Pipeline:
  1. Load all self-authored AI-style samples in evaluation/samples/*.txt.
     Each sample carries YAML-ish front metadata (flavour, description).
  2. Humanize each sample with the REAL production path
     (web/backend generate_rewrite: lint -> Groq edits -> verified apply).
  3. Score: static metrics (metrics.py) + LLM-as-judge (judge.py).
  4. Write per-sample JSON + a summary to evaluation/results/.

Usage (from repo root):
    python evaluation/run_evaluation.py                 # all samples
    python evaluation/run_evaluation.py --sample s01    # one sample
    python evaluation/run_evaluation.py --no-judge      # static metrics only

The GROQ_API_KEY is read from web/backend/.env and never printed or
committed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for p in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "web" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation import judge, metrics  # noqa: E402
from vietnamese_writing_skills.cli.lint import lint_text  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def parse_sample(path: Path) -> dict:
    """Front matter: lines '---' separated; rest is the text."""
    raw = path.read_text(encoding="utf-8").strip()
    meta = {"file": path.name}
    text = raw
    if raw.startswith("---"):
        head, _, body = raw.partition("\n---\n")
        for line in head[3:].strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        text = body.strip()
    meta["text"] = text
    return meta


def humanize(text: str) -> dict:
    """Call the production rewrite service directly (no HTTP hop)."""
    from app.services.rewriter import generate_rewrite

    response = generate_rewrite(text, skill="humanizer-vi", issue_ids=None)
    return {
        "rewritten": response.rewrite,
        "stats": response.stats.model_dump(),
        "applied_edits": [e.model_dump() for e in response.applied_edits],
        "unresolved_issues": [u.model_dump() for u in response.unresolved_issues],
    }


def run_one(sample: dict, use_judge: bool) -> dict:
    original = sample["text"]
    issues_before = len(lint_text(original))
    t0 = time.time()
    result = humanize(original)
    elapsed = round(time.time() - t0, 1)
    rewritten = result["rewritten"]
    issues_after = len(lint_text(rewritten))

    record: dict = {
        "name": sample.get("name", sample["file"]),
        "file": sample["file"],
        "flavour": sample.get("flavour", "unknown"),
        "description": sample.get("description", ""),
        "original": original,
        "rewritten": rewritten,
        "rewrite_stats": result["stats"],
        "applied_edits": result["applied_edits"],
        "unresolved_issues": result["unresolved_issues"],
        "latency_seconds": elapsed,
        "static": metrics.static_report(original, rewritten, issues_before, issues_after),
        "llm_judge": judge.judge_pair(original, rewritten) if use_judge else {
            "skipped": True
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", help="only run this sample (matches file stem prefix)")
    parser.add_argument("--no-judge", action="store_true", help="skip LLM judge calls")
    parser.add_argument(
        "--tag",
        help="write results into results/<tag>/ instead of results/ "
        "(e.g. --tag roundN keeps each judging round on disk)",
    )
    args = parser.parse_args()

    samples = sorted((parse_sample(p) for p in SAMPLES_DIR.glob("*.txt")), key=lambda s: s["file"])
    if args.sample:
        samples = [s for s in samples if s["file"].startswith(args.sample)]
    if not samples:
        raise SystemExit("no samples matched")

    out_dir = RESULTS_DIR / args.tag if args.tag else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for s in samples:
        print(f"[run] {s['file']} ({s.get('flavour', '?')}) ...", flush=True)
        try:
            rec = run_one(s, use_judge=not args.no_judge)
        except Exception as exc:  # noqa: BLE001 - keep going, log failure
            rec = {
                "name": s.get("name", s["file"]),
                "file": s["file"],
                "flavour": s.get("flavour", "unknown"),
                "error": f"{type(exc).__name__}: {exc}",
                "original": s["text"],
            }
            print(f"  [error] {rec['error']}")
        records.append(rec)
        out = out_dir / f"{rec['file']}.json"
        out.write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = summarize(records)
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "n_samples": len(records),
                "summary": summary,
                "records_note": ("one JSON per sample in results/ (or results/<tag>/ with --tag), named <samplefile>.json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def summarize(records: list[dict]) -> dict:
    ok = [r for r in records if "error" not in r]
    failed = [r for r in records if "error" in r]
    judged = [r for r in ok if isinstance(r.get("llm_judge"), dict) and "error" not in r["llm_judge"] and not r["llm_judge"].get("skipped")]

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    meaning_scores = [r["static"]["meaning"]["score"] for r in ok]
    stdev_delta = [r["static"]["sentence_len_stdev_delta"] for r in ok]
    rob_before = [r["static"]["robotic_density_before"] for r in ok]
    rob_after = [r["static"]["robotic_density_after"] for r in ok]
    lint_before = [r["static"]["lint_issues_before"] for r in ok]
    lint_after = [r["static"]["lint_issues_after"] for r in ok]
    nat = [r["llm_judge"]["naturalness"] for r in judged]
    mp = [r["llm_judge"]["meaning_preserved"] for r in judged]
    tone = [r["llm_judge"]["tone_preserved"] for r in judged]
    return {
        "n_run": len(records),
        "n_failed": len(failed),
        "meaning_score_static": _mean(meaning_scores),
        "sentence_len_stdev_delta_mean": _mean(stdev_delta),
        "robotic_density_before": _mean(rob_before),
        "robotic_density_after": _mean(rob_after),
        "lint_issues_before": _mean([float(x) for x in lint_before]),
        "lint_issues_after": _mean([float(x) for x in lint_after]),
        "judge_naturalness": _mean(nat),
        "judge_meaning_preserved": _mean(mp),
        "judge_tone_preserved": _mean(tone),
        "judge_n": len(judged),
        "failed_files": [r["file"] for r in failed],
    }


if __name__ == "__main__":
    main()
