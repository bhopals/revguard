#!/usr/bin/env python3
"""RevGuard CLI — review a real git repository's changes.

Examples:
  # Review working-tree changes against main:
  python3 revguard.py --repo ~/code/myproject --base main

  # Review a branch or PR head against its merge base:
  python3 revguard.py --repo ~/code/myproject --base main --head feature/x

Output goes to ./reviews/<repo>-<timestamp>/: findings.json, report.md,
report.html, and the full agent trajectories.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from agent.run import review_diff, write_report  # noqa: E402
from agent.html_report import write_html_report  # noqa: E402


def git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def snapshot(repo, head, dest):
    """Materialize the post-change tree at dest (no .git)."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if head:
        tar = subprocess.Popen(["git", "-C", str(repo), "archive", head],
                               stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(dest)], stdin=tar.stdout,
                       check=True)
        tar.wait()
    else:
        shutil.copytree(
            repo, dest, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "node_modules", ".venv", "venv",
                ".pytest_cache", "*.pyc"),
        )
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="path to a git repository")
    ap.add_argument("--base", required=True, help="base ref to diff against")
    ap.add_argument("--head", help="head ref (default: working tree)")
    ap.add_argument("--config", default="v5",
                    help="pipeline config (default v5, the final one)")
    ap.add_argument("--title", help="PR title (default: from last commit)")
    ap.add_argument("--description", default="", help="PR description")
    ap.add_argument("--out", default="reviews", help="output root")
    ap.add_argument("--paths", nargs="*", default=None,
                    help="limit the review to these pathspecs (e.g. src/"
                         " ':(exclude)vendor/'), passed to git diff")
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        sys.exit(f"{repo} is not a git repository")

    rev_range = f"{args.base}...{args.head}" if args.head else args.base
    pathspec = ["--"] + args.paths if args.paths else []
    diff = git(repo, "diff", rev_range, *pathspec)
    if not diff.strip():
        sys.exit("no changes to review")
    files = git(repo, "diff", "--name-only", rev_range, *pathspec).split()
    title = args.title or git(
        repo, "log", "-1", "--format=%s",
        args.head or "HEAD").strip() or "Working tree changes"

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / f"{repo.name}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reviewing {repo.name} [{rev_range}]: {len(files)} files,"
          f" {len(diff.splitlines())} diff lines (config {args.config})")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = snapshot(repo, args.head, Path(tmp) / "work")
        result = review_diff(
            args.config, title, args.description, diff, files, workdir,
            lambda dest: snapshot(repo, args.head, dest),
            out_dir / "trajectories",
        )

    meta = {"title": title, "pr_description": args.description or rev_range}
    (out_dir / "findings.json").write_text(json.dumps(result, indent=2))
    write_report(out_dir / "report.md", meta, result["findings"], args.config)
    write_html_report(out_dir / "report.html", meta, result)
    n = len(result["findings"])
    print(f"\n{n} confirmed finding(s)"
          f" ({result['raw_finding_count']} raw, {result['merged_count']}"
          f" after merge) in {result['seconds']}s, ${result['cost_usd']:.2f}")
    print(f"Report: {out_dir}/report.md (+ report.html, findings.json)")


if __name__ == "__main__":
    main()
