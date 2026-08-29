# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] next_month does not roll over the year for December

`ledgerly/utils.py:51` — correctness

next_month splits 'YYYY-MM' and computes int(m) + 1 without handling m == 12: next_month('2026-12') returns '2026-13' instead of '2027-01'. rollover_budgets (ledgerly/reports.py:65) uses this as the target month passed to set_budget, so rolling over a December budget silently creates a budget row for the nonexistent month '2026-13'. That row will never match monthly_summary or budget_status queries for the real next month (which filter on 'substr(spent_on,1,7) = ?' or 'month = ?' with a correctly formatted key), so the carried-over budget becomes permanently invisible/unusable — the rollover feature silently fails for every year boundary.

*Verified: Ran `python3 -c "from ledgerly.utils import next_month; print(next_month('2026-12'))"` which printed '2026-13' instead of '2027-01', confirming no year-rollover handling for month=12. Verified via grep that reports.py budget_status/monthly_summary filter with exact string equality ('month = ?' and 'substr(spent_on,1,7) = ?'), so a budget row stored under '2026-13' would never be matched by real-Ja*

## 2. [MAJOR] test_rollover assertion is a tautology that can never fail

`tests/test_ledgerly.py:108` — test-adequacy

`assert len(status) >= 0` is always true since `len()` never returns a negative number. This test exercises `rollover_budgets` and `next_month` but verifies nothing about their behavior: it does not check that `target` equals "2026-04", that a budget row was actually created in the target month, or that the rolled-over limit equals the expected 10000 + (10000-4000) = 16000 cents ("$160.00"). A completely broken implementation of `rollover_budgets` (e.g. one that writes to the wrong month, computes the wrong carry amount, or silently no-ops) would still pass this test. The PR's core new behavior — correct carry-over math and correct target-month computation — ships with no real test coverage.

*Verified: Read tests/test_ledgerly.py:108 confirming the sole assertion is `assert len(status) >= 0`. Ran the test as-is (passed), then patched ledgerly/reports.py so rollover_budgets never calls set_budget (a no-op stub) and reran `pytest -k test_rollover` — it still passed. This proves the test provides no coverage of the new rollover math/target-month behavior; a completely broken implementation passes u*
