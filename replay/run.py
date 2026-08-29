"""Escaped-bug replay: run RevGuard (or the baseline) on real historical
open-source commits that introduced real bugs which escaped human review.

The post-PR tree of each commit is vendored under replay/vendor/<case>/
(MIT-licensed upstreams, license files included, provenance in
COMMIT.txt), together with the exact commit diff (pr.diff), so the
replay is fully offline-reproducible. cases.json records the known
escaped bug and where it was eventually fixed upstream.

Usage:
  python3 replay/run.py --case tinydb_445             # RevGuard v5
  python3 replay/run.py --case tinydb_445 --baseline  # one-prompt baseline
  python3 replay/run.py --all [--baseline]

Judging is deliberately simple and manual-verifiable: the script prints
every confirmed finding and whether any of them lands in the file that
contains the known escaped bug and mentions its key identifiers; the
final call is documented in replay/README.md with quotes.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.run import review_diff, write_report  # noqa: E402
from agent.html_report import write_html_report  # noqa: E402
from revguard import run_baseline  # noqa: E402

REPLAY = ROOT / "replay"
CASES = json.loads((REPLAY / "cases.json").read_text())


def make_workdir(case_id, dest):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(REPLAY / "vendor" / case_id, dest,
                    ignore=shutil.ignore_patterns("pr.diff", "COMMIT.txt",
                                                  "__pycache__"))
    return dest


def judge(meta, findings):
    bug = meta["escaped_bug"]
    hits = []
    for f in findings:
        in_file = any(str(f.get("file", "")).endswith(e)
                      for e in bug["expect_in"])
        text = (str(f.get("title", "")) + " "
                + str(f.get("description", ""))).lower()
        kw = sum(1 for k in bug["expect_keywords"] if k.lower() in text)
        if in_file and kw >= 1:
            hits.append(f)
    return hits


def run_case(case_id, baseline=False, config="v5"):
    meta = CASES[case_id]
    diff = (REPLAY / "vendor" / case_id / "pr.diff").read_text()
    system = "baseline" if baseline else config
    out_dir = REPLAY / "results" / f"{case_id}-{system}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {case_id} [{system}] — {meta['title']}")

    if baseline:
        result = run_baseline(meta["title"], meta["description"], diff,
                              out_dir)
    else:
        files = sorted({
            line[6:] for line in diff.splitlines()
            if line.startswith("+++ b/")
        })
        with tempfile.TemporaryDirectory() as tmp:
            workdir = make_workdir(case_id, Path(tmp) / "work")
            result = review_diff(
                config, meta["title"], meta["description"], diff, files,
                workdir, lambda dest: make_workdir(case_id, dest),
                out_dir / "trajectories",
            )

    rmeta = {"title": meta["title"], "pr_description": meta["description"]}
    (out_dir / "findings.json").write_text(json.dumps(result, indent=2))
    write_report(out_dir / "report.md", rmeta, result["findings"], system)
    write_html_report(out_dir / "report.html", rmeta, result)

    for f in result["findings"]:
        print(f"  finding: {f.get('file')}:{f.get('line')}"
              f" [{f.get('severity')}] {f.get('title')}")
    hits = judge(meta, result["findings"])
    verdict = "CAUGHT" if hits else "MISSED"
    print(f"  known escaped bug: {meta['escaped_bug']['summary'][:100]}...")
    print(f"  --> {verdict} the escaped bug"
          f" ({len(result['findings'])} confirmed finding(s),"
          f" {result['seconds']}s, ${result['cost_usd']:.2f})")
    return {"case": case_id, "system": system, "verdict": verdict,
            "findings": len(result["findings"]),
            "seconds": result["seconds"], "cost_usd": result["cost_usd"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=list(CASES))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--config", default="v5")
    args = ap.parse_args()
    ids = list(CASES) if args.all else [args.case]
    if ids == [None]:
        ap.error("pass --case or --all")
    summary = [run_case(c, args.baseline, args.config) for c in ids]
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
