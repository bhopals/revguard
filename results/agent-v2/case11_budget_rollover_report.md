# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] next_month does not roll over the year for December

`ledgerly/utils.py:51` — correctness

next_month("2026-12") computes int("12")+1=13 and returns "2026-13", an invalid month key instead of "2027-01". This is called from rollover_budgets (ledgerly/reports.py:65). Any user who runs rollover for a December budget gets a budget row inserted with month="2026-13". Since all other month keys are produced by month_of() (ledgerly/utils.py:46-48) via real date objects, "2026-13" can never equal a real spent_on month (reports.py:27 uses substr(spent_on,1,7)) nor be looked up by any legitimate budget_status(db, user_id, month) call (reports.py:43) — the rolled-over budget becomes permanently orphaned/inaccessible, silently losing the carried-over funds for that category with no error raised.

## 2. [MAJOR] test_rollover asserts a tautology and never verifies rollover behavior

`tests/test_ledgerly.py:108` — test-adequacy

The only assertion is `assert len(status) >= 0`, which is always true since `len()` can never be negative. The test does not check that `rollover_budgets` created a budget in the target month, that the new limit equals original_limit + unspent carry (10000 + 6000 = 16000 in this scenario), or that the returned `target` month string is correct ('2026-04'). As written, this test would still pass even if `rollover_budgets` did nothing at all, wrote the wrong limit, wrote to the wrong month, or raised no error while silently corrupting data. It provides no regression protection for the new feature.
