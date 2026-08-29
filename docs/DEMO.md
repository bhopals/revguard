# RevGuard — how to show it in action

Copy-paste commands, what each one does, and what you'll see. For the concepts
behind them, read [WALKTHROUGH.md](WALKTHROUGH.md) first. Every command below
was run for real; the outputs shown are actual results from this repo.

**Prerequisites:** Python 3.10+, `pytest`, and the Claude Code CLI logged in
(`claude` on your PATH). No API key juggling — the CLI uses your session. No
other dependencies.

```bash
cd revguard
```

There are four demos, shortest first. Demo 1 needs no API calls; Demos 2–4
call the model.

---

## Demo 0 (10 seconds, no API) — prove the benchmark is honest

The whole project rests on one claim: the planted bugs are invisible to CI.
Prove it:

```bash
make validate
```

Expected: every case reports `tests pass`, and the last line is
`All cases valid.` This runs all 22 cases' test suites and confirms every bug
anchor resolves to exactly one line. **Zero API calls** — it's pure Python.

```bash
make test      # 17 self-tests for the scoring harness itself
```

---

## Demo 1 (≈2 min, one API run) — review ONE hard PR, watch the pipeline

This is the best single demo. Case 21 is a "performance refactor" PR that
looks innocent and whose tests pass, but it hides three cross-module bugs.

```bash
python3 agent/run.py --config v5 --case case21_perf_reports --run-name demo
```

`--case` accepts the bare name (or a unique prefix like `case21`, or the full
`cases/case21_perf_reports` path). `--run-name demo` writes the output to
`results/demo/` so it (a) always runs fresh instead of printing
`cached, skipping`, and (b) never overwrites the committed canonical result in
`results/agent-v5/` that the dashboard cites. (If you don't need to preserve
that, `--force` re-runs in place instead.)

What happens, in order (you'll see it in the console and in `trajectories/`):

1. Three reviewers run in parallel (correctness / security / tests).
2. Their findings are merged.
3. Each finding gets a fresh sandbox and an adversarial verifier with a shell.
4. Only confirmed findings are written to a report.

Actual result on this case:

```
case21_perf_reports: 2 raw -> 2 merged -> 2 final (92.3s, $0.44)
```

Open the report:

```bash
open results/demo/case21_perf_reports_report.html    # or _report.md
```

You'll see the seeded bugs, each with the verifier's evidence quoted (a fresh
run catches two or three of them — LLM runs vary slightly; the two criticals
are always caught):

- `ledgerly/reports.py:44` — the refactor's new JOIN lost its month filter, so
  every budget sums a category's spend **across all time**. Tests pass only
  because the fixtures never span two months.
- `ledgerly/db.py:100` — a new `CREATE INDEX` without `IF NOT EXISTS` crashes
  the app the **second** time the database is opened. Tests never catch it
  because they use in-memory databases that never reopen.
- `ledgerly/db.py:110` — `PRAGMA synchronous = OFF` silently trades crash
  durability for speed in a finance app.

**The money shot:** open the verifier's trajectory for the second bug —

```bash
python3 tools/render_trajectory.py \
  trajectories/demo/case21_perf_reports/verifier_01.jsonl | less
```

The verifier doesn't *argue* the crash is likely. It creates a file-backed
database, opens it twice, and shows the `sqlite3.OperationalError`, then greps
the tests to explain why CI stayed green. That's "evidence, not opinion" made
literal.

### Contrast with the baseline (same PR, same model, one prompt)

```bash
python3 baseline/run.py --case cases/case21_perf_reports --force
cat results/baseline/case21_perf_reports.json
```

The baseline reviews the diff text alone — faster and cheaper (~$0.07), but it
cannot open a database or read the untouched module the JOIN depends on, so on
the hard cases it misses execution-only bugs and hedges the rest into "you
might want a test for…" comments.

---

## Demo 2 (≈1 min per system) — the measured comparison

Run both systems on a few cases and score them with the fixed rule:

```bash
# (Demo 1 already produced the v5 + baseline results for case21.)
python3 agent/run.py --config v5 --case cases/case05_new_categories --force  # a CLEAN PR
python3 baseline/run.py --case cases/case05_new_categories --force

python3 eval/compare.py results/baseline results/agent-v5
```

Two things to point at:

- On the **clean PR** (`case05`), neither system invents a finding — no false
  positives. That discipline is the whole point.
- The comparison table prints recall / precision / F1 / false positives / time
  / cost. The full 22-case version is pre-computed in
  [dashboard.html](dashboard.html) and the [CHANGELOG](CHANGELOG.md).

To regenerate the full dashboard from whatever results exist:

```bash
python3 eval/dashboard.py && open docs/dashboard.html
```

---

## Demo 3 (≈2 min, the "would a team use this?" demo) — review a real GitHub PR

The pipeline isn't just a benchmark harness. Point it at any GitHub PR:

```bash
# Review a PR and print the report locally:
python3 revguard.py --pr owner/repo#123

# Review it AND post the review as a PR comment (needs gh write access):
python3 revguard.py --pr owner/repo#123 --post-comment

# Run the fair one-prompt baseline on the same PR, for comparison:
python3 revguard.py --pr owner/repo#123 --baseline
```

**The live proof this works — on RevGuard itself.** We opened a real PR on the
public repo and ran RevGuard on it:
<https://github.com/bhopals/revguard/pull/1>

Read the two comments there. On the first pass RevGuard found a bug we'd
planted **and two real security holes we'd accidentally written into the
`--pr` feature** — argument injection via a git ref name (its verifier
reproduced it by building a malicious ref) and prompt injection via untrusted
PR text. We fixed both; the second comment shows the re-review confirming
they're gone and surfacing one more real logic bug. The tool made its own next
version safer — that's the workflow end to end.

You can also review a local repo or branch:

```bash
python3 revguard.py --repo /path/to/repo --base main               # working tree
python3 revguard.py --repo /path/to/repo --base main --head feat/x # a branch
python3 revguard.py --repo . --base HEAD~1 --paths src/            # scoped
```

Output for all of these lands in `reviews/<label>-<timestamp>/`:
`report.md`, `report.html`, `findings.json`, and full `trajectories/`.

---

## Demo 4 (≈1–2 min each) — real escaped bugs from open source

Proof RevGuard flags real defects, not just ones we planted. `replay/` holds
three real MIT-licensed OSS commits that shipped bugs past human review:

```bash
python3 replay/run.py --case schedule_517            # RevGuard v5
python3 replay/run.py --case schedule_517 --baseline # the baseline
python3 replay/run.py --all                          # all three
```

`schedule_517` is the headline: a timezone bug that lived **~18 months** in a
released library. RevGuard names the exact line and explains the failure.
(Both the baseline and RevGuard catch these — they're small diffs, so per
finding #1 the baseline keeps pace; the value here is *external validity*.)
Details in [../replay/README.md](../replay/README.md).

---

## Cheat sheet

| Goal | Command |
|---|---|
| Prove benchmark is honest (no API) | `make validate` |
| Harness self-tests (no API) | `make test` |
| Review one hard PR with the pipeline | `python3 agent/run.py --config v5 --case case21_perf_reports --run-name demo` |
| Same PR through the baseline | `python3 baseline/run.py --case case21_perf_reports --out results/demo-baseline` |
| Score any results dirs | `python3 eval/compare.py results/baseline results/agent-v5` |
| Rebuild the dashboard | `python3 eval/dashboard.py` |
| Review a real GitHub PR | `python3 revguard.py --pr owner/repo#N [--post-comment] [--baseline]` |
| Review a local repo | `python3 revguard.py --repo . --base main` |
| Replay a real escaped OSS bug | `python3 replay/run.py --case schedule_517` |
| Read a trajectory | `python3 tools/render_trajectory.py <path>.jsonl` |
| Full reproduction from scratch | see [REPRODUCTION.md](REPRODUCTION.md) |

---

## What a good live walkthrough looks like (5 minutes)

1. `make validate` → "the bugs are invisible to CI; here's proof." (10s)
2. Demo 1 on case21 → watch reviewers + verifier, open the HTML report. (2m)
3. Open the verifier trajectory → "it reproduced the crash, didn't guess." (30s)
4. Open PR #1 on GitHub → "it found real security bugs in itself." (1m)
5. Point at the dashboard + the 18-month `schedule` bug → results land. (1m)
