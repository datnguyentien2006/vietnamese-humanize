# -*- coding: utf-8 -*-
"""Print a per-sample dashboard from evaluation/results/*.json (root or round*/)."""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
d = Path(__file__).resolve().parents[1] / "evaluation" / "results"
# legacy layout (results/*.json) plus tagged rounds (results/roundN/)
paths = sorted(d.glob("sample*.json")) + sorted(d.glob("*/sample*.json"))
for f in paths:
    r = json.loads(f.read_text(encoding="utf-8"))
    s = r["static"]
    j = r.get("llm_judge", {})
    if "error" in j:
        judge = "ERROR"
    elif j.get("skipped"):
        judge = "skipped"
    else:
        judge = "nat={} mp={} tone={}".format(
            j.get("naturalness"), j.get("meaning_preserved"), j.get("tone_preserved")
        )
    st = r["rewrite_stats"]
    tag = f.parent.name if f.parent.name != "results" else "root"
    print(
        "[{}] {:<34} rob {}->{}  lint {}->{}  stdevD {:+}  meaning {}  fixed={}/{} rej={}  judge {}".format(
            tag,
            r["file"][:34],
            s["robotic_density_before"],
            s["robotic_density_after"],
            s["lint_issues_before"],
            s["lint_issues_after"],
            s["sentence_len_stdev_delta"],
            s["meaning"]["score"],
            st["fixed"],
            st["total_issues"],
            st["edits_rejected"],
            judge,
        )
    )
    m = s["meaning"]
    if m["entities_missing"]:
        print("   MISSING:", m["entities_missing"][:6])
    if isinstance(j, dict) and j.get("factual_losses"):
        print("   judge_losses:", j["factual_losses"][:4])
    if isinstance(j, dict) and j.get("unnatural_phrases"):
        print("   unnatural:", j["unnatural_phrases"][:5])
    if isinstance(j, dict) and j.get("error"):
        print("   judge_error:", str(j["error"])[:140])
