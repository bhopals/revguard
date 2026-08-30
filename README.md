# RevGuard — a code review agent you don't learn to ignore

*micro1 Frontier Engineering Challenge 2026 — Agentic Workflows Hackathon*

Everything in this repository — code, benchmark, prompts, docs — was
created during the event (see git history). Pre-existing components used:
Python 3.12, pytest, and the Claude Code CLI as the agent runtime.

> **New here?** Read [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) for a full
> plain-English tour of every file and how the pipeline works step by step,
> then run `make validate && make agent && make eval` (see
> [docs/REPRODUCTION.md](docs/REPRODUCTION.md)).

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
one: **Ledgerly**, an expense-tracking service written for this benchmark
(Python stdlib + sqlite; the tier-3 "Pro" variant is ~1,400 LOC across 10
modules with 53 passing tests), and **22 pull requests** against it
containing **61 seeded defects** with anchor-based labels — SQL injection,
path traversal, float money corruption, missing WHERE and JOIN
predicates, IDOR, stale caches, lexicographic money sorting, a schema
change that silently breaks an untouched module, tests weakened or
shaped to sneak a bug past CI, and more. Two PRs are completely clean,
to measure false-positive discipline. The cases come in tiers: 16 small
PRs (tiers 1–2) and six **tier-3** PRs — 150–400 line multi-file diffs
with refactor noise, cross-module bugs invisible from the diff alone,
and defects that only execution exposes.

Every case's post-PR test suite **passes** — by construction, the benchmark
measures exactly what CI misses. `make validate` re-proves this in a few
minutes with zero API calls.

The matching rule (same file, line within ±6 of a labeled anchor,
category not required) was fixed before any system ran and applies
identically to baseline and agent — see `eval/score.py`. Labels were
refined in two documented adjudication rounds (`docs/CHANGELOG.md`);
both rounds raised the *baseline's* score, which is how you know they
were honest.

## The Console — explore every run, finding, and verification

`docs/console.html` is a self-contained interactive UI (open it in any browser,
no server) that reads the committed `results/` and `trajectories/`. Three views:

- **Overview** — the scoreboard: every system on the same 22 cases, the tier-3
  win, and the honest overall-F1 nuance.
- **Cases & findings** — all 22 PRs; open one for its diff, what each system
  found, and the ground-truth bugs (caught / missed).
- **Verification traces** — the part no other review tool shows: pick a finding
  and watch the adversarial verifier's actual attempt to disprove it — the
  commands it ran, the crash it reproduced, its verdict — plus the noise it
  threw out. Rebuild anytime with `make console`.

## Results

Three findings, in order of importance:

**1. The base model has solved small-PR review.** On the 16 small-PR
cases the one-prompt baseline found 39/39 seeded defects. Any agent
machinery there is overhead — ours included. We report this instead of
hiding it.

**2. Where review is actually hard, the pipeline wins on every metric.**
On the six tier-3 PRs (150–400 line multi-file diffs, cross-module bugs,
misleading tests):

| system | found | recall | precision | F1 | false positives |
|---|---|---|---|---|---|
| baseline (same model, 1 prompt) | 19/22 | 0.86 | 0.90 | 0.884 | 2 |
| **RevGuard v5** | **20/22** | **0.91** | **0.95** | **0.930** | **1** |

**3. The pipeline is stable; the baseline is not.** Both systems were
run twice end-to-end (fresh runs, nothing cached). v5 produced
*identical* overall numbers both times — F1 0.887, exactly 3 false
positives — and tier-3 F1 of 0.930 / 0.933. The baseline held its recall
but its false positives **tripled between runs** (6 → 18; overall F1
0.928 → 0.847, mean 0.888). Run-to-run noise is the "bot that cries
wolf" failure mode showing up as variance, and the policy-gated verifier
is what pins it down. On mean-of-runs the two systems tie overall
(0.887 vs 0.888) while v5 wins tier-3 (0.93 vs 0.887) and noise
(3±0 vs 12±6 false positives).

Neither system ever flagged anything on the two clean PRs, in any run.
A tier-3 review costs v5 ~2 minutes and ~$0.50 against 30–60 minutes of
a senior engineer's attention. Every cell traces to a JSON under
`results/`; `make eval` regenerates the table, and `docs/dashboard.html`
renders the full per-case grid across all eight runs.

Characteristic difference in *behavior*, not just numbers: when the
baseline can't confirm a suspicion from the diff alone, it hedges —
real defects come back as "there's no test covering X" advisories. The
pipeline reads the repo and executes reproductions instead: its report
for the perf-refactor case doesn't argue the reopen-crash is likely, it
opens the database twice in a sandbox and shows the OperationalError.

## Improvement changelog

The full, honest iteration story — including the version that was worse
than the baseline, the verifier that confirmed 54/54 findings, and the
experiment we removed for the opposite of the expected reason — is in
**[docs/CHANGELOG.md](docs/CHANGELOG.md)**. Every entry has measured
numbers.

## Use it on a real repository or a live GitHub PR

The benchmark proves the pipeline; `revguard.py` ships it:

```bash
python3 revguard.py --repo /path/to/repo --base main              # working tree
python3 revguard.py --repo /path/to/repo --base main --head br    # a branch
python3 revguard.py --repo . --base HEAD~1 --paths src/           # scoped
python3 revguard.py --pr owner/repo#123                           # a GitHub PR
python3 revguard.py --pr owner/repo#123 --post-comment            # + post review
python3 revguard.py --pr owner/repo#123 --baseline                # fair baseline
```

Output: `report.md`, a self-contained `report.html`, `findings.json`,
and full trajectories, under `reviews/`.

**It found real bugs in itself.** We opened a live PR on this repo adding
a `--min-severity` flag ([PR #1](https://github.com/bhopals/revguard/pull/1),
with one seeded crash) and ran `revguard.py --pr` on it. RevGuard flagged
the seeded bug *and two real vulnerabilities we had just written into the
`--pr` feature* — argument injection via a hostile git ref name (which its
verifier reproduced by building a malicious ref) and prompt injection via
untrusted PR text — then posted the review as a PR comment. Both are now
fixed on `main` (`ea2375c`). Earlier dogfooding caught two more CLI bugs
(argv size limit on large diffs; pathspec scoping). A separate run
reviewed a clean commit and **approved it with zero findings** — the same
discipline it shows on the benchmark's clean PRs. The tool improving its
own next version is the whole workflow working end to end.

### External validity — real escaped bugs (`replay/`)

Beyond our seeded benchmark, `replay/` runs RevGuard on three real
MIT-licensed OSS commits that shipped bugs past human review (TinyDB #445;
a `schedule` refactor; `schedule` #517, which lived **~18 months** in
released code). Both the baseline and RevGuard catch all three — these
are small diffs, so per finding #1 the baseline keeps pace, but it proves
the tool flags *real* defects, not just planted ones. See
[replay/README.md](replay/README.md).

## Reproduction

See [docs/REPRODUCTION.md](docs/REPRODUCTION.md). Short version:
`make validate && make baseline && make agent && make eval` on a machine
with Python 3.10+, pytest, and a logged-in Claude Code CLI.

## Repository layout

```
target_repo/       Ledgerly, the tier-1/2 codebase under review (tests pass)
target_repo_pro/   the expanded tier-3 codebase (10 modules, 53 tests)
cases/             22 PR cases: changed files + anchor-based ground truth
baseline/          the fair baseline: one prompt, diff inline, no tools
agent/             RevGuard pipeline (configs v1-v5 = changelog iterations)
revguard.py        CLI: run the pipeline on any real git repository
eval/              fixed scoring rule, comparison table, dashboard
tools/             case utilities, validator, adjudication, renderers
results/           findings, reports, timing, cost (scoring input)
trajectories/      full stream-json trajectory of every agent invocation
reviews/           real-repo review outputs (committed dogfood demo)
docs/              walkthrough, reproduction guide, changelog, dashboard
tests/             self-tests for the scoring harness itself
```

### Representative trajectories (all rendered as .md beside the .jsonl)

- `trajectories/agent-v5/case21_perf_reports/verifier_01.md` — the
  verifier does not argue the reopen-crash is likely; it creates a
  file-backed database, reopens it, gets the OperationalError, and greps
  the test suite to explain why CI never sees it. 5 turns, $0.06.
- `trajectories/agent-v5/case21_perf_reports/reviewer_correctness.md` —
  a specialist walking the JOIN rewrite against the old query and
  catching the lost month predicate.
- `trajectories/agent-v3/case15_summary_cache/` — the truth-only
  verifier era: executed reproductions of the stale cache (kept) but
  also confirmations of advisory comments (the measured failure that
  led to the policy gate).
- `trajectories/baseline/case21_perf_reports.jsonl` — the baseline's
  single-shot review of the same PR, for contrast.

## Main failure mode and hot take

Short version — the full argument closes [docs/CHANGELOG.md](docs/CHANGELOG.md):

- **Failure mode:** filtering stages don't just remove noise, they define
  what the system is allowed to notice. Two real tier-3 defects were
  *mentioned* by reviewers in adjacent framings and then lost to lane
  boundaries or the policy gate. Every gate you add needs its own
  miss-audit.
- **Hot take:** verification checks truth, but most bad review comments
  are *true* ("there are no tests for X" — correct, and still noise).
  Our truth-only verifier confirmed 54/54 findings: pure cost. A useful
  verifier needs a policy gate, and the reviewers feeding it should be
  permissive *because* it exists. And don't build agents for regimes the
  base model already solved — benchmark until you find where it breaks,
  then build exactly there.
