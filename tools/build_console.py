"""Build the RevGuard Console — a single self-contained HTML app that
visualizes every run, finding, and verification trace, reading only the
committed results/ and trajectories/. Data is inlined into the page so it
works offline via file:// with no server. Regenerate with `make console`.

    python3 tools/build_console.py   ->   docs/console.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.score import match_case  # noqa: E402
from eval.compare import collect  # noqa: E402
from tools.case_utils import (  # noqa: E402
    ground_truth, list_cases, load_meta, make_diff,
)

RESULTS = ROOT / "results"
TRAJ = ROOT / "trajectories"
DETAIL_SYSTEMS = ["baseline", "agent-v5"]   # full case detail for these
TRACE_SYSTEM = "agent-v5"                    # verification traces from here
ALL_SYSTEMS = ["baseline", "agent-v1", "agent-v2", "agent-v3", "agent-v4",
               "agent-v5"]


def _trunc(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + f"\n… (+{len(s)-n} chars)"


def distill_trajectory(path):
    """Turn a stream-json .jsonl into a compact list of steps the UI can
    render: assistant text, tool calls (name + key input), tool results."""
    steps = []
    if not path.exists():
        return steps
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    steps.append({"k": "say", "text": _trunc(b["text"], 900)})
                elif b.get("type") == "tool_use":
                    inp = b.get("input", {})
                    key = (inp.get("command") or inp.get("file_path")
                           or inp.get("pattern") or json.dumps(inp))
                    steps.append({"k": "tool", "name": b.get("name"),
                                  "arg": _trunc(key, 300)})
        elif t == "user":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "\n".join(x.get("text", "") for x in c
                                      if isinstance(x, dict))
                    steps.append({"k": "out", "text": _trunc(c, 700)})
        elif t == "result":
            steps.append({"k": "done",
                          "turns": ev.get("num_turns"),
                          "cost": ev.get("total_cost_usd"),
                          "secs": round(ev.get("duration_ms", 0) / 1000, 1)})
    return steps


def hits_truth(finding, gt):
    from eval.score import _hits
    return any(_hits(finding, d) for d in gt)


def tier_stats(system, cases, tier_filter):
    g = m = fp = 0
    for cdir in cases:
        meta = load_meta(cdir)
        if not tier_filter(meta.get("tier", 1)):
            continue
        rf = RESULTS / system / f"{meta['id']}.json"
        if not rf.exists():
            continue
        gt = ground_truth(cdir)
        matched, fps = match_case(gt, json.loads(rf.read_text()).get("findings", []))
        g += len(gt); m += len(matched); fp += len(fps)
    recall = m / g if g else 0
    prec = m / (m + fp) if (m + fp) else 0
    f1 = 2 * prec * recall / (prec + recall) if (prec + recall) else 0
    return {"found": m, "gt": g, "recall": round(recall, 2),
            "precision": round(prec, 2), "f1": round(f1, 3), "fp": fp}


def build():
    cases = list_cases()
    comparison = collect([RESULTS / s for s in ALL_SYSTEMS
                          if (RESULTS / s).is_dir()])
    tier3 = {s: tier_stats(s, cases, lambda t: t == 3)
             for s in ("baseline", "agent-v5")}

    case_index = []
    case_detail = {}      # case_id -> {meta, diff, systems:{sys:{...}}}
    for cdir in cases:
        meta = load_meta(cdir)
        cid = meta["id"]
        gt = ground_truth(cdir)
        diff = make_diff(cdir)
        case_index.append({
            "id": cid, "title": meta["title"], "tier": meta.get("tier", 1),
            "clean": meta["clean"], "gt": len(gt),
            "pr_description": meta["pr_description"],
        })
        systems = {}
        for sysname in DETAIL_SYSTEMS:
            rf = RESULTS / sysname / f"{cid}.json"
            if not rf.exists():
                continue
            data = json.loads(rf.read_text())
            findings = data.get("findings", [])
            matched, fps = match_case(gt, findings)
            for f in findings:
                f["_true"] = hits_truth(f, gt)
                # attach distilled trace for the trace system's confirmed findings
                f["_trace"] = None
            # attach traces (verifier_NN) for the trace system, by index
            if sysname == TRACE_SYSTEM:
                tdir = TRAJ / sysname / cid
                for i, f in enumerate(findings):
                    vp = tdir / f"verifier_{i:02d}.jsonl"
                    f["_trace"] = distill_trajectory(vp)
            missed = [d["id"] for d in gt if d["id"] not in matched]
            systems[sysname] = {
                "findings": findings,
                "rejected": data.get("rejected_findings", []),
                "stages": data.get("stages", []),
                "seconds": data.get("seconds"),
                "cost_usd": data.get("cost_usd"),
                "raw": data.get("raw_finding_count"),
                "found": len(matched), "missed": missed,
                "false_positives": len(fps),
            }
        case_detail[cid] = {
            "meta": {"title": meta["title"], "tier": meta.get("tier", 1),
                     "clean": meta["clean"],
                     "pr_description": meta["pr_description"],
                     "defects": [{"id": d["id"], "file": d["file"],
                                  "line": d["line"], "severity": d["severity"],
                                  "category": d["category"],
                                  "description": d["description"]}
                                 for d in gt]},
            "diff": diff,
            "systems": systems,
        }

    payload = {
        "comparison": comparison,
        "tier3": tier3,
        "cases": case_index,
        "detail": case_detail,
        "detail_systems": DETAIL_SYSTEMS,
    }
    data_json = json.dumps(payload, separators=(",", ":"))

    template = (ROOT / "tools" / "console_template.html").read_text()
    html = template.replace("/*__DATA__*/null", data_json)
    out = ROOT / "docs" / "console.html"
    out.write_text(html)
    size = out.stat().st_size / 1024
    print(f"wrote {out}  ({size:.0f} KB, {len(cases)} cases, "
          f"{len(ALL_SYSTEMS)} systems)")


if __name__ == "__main__":
    build()
