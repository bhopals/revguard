# Reproduction guide

Written for a clean environment. Total runtime for the full reproduction is
roughly 35–50 minutes, most of it the v3 agent sweep; approximate API cost is
in the results table in the README (per-case cost is recorded in every result
JSON, so you can verify rather than trust this doc).

## Prerequisites

| Requirement | Version used | Notes |
|---|---|---|
| Python | 3.12 (3.10+ fine) | stdlib only, no pip install for the project itself |
| pytest | 8.x | `pip install pytest` — only dependency, used by the benchmark repos |
| Claude Code CLI | 2.1.251 | `npm install -g @anthropic-ai/claude-code`, logged in (subscription) or `ANTHROPIC_API_KEY` set |

Model: all systems (baseline and every agent config) run on the same model,
the CLI's `sonnet` alias (Claude Sonnet). Override with `REVGUARD_MODEL=<model>`
if you want to reproduce on a different model — but use the same one for
baseline and agent, or the comparison is meaningless.

Agents are launched with `--restricted --strict-mcp-config`: they ignore your
user/project Claude settings, cannot reach the network tools, and their file
tools are confined to a per-case sandbox copy of the benchmark repo. Nothing
in this project writes outside its own directory and temp dirs.

## Steps

```bash
cd revguard

# 1. Verify the benchmark itself: every anchor resolves, every post-PR
#    test suite passes (the premise: CI is green, bugs are hidden).
make validate            # ~1 min, no API calls

# 2. Baseline: one direct prompt per case, diff pasted inline, no tools.
make baseline            # ~15 min, 22 API calls

# 3. Final agent pipeline (v5): recall-tuned parallel specialists +
#    policy-gated adversarial verifier.
make agent               # ~45-60 min, ~$11 total

# 4. Score everything present under results/ with the fixed matching rule.
make eval
```

`make eval` prints the comparison table (recall / precision / F1 / false
positives / time / cost per system). Expected output: the table in the
README's Results section, within a small margin — LLM runs are not bit-for-bit
deterministic, so counts can shift by a finding or two; the ordering of the
systems should hold.

To reproduce the intermediate changelog iterations:

```bash
python3 agent/run.py --config v1   # single tooled reviewer, conservative
python3 agent/run.py --config v2   # parallel specialists, no verifier
python3 agent/run.py --config v3   # + truth-only verifier (the rubber stamp)
python3 agent/run.py --config v4   # the removed experiment (adds nitpick reviewer)
```

Repeat runs for variance use fresh result dirs:

```bash
python3 baseline/run.py --out results/baseline-r2 --traj trajectories/baseline-r2
python3 agent/run.py --config v5 --run-name agent-v5-r2
```

To review a real repository with the final pipeline (the tool itself):

```bash
python3 revguard.py --repo /path/to/repo --base main            # working tree
python3 revguard.py --repo /path/to/repo --base main --head br  # a branch
```

Every run writes:
- `results/<system>/<case>.json` — findings + timing + cost (scoring input)
- `results/<system>/<case>_report.md` — the human-facing review report
- `trajectories/<system>/<case>/*.jsonl` — full stream-json trajectory of
  every agent invocation (reviewers and verifiers), as submitted

Runs are cached per case; pass `--force` to re-run.

## Scoring rule (fixed before any system was measured)

A predicted finding matches a ground-truth defect if it names the same file
and its line is within 6 lines of the defect's anchor line (anchors are
unique code substrings resolved at scoring time — see `tools/case_utils.py`).
Category labels are reported but not required for a match. Each defect
matches at most once; every unmatched prediction is a false positive;
findings on the two clean-PR cases are false positives by definition. The
implementation is ~60 lines in `eval/score.py`.
