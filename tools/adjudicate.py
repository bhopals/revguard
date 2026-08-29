"""List every false positive and miss across result dirs, for label
adjudication. The adjudication policy (fixed before round 2):

1. A finding that describes a ground-truth defect's behavior but points
   at a different-but-defensible location gets an alternate anchor.
2. A finding that identifies a GENUINE defect our labels lack gets
   promoted to ground truth (with a note), whichever system found it.
3. Advisory comments ("add tests for X", "consider validating") stay
   false positives — unless the text concretely states the defect's
   failure behavior, in which case rule 1/2 applies.
4. All changes apply to every system retroactively; nothing is ever
   removed from ground truth after a system has found it.

Usage: python3 tools/adjudicate.py results/baseline results/agent-v5 ...
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.score import match_case  # noqa: E402
from tools.case_utils import ground_truth, list_cases, load_meta  # noqa: E402


def main():
    for system_dir in sys.argv[1:]:
        system_dir = Path(system_dir)
        print(f"\n======== {system_dir.name} ========")
        for case in list_cases():
            meta = load_meta(case)
            rf = system_dir / f"{meta['id']}.json"
            if not rf.exists():
                continue
            gt = ground_truth(case)
            data = json.loads(rf.read_text())
            matched, fps = match_case(gt, data.get("findings", []))
            for d in gt:
                if d["id"] not in matched:
                    print(f"MISS {meta['id']} {d['id']}"
                          f" (gt {d['file']}:{d['line']}) {d['description'][:70]}")
            for f in fps:
                print(f"FP   {meta['id']} {f.get('file')}:{f.get('line')}"
                      f" [{f.get('category')}] {f.get('title', '')[:78]}")
                desc = str(f.get("description", ""))[:160]
                print(f"       {desc}")


if __name__ == "__main__":
    main()
