# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [?] next_month does not roll over the year for December

`ledgerly/utils.py:54` — correctness

next_month('2026-12') computes int('12')+1 = 13 and returns '2026-13', an invalid month key that never matches any real date's month_of() output. rollover_budgets(db, user_id, '2026-12') will therefore silently create budgets under the bogus month '2026-13' that are permanently unreachable by budget_status/monthly_summary for any real month, effectively losing the rolled-over budget for every December-to-January transition (a case guaranteed to occur every year).

## 2. [?] Rollover formula doubles the budget instead of carrying only the unspent remainder

`ledgerly/reports.py:75` — correctness

new_limit = b['limit_cents'] + carry, where carry = max(limit - spent, 0). Since the same limit_cents is used both as the base and to compute the unspent carry, if a category is fully unspent in a month, new_limit becomes 2x the original limit (e.g. limit=10000, spent=0 -> new_limit=20000), not limit+leftover-from-a-separate-base as the docstring implies. Running rollover_budgets repeatedly across consecutive months with little/no spending causes the budget to compound geometrically (10000 -> 20000 -> 40000 -> ...) rather than simply accumulating the unspent leftover, which is very likely not the intended 'carry unspent budget' behavior and will produce runaway budget limits in real usage.

## 3. [?] test_rollover assertion is a tautology and verifies nothing

`tests/test_ledgerly.py:108` — test-adequacy

assert len(status) >= 0 is always true regardless of behavior (len() can never be negative), so this test cannot fail even if rollover_budgets computes the wrong target month, the wrong new_limit, or fails to create any budget row at all. It gives false confidence that the new rollover feature (including the doubling bug and the December year-rollover bug above) is covered by tests.
