"""Thin wrapper around Claude Code CLI headless mode.

Every agent in this project (baseline and pipeline stages) runs through
run_agent(), so all of them get identical plumbing: the same model, a
sandboxed working directory, an explicit tool allowlist, and a stream-json
trajectory captured to disk (submission deliverable #4).
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

DEFAULT_MODEL = os.environ.get("REVGUARD_MODEL", "sonnet")


class AgentError(Exception):
    pass


def run_agent(prompt, *, system_prompt=None, cwd=None, allowed_tools=(),
              model=None, trajectory_path=None, timeout=900, retries=2):
    """Run one headless Claude Code agent. Returns a dict with
    text (final response), cost_usd, seconds, num_turns.

    Transient failures (rate limits, network) are retried with backoff so
    a long unattended sweep survives blips."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            return _run_agent_once(
                prompt, system_prompt=system_prompt, cwd=cwd,
                allowed_tools=allowed_tools, model=model,
                trajectory_path=trajectory_path, timeout=timeout,
            )
        except (AgentError, subprocess.TimeoutExpired) as e:
            last_err = e
            if attempt < retries:
                time.sleep(20 * (attempt + 1))
    raise AgentError(f"failed after {retries + 1} attempts: {last_err}")


def _run_agent_once(prompt, *, system_prompt=None, cwd=None, allowed_tools=(),
                    model=None, trajectory_path=None, timeout=900):
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--model", model or DEFAULT_MODEL,
        # Full isolation: no user/project settings, no MCP, file tools
        # confined to cwd, only the tools we name.
        "--restricted", "--strict-mcp-config",
        "--tools", ",".join(allowed_tools) if allowed_tools else "",
    ]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    start = time.time()
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )
    elapsed = round(time.time() - start, 1)
    if trajectory_path:
        Path(trajectory_path).parent.mkdir(parents=True, exist_ok=True)
        Path(trajectory_path).write_text(proc.stdout)
    if proc.returncode != 0:
        raise AgentError(
            f"claude exited {proc.returncode}: {proc.stderr[-800:]}"
        )
    result = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            result = event
    if result is None or result.get("subtype") != "success":
        raise AgentError(f"no successful result event (last: {result})")
    return {
        "text": result.get("result", ""),
        "cost_usd": result.get("total_cost_usd"),
        "seconds": elapsed,
        "num_turns": result.get("num_turns"),
    }


_JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def extract_json(text):
    """Parse the last ```json fenced block (or a bare JSON body) from a
    response. Raises AgentError when nothing parses."""
    blocks = _JSON_BLOCK.findall(text)
    candidates = list(reversed(blocks)) + [text.strip()]
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    # Last resort: first {...} span.
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise AgentError(f"could not extract JSON from response:\n{text[:500]}")
