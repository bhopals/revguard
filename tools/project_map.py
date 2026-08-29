"""Print an annotated map of the project. Used for the demo's codebase tour
and as a quick orientation aid. Counts are computed live so they stay true.

    python3 tools/project_map.py      (or: make map)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count(glob, base=ROOT):
    return sum(1 for _ in base.glob(glob))


def loc(*globs):
    n = 0
    for g in globs:
        for f in ROOT.glob(g):
            n += sum(1 for _ in f.open())
    return n


def main():
    n_cases = count("cases/case*/meta.json") and count("cases/case*")
    n_pro = count("target_repo_pro/ledgerly/*.py")
    agent_loc = loc("agent/*.py", "agent/prompts/*.py")

    rows = [
        ("target_repo/", "the expense-tracker app under review (tiers 1-2)"),
        ("target_repo_pro/", f"the larger app for hard PRs (tier 3) — {n_pro} modules"),
        ("cases/", f"{n_cases} pull requests carrying 61 labeled, planted bugs"),
        ("agent/", f"THE PIPELINE — parallel reviewers + adversarial verifier ({agent_loc} LOC)"),
        ("  prompts/", "each agent's instructions (reviewer & verifier briefs)"),
        ("baseline/", "the fair comparison: one prompt, no tools, same model"),
        ("eval/", "fixed scoring rule, comparison table, dashboard"),
        ("tools/", "case utilities, benchmark validator, trajectory renderer"),
        ("replay/", "real escaped bugs from open-source (external validity)"),
        ("revguard.py", "THE PRODUCT — review any local repo or live GitHub PR"),
        ("results/", "every run's findings, timing, cost — the evidence"),
        ("trajectories/", "full agent transcripts (a required deliverable)"),
        ("tests/", "self-tests for the scoring harness itself"),
        ("docs/", "walkthrough, changelog, demo scripts, dashboard"),
        ("Makefile", "one command each: validate · baseline · agent · eval · test"),
    ]
    labels = [n.strip() for n, _ in rows]
    width = max(len(x) for x in labels) + 2
    print("\n  revguard/  —  an evidence-linked code-review agent + its benchmark\n")
    for i, (name, desc) in enumerate(rows):
        nested = name.startswith("  ")
        label = name.strip()
        if nested:
            prefix = "  │      └ "
            pad = width - 2
        else:
            prefix = "  └── " if i == len(rows) - 1 else "  ├── "
            pad = width
        print(f"{prefix}{label:<{pad}}{desc}")
    print()


if __name__ == "__main__":
    main()
