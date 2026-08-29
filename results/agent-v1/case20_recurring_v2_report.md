# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Biweekly cadence fires every week, not every second week

`ledgerly/recurring.py:106` — correctness

The `else` branch handling `cadence == "biweekly"` (lines 106-111) is byte-for-byte identical to the weekly branch above it: it emits every date matching `rule["weekday"]` in `(start, end]`, with no check on how many weeks have elapsed since a reference date. So a biweekly rule for e.g. Monday will materialize an expense every single Monday, exactly like a weekly rule — silently doubling the number and total amount of charges a user expects for a 'biweekly' subscription. The included test (`TestBiweekly.test_biweekly_occurrence`) uses an 8-day window (2026-03-02 to 2026-03-10) that contains only one Monday, so it cannot distinguish 'every week' from 'every second week' and passes despite the bug.

## 2. [MAJOR] resume_rule backfills all charges accrued during the paused period instead of resuming from now

`ledgerly/recurring.py:63` — correctness

resume_rule's docstring promises 'charging resumes from now', but resume_rule (and pause_rule) never touch `last_materialized`. Because materialize_due (lines 125-140) skips inactive rules entirely, `last_materialized` stays frozen at whatever it was when the rule was paused. When the rule is reactivated and materialize_due next runs, occurrences_between is computed from that stale `last_materialized` up to today, so every occurrence that fell inside the pause window gets materialized in one burst on resume — e.g. pause a weekly Monday rule for 4 weeks, resume it, and the next materialize_due call creates 4 expenses at once, effectively charging the user retroactively for the paused period. This contradicts the documented pause/resume behavior and is a new failure mode introduced by this PR, since reactivation was previously impossible (deactivate_rule was permanent). The included tests only exercise a rule that was never materialized before being paused, so they never observe the backfill.
