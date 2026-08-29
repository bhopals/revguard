"""Baseline reviewer: one direct prompt, diff pasted inline, no tools.

This is the honest representation of how the task is commonly handled
today: paste the PR diff into an LLM chat and ask for a review. Same
model as the agent pipeline, same cases, same output schema.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.runtime import extract_json, run_agent  # noqa: E402
from tools.case_utils import load_meta, make_diff  # noqa: E402

PROMPT_TEMPLATE = """You are reviewing a pull request for the Ledgerly expense-tracking service (Python, sqlite, stdlib only).

PR title: {title}
PR description: {description}

Review the diff below and report every genuine defect you find (bugs, security vulnerabilities, robustness problems, inadequate tests). Do not report style nits.

Respond with ONLY a JSON object in this exact schema:
{{"findings": [{{"file": "path/relative/to/repo", "line": <line number in the new version of the file>, "category": "correctness|security|robustness|test-adequacy", "severity": "critical|major|minor", "title": "<short>", "description": "<what is wrong and why it matters>"}}]}}

If the diff has no defects, return {{"findings": []}}.

--- DIFF ---
{diff}
"""


def review_case(case_dir, out_dir, traj_dir):
    import os
    quiet = bool(os.environ.get("REVGUARD_QUIET"))
    meta = load_meta(case_dir)
    diff = make_diff(case_dir)
    prompt = PROMPT_TEMPLATE.format(
        title=meta["title"], description=meta["pr_description"], diff=diff,
    )
    if not quiet:
        print(f"  BASELINE — one prompt, diff pasted inline, NO tools, NO "
              f"verifier. Reviewing '{meta['title']}'…", flush=True)
    with tempfile.TemporaryDirectory() as empty:
        res = run_agent(
            prompt,
            allowed_tools=(),  # no tools: pure single-prompt review
            cwd=empty,  # empty sandbox so no repo context leaks in
            trajectory_path=Path(traj_dir) / f"{meta['id']}.jsonl",
        )
    findings = extract_json(res["text"]).get("findings", [])
    if not quiet:
        for f in findings:
            print(f"      · {f.get('file')}:{f.get('line')} "
                  f"[{f.get('severity')}] {str(f.get('title',''))[:56]}", flush=True)
    out = {
        "case": meta["id"],
        "system": "baseline",
        "findings": findings,
        "seconds": res["seconds"],
        "cost_usd": res["cost_usd"],
        "num_turns": res["num_turns"],
    }
    out_path = Path(out_dir) / f"{meta['id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"{meta['id']}: {len(findings)} findings"
          f" ({res['seconds']}s, ${res['cost_usd']:.2f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="single case: a path, a bare name, or a"
                    " unique prefix (e.g. cases/case21_perf_reports, case21)")
    ap.add_argument("--out", default=str(ROOT / "results" / "baseline"))
    ap.add_argument("--traj", default=str(ROOT / "trajectories" / "baseline"))
    ap.add_argument("--force", action="store_true", help="re-run existing")
    args = ap.parse_args()

    from tools.case_utils import list_cases, resolve_case
    cases = [resolve_case(args.case)] if args.case else list_cases()
    for case in cases:
        meta = load_meta(case)
        if not args.force and (Path(args.out) / f"{meta['id']}.json").exists():
            print(f"{meta['id']}: cached, skipping")
            continue
        review_case(case, args.out, args.traj)


if __name__ == "__main__":
    main()
