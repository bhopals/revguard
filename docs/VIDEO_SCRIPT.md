# Solution video script (target: 4:30)

Record screen + voice. Terminal font large. Have these ready in tabs:
README results table, docs/dashboard.html, one tier-3 HTML report
(case21), one verifier trajectory markdown, docs/CHANGELOG.md.

## 0:00–0:40 — The problem (talking over README intro)

> "Senior code reviewers are the bottleneck on every team I've worked
> with. CI catches what tests cover — humans catch what tests miss.
> AI review bots exist, but they have a trust problem: they spray
> plausible-sounding comments, engineers learn they cry wolf, and then
> the bot gets ignored. RevGuard inverts that: no finding reaches a
> human unless a separate adversarial agent — with the repo and a
> shell — has tried to disprove it and failed."

## 0:40–1:20 — The baseline and the benchmark (dashboard tab)

> "To measure anything you need ground truth, so the project includes a
> benchmark: a working expense-tracker codebase and 22 pull requests
> containing 59 labeled defects — SQL injection, money-through-float,
> stale caches, tests weakened to sneak bugs past CI. Every case's test
> suite passes: the benchmark is exactly what CI misses. The baseline is
> the honest 'what people do today': paste the diff into the same model,
> one prompt. First finding: on small PRs the baseline is nearly
> perfect — modern models have solved small-diff review. So we grew the
> benchmark to large multi-file PRs with cross-module bugs, where the
> baseline drops: it misses execution-dependent defects and hedges real
> bugs into 'maybe add a test' comments."

## 1:20–2:50 — One realistic execution, start to finish (terminal)

Run live (or pre-recorded):

    python3 agent/run.py --config v5 --case cases/case21_perf_reports --force

While it runs, narrate the architecture:

> "Three specialist reviewers — correctness-and-robustness, security,
> test-adequacy — run in parallel. Each has the diff plus the full repo
> with read and grep tools. Their findings are merged, then every
> finding goes to the adversarial verifier: a fresh sandbox copy of the
> repo, Bash enabled, and one instruction — prove this claim wrong.
> Watch case21: the PR is a performance refactor that collapses budget
> lookups into one JOIN. The JOIN lost its month predicate, sqlite got
> a durability-killing pragma, and the new index crashes the app on the
> second database open. CI is green — the tests use in-memory databases
> that never reopen. The verifier doesn't read about the index bug — it
> REPRODUCES it, opening the database twice in its sandbox and getting
> the OperationalError."

Show the HTML report (case21_report.html) and the verifier trajectory md.

## 2:50–3:40 — Results + changelog (README table, then CHANGELOG)

> "Final numbers, same 22 cases, same model, same scoring rule. On the
> large tier-3 PRs the pipeline wins everything: F1 0.930 versus 0.884,
> recall 0.91 versus 0.86, one false positive versus two. On small PRs
> the baseline is saturated at 39 out of 39 — we report that instead of
> hiding it: the base model has solved small-diff review. And
> stability: we ran both systems twice — the pipeline's numbers were
> IDENTICAL both runs, three false positives each time, while the
> baseline's false positives tripled from six to eighteen. The
> changelog is the honest part: v1 — tools plus a conservative brief —
> was WORSE than the baseline. The biggest gain came from re-layering:
> reviewers tuned for recall, verifier owning precision. And the
> experiment we removed — a nitpick reviewer — taught the opposite of
> the expected lesson: it found eleven defects the specialists missed,
> because its brief was permissive. We removed the lane and kept the
> permissiveness."

## 3:40–4:20 — Real-world workflow (terminal)

    python3 revguard.py --repo <this repo> --base HEAD~1

> "It's not just a benchmark harness — point it at any git repo. It
> reviewed its own latest commit and [what it found]. Reports come out
> as markdown and a self-contained HTML page a reviewer would actually
> sign."

## 4:20–4:45 — Hot take

> [From CHANGELOG hot take — verifier starvation insight:] "My hot
> take: everyone bolts verification onto agent pipelines; almost nobody
> asks whether the upstream is feeding it anything to verify. A
> verifier behind conservative reviewers confirmed 29 of 29 findings —
> pure cost, zero value. Calibrate stages as a SYSTEM: generators
> should over-produce, verifiers should be ruthless. That division of
> labor is the whole trick."
