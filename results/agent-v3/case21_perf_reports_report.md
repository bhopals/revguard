# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status aggregates all-time expenses instead of the target month

`ledgerly/reports.py:44` — correctness

The rewritten query joins expenses to budgets only on `e.user_id = b.user_id AND e.category = b.category`, with no filter tying `e.spent_on` to the requested `month`. The old code computed `spend` via `monthly_summary()`, which filters expenses with `substr(spent_on, 1, 7) = ?month` (reports.py:27) before matching them to that month's budgets. The new query drops this filter entirely, so `spent` becomes the category's all-time total spend across every month the user has ever recorded expenses in, not just the queried month. Concretely: a user with a $50 budget for 'groceries' in 2026-08 who spent $40 in July and $10 in August will see `spent` = $50 for August (all-time) instead of $10, incorrectly flagging `over_budget` and reporting wrong 'remaining'/'spent' amounts. This also silently breaks `run_budget_alerts` (notify.py:54), which relies on budget_status to fire one-time over-budget notifications per (category, month) — it will now over-fire and report inflated spend in the alert body, contradicting the PR's stated 'no behavior change intended'.

*Verified: Read ledgerly/reports.py:40-49 — the LEFT JOIN condition is `e.user_id = b.user_id AND e.category = b.category` with no predicate tying e.spent_on to the queried month; the WHERE clause only filters budgets (b.user_id, b.month). Reproduced with an in-memory DB: inserted a $50 groceries budget for 2026-08, a $40 expense in 2026-07, and a $10 expense in 2026-08. `budget_status(db, 1, '2026-08')` ret*

## 2. [MAJOR] No test catches missing month filter in rewritten budget_status query

`tests/test_ledgerly.py:96` — test-adequacy

The PR rewrote budget_status's SQL to LEFT JOIN expenses to budgets on user_id and category only, dropping the month filter on expenses.spent_on that the old monthly_summary()-based implementation had (via substr(spent_on,1,7) = month). This means spent is now summed across ALL months for that category, not just the requested month — a real behavior change despite the PR claiming 'no behavior change intended'. Neither test_budget_status (line 96-101) nor test_budget_upsert (line 103-107) was updated or extended to add an expense in a different month; both only add expenses within the queried month '2026-03', so they pass identically whether or not the query is month-scoped. A test that adds an expense in e.g. '2026-04' for the same category and then calls budget_status(db, user, '2026-03') would fail on this PR's code (spent/over_budget would incorrectly include the April expense) but was never added, so the regression ships undetected.

*Verified: Read ledgerly/reports.py: budget_status's new SQL joins expenses to budgets on user_id and category only, with no filter on expenses.spent_on's month (unlike monthly_summary which uses substr(spent_on,1,7)=month). Reproduced with a script: added a $3.50 March food expense and a $10.00 April food expense with a $3.00 budget for March; budget_status(db, user, '2026-03') returned spent='$13.50' (shou*
