"""Sanity-check every case: anchors resolve, post-PR test suite passes.

Run:  python3 tools/validate_cases.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.case_utils import (  # noqa: E402
    build_workdir, ground_truth, list_cases, load_meta, make_diff,
)


def main():
    failures = 0
    for case in list_cases():
        meta = load_meta(case)
        try:
            gt = ground_truth(case)
        except ValueError as e:
            print(f"FAIL {case.name}: {e}")
            failures += 1
            continue
        diff = make_diff(case)
        with tempfile.TemporaryDirectory() as tmp:
            work = build_workdir(case, Path(tmp) / "repo")
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=work, capture_output=True, text=True,
            )
        ok = proc.returncode == 0
        if not ok:
            print(f"FAIL {case.name}: post-PR tests failed")
            print(proc.stdout[-2000:])
            failures += 1
        else:
            kind = "clean" if meta["clean"] else f"{len(gt)} defects"
            print(f"ok   {case.name}: tests pass, {kind},"
                  f" diff {len(diff.splitlines())} lines")
    if failures:
        sys.exit(1)
    print("\nAll cases valid.")


if __name__ == "__main__":
    main()
