# Code review: Roll unused budget into the next month

> Frequently requested feature: at month end, carry each category's unspent budget into the next month. Adds a next_month helper and rollover_budgets(), plus a test.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] next_month() produces an invalid month key at year boundaries

`ledgerly/utils.py:51` — correctness

next_month(month) splits 'YYYY-MM' and computes f"{y}-{int(m)+1:02d}" without checking for month overflow. For month="2026-12", this returns "2026-13" instead of "2027-01". Since rollover_budgets() (ledgerly/reports.py:65) is specifically meant to run at month end for every month including December, calling rollover_budgets(db, user_id, "2026-12") writes a budget row with month="2026-13" via set_budget (ledgerly/reports.py:76). That key never matches any real month produced by month_of() (ledgerly/utils.py:46-48, always zero-padded 01-12) or any expense's substr(spent_on,1,7). As a result, budget_status(db, user_id, "2027-01") returns no rolled-over budget for that category — the carried-over limit is silently orphaned under an unreachable month key, and users lose their rolled-over budget every December-to-January transition.

*Verified: Ran `next_month('2026-12')` directly → returned '2026-13' instead of '2027-01'. Then reproduced the full described scenario against the real Database: set a $100 food budget for 2026-12, spent $40, called rollover_budgets(db, user, '2026-12') → returned target key '2026-13'; budget_status(db, user, '2026-13') shows the carried-over $160 budget exists under that bogus key, while budget_status(db, user, '2027-01') returns [] (empty), confirming the rolled-over budget is silently orphaned and invisible for the real next month. Grep confirms next_month() is the sole implementation used by rollover_budgets and has no year-boundary handling anywhere in the codebase.*

## 2. [MAJOR] New rollover test asserts a tautology

`tests/test_ledgerly.py:108` — test-adequacy

`assert len(status) >= 0` is always true (len() can never be negative) and therefore verifies nothing about rollover_budgets' actual behavior — not the target month returned, not the new limit value (should be 10000 + (10000-4000) = 16000), and not that a budget row was even created for the rolled-over month. This test would pass even if rollover_budgets were completely broken (e.g. if it wrote to the wrong month or computed the wrong new_limit), giving false confidence and masking the next_month year-rollover bug.

*Verified: Read tests/test_ledgerly.py:103-108 and confirmed the exact tautological assertion `assert len(status) >= 0`. Ran the actual test (passes). Then demonstrated with a direct script that this same assertion pattern would pass even for a deliberately broken rollover_budgets that writes to the wrong month ('WRONG-MONTH') with a nonsensical limit (999999) while returning a plausible-looking but incorrect target ('2026-04') — budget_status on the (empty) returned target yields status=[] and len([])>=0 is still True.*

## 3. [MINOR] Missing blank line before new function breaks file's spacing convention

`ledgerly/reports.py:59` — correctness

Every other top-level function in this file (set_budget, monthly_summary, budget_status) is separated by two blank lines per PEP 8, but rollover_budgets is preceded by only one blank line, inconsistent with the rest of the module and easy to miss in review.

*Verified: Read ledgerly/reports.py lines 50-78 and wrote a script counting blank lines preceding each top-level def/class. BudgetError, set_budget, monthly_summary, and budget_status all have 2 blank lines before them, while rollover_budgets (line 59) has only 1 blank line before it, exactly as the finding describes.*
