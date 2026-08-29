# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Biweekly cadence fires every week, not every second week

`ledgerly/recurring.py:106` — correctness

The `biweekly` branch of occurrences_between (lines 106-111) is logically identical to the `weekly` branch: it appends every date in (start, end] whose weekday matches rule['weekday'], with no tracking of week parity relative to any anchor date. There is also no column in recurring_rules (see ledgerly/db.py CREATE TABLE recurring_rules) to store a rule creation/anchor date that would let the code determine 'every second week'. As a result, a rule created with cadence='biweekly' materializes an expense every single week — double the intended frequency — silently overcharging the user's tracked spending. The included test (test_biweekly_occurrence) only checks an 8-day window containing exactly one matching Monday, so it can't distinguish weekly-every-week behavior from true biweekly behavior and passes despite the bug.

*Verified: Read ledgerly/recurring.py lines 100-111: the biweekly branch is logically identical to the weekly branch (same loop, same weekday check, no parity/anchor tracking, only a misleading comment differs). Confirmed via execution: occurrences_between({'cadence':'biweekly','weekday':0}, date(2026,3,2), date(2026,4,13)) returned all 6 Mondays in the 6-week window instead of 3, proving it fires every week. Also checked ledgerly/db.py CREATE TABLE recurring_rules schema — there is no anchor/creation-date column anywhere, so no mechanism exists to compute week parity for true biweekly cadence.*

## 2. [MAJOR] resume_rule contradicts its own docstring by backdating charges accrued during the pause

`ledgerly/recurring.py:63` — correctness

resume_rule's docstring (line 64) promises 'charging resumes from now', but the implementation (lines 65-68) only sets active=1 and never touches last_materialized. Since materialize_due (line 121-124) only queries active=1 rules and only advances last_materialized for rules it processes, a paused rule's last_materialized stays frozen at whatever it was before pause_rule was called. Concretely: create a monthly rule that materializes on 2026-03-06 (last_materialized='2026-03-06'), pause it, leave it paused through April and May, then resume_rule on 2026-06-01. The next materialize_due call computes occurrences_between(rule, start=2026-03-06, end=today) and will create backdated expenses for every monthly/weekly occurrence that fell inside the paused window (e.g. Apr 5, May 5), even though the rule was suspended the whole time. This directly contradicts the documented 'resumes from now' guarantee and produces surprise historical charges. Neither test_resume_reactivates nor any other test covers a pause/resume cycle spanning more than one materialization period, so this gap isn't caught.

*Verified: Read ledgerly/recurring.py: resume_rule (lines 63-68) only sets active=1 and never updates last_materialized; materialize_due (115-141) queries only active=1 rules and computes start from the frozen last_materialized.*

## 3. [MAJOR] Biweekly occurrence test cannot detect that the cadence fires every week instead of every second week

`tests/test_recurring.py:68` — test-adequacy

occurrences_between()'s biweekly branch (ledgerly/recurring.py:106-111) is byte-for-byte identical to the weekly branch: it matches every date whose weekday equals rule['weekday'], with no logic to skip alternate weeks. The only test for this, test_biweekly_occurrence, uses a date range of just 9 days (2026-03-02 to 2026-03-10), which contains exactly one Monday (2026-03-09) regardless of whether the cadence is weekly or biweekly. So the test passes identically whether or not the 'every second week' behavior is implemented, and gives false confidence that the biweekly feature works. A range spanning 3+ weeks (e.g. 2026-03-02 to 2026-03-23, which has Mondays on 3/9, 3/16, 3/23) would show the real bug: it should return only [3/9, 3/23] for true biweekly but the current code returns [3/9, 3/16, 3/23]. As shipped, any user creating a 'biweekly' rule will actually be charged every week, and no test catches it.

*Verified: Read ledgerly/recurring.py:97-110: the biweekly branch is logically identical to the weekly branch (same loop, same `d.weekday() == rule['weekday']` check, no anchor-date or week-parity logic to skip alternate weeks). Ran `occurrences_between({'cadence':'biweekly','weekday':0}, 2026-03-02, 2026-03-23)` and got `[2026-03-09, 2026-03-16, 2026-03-23]` — every Monday, not every second one — proving the biweekly cadence fires weekly. The shipped test `test_biweekly_occurrence` only spans 2026-03-02 to 2026-03-10 (one Monday), so it passes regardless; ran `pytest -k biweekly` and confirmed both tests pass despite the bug. Grepped the whole file for any parity/skip logic and found none.*

## 4. [MINOR] pause_rule duplicates deactivate_rule instead of reusing it, and neither is updated to know about the other

`ledgerly/recurring.py:55` — correctness

`pause_rule` (lines 55-60) has an identical body to the pre-existing `deactivate_rule` (lines 43-52): both set `active = 0` after an ownership check. `deactivate_rule` still inlines its own SELECT/ownership check instead of being refactored to use the new `_own_rule` helper, so the same 5-line ownership check now exists in two places (43-49 and 71-77) that can silently drift apart. The PR should have either made `deactivate_rule` an alias for `pause_rule` (or vice versa) or removed one entirely; keeping both as separate, functionally-identical public entry points is confusing for callers deciding which one to use, and doubles the maintenance surface for what is one operation.

*Verified: Read ledgerly/recurring.py directly. deactivate_rule (lines 43-52) inlines a SELECT/ownership check identical to the new _own_rule helper (lines 71-78) instead of calling it, and pause_rule (lines 55-60) is functionally identical to deactivate_rule (ownership check + `active = 0` update) but does call _own_rule. Grep confirms both are used as separate public functions in tests/test_recurring.py with no aliasing or deduplication between them, so the same ownership-check logic exists in two places (43-49 and 71-77) and two near-duplicate deactivation entry points exist.*
