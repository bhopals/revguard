# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Biweekly test cannot distinguish true biweekly cadence from a plain weekly bug

`tests/test_recurring.py:68` — test-adequacy

test_biweekly_occurrence() (tests/test_recurring.py:69-73) uses the range date(2026,3,2) to date(2026,3,10), which contains exactly one Monday (2026-03-09). The implementation's 'biweekly' branch in recurring.py:106-111 is byte-for-byte identical to the 'weekly' branch (it fires on every matching weekday, with no every-other-week filtering at all) — it is effectively mislabeled weekly logic. Because the test window only spans 8 days, it can never contain two Mondays, so the test passes regardless of whether the code implements real every-second-week cadence or just fires every week. A correct test would use a longer window (e.g. spanning 3+ weeks) where true biweekly output (one occurrence per two weeks) is distinguishable from weekly output (one occurrence per week); as written, the test gives false confidence that biweekly cadence works when it actually behaves the same as weekly.

## 2. [MAJOR] Biweekly cadence fires every week, not every second week

`ledgerly/recurring.py:106` — correctness

The `else` branch for biweekly (lines 106-111) is byte-for-byte identical to the weekly branch (lines 100-105): it appends every date whose weekday matches `rule["weekday"]`, with no logic to skip alternating weeks. There is no anchor/reference date stored on the rule (recurring_rules has no such column, per ledgerly/db.py) that could be used to determine week parity, so as implemented a 'biweekly' rule behaves exactly like a 'weekly' rule and will charge the user every week instead of every other week. For example, a biweekly Monday rule materialized over a month will produce 4 occurrences instead of the expected ~2. The included test (test_biweekly_occurrence) only checks a single 8-day window containing exactly one Monday, so it cannot distinguish weekly-every-week behavior from true biweekly behavior and passes despite the bug.

## 3. [MAJOR] resume_rule backfills all occurrences missed during the pause instead of resuming 'from now' as documented

`ledgerly/recurring.py:63` — correctness

resume_rule's docstring states 'charging resumes from now,' but resume_rule only flips `active` back to 1 and never touches `last_materialized`. Meanwhile materialize_due (line 122) only updates `last_materialized` for rules that are currently active (its query filters `active = 1`), so while a rule is paused its `last_materialized` stays frozen at the value from before the pause. When the rule is resumed, the next materialize_due call computes `start = parse_iso_date(rule['last_materialized'])` (line 127), which is the pre-pause date, and generates an expense for every occurrence between that old date and today — i.e. it backfills the entire paused period rather than resuming from the current date. Concrete scenario: a monthly rent rule last materialized Jan 1 is paused on Jan 10 and resumed on Jun 15; the next materialize_due call will create 6 back-dated expenses (Jan–Jun) instead of 0, contradicting the documented 'resumes from now' behavior and silently over-charging the user for months they intended to skip. The included test only pauses and resumes within the same billing period before any materialization, so it cannot catch this backfill behavior.
