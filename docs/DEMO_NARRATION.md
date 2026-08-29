# RevGuard — live terminal-demo narration (target ~4:00)

This is the narration for a **screen-recorded terminal walkthrough** that runs
the `docs/DEMO.md` commands one by one. (The other track, `docs/NARRATION.md`,
is for the polished self-playing screencast — use whichever you're recording.)

**Setup before you hit record:** the slow steps are pre-run, so nothing here
waits on the model. You'll *show* each command and cut to output that already
exists. Have two things open: a terminal in the `revguard/` folder, and a
browser tab at the PR — `https://github.com/bhopals/revguard/pull/1`.

Speak at a natural pace. `»` = type/run this. `[CUT]` = jump to the pre-made
output. `[SAY]` = your line.

---

### 0. Cold open (0:00–0:20)

`[SAY]` "This is RevGuard — a code-review agent with one rule: no finding
reaches a human unless a second agent has tried to disprove it, by running the
code, and failed. Let me show you it working, end to end."

---

### 1. The benchmark is honest — `make validate` (0:20–0:50)

`» make validate`

`[SAY]` (while the green `ok` lines scroll) "Everything rests on one claim: the
bugs we're testing against are invisible to CI. `make validate` runs all
twenty-two pull requests' test suites — every one passes — and confirms each
planted bug resolves to a real line. No API calls, just proof the benchmark is
honest. There's the line: **All cases valid.**"

---

### 2. Review one hard PR (0:50–1:40)

`» python3 agent/run.py --config v5 --case case21_perf_reports --run-name demo`

`[SAY]` "Now a real review. This case is a *performance refactor* — it looks
clean, and its tests pass. Watch what RevGuard does: three specialist reviewers
run in parallel — correctness, security, tests — each with tools to read the
whole repo, not just the diff. Their findings merge, then every finding goes to
an adversarial verifier with a shell whose only job is to prove it wrong."

`[CUT]` to the final line:
```
case21_perf_reports: 3 raw → 3 merged → 3 final (…s, $…)
```

`[SAY]` "Three findings, every one confirmed by the verifier. Let's read them."

`» open results/demo/case21_perf_reports_report.html`

`[SAY]` "Two critical, one major. First — the refactor's new database JOIN
silently lost its month filter, so every budget now sums spending across *all
time*. Second — a new index definition crashes the app the *second* time the
database is opened. And third — it quietly turned off SQLite's crash
durability. The tests never catch any of these, because they use in-memory
databases that never reopen."

---

### 3. The verifier's evidence — the money shot (1:40–2:15)

`» python3 tools/render_trajectory.py trajectories/demo/case21_perf_reports/verifier_01.jsonl | less`

`[SAY]` "Here's what makes it trustworthy. This is the verifier's actual
trajectory for that second bug. It didn't *argue* the crash was likely — it
created a real database file, opened it twice, and captured the actual
`OperationalError`. Then it grepped the tests to explain why CI stayed green.
That's the difference between an opinion and evidence."

`[SAY]` (scroll to the verdict line) "Verdict: CONFIRMED. Only findings that
survive this reach the report."

---

### 4. The fair baseline, same PR (2:15–2:50)

`» python3 baseline/run.py --case case21_perf_reports --out results/demo-baseline`

`[SAY]` "Is the pipeline actually better than just asking the model? Here's the
fair baseline — the same PR, the same model, one prompt, no tools. It's faster
and cheaper. But it can only read the diff text — it can't open a database or
check the untouched module the JOIN depends on. So on hard PRs it misses the
execution-only bugs and hedges the rest into 'you might want a test for…'
comments. That difference is the whole project."

`[CUT]` `» python3 eval/compare.py results/demo-baseline results/demo`
`[SAY]` (point at the table) "Side by side on this case."

---

### 5. The full results (2:50–3:20)

`» open docs/dashboard.html`

`[SAY]` "Across the whole benchmark, three findings. One: on small PRs the base
model is already perfect — thirty-nine out of thirty-nine — so we don't pretend
our machinery helps there. Two: on large, realistic PRs the pipeline wins on
every metric — F-one of point-nine-three versus point-eight-eight. Three, my
favorite: we ran both twice, and RevGuard was identical — three false positives
both runs — while the baseline's tripled to eighteen. That instability *is* the
cry-wolf problem, measured."

---

### 6. It works on real code — the dogfood PR (3:20–3:55)

`[SAY]` "And it's not just a benchmark harness. `revguard.py --pr` reviews any
GitHub pull request."

`» python3 revguard.py --pr bhopals/revguard#1` *(optional — or just show the
result, since it's already posted)*

`[CUT]` to the browser tab at
`https://github.com/bhopals/revguard/pull/1` — scroll the two RevGuard comments.

`[SAY]` "We ran it on a real pull request on this very repo. On the first pass
it found a bug we'd planted — *and two real security holes we'd accidentally
written into the tool itself*: argument injection through a git ref name, which
its verifier reproduced with a live exploit, and prompt injection through PR
text. We fixed both; the second comment shows the re-review confirming they're
gone. The tool made its own next version safer."

---

### 7. Close (3:55–4:10)

`[SAY]` "That's RevGuard: not a reviewer that finds more — a reviewer you don't
learn to ignore. Everything's public and reproducible from a clean checkout at
github dot com slash bhopals slash revguard. Thanks for watching."

---

## Notes for a clean recording
- Every command above reads from **pre-run** output (`results/demo/`,
  `results/demo-baseline/`, the committed PR comments), so nothing stalls on the
  model. If you *do* execute a command live and see `cached, skipping`, that's
  expected — add `--force`, or just cut to the output that's already there.
- Keep the terminal font large (18–20pt) and the window ~100 columns.
- Total is ~4:10; if you need to hit 4:00, drop step 4's `eval/compare` line.
- Optional extra (external validity): `python3 replay/run.py --case schedule_517`
  — a real bug that lived ~18 months in a released library, from `replay/`.
