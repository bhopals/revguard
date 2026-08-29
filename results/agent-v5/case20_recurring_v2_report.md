# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Biweekly cadence fires every week, not every second week

`ledgerly/recurring.py:106` — correctness

The `else` branch handling `biweekly` (lines 106-111) is byte-for-byte identical to the `weekly` branch (lines 100-105): it appends every date matching `rule["weekday"]` between start and end, with no notion of alternating weeks. There is no anchor/reference date stored on the rule to determine which weeks are 'on' vs 'off', so the code cannot actually skip every other week. As a result, a rule created with cadence='biweekly' will materialize an expense every single week (e.g. calling `materialize_due` weekly on a biweekly $50 rule produces 4 charges/month instead of 2), directly contradicting the PR description ('every second week on a weekday') and the inline comment on line 106. The included test `test_biweekly_occurrence` only checks an 8-day window containing a single Monday, so it cannot distinguish weekly-every-week behavior from true biweekly behavior and passes despite the bug.

*Verified: Read ledgerly/recurring.py lines 97-113: the biweekly branch is logically identical to the weekly branch (same weekday-match loop, no anchor date or parity/week-count check to skip alternate weeks), differing only by a misleading '# biweekly' comment. Executed occurrences_between({'cadence':'biweekly','weekday':0}, 2026-03-01, 2026-04-30) directly: it returned 9 Mondays over 2 months (every single week), proving biweekly behaves identically to weekly rather than firing every second week.*

## 2. [MAJOR] resume_rule backfills charges accrued during the paused period, contradicting its own docstring

`ledgerly/recurring.py:64` — correctness

resume_rule's docstring promises 'charging resumes from now', implying occurrences during the paused window should not be retroactively charged. However, pause_rule (lines 55-60) only sets active=0 and never touches last_materialized, and resume_rule (lines 63-68) only sets active=1 without resetting last_materialized to the resume date. Since materialize_due (lines 125-140) computes occurrences from the rule's stored last_materialized up to today for any active rule, resuming a rule that had accumulated history before being paused will cause materialize_due to backfill every occurrence that fell within the paused interval (e.g., a monthly rule last materialized in January, paused in February, resumed in April, will generate charges for the missed February and March occurrences on the next materialize_due call) instead of resuming from now as documented. The test `test_resume_reactivates` doesn't catch this because the rule is paused immediately after creation (last_materialized is still None), so the pre-existing 'first run' catch-up-from-start-of-month logic masks the missing reset and the assertion of n==1 passes coincidentally.

*Verified: Read ledgerly/recurring.py: pause_rule (55-60) and resume_rule (63-68) only toggle active, never touch last_materialized; materialize_due (115-141) always computes occurrences from stored last_materialized to today for any active rule. Reproduced live: created a monthly rule, materialized once in Jan (sets last_materialized=2026-01-10), paused, resumed, then materialized in April — got 3 backfilled charges (Feb, Mar, Apr) in one call, despite resume_rule's docstring promising 'charging resumes from now'.*

## 3. [MAJOR] Biweekly occurrence test window can't distinguish biweekly from weekly cadence

`tests/test_recurring.py:69` — test-adequacy

test_biweekly_occurrence checks occurrences_between({'cadence': 'biweekly', 'weekday': 0}, date(2026,3,2), date(2026,3,10)) == [date(2026,3,9)]. The window (start, end] only contains a single Monday (March 9); a purely weekly implementation would produce the identical result. The actual biweekly branch in ledgerly/recurring.py (lines 106-111) is byte-for-byte the same logic as the weekly branch (lines 100-105) — it fires on every matching weekday, not every second week, ignoring the reference start date entirely. This is a real bug that the test does not catch because the chosen window is too narrow. A window spanning 3+ weeks (e.g. 2026-03-02 to 2026-03-23) would show the bug: correct biweekly output should be [2026-03-09, 2026-03-23] (skipping 2026-03-16), but the current implementation returns [2026-03-09, 2026-03-16, 2026-03-23], which the existing test cannot detect.

*Verified: Read ledgerly/recurring.py lines 100-111: the 'biweekly' branch is identical logic to 'weekly' (fires on every matching weekday, never checks distance from `start` in weeks). Ran occurrences_between({'cadence':'biweekly','weekday':0}, date(2026,3,2), date(2026,3,23)) directly and got [2026-03-09, 2026-03-16, 2026-03-23] — every week, not every second week — confirming biweekly is broken. Ran the same call with the test's actual window (2026-03-02 to 2026-03-10) and got [2026-03-09], matching the test assertion, confirming the narrow window masks the bug. Full test suite (pytest tests/test_recurring.py) passes 12/12 despite this core defect.*

## 4. [MINOR] test_resume_reactivates never exercises the 'charging resumes from now' contract

`tests/test_recurring.py:87` — test-adequacy

resume_rule's docstring (ledgerly/recurring.py:64) promises 'charging resumes from now', implying occurrences that fell within the paused period should not be materialized on resume. The test pauses the rule immediately after creation, before materialize_due has ever run, so rule['last_materialized'] is still NULL when resume_rule is called. Because pause_rule/resume_rule never touch last_materialized (ledgerly/recurring.py:55-68), materialize_due falls back to the 'first run' start-of-month heuristic (line 130) regardless of the pause, and the assert n == 1 only confirms the rule is active again — not that occurrences from the paused window were skipped. If a rule is materialized once, then paused for a period spanning a due date, then resumed and materialized again, the implementation will still emit an expense for the date that occurred during the pause (last_materialized only reflects the last materialize_due call, not the pause boundary), contradicting the docstring. The current test structure avoids this scenario entirely, so it cannot fail even though the promised behavior is not implemented.

*Verified: Read ledgerly/recurring.py: pause_rule/resume_rule (lines 55-68) only toggle the `active` flag and never touch `last_materialized`; materialize_due (line 115-141) falls back to a start-of-month heuristic whenever last_materialized is NULL. Reproduced with a script: created a monthly rule, materialized it once in Feb (n=1), paused it, resumed it after a March 5 due date had passed inside the pause window, then materialized again — it still emitted the March 5 expense (n=1), directly violating resume_rule's docstring 'charging resumes from now'.*
