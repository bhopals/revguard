#!/bin/bash
# Remaining evaluation compute, in order. Every step is cached per case,
# so this script is safe to re-run after any interruption.
set -x
cd "$(dirname "$0")/.."

# Fill tier-3 for the earlier configs (cases 1-16 are cached).
python3 agent/run.py --config v1
echo "=== V1 TIER3 DONE ==="
python3 agent/run.py --config v2
echo "=== V2 TIER3 DONE ==="
python3 agent/run.py --config v3
echo "=== V3 TIER3 DONE ==="

# The removal-candidate experiment and the final config, all 22 cases.
python3 agent/run.py --config v4
echo "=== V4 DONE ==="
python3 agent/run.py --config v5
echo "=== V5 DONE ==="

# Repeat runs for variance (fresh result dirs => nothing cached).
python3 baseline/run.py --out results/baseline-r2 --traj trajectories/baseline-r2
echo "=== BASELINE R2 DONE ==="
python3 agent/run.py --config v5 --run-name agent-v5-r2
echo "=== V5 R2 DONE ==="

python3 eval/compare.py
echo "=== ALL DONE ==="
