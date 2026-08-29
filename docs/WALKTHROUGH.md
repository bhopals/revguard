# RevGuard — complete project walkthrough

This is the "explain the whole thing" document. It assumes no prior context
and walks from the idea, through every file, to a step-by-step trace of what
happens when you run a review. If you only read one doc to understand the
project, read this one. For hands-on commands, see the Makefile targets
(`make validate`, `make agent`, `make eval`) and [REPRODUCTION.md](REPRODUCTION.md).

---

## 1. The idea in one paragraph

**RevGuard** is a code-review agent whose defining rule is: *no finding
reaches a human unless a second, adversarial agent has tried to disprove it —
by actually running the code — and failed.* Because a claim like "our
reviewer is good" is worthless without proof, the project also includes the
**benchmark that measures it**: a real app, 22 pull requests with 61 planted
and labeled bugs, and a fair baseline. The measurements are the real story.

**Who it's for:** engineering teams where senior reviewers are the
bottleneck. CI catches what tests cover; humans catch what tests *miss*.
Existing AI review bots fail the same way — they spray plausible but wrong
comments until people learn to ignore them. So the goal is not "find more
issues," it is **"only tell me things that are true, with evidence."**

---

## 2. The four parts of the project

```
   ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
   │  THE BENCHMARK  │     │   THE PIPELINE   │     │ THE MEASUREMENT │
   │ target_repo(_pro)│ ──> │     agent/       │ ──> │ baseline/, eval/│
   │ cases/ (22 PRs, │     │ reviewers +      │     │ same cases,     │
   │ 61 bugs)        │     │ verifier         │     │ fixed scoring   │
   └─────────────────┘     └──────────────────┘     └─────────────────┘
            │                       │                        │
            └───────── all three feed ──> results/, docs/, dashboard
                                    │
                          ┌──────────────────┐
                          │   THE PRODUCT    │
                          │   revguard.py    │  ← run the pipeline on ANY
                          │  (real git / PR) │    real repo or GitHub PR
                          └──────────────────┘
```

1. **The benchmark** — the yardstick. A working app plus PRs with known bugs.
2. **The pipeline** — the reviewer. Parallel specialists → adversarial verifier.
3. **The measurement** — the proof. A fair baseline, one scoring rule, results.
4. **The product** — `revguard.py`, which runs the same pipeline on real code.

---

## 3. Every file, explained

### 3.1 The benchmark — the codebases under review

| Path | What it is |
|---|---|
| `target_repo/ledgerly/` | **Ledgerly**: a small expense-tracker service (Python stdlib + sqlite). Modules: `db.py`, `auth.py`, `expenses.py`, `reports.py`, `utils.py`. All tier‑1/2 PRs are changes to this. |
| `target_repo/tests/` | Ledgerly's passing test suite (16 tests). |
| `target_repo_pro/` | **Ledgerly Pro**: the same app grown to ~1,400 LOC across 10 modules (adds `household.py`, `recurring.py`, `importers.py`, `notify.py`, `api.py`) with 53 tests. Tier‑3 PRs target this. Kept separate so tier‑1/2 comparisons stay frozen as the app grows. |

Why two repos? Small diffs turned out to be *solved* by the base model, so we
needed a harder codebase (bigger, more cross-module coupling) to find where a
review pipeline actually earns its cost.

### 3.2 The cases — the pull requests with known bugs

```
cases/case21_perf_reports/
├── meta.json              # the PR's title, description, and labeled bugs
└── changed/               # the post-PR version of every file the PR touches
    └── ledgerly/
        ├── db.py          # (mirrors target_repo_pro's layout)
        └── reports.py
```

- **22 cases total**: 14 tier‑1/2 PRs with bugs, **2 clean PRs** (no bugs, to
  measure false-positive discipline), and **6 tier‑3** large multi-file PRs.
- **61 labeled defects** across them.
- `meta.json` holds each bug as an **anchor**: a unique code substring, not a
  line number. Line numbers are resolved at scoring time (`tools/case_utils.py`)
  so labels can never drift out of sync with the code.
- The magic property: **every case's test suite passes.** By construction the
  benchmark measures exactly what CI misses.

A `meta.json` defect looks like:
```json
{
  "id": "c21-d1",
  "file": "ledgerly/reports.py",
  "anchor": "\"   AND e.category = b.category\"",
  "category": "correctness",
  "severity": "critical",
  "description": "The LEFT JOIN matches on user and category but NOT month …"
}
```

### 3.3 The pipeline — `agent/`

| File | Role |
|---|---|
| `agent/runtime.py` | The **agent runtime**. Wraps the Claude Code CLI in headless mode (`claude -p … --restricted --strict-mcp-config --tools …`). Every agent — reviewer or verifier — goes through `run_agent()`, so all get identical isolation, a stream-json trajectory saved to disk, and retry-with-backoff. `extract_json()` parses the agent's final JSON. |
| `agent/run.py` | The **orchestrator**. Defines the configs (`v1`…`v5`, `v5-fast`), runs the reviewers in parallel, merges/dedupes findings, runs the verifier per finding, and writes the report. `review_diff()` is the transport-agnostic core shared by the benchmark runner and the CLI. |
| `agent/prompts/reviewer_common.md` | Base reviewer brief, v1–v4 (conservative calibration). |
| `agent/prompts/reviewer_common_v2.md` | Base reviewer brief, v5 (recall-tuned: "a verifier is downstream, so over-report real defects"). |
| `agent/prompts/specialists.py` | The per-lane focus briefs: `correctness`, `security`, `tests`, plus `generalist`/`nitpick`. `SPECIALISTS_V2` is the v5 set (correctness lane also owns robustness; tests lane is banned from "no tests for X" advice). |
| `agent/prompts/verifier.md` | Verifier brief, v3 (truth-only: "prove this claim wrong"). |
| `agent/prompts/verifier_v2.md` | Verifier brief, v5 (truth **and** policy gate: rejects advisory comments even when factually true). |
| `agent/html_report.py` | Renders a self-contained, theme-aware HTML review report. |

### 3.4 The measurement — `baseline/`, `eval/`

| File | Role |
|---|---|
| `baseline/run.py` | The **fair baseline**: one prompt, the diff pasted inline, no tools, same model. This is "what people do today." |
| `eval/score.py` | The **scoring rule**, fixed before any system ran: a finding matches a labeled bug if it names the same file and its line is within **±6** of the anchor (category not required). Each bug matches once; extras are false positives; findings on clean PRs are all false positives. |
| `eval/compare.py` | Prints the system-comparison table (recall/precision/F1/FPs/time/cost). |
| `eval/stages.py` | Attributes what each pipeline **stage** contributed (how many true vs false findings the verifier killed). |
| `eval/dashboard.py` | Renders `docs/dashboard.html` — the whole evaluation at a glance. |

### 3.5 The tools — `tools/`

| File | Role |
|---|---|
| `tools/case_utils.py` | Case plumbing: resolve anchors → line numbers, build a working copy of a case's repo, produce the PR diff, load ground truth. |
| `tools/validate_cases.py` | **Benchmark integrity check** (`make validate`): every anchor resolves uniquely and every case's post-PR test suite passes. Zero API calls. |
| `tools/adjudicate.py` | Lists every false positive and miss across systems, for the labeling adjudication rounds (with a fixed written policy). |
| `tools/render_trajectory.py` | Turns a stream-json trajectory (`.jsonl`) into readable markdown. |
| `tools/run_remaining.sh` | The resumable script that ran the full sweep set. |

### 3.6 The product — `revguard.py`

The CLI that runs the pipeline on **real** code: a local git repo, a branch, or
a live GitHub PR (`--pr owner/repo#N`), with optional `--post-comment` and a
`--baseline` mode for fair external comparisons. Includes the security
hardening RevGuard found in its own review (ref-name and prompt-injection
guards). Output lands in `reviews/`.

### 3.7 External validity — `replay/`

| Path | Role |
|---|---|
| `replay/cases.json` | Three **real** MIT-licensed OSS commits that shipped bugs past human review, with the known bug and its upstream fix. |
| `replay/vendor/<case>/` | The vendored post-commit tree + `pr.diff` + license, so it runs offline. |
| `replay/run.py` | Runs RevGuard or the baseline on each, and judges whether the known escaped bug was caught. |
| `replay/README.md` | The results and what they mean. |

### 3.8 The story — `docs/`, `README.md`

- `README.md` — the pitch: user, bottleneck, results, how to run.
- `docs/CHANGELOG.md` — the **honest iteration story**, every version measured.
- `docs/REPRODUCTION.md` — clean-environment steps and exact commands.
- `docs/dashboard.html` — generated results dashboard.
- `tests/test_harness.py` — self-tests for the scoring harness (`make test`).

---

## 4. How the pipeline works — step by step

When you review one PR (a benchmark case, or a real diff), here's the exact
flow inside `agent/run.py`'s `review_diff()`:

```
INPUT: PR title + description, the unified diff, and a sandbox copy of the
       full post-PR repository.

STEP 1 — Reviewers (parallel).
   Three specialist agents launch at once, each via run_agent():
     • correctness+robustness   • security   • test-adequacy
   Each one gets:
     - the diff (what changed)
     - Read/Grep/Glob tools over the FULL repo (not just the diff) — because
       some bugs only exist relative to untouched code
     - its narrow brief (only report in your lane)
   Each returns structured findings: {file, line, category, severity,
   title, description}.

STEP 2 — Merge + dedupe.
   Findings from all three lanes are pooled; near-duplicates (same file,
   within 3 lines) are collapsed, keeping the highest severity.

STEP 3 — Adversarial verification (parallel, one agent per finding).
   For each surviving finding, a FRESH sandbox copy of the repo is made and a
   verifier agent launches with Read/Grep/Glob AND Bash. Its only job: prove
   the finding wrong. It writes reproduction scripts, runs tests, greps for
   the missing safeguard. It returns CONFIRMED or REJECTED, and (v5) rejects
   findings that are true-but-advisory ("no test for X").
   Fresh sandbox per verifier = no verification can contaminate another.

STEP 4 — Report.
   Only CONFIRMED findings survive. They're written as:
     - report.md   (human-readable, ranked by severity, with the verifier's
                    evidence quoted under each finding)
     - report.html (self-contained page)
     - findings.json (machine-readable, includes rejected findings + costs)
   Every agent's full trajectory is saved under trajectories/.
```

Why this shape wins (and the honest caveats) is the whole
[CHANGELOG](CHANGELOG.md): reviewers tuned for **recall**, verifier owning
**precision**, because measurement showed a conservative reviewer starves the
verifier and a truth-only verifier rubber-stamps true-but-useless comments.

---

## 5. How measurement works — step by step

```
make validate   → prove the benchmark itself is sound (anchors resolve,
                   every case's tests pass). No API calls.

make baseline   → run the one-prompt baseline on all 22 cases.
                  Writes results/baseline/<case>.json

make agent      → run the v5 pipeline on all 22 cases.
                  Writes results/agent-v5/<case>.json

make eval       → eval/score.py matches every system's findings against the
                  frozen ground truth using the ±6-line rule, and
                  eval/compare.py prints recall / precision / F1 / false
                  positives / time / cost per system.
```

Everything is cached per case (delete a result file, or pass `--force`, to
re-run). All systems use the **same model**, so every measured difference is
attributable to workflow design, not model choice.

---

## 6. What the numbers say (the headline)

Three findings, in order of importance (full tables in the
[CHANGELOG](CHANGELOG.md) and [dashboard](dashboard.html)):

1. **The base model has solved small-PR review.** On the 16 small PRs the
   one-prompt baseline found 39/39 bugs. We report that instead of hiding it.
2. **On large, realistic PRs the pipeline wins on every metric.** Tier‑3:
   RevGuard F1 **0.930** vs baseline **0.884**; better recall, better
   precision, fewer false positives.
3. **The pipeline is stable; the baseline is not.** Run twice end-to-end,
   RevGuard's numbers were identical (3 false positives both times); the
   baseline's false positives tripled (6 → 18). That run-to-run noise *is*
   the "cry wolf" failure mode, quantified.

---

## 7. Where to go next

- **Reproduce every number from scratch:** [REPRODUCTION.md](REPRODUCTION.md).
- **Read the honest iteration story:** [CHANGELOG.md](CHANGELOG.md).
- **See it on real bugs:** [../replay/README.md](../replay/README.md).
