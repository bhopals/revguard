# RevGuard — reproduction entry points.
# Requires: Python 3.10+, pytest, Claude Code CLI (logged in). No other deps.

.PHONY: validate baseline agent eval test clean-results

# Sanity-check the benchmark: anchors resolve, every post-PR suite passes.
validate:
	python3 tools/validate_cases.py

# Run the single-prompt baseline over all 12 cases (cached; --force to redo).
baseline:
	python3 baseline/run.py

# Run the final agent pipeline (v3) over all 12 cases.
agent:
	python3 agent/run.py --config v3

# Score every system present under results/ and print the comparison table.
eval:
	python3 eval/compare.py

clean-results:
	rm -rf results trajectories

# Harness self-tests: scoring rules, dedupe, benchmark integrity.
test:
	python3 -m pytest tests/ -q
