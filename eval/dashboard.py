"""Generate docs/dashboard.html: the full evaluation at a glance.

Deterministic render of results/ — comparison table, per-case grid, and
verifier attribution. Usage:
    python3 eval/dashboard.py results/baseline results/agent-v1 ...
Defaults to every directory under results/.
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.compare import collect  # noqa: E402
from eval.score import score_results  # noqa: E402
from tools.case_utils import list_cases, load_meta  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

STYLE = """
:root { color-scheme: light dark; --fg:#1c1c1c; --bg:#fbfaf8; --card:#fff;
 --muted:#666; --line:#e3ded6; --good:#2e7d32; --warn:#e65100; --bad:#c62828; }
@media (prefers-color-scheme: dark){ :root { --fg:#e8e6e3; --bg:#16181d;
 --card:#1f232b; --muted:#9aa0a6; --line:#333944; } }
body { font:15px/1.5 -apple-system,"Segoe UI",sans-serif; margin:0;
 color:var(--fg); background:var(--bg); }
main { max-width:1100px; margin:0 auto; padding:36px 24px 80px; }
h1 { font-size:24px; } h2 { font-size:18px; margin-top:36px; }
.tablewrap { overflow-x:auto; }
table { border-collapse:collapse; background:var(--card); font-size:13.5px; }
th,td { border:1px solid var(--line); padding:6px 10px; text-align:right; }
th:first-child, td:first-child { text-align:left; }
th { background:transparent; color:var(--muted); font-weight:600; }
.best { font-weight:700; color:var(--good); }
.miss { color:var(--bad); } .ok { color:var(--good); }
.note { color:var(--muted); font-size:13px; }
"""


def fmt_cell(found, gt, fp, clean):
    if clean:
        cls = "ok" if fp == 0 else "miss"
        return f'<td class="{cls}">{"clean" if fp == 0 else f"{fp} FP"}</td>'
    cls = "ok" if found == gt and fp == 0 else ("miss" if found < gt else "")
    extra = f" +{fp}fp" if fp else ""
    return f'<td class="{cls}">{found}/{gt}{extra}</td>'


def main():
    dirs = [Path(d) for d in sys.argv[1:]] or sorted(
        p for p in (ROOT / "results").iterdir() if p.is_dir())
    rows = collect(dirs)
    best_f1 = max(r["f1"] for r in rows)

    head = ("<tr><th>system</th><th>cases</th><th>found</th><th>recall</th>"
            "<th>precision</th><th>F1</th><th>FPs</th><th>clean-PR FPs</th>"
            "<th>avg s/case</th><th>avg $/case</th></tr>")
    body = "".join(
        "<tr><td>{system}</td><td>{cases}</td><td>{found}</td>"
        "<td>{recall}</td><td>{precision}</td>"
        "<td class=\"{cls}\">{f1}</td><td>{fp}</td><td>{clean_fp}</td>"
        "<td>{avg_s}</td><td>{avg_cost}</td></tr>".format(
            cls="best" if r["f1"] == best_f1 else "", **r)
        for r in rows)

    cases = list_cases()
    grid_head = ("<tr><th>case</th><th>tier</th><th>GT</th>"
                 + "".join(f"<th>{html.escape(d.name)}</th>" for d in dirs)
                 + "</tr>")
    reports = {d.name: score_results(d)["per_case"] for d in dirs}
    grid_rows = []
    for case in cases:
        meta = load_meta(case)
        gt_n = len(meta.get("defects", []))
        tier = meta.get("tier", 1)
        cells = []
        for d in dirs:
            pc = next((c for c in reports[d.name]
                       if c.get("case") == meta["id"]), None)
            if pc is None or "status" in pc:
                cells.append("<td>—</td>")
            else:
                cells.append(fmt_cell(pc["found"], pc["gt"],
                                      pc["false_positives"], pc["clean"]))
        label = meta["id"] + (" (clean)" if meta["clean"] else "")
        grid_rows.append(f"<tr><td>{html.escape(label)}</td><td>{tier}</td>"
                         f"<td>{gt_n}</td>{''.join(cells)}</tr>")

    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RevGuard Benchmark Dashboard</title><style>{STYLE}</style></head>
<body><main>
<h1>RevGuard — seeded-defect benchmark results</h1>
<p class="note">22 PR cases against the Ledgerly codebase (tiers 1-2: small
PRs, tier 3: large multi-file PRs on the expanded app), 61 anchor-labeled
defects, 2 clean PRs. All systems run the same model; matching rule fixed in
eval/score.py. Every number traces to a JSON file in results/.</p>
<h2>System comparison</h2>
<div class="tablewrap"><table>{head}{body}</table></div>
<h2>Per-case results (found/ground-truth, +false positives)</h2>
<div class="tablewrap"><table>{grid_head}{''.join(grid_rows)}</table></div>
</main></body></html>"""
    out = ROOT / "docs" / "dashboard.html"
    out.write_text(doc)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
