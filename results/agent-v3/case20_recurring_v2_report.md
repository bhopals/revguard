# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] Biweekly test uses a date range with only one matching weekday, so it can't distinguish biweekly from weekly

`tests/test_recurring.py:69` — test-adequacy

`test_biweekly_occurrence` queries `occurrences_between` over the 8-day window (2026-03-02, 2026-03-10], which contains exactly one Monday (2026-03-09). The implementation's 'biweekly' branch (recurring.py:106-111) is a verbatim copy of the 'weekly' branch — it fires every week, not every second week — yet this test still passes because the tested window is too short to expose more than one occurrence of the weekday. A correct test needs a range spanning at least 3-4 weeks (e.g. 2026-03-02 to 2026-03-30) so it can assert that intermediate Mondays (e.g. 2026-03-16) are skipped. As written, the test is a tautology with respect to the claimed 'every second week' behavior and would pass unchanged even if biweekly were literally aliased to weekly, which is exactly the bug present in the shipped code.

*Verified: Read recurring.py:100-111: the 'biweekly' branch is byte-for-byte identical to the 'weekly' branch (no every-other-week filtering logic exists anywhere). Ran occurrences_between with rule cadence='biweekly' over 2026-03-02..2026-03-30: it returned all four Mondays (03-09, 03-16, 03-23, 03-30) instead of skipping alternating weeks, proving biweekly behaves exactly like weekly. Ran the actual shippe*

## 2. [MAJOR] Biweekly cadence fires every week, not every second week

`ledgerly/recurring.py:106` — correctness

The `biweekly` branch of occurrences_between (lines 106-111) is byte-for-byte identical to the `weekly` branch (lines 100-105): it appends every date in (start, end] whose weekday matches, with no anchoring to determine odd/even weeks relative to rule creation or a prior occurrence. A rule with cadence='biweekly' will therefore materialize an expense every single week, exactly like a weekly rule, doubling the intended charge frequency (e.g. a $50 biweekly subscription becomes $100/month instead of ~$25/2wk over a month). The included test (test_biweekly_occurrence) only checks a single 8-day window, so it can't distinguish 'every week' from 'every second week' and passes despite the bug.

*Verified: Read ledgerly/recurring.py lines 100-112: the biweekly branch is byte-identical logic to weekly (checks only d.weekday() == rule['weekday'], no parity/anchor check). Executed occurrences_between with a biweekly Monday rule over a 4-week window (2026-03-02 to 2026-03-30): got all 4 Mondays [03-09, 03-16, 03-23, 03-30] instead of the expected 2, proving it fires every week. The included test only co*

## 3. [MAJOR] resume_rule backfills charges accrued during the pause instead of resuming 'from now'

`ledgerly/recurring.py:63` — correctness

pause_rule (line 55) only flips active=0 and never advances last_materialized; materialize_due (line 122) filters on active=1, so last_materialized stays frozen at whatever it was before the pause. resume_rule's docstring promises 'charging resumes from now,' but it (line 63-68) also never touches last_materialized. Consequently, the next materialize_due call after resume computes `start = parse_iso_date(rule['last_materialized'])` from before the pause and materializes every occurrence that fell inside the entire paused interval. Example: a monthly rule last materialized 2026-01-15, paused on 2026-01-20, resumed on 2026-04-01 — calling materialize_due(today=2026-04-01) will create backdated expenses for Feb 5 and Mar 5 even though the rule was suspended that whole time, contradicting the stated 'resumes from now' guarantee and silently charging the user for a period they explicitly paused. The included tests never call materialize_due before pausing, so this backfill is not exercised.

*Verified: Read ledgerly/recurring.py: pause_rule (line 55-60) only sets active=0, resume_rule (63-68) only sets active=1; neither touches last_materialized. materialize_due (115-141) queries only active=1 rows and computes start from rule['last_materialized']. Reproduced with a live script: created a monthly rule, set last_materialized='2026-01-15', called pause_rule then resume_rule, then materialize_due(t*
