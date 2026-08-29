# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] next_month doesn't roll over the year at December

`ledgerly/utils.py:51` — correctness

next_month(month) splits 'YYYY-MM' and does int(m) + 1 without ever incrementing the year or wrapping the month back to 01. Calling next_month('2026-12') returns '2026-13' instead of '2027-01'. Since rollover_budgets(db, user_id, '2026-12') calls next_month internally and then writes budgets via set_budget(db, user_id, category, '2026-13', new_limit) (reports.py:65,76), it silently inserts a budget row with an invalid month key. No expense's spent_on will ever match substr(spent_on,1,7) == '2026-13' in monthly_summary/budget_status, and no real 'YYYY-MM' month string produced by month_of() will ever equal '2026-13', so the rolled-over budget becomes permanently orphaned/invisible for any December-to-January rollover — the exact 'month end' scenario the PR's description highlights as the target use case.

*Verified: Ran `next_month('2026-12')` directly: returns '2026-13' instead of '2027-01' (no year increment or month wrap in ledgerly/utils.py:50-53, confirmed by reading the source, matches diff exactly). Then reproduced full end-to-end scenario: set_budget for 'food' in '2026-12', called reports.rollover_budgets(db, user, '2026-12') which returns target='2026-13'; budget_status(db, user, '2026-13') shows the rolled-over budget row exists there, but budget_status(db, user, '2027-01') (the real next month) returns an empty list — the rolled-over budget is invisible under the correct month key. This is precisely the December-to-January rollover scenario the PR targets.*

## 2. [MAJOR] rollover_budgets silently overwrites an existing budget already set for the target month

`ledgerly/reports.py:76` — correctness

rollover_budgets computes new_limit purely from the from_month's limit and spend, then calls set_budget(db, user_id, b['category'], target, new_limit), which performs an INSERT ... ON CONFLICT DO UPDATE (reports.py:13-19). If the user has already explicitly configured a budget for the target month (e.g. they set next month's 'food' budget to $50 before running rollover), rollover_budgets overwrites it with the computed carry-over value instead of adding to it or preserving the user's explicit choice, with no check for an existing target-month budget and no warning. This silently discards budget data the user configured for the destination month.

*Verified: Read reports.py: set_budget (lines 10-19) does INSERT ... ON CONFLICT DO UPDATE SET limit_cents = excluded.limit_cents unconditionally, and rollover_budgets (lines 59-77) calls it with a computed carry-over value with no prior check for an existing target-month budget. Reproduced live: set food budget to $100 for 2026-03, spent $40; explicitly set food budget for 2026-04 to $50 (simulating a user's own choice); called rollover_budgets(db, user, '2026-03'). Result: budget_status for 2026-04 showed limit $160.00 (100 + 60 carry), silently discarding the user's explicit $50 setting.*

## 3. [MAJOR] test_rollover assertion is a tautology that can never fail

`tests/test_ledgerly.py:108` — test-adequacy

`len(status) >= 0` is always true since `len()` never returns a negative number; this assertion cannot fail regardless of what `rollover_budgets` does. The test sets a $100 budget, spends $40, then calls `rollover_budgets` and checks the resulting month's status — but never asserts the actual carried-over limit (expected $160: original $100 limit + $60 unspent per the docstring), never asserts the target month string returned, and never asserts `status` is non-empty (a bug that broke `set_budget`/`budget_status` wiring for the target month would still pass since an empty list also satisfies `len(status) >= 0`). This test provides no real coverage for the new `rollover_budgets` function or the arithmetic it promises in its docstring.

*Verified: Read tests/test_ledgerly.py:107-108, confirmed the exact code from the diff: `assert len(status) >= 0`, which is mathematically always true since len() never returns negative. Ran the real test (passes). Then replaced rollover_budgets with a stub that does nothing but compute and return the target month string (no budgets set, no arithmetic) and reran test_rollover — it still PASSED, proving the test provides zero real verification of the function's behavior, arithmetic, or wiring. Restored original file afterward.*
