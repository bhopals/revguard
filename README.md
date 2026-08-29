# RevGuard — a code review agent you don't learn to ignore

*micro1 Frontier Engineering Challenge 2026 — Agentic Workflows Hackathon*

## The user and the bottleneck

The intended user is an engineering team where **senior reviewers are the
bottleneck**. CI only catches what tests cover; humans must catch what tests
miss — logic bugs, security holes, silently weakened tests. A careful review
of a mid-size PR costs 30–60 minutes of a senior engineer's attention, so
reviews queue up, and under time pressure they degrade into skimming.

The obvious fix — an AI review bot — has a well-known failure mode: it sprays
plausible-sounding comments, most of them wrong or irrelevant. Engineers
learn within a week that the bot cries wolf, and then they ignore it, at
which point it has negative value. The bottleneck worth solving is not
"find more possible issues"; it is **"only tell me things that are true,
with evidence"**.

RevGuard is built around that inversion: every finding must survive an
adversarial verification agent whose only job is to prove the finding wrong —
by reading the code and, wherever possible, by *executing* a reproduction in
a sandbox — before a human ever sees it.

## How it works

```
                    PR diff + post-PR repo (sandbox copy)
                                   |
          +------------------------+------------------------+
          |                        |                        |
   correctness reviewer     security reviewer        tests reviewer
   (Read/Grep/Glob on       (Read/Grep/Glob)         (Read/Grep/Glob)
    the full repo)                 |                        |
          +------------------------+------------------------+
                                   |
                          merge + dedupe findings
                                   |
                     adversarial verifier (per finding,
                     fresh repo sandbox, Bash allowed:
                     tries to FALSIFY the claim by
                     execution; only CONFIRMED survive)
                                   |
                     evidence-linked review report
                     (file:line, failure scenario,
                      verification evidence)
```

Design choices, and why each one is there:

- **Tools + context over prompt size.** Reviewers get the diff *and* a real
  repository with Read/Grep/Glob. Several benchmark bugs are invisible from
  the diff alone (e.g. a diff that adds a currency column is only wrong
  because an untouched reports module sums across currencies).
- **Specialists over one generalist.** Each reviewer carries a narrow brief
  (correctness / security / test-adequacy) with domain-specific checklists,
  and explicitly does not report outside its lane.
- **Adversarial verification.** A separate agent receives one finding at a
  time in a fresh sandbox copy of the repo, with Bash enabled, and is
  instructed to attack the claim — run the code, write a reproduction,
  grep for the missing safeguard. Findings it cannot confirm are dropped.
  This stage exists because reviewers (human and LLM alike) are rewarded
  for plausible pattern-matches; verification converts "plausible" into
  "demonstrated".
- **Isolation as a feature.** Every agent runs via `claude -p --restricted
  --strict-mcp-config`: no user settings, no network tools, file access
  confined to the per-case sandbox. Verifier Bash runs happen in a
  throwaway copy so no verification can contaminate another.

Everything (baseline included) runs on the same model, so every measured
difference is attributable to workflow design, not model choice.

## The benchmark

You cannot measure a reviewer without ground truth, so the project includes
one: **Ledgerly**, a small expense-tracking service (Python stdlib + sqlite,
16 passing tests), and **16 pull requests** against it containing **35
seeded defects** with anchor-based labels — SQL injection, path traversal,
float money corruption, missing WHERE clauses, IDOR, stale caches,
lexicographic money sorting, tests weakened to sneak a bug past CI, and
more. Two PRs are completely clean, to measure false-positive discipline.
Four are "tier 2": larger, noisier diffs and cross-file bugs whose
wrongness is only visible outside the diff.

Every case's post-PR test suite **passes** — by construction, the benchmark
measures exactly what CI misses. `make validate` re-proves this in about a
minute with zero API calls.

The matching rule (same file, line within ±6 of the labeled anchor,
category not required) was fixed before any system ran and applies
identically to baseline and agent. See `eval/score.py`.

## Results

<!-- RESULTS_TABLE -->

*(Numbers are produced by `make eval` from the JSONs in `results/`; every
cell traces to files in this repo.)*

## Improvement changelog

<!-- CHANGELOG -->

## Reproduction

See [docs/REPRODUCTION.md](docs/REPRODUCTION.md). Short version:
`make validate && make baseline && make agent && make eval` on a machine
with Python 3.10+, pytest, and a logged-in Claude Code CLI.

## Repository layout

```
target_repo/     Ledgerly, the codebase under review (all tests pass)
cases/           16 PR cases: changed files + anchor-based ground truth
baseline/        the fair baseline: one prompt, diff inline, no tools
agent/           RevGuard pipeline (configs v1-v4 = changelog iterations)
eval/            fixed scoring rule + comparison table
tools/           case utilities + benchmark validator
results/         findings, reports, timing, cost (scoring input)
trajectories/    full stream-json trajectory of every agent invocation
docs/            reproduction guide
```

## Main failure mode and hot take

<!-- HOT_TAKE -->
