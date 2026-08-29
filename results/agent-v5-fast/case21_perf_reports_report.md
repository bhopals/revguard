# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] LEFT JOIN missing month filter on expenses

`ledgerly/reports.py:44` — correctness

The refactored budget_status query joins expenses without filtering by month. The ON clause only matches e.user_id = b.user_id and e.category = b.category, so it aggregates expenses from all months, not just the specified month. The WHERE clause filters budgets but not the joined expenses. This causes SUM(e.amount_cents) to include expenses from months other than the queried month, breaking the function's contract and returning wrong budget status. Scenario: budget for 2026-03 with limit $10.00, $5 spent in 2026-02, $6 spent in 2026-03. budget_status(..., '2026-03') should report spent=$6.00 but will report spent=$11.00 (over budget by $1 instead of under by $4).

*Verified: Read ledgerly/reports.py: the LEFT JOIN's ON clause only matches e.user_id = b.user_id AND e.category = b.category, with no month/spent_on filter on expenses; the WHERE clause only filters budgets. Reproduced with a live SQLite DB: inserted a $10.00 budget for category 'food' in 2026-03, a $5.00 expense in 2026-02, and a $6.00 expense in 2026-03. budget_status(db, 1, '2026-03') returned spent='$11.00', remaining='-$1.00', over_budget=True — matching the finding's predicted wrong output exactly, instead of the correct spent='$6.00', remaining='$4.00', over_budget=False. This is a genuine, reachable correctness bug in the refactored query, not a test-coverage issue.*
