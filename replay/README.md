# Escaped-bug replay — external validation on real OSS history

The 22-case benchmark uses defects *we* seeded. The fair question a judge
asks next is: *does RevGuard find real bugs it didn't plant?* This replay
answers it on three real commits from popular MIT-licensed Python
projects — each one **introduced a bug that passed human code review and
shipped**, and was fixed later upstream. We run the exact
bug-introducing diff through both the one-prompt baseline and RevGuard v5
and check whether each flags the defect that actually escaped.

Everything needed is vendored under `replay/vendor/<case>/` (post-commit
tree + `pr.diff` + `COMMIT.txt`, upstream MIT licenses included), so the
replay is offline and reproducible: `python3 replay/run.py --all` (add
`--baseline` for the baseline). Ground truth and the upstream fix for
each case are in `cases.json`.

## The three cases

| case | upstream | the bug that escaped review | time to fix upstream |
|---|---|---|---|
| `tinydb_445` | TinyDB #445 | new `map` feature calls `cond.is_cacheable()` on every query, but TinyDB's public API accepts plain callables as queries — every custom-callable query now raises `AttributeError` | 8 days (issue #454, fix `1fa99fb`) |
| `schedule_refactor` | schedule "make at() easier to read" | a readability refactor guards `len(time_values) == 1` then unpacks two names from it — `at(':SS')` always raises `ValueError` | same author, next commit (`245728b`) |
| `schedule_517` | schedule #517 | new timezone `.at()` support; an untouched pre-existing "run today" check still compares a target-timezone `at_time` to local `now.time()`, scheduling runs a day off near the boundary | **~18 months** (Apr 2022 → Oct 2023, fix `1b34599` / #583) |

## Results

| case | baseline | RevGuard v5 |
|---|---|---|
| tinydb_445 | **CAUGHT** (4 findings, $0.08) | **CAUGHT** (3 findings, $0.85) |
| schedule_refactor | **CAUGHT** (1 finding, $0.05) | **CAUGHT** (1 finding, $0.38) |
| schedule_517 | **CAUGHT** (5 findings, $0.20) | **CAUGHT** (5 findings, $1.66) |

**Both systems caught all three real escaped bugs.** Two things follow,
and they line up exactly with the main benchmark:

1. **External validity.** RevGuard flags real defects that got past real
   human reviewers and shipped — not just defects we planted. The
   schedule_517 timezone bug lived in released code for ~18 months;
   RevGuard names the exact line and explains the failure. That is the
   headline: *this tool would have caught, in one review, a bug the
   project took a year and a half to find.*
2. **These are small diffs (25–370 lines), so the baseline keeps pace.**
   Consistent with benchmark finding #1 — the base model has solved
   small-diff review — the extra machinery earns its cost on large
   multi-file PRs (benchmark tier 3), not here. We report that honestly
   rather than staging a win.

What RevGuard adds even when the verdict matches is **verification
evidence**: for schedule_517 its verifier didn't just assert the bug, it
traced the timezone conversion through `_schedule_next_run` and showed
the `at_time` (target tz) vs `now.time()` (local) mismatch line by line
(see `replay/results/schedule_517-v5/report.md`).

> Provenance: all three commits are real and public; SHAs and upstream
> fix references are in `cases.json`. Upstreams are MIT-licensed and their
> license files are vendored alongside the snapshots.
