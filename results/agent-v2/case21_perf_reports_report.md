# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status now sums all-time expenses instead of the target month's

`ledgerly/reports.py:44` — correctness

The LEFT JOIN in budget_status (lines 44-46) joins expenses to budgets on user_id and category only, with no condition on spent_on/month. The old code computed spend via monthly_summary, which filters expenses with `substr(spent_on, 1, 7) = ?` for the given month. Now `spent` for each category is the SUM of amount_cents across every expense ever recorded in that category for the user, regardless of month. Example: a user has a $50 grocery budget for 2026-08 and spent $30 in July and $10 in August; budget_status('2026-08') will report spent=$40 (July+August combined) instead of the correct $10, incorrectly showing remaining=$10 instead of $40, and could wrongly flag over_budget or hide a real overage in other months. This directly contradicts the PR's 'no behavior change intended' claim and the function's docstring ('Compare spend against each budget set for the month').

## 2. [MAJOR] No test covers cross-month expense leakage introduced by the single-query rewrite

`tests/test_ledgerly.py:96` — test-adequacy

The PR rewrites budget_status's SQL (ledgerly/reports.py:40-49) to LEFT JOIN expenses to budgets on user_id and category only, with no month/spent_on filter on the expenses side (monthly_summary at line 27 correctly filters via substr(spent_on,1,7)=month, but the new budget_status query does not). This means an expense recorded in a different month than the requested budget month, but in the same category, is now incorrectly included in the 'spent' total. The existing tests (test_budget_status at line 96-101, test_budget_upsert at line 103-107) only add expenses within the same month as the budget being queried, so they cannot detect this regression despite it directly contradicting the PR's 'no behavior change intended' claim. A test adding an expense in a different month (e.g., '2026-04-01') for the same user/category as a '2026-03' budget, then asserting budget_status for '2026-03' does NOT include that expense, would have caught this.
