"""Score every system's results directory and print the comparison table.

Usage: python3 eval/compare.py [results/baseline results/agent-v1 ...]
Defaults to every directory under results/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.score import score_results  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def collect(dirs):
    rows = []
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        rep = score_results(d)
        s = rep["summary"]
        secs = [c.get("seconds") for c in rep["per_case"] if c.get("seconds")]
        costs = [c.get("cost_usd") for c in rep["per_case"] if c.get("cost_usd")]
        n = sum(1 for c in rep["per_case"] if "status" not in c)
        rows.append({
            "system": d.name,
            "cases": n,
            "recall": s["recall"],
            "precision": s["precision"],
            "f1": s["f1"],
            "found": f"{s['found']}/{s['ground_truth_defects']}",
            "fp": s["false_positives"],
            "clean_fp": s["clean_case_false_positives"],
            "avg_s": round(sum(secs) / len(secs), 1) if secs else None,
            "avg_cost": round(sum(costs) / len(costs), 3) if costs else None,
        })
    return rows


def main():
    dirs = sys.argv[1:] or sorted(
        p for p in (ROOT / "results").iterdir() if p.is_dir()
    )
    rows = collect(dirs)
    cols = ["system", "cases", "found", "recall", "precision", "f1",
            "fp", "clean_fp", "avg_s", "avg_cost"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")


if __name__ == "__main__":
    main()
