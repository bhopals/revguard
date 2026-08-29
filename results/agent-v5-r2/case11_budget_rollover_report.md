# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] next_month does not roll over the year at December

`ledgerly/utils.py:51` — correctness

next_month splits 'YYYY-MM' and does f"{y}-{int(m)+1:02d}" without checking for month 12. Calling next_month('2026-12') produces '2026-13' instead of '2027-01'. Since rollover_budgets(db, user_id, '2026-12') uses this as the target month for set_budget, the rolled-over budget is stored under the nonexistent month key '2026-13'. Any subsequent budget_status/monthly_summary call for the real next month '2027-01' will find no budget (WHERE month = ? does an exact string match), silently losing the carried-over budget for every year-end rollover.

*Verified: Read ledgerly/utils.py:51-54, confirmed next_month does int(m)+1 with no month-12 handling. Executed next_month('2026-12') -> '2026-13'. Ran full end-to-end repro: set_budget for 2026-12, add_expense, rollover_budgets(db, user, '2026-12') returns target='2026-13'; budget_status(db, user, '2027-01') returns [] (empty) despite the carried-over budget existing, while budget_status(db, user, '2026-13') shows the budget. This confirms the carried-over budget is silently stored under a nonexistent month key and is unreachable via the real next month, exactly as described. No correction/safeguard exists elsewhere in the codebase.*

## 2. [MAJOR] test_rollover asserts a tautology and cannot fail

`tests/test_ledgerly.py:108` — test-adequacy

The only assertion in test_rollover is `assert len(status) >= 0` (line 108). `len()` of a list can never be negative, so this assertion always passes regardless of what `rollover_budgets` and `budget_status` return — even if `rollover_budgets` raised no error but produced an empty or wrong list, or if `budget_status` returned garbage, the test would still pass. The test sets up a budget of 10000 cents with 4000 spent (expecting a rolled-over limit of 10000 + 6000 = 16000 for the target month), but never checks the category, limit, spent, or remaining values of `status[0]`, nor does it check the value of `target` (the month key returned by `rollover_budgets`/`next_month`). As written, this test would pass even if `rollover_budgets` did nothing to the budgets table, or if `next_month('2026-03')` returned an incorrect month key, providing no real regression protection for the new feature.

*Verified: Read tests/test_ledgerly.py:108, confirming the only assertion in test_rollover is `assert len(status) >= 0`. Ran pytest -k test_rollover: passes. Then reproduced the test body with rollover_budgets replaced by a stub that does nothing to the budgets table and returns a garbage month key ('not-a-real-month'); budget_status on that key returned [] and `assert len(status) >= 0` still passed. This proves the assertion is a true tautology (len() of a list is always >= 0) that cannot detect a broken or no-op rollover_budgets, an incorrect next_month calculation, or wrong budget_status contents.*

## 3. [MAJOR] rollover_budgets silently overwrites a budget already set for the target month

`ledgerly/reports.py:76` — correctness

rollover_budgets computes a new_limit purely from from_month's data and calls set_budget(db, user_id, category, target, new_limit), which performs an INSERT ... ON CONFLICT DO UPDATE. If the user (or another process) already explicitly set a budget for the target month/category (e.g. planned a higher April budget of $200 before March ends), running rollover_budgets for March will overwrite that April budget with the computed carry-over value, discarding the user's explicit setting with no warning or merge logic. This is a real data-loss scenario whenever rollover is run after a future-month budget has already been configured.

*Verified: Read ledgerly/reports.py: set_budget performs INSERT ... ON CONFLICT (user_id,category,month) DO UPDATE SET limit_cents = excluded.limit_cents unconditionally, and rollover_budgets computes new_limit solely from from_month data then calls set_budget(db, user_id, category, target, new_limit) with no check of any pre-existing target-month budget. Reproduced with a live in-memory SQLite DB: set an explicit April 'food' budget of $200 (20000 cents), then a March budget of $100 with $40 spent, then ran rollover_budgets(db, user_id, '2026-03'). Result: the April budget row was overwritten to 16000 cents ($160), silently discarding the user's explicit $200 setting.*
