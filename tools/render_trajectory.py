"""Render a stream-json trajectory (.jsonl) as readable markdown.

Usage:
  python3 tools/render_trajectory.py trajectories/agent-v3/case01_csv_export/verifier_00.jsonl
  python3 tools/render_trajectory.py --all   # render every trajectory to .md next to it
"""

import json
import sys
from pathlib import Path

TRUNC = 1200


def _t(text, limit=TRUNC):
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"\n… [{len(text)-limit} chars truncated]"


def render(path):
    lines = [f"# Trajectory: `{Path(path).as_posix()}`", ""]
    for raw in Path(path).read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            lines += [f"**Session init** — model `{ev.get('model')}`, "
                      f"tools: {', '.join(ev.get('tools', [])) or 'none'}", ""]
        elif t == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    lines += ["**Assistant:**", "", _t(block["text"]), ""]
                elif block.get("type") == "tool_use":
                    args = json.dumps(block.get("input", {}))
                    lines += [f"**Tool call → {block.get('name')}**", "",
                              "```json", _t(args, 600), "```", ""]
        elif t == "user":
            for block in ev.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    if isinstance(content, list):
                        content = "\n".join(
                            c.get("text", "") for c in content
                            if isinstance(c, dict)
                        )
                    lines += ["**Tool result:**", "", "```",
                              _t(content or "(empty)", 800), "```", ""]
        elif t == "result":
            lines += ["---",
                      f"**Final result** ({ev.get('num_turns')} turns, "
                      f"{ev.get('duration_ms', 0)/1000:.1f}s, "
                      f"${ev.get('total_cost_usd', 0):.3f}):", "",
                      _t(ev.get("result", "")), ""]
    return "\n".join(lines)


def main():
    if "--all" in sys.argv:
        root = Path(__file__).resolve().parent.parent / "trajectories"
        for jl in sorted(root.rglob("*.jsonl")):
            jl.with_suffix(".md").write_text(render(jl))
            print(f"rendered {jl.with_suffix('.md').relative_to(root.parent)}")
    else:
        print(render(sys.argv[1]))


if __name__ == "__main__":
    main()
