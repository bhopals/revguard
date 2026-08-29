"""RevGuard orchestrator.

Configs map to the improvement changelog — each iteration is reproducible:

  v1  one generalist reviewer with repo tools (context + tools)
  v2  three parallel specialist reviewers (orchestration)
  v3  v2 + adversarial verifier that must fail to falsify each finding
  v4  v3 + a nitpick/code-quality reviewer (the experiment we evaluate)

Usage:
  python3 agent/run.py --config v3                 # all cases
  python3 agent/run.py --config v3 --case cases/case01_csv_export
"""

import argparse
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.runtime import AgentError, extract_json, run_agent  # noqa: E402
from agent.prompts.specialists import SPECIALISTS, SPECIALISTS_V2  # noqa: E402
from tools.case_utils import build_workdir, list_cases, load_meta, make_diff  # noqa: E402

PROMPTS = ROOT / "agent" / "prompts"
VERIFIER_PROMPT = (PROMPTS / "verifier.md").read_text()

# `common` picks the base reviewer brief: reviewer_common.md is the original
# conservative calibration (v1-v4, kept frozen for reproducibility);
# reviewer_common_v2.md is the recall-tuned calibration introduced in v5
# after measuring that conservative reviewers starve the verifier.
CONFIGS = {
    "v1": {"specialists": ["generalist"], "verify": False,
           "common": "reviewer_common.md"},
    "v2": {"specialists": ["correctness", "security", "tests"], "verify": False,
           "common": "reviewer_common.md"},
    "v3": {"specialists": ["correctness", "security", "tests"], "verify": True,
           "common": "reviewer_common.md"},
    "v4": {"specialists": ["correctness", "security", "tests", "nitpick"],
           "verify": True, "common": "reviewer_common.md"},
    "v5": {"specialists": ["correctness", "security", "tests"], "verify": True,
           "common": "reviewer_common_v2.md", "specialist_set": "v2"},
}

REVIEW_TASK = """Review this pull request.

PR title: {title}
PR description: {description}

Files changed: {files}

--- DIFF (old -> new) ---
{diff}
--- END DIFF ---

The full post-PR repository is in your working directory. Investigate as needed, then output your findings JSON."""

VERIFY_TASK = """A reviewer reported this finding on the pull request described below. Attack it.

PR title: {title}
Finding under review:
{finding}

--- DIFF (old -> new) ---
{diff}
--- END DIFF ---

The full post-PR repository is in your working directory. Try to falsify the claim (prefer execution), then output your verdict JSON."""


def _line_of(f):
    try:
        return int(f.get("line", -999))
    except (TypeError, ValueError):
        return -999


def dedupe(findings):
    """Merge findings that point at the same file within 3 lines."""
    kept = []
    for f in sorted(findings, key=lambda x: ({"critical": 0, "major": 1,
                                              "minor": 2}.get(x.get("severity"), 3))):
        if any(k.get("file") == f.get("file")
               and abs(_line_of(k) - _line_of(f)) <= 3
               for k in kept):
            continue
        kept.append(f)
    return kept


def run_specialist(name, common_prompt, title, description, diff, files,
                   workdir, traj_dir, specialist_set="v1"):
    briefs = SPECIALISTS_V2 if specialist_set == "v2" else SPECIALISTS
    prompt = REVIEW_TASK.format(
        title=title, description=description,
        files=", ".join(files), diff=diff,
    )
    res = run_agent(
        prompt,
        system_prompt=common_prompt + "\n" + briefs[name],
        cwd=workdir,
        allowed_tools=("Read", "Grep", "Glob"),
        trajectory_path=Path(traj_dir) / f"reviewer_{name}.jsonl",
    )
    findings = extract_json(res["text"]).get("findings", [])
    for f in findings:
        f["reviewer"] = name
    return findings, res


def run_verifier(finding, title, diff, make_sandbox, traj_dir, idx):
    """Each verification runs in a FRESH copy of the repo so one verifier's
    scratch files or edits can never contaminate another's evidence."""
    with tempfile.TemporaryDirectory() as tmp:
        work = make_sandbox(Path(tmp) / "repo")
        prompt = VERIFY_TASK.format(
            title=title,
            finding=json.dumps(finding, indent=2),
            diff=diff,
        )
        res = run_agent(
            prompt,
            system_prompt=VERIFIER_PROMPT,
            cwd=work,
            allowed_tools=("Read", "Grep", "Glob", "Bash"),
            trajectory_path=Path(traj_dir) / f"verifier_{idx:02d}.jsonl",
        )
    verdict = extract_json(res["text"])
    return verdict, res


def review_diff(config_name, title, description, diff, files, workdir,
                make_sandbox, traj_dir):
    """Run the full pipeline on one diff. Transport-agnostic core shared by
    the benchmark runner and the real-repo CLI. Returns a result dict."""
    cfg = CONFIGS[config_name]
    common_prompt = (PROMPTS / cfg["common"]).read_text()
    traj_dir = Path(traj_dir)
    traj_dir.mkdir(parents=True, exist_ok=True)

    total_cost, total_seconds = 0.0, 0.0
    stage_meta = []

    # Stage 1: reviewers in parallel.
    all_findings = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {
            pool.submit(run_specialist, name, common_prompt, title,
                        description, diff, files, workdir, traj_dir,
                        cfg.get("specialist_set", "v1")): name
            for name in cfg["specialists"]
        }
        for fut in futs:
            name = futs[fut]
            try:
                findings, res = fut.result()
            except AgentError as e:
                print(f"  [{title}] reviewer {name} FAILED: {e}")
                stage_meta.append({"stage": f"reviewer_{name}", "error": str(e)})
                continue
            all_findings += findings
            total_cost += res["cost_usd"] or 0
            total_seconds = max(total_seconds, res["seconds"])  # parallel
            stage_meta.append({"stage": f"reviewer_{name}",
                               "findings": len(findings),
                               "seconds": res["seconds"],
                               "cost_usd": res["cost_usd"]})

    merged = dedupe(all_findings)

    # Stage 2: adversarial verification (parallel, fresh sandbox each).
    rejected = []
    if cfg["verify"] and merged:
        verify_seconds = 0.0
        confirmed = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = {
                pool.submit(run_verifier, f, title, diff, make_sandbox,
                            traj_dir, i): (i, f)
                for i, f in enumerate(merged)
            }
            for fut in futs:
                i, f = futs[fut]
                try:
                    verdict, res = fut.result()
                except AgentError as e:
                    print(f"  [{title}] verifier {i} FAILED ({e});"
                          " keeping finding unverified")
                    f["verification"] = {"verdict": "UNVERIFIED",
                                         "evidence": str(e)}
                    confirmed.append(f)
                    continue
                total_cost += res["cost_usd"] or 0
                verify_seconds = max(verify_seconds, res["seconds"])
                f["verification"] = verdict
                if verdict.get("verdict") == "CONFIRMED":
                    if verdict.get("adjusted_severity"):
                        f["severity"] = verdict["adjusted_severity"]
                    confirmed.append(f)
                else:
                    rejected.append(f)
        total_seconds += verify_seconds
        stage_meta.append({"stage": "verifier",
                           "in": len(merged), "confirmed": len(confirmed),
                           "seconds": verify_seconds})
        final = confirmed
    else:
        final = merged

    return {
        "findings": final,
        "rejected_findings": rejected,
        "raw_finding_count": len(all_findings),
        "merged_count": len(merged),
        "stages": stage_meta,
        "seconds": round(total_seconds, 1),
        "cost_usd": round(total_cost, 4),
    }


def review_case(case_dir, config_name, out_root, traj_root, work_root):
    from tools.case_utils import changed_files
    meta = load_meta(case_dir)
    diff = make_diff(case_dir)
    files = changed_files(case_dir)
    workdir = build_workdir(case_dir, Path(work_root) / meta["id"])

    result = review_diff(
        config_name, meta["title"], meta["pr_description"], diff, files,
        workdir, lambda dest: build_workdir(case_dir, dest),
        Path(traj_root) / meta["id"],
    )
    out = {"case": meta["id"], "system": f"agent-{config_name}", **result}
    out_dir = Path(out_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{meta['id']}.json").write_text(json.dumps(out, indent=2))
    write_report(out_dir / f"{meta['id']}_report.md", meta, out["findings"],
                 config_name)
    from agent.html_report import write_html_report
    write_html_report(out_dir / f"{meta['id']}_report.html", meta, out)
    print(f"{meta['id']}: {out['raw_finding_count']} raw"
          f" -> {out['merged_count']} merged -> {len(out['findings'])} final"
          f" ({out['seconds']}s, ${out['cost_usd']:.2f})")
    shutil.rmtree(workdir, ignore_errors=True)


SEV_ORDER = {"critical": 0, "major": 1, "minor": 2}


def write_report(path, meta, findings, config_name):
    lines = [
        f"# Code review: {meta['title']}",
        "",
        f"> {meta['pr_description']}",
        "",
    ]
    if not findings:
        lines += [
            "**Verdict: approve.** No blocking defects found. Every hypothesis "
            "raised during review was either confirmed fixed in the diff or "
            "rejected under verification.",
        ]
    else:
        crit = sum(1 for f in findings if f.get("severity") == "critical")
        lines += [
            f"**Verdict: request changes.** {len(findings)} blocking finding(s), "
            f"{crit} critical.",
            "",
        ]
        for i, f in enumerate(
                sorted(findings, key=lambda x: SEV_ORDER.get(x.get("severity"), 3)), 1):
            lines += [
                f"## {i}. [{f.get('severity', '?').upper()}] {f.get('title', 'finding')}",
                "",
                f"`{f.get('file')}:{f.get('line')}` — {f.get('category')}",
                "",
                f.get("description", ""),
            ]
            ver = f.get("verification")
            if ver:
                lines += ["", f"*Verified: {ver.get('evidence', '')[:400]}*"]
            lines.append("")
    Path(path).write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=list(CONFIGS))
    ap.add_argument("--case", help="single case directory")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--run-name", help="results dir name (default"
                    " agent-<config>); use e.g. agent-v5-r2 for repeat runs")
    args = ap.parse_args()

    name = args.run_name or f"agent-{args.config}"
    out_root = ROOT / "results" / name
    traj_root = ROOT / "trajectories" / name
    work_root = Path(tempfile.gettempdir()) / f"revguard-work-{name}"

    cases = [Path(args.case)] if args.case else list_cases()
    for case in cases:
        meta = load_meta(case)
        if not args.force and (out_root / f"{meta['id']}.json").exists():
            print(f"{meta['id']}: cached, skipping")
            continue
        review_case(case, args.config, out_root, traj_root, work_root)


if __name__ == "__main__":
    main()
