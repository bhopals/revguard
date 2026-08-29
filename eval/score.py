"""Score a reviewer's findings against a case's ground truth.

Matching rule (fixed before any system was run, applied identically to
baseline and agent):

  A predicted finding matches a ground-truth defect when it names the same
  file and its line falls within LINE_TOLERANCE lines of the defect's
  anchor line. Category is reported but NOT required for a match — finding
  the bug matters more than labeling it.

  Each ground-truth defect can be matched at most once (extra duplicates
  are ignored, not penalized). Every unmatched prediction is a false
  positive. Predictions on clean cases are all false positives.

Metrics: precision, recall, F1 over all cases pooled; false positives on
clean PRs tracked separately as a signal-to-noise measure.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.case_utils import ground_truth, list_cases, load_meta  # noqa: E402

LINE_TOLERANCE = 6


def match_case(gt, findings):
    """Greedy match findings to ground truth. Returns (matched_ids, fp_list)."""
    remaining = {d["id"]: d for d in gt}
    matched = {}
    false_pos = []
    for f in findings:
        hit = None
        for did, d in remaining.items():
            if f.get("file") == d["file"] and abs(int(f.get("line", -999)) - d["line"]) <= LINE_TOLERANCE:
                hit = did
                break
        if hit is not None:
            matched[hit] = f
            del remaining[hit]
        else:
            # A duplicate report of an already-matched defect is not a FP.
            dup = any(
                f.get("file") == d["file"]
                and abs(int(f.get("line", -999)) - gd["line"]) <= LINE_TOLERANCE
                for did, d in matched.items()
                for gd in [next(g for g in gt if g["id"] == did)]
            )
            if not dup:
                false_pos.append(f)
    return matched, false_pos


def score_results(results_dir):
    """Aggregate scores for a results directory of <case_id>.json files."""
    results_dir = Path(results_dir)
    total_gt = total_matched = total_fp = total_pred = 0
    clean_fp = 0
    per_case = []
    for case in list_cases():
        meta = load_meta(case)
        gt = ground_truth(case)
        rf = results_dir / f"{meta['id']}.json"
        if not rf.exists():
            per_case.append({"case": meta["id"], "status": "MISSING"})
            continue
        data = json.loads(rf.read_text())
        findings = data.get("findings", [])
        matched, fps = match_case(gt, findings)
        total_gt += len(gt)
        total_matched += len(matched)
        total_fp += len(fps)
        total_pred += len(matched) + len(fps)
        if meta["clean"]:
            clean_fp += len(fps)
        per_case.append({
            "case": meta["id"],
            "clean": meta["clean"],
            "gt": len(gt),
            "found": len(matched),
            "missed": [d["id"] for d in gt if d["id"] not in matched],
            "false_positives": len(fps),
            "fp_titles": [f.get("title", f.get("description", ""))[:80] for f in fps],
            "seconds": data.get("seconds"),
            "cost_usd": data.get("cost_usd"),
        })
    precision = total_matched / total_pred if total_pred else 0.0
    recall = total_matched / total_gt if total_gt else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "summary": {
            "ground_truth_defects": total_gt,
            "found": total_matched,
            "false_positives": total_fp,
            "clean_case_false_positives": clean_fp,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        },
        "per_case": per_case,
    }


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "results/agent"
    report = score_results(results_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
