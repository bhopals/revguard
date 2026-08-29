"""Stage attribution: what did each pipeline stage contribute?

For a verified config, reports per-case and total: raw reviewer findings,
after-merge count, verifier verdicts (confirmed / rejected), and — joined
with ground truth — how many TRUE findings the verifier killed (recall
cost) vs FALSE findings it killed (precision gain).

Usage: python3 eval/stages.py results/agent-v3
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.score import _hits  # noqa: E402
from tools.case_utils import ground_truth, list_cases, load_meta  # noqa: E402


def main():
    results_dir = Path(sys.argv[1])
    tot = {"raw": 0, "merged": 0, "confirmed": 0, "rejected": 0,
           "killed_true": 0, "killed_false": 0}
    for case in list_cases():
        meta = load_meta(case)
        rf = results_dir / f"{meta['id']}.json"
        if not rf.exists():
            continue
        data = json.loads(rf.read_text())
        gt = ground_truth(case)
        tot["raw"] += data.get("raw_finding_count", 0)
        tot["merged"] += data.get("merged_count", 0)
        kept = data.get("findings", [])
        tot["confirmed"] += len(kept)
        # Rejected findings only exist in the stage metadata counts; to
        # attribute them we re-read verifier verdicts stored on findings.
        # Kept findings carry verification; rejected ones were dropped, so
        # reconstruct from stages: in - confirmed = rejected.
        for s in data.get("stages", []):
            if s.get("stage") == "verifier":
                rejected = s["in"] - s["confirmed"]
                tot["rejected"] += rejected
        # How many kept findings are true?
        for f in kept:
            true = any(_hits(f, d) for d in gt)
            f["_true"] = true
    # killed_true/false need the rejected findings themselves; those are in
    # trajectories but simplest source is: merged - kept, evaluated against
    # GT via the per-case JSON if present. We store rejected findings when
    # available under 'rejected_findings' (newer runs); older runs report
    # only counts.
    for case in list_cases():
        meta = load_meta(case)
        rf = results_dir / f"{meta['id']}.json"
        if not rf.exists():
            continue
        data = json.loads(rf.read_text())
        gt = ground_truth(case)
        for f in data.get("rejected_findings", []):
            if any(_hits(f, d) for d in gt):
                tot["killed_true"] += 1
            else:
                tot["killed_false"] += 1
    print(json.dumps(tot, indent=2))


if __name__ == "__main__":
    main()
