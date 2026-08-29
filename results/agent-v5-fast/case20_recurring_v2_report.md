# Code review: Recurring rules: biweekly cadence and pause/resume

> Adds the two most requested recurring-rule features: a biweekly cadence (every second week on a weekday) and pause/resume so users can suspend a subscription rule while keeping its history. Tests included for both.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] Biweekly cadence implementation is identical to weekly; doesn't skip alternate weeks

`ledgerly/recurring.py:106` — correctness

Lines 106-111 (biweekly branch) are a verbatim copy of lines 100-105 (weekly branch). The code appends every occurrence of the matching weekday without checking for alternation. The PR description promises 'a biweekly cadence (every second week on a weekday)' but the implementation returns all matching weekdays like weekly, not every other week. For example, a biweekly Monday rule from 2026-03-01 to 2026-03-31 will incorrectly produce [2026-03-02, 2026-03-09, 2026-03-16, 2026-03-23] instead of alternating weeks like [2026-03-02, 2026-03-16] or [2026-03-09, 2026-03-23].

*Verified: Read ledgerly/recurring.py lines 100-112: the biweekly branch (else clause) is byte-identical logic to the weekly branch, only differing by an inline comment '# biweekly'. Executed occurrences_between({'cadence':'biweekly','weekday':0}, 2026-03-01, 2026-03-31) directly: returned [03-02, 03-09, 03-16, 03-23, 03-30] — every single Monday, not alternating weeks, confirming no skip-logic exists.*

## 2. [CRITICAL] Biweekly test window too narrow to verify alternating-week behavior

`tests/test_recurring.py:69` — test-adequacy

test_biweekly_occurrence uses a 9-day range (2026-03-02 to 2026-03-10) containing only one Monday (3/9). This window cannot distinguish between a correct biweekly implementation (every other Monday) and the broken implementation (all Mondays). Both would return [2026-03-09]. To verify biweekly returns alternating occurrences, the test must cover a range with 2+ instances of the target weekday (e.g., 2026-03-02 to 2026-03-23, spanning 3 Mondays on 3/9, 3/16, 3/23) and assert only every other one is returned.

*Verified: Read ledgerly/recurring.py: the biweekly branch in occurrences_between is a byte-for-byte copy of the weekly branch (same loop, same `d.weekday() == rule['weekday']` check, no alternation logic based on start date). Ran the actual PR test (test_biweekly_occurrence) — it passes. Then reproduced occurrences_between with the same rule but a wider range (2026-03-02 to 2026-03-23, 3 Mondays): biweekly returns [3/9, 3/16, 3/23], identical to calling with cadence='weekly'. This proves biweekly is completely non-functional (behaves exactly like weekly, i.e.*
