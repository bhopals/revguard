"""Shared helpers for working with review cases.

A case directory looks like:

    cases/case01_csv_export/
        meta.json     case metadata + ground-truth defects (anchor-based)
        changed/      full post-PR versions of every file the PR touches,
                      mirroring target_repo's layout

Ground-truth defects reference an `anchor`: a substring unique within the
post-PR version of the file. Line numbers are resolved at scoring time, so
authored metadata can never drift out of sync with the code.
"""

import difflib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_REPO = ROOT / "target_repo"
CASES_DIR = ROOT / "cases"


def load_meta(case_dir):
    return json.loads((Path(case_dir) / "meta.json").read_text())


def target_repo_for(case_dir):
    """Tier 1/2 cases review target_repo; tier 3 reviews target_repo_pro
    (meta's `repo` field). Separate frozen repos keep earlier comparisons
    valid as the project grows."""
    return ROOT / load_meta(case_dir).get("repo", "target_repo")


def list_cases():
    return sorted(p for p in CASES_DIR.iterdir() if (p / "meta.json").exists())


def resolve_case(spec):
    """Turn a --case value into a real case directory. Accepts a full path
    ('cases/case21_perf_reports'), a bare case name ('case21_perf_reports'),
    or a substring/prefix that uniquely names one case ('case21', '21').
    Raises SystemExit with a helpful message otherwise."""
    p = Path(spec)
    if (p / "meta.json").exists():
        return p
    if (CASES_DIR / spec / "meta.json").exists():
        return CASES_DIR / spec
    names = [c.name for c in list_cases()]
    matches = [n for n in names
               if n == spec or n.startswith(spec)
               or spec in n or f"case{spec}" == n or n.startswith(f"case{spec}_")]
    if len(matches) == 1:
        return CASES_DIR / matches[0]
    import sys
    if not matches:
        sys.exit(f"no case matches {spec!r}. Available cases:\n  "
                 + "\n  ".join(names))
    sys.exit(f"{spec!r} is ambiguous — matches {matches}. Be more specific.")


def changed_files(case_dir):
    """Relative paths of every file the PR touches (added or modified)."""
    changed_root = Path(case_dir) / "changed"
    return sorted(
        str(p.relative_to(changed_root))
        for p in changed_root.rglob("*")
        if p.is_file()
    )


def build_workdir(case_dir, dest):
    """Materialize the post-PR repo: target_repo overlaid with changed/."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(target_repo_for(case_dir), dest,
                    ignore=shutil.ignore_patterns("__pycache__"))
    changed_root = Path(case_dir) / "changed"
    for rel in changed_files(case_dir):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(changed_root / rel, target)
    return dest


def make_diff(case_dir):
    """Unified diff of the PR: target_repo -> target_repo + changed/."""
    chunks = []
    changed_root = Path(case_dir) / "changed"
    repo = target_repo_for(case_dir)
    for rel in changed_files(case_dir):
        old_path = repo / rel
        old = old_path.read_text().splitlines(keepends=True) if old_path.exists() else []
        new = (changed_root / rel).read_text().splitlines(keepends=True)
        diff = difflib.unified_diff(
            old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3
        )
        chunks.append("".join(diff))
    return "\n".join(chunks)


def resolve_anchor(case_dir, rel_path, anchor):
    """Return the 1-based line number of `anchor` in the post-PR file.

    Files the PR touches resolve against changed/; a defect may also be
    validly reported in an untouched file (e.g. the aggregation a schema
    change breaks), which resolves against the case's target repo.

    Raises if the anchor is missing or ambiguous — that means the case
    metadata is broken and must be fixed before the eval can run.
    """
    changed_path = Path(case_dir) / "changed" / rel_path
    if changed_path.exists():
        text = changed_path.read_text()
    else:
        text = (target_repo_for(case_dir) / rel_path).read_text()
    hits = [i + 1 for i, line in enumerate(text.splitlines()) if anchor in line]
    if len(hits) != 1:
        raise ValueError(
            f"anchor {anchor!r} matched {len(hits)} lines in {rel_path}"
            f" (case {Path(case_dir).name})"
        )
    return hits[0]


def ground_truth(case_dir):
    """Ground-truth defects with anchors resolved to line numbers.

    Each defect carries `points`: every (file, line) location where
    reporting it is acceptable — the primary anchor plus any
    `alt_anchors` added during the label adjudication pass (see
    docs/CHANGELOG in the README). `file`/`line` remain the primary
    location for display.
    """
    meta = load_meta(case_dir)
    out = []
    for d in meta.get("defects", []):
        points = [(d["file"], resolve_anchor(case_dir, d["file"], d["anchor"]))]
        for alt in d.get("alt_anchors", []):
            points.append(
                (alt["file"], resolve_anchor(case_dir, alt["file"], alt["anchor"]))
            )
        out.append({
            "id": d["id"],
            "file": points[0][0],
            "line": points[0][1],
            "points": points,
            "category": d["category"],
            "severity": d["severity"],
            "description": d["description"],
        })
    return out
