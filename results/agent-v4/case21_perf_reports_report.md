# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status join drops the month filter on expenses, aggregating all-time spend instead of the requested month's spend

`ledgerly/reports.py:44` — correctness

The rewritten query joins `expenses e` to `budgets b` only on `e.user_id = b.user_id AND e.category = b.category` — it never constrains `e.spent_on` to the requested month. The old code computed `spend` via `monthly_summary`, which filters expenses with `substr(spent_on, 1, 7) = ?` (the month), so `spent` was always scoped to the queried month. Now `spent` is the SUM of every expense the user has ever logged in that category, across all months. Concrete failure: a user sets a $50/month 'food' budget for 2026-03, spends $40 in 2026-01 and $20 in 2026-03 (well under budget for March). `budget_status(db, user, '2026-03')` will report spent=$60, remaining=-$10, and over_budget=True, even though March spend is only $20 and under budget. This also corrupts `run_budget_alerts` in ledgerly/notify.py, which calls `budget_status` directly and fires an 'over_budget' notification based on the inflated, cross-month total — a user could receive incorrect over-budget alerts driven entirely by spending from unrelated months. This directly contradicts the PR's own description ('No behavior change intended') and the function's docstring ('Compare spend against each budget set for the month').

*Verified: Read ledgerly/reports.py: the LEFT JOIN condition is `e.user_id = b.user_id AND e.category = b.category` only, with no constraint on e.spent_on, while the WHERE clause filters only budgets (b.user_id, b.month). Reproduced with a live SQLite DB matching the reviewer's exact scenario: user has a $50 'food' budget for 2026-03, spends $40 in 2026-01 and $20 in 2026-03. budget_status(db, user, '2026-03') returned spent='$60.00', remaining='-$10.00', over_budget=True — i.e. all-time spend across months, not just March's $20.*

## 2. [MAJOR] budget_status tests don't cover cross-month expenses, missing the new query's dropped month filter

`tests/test_ledgerly.py:96` — test-adequacy

The PR rewrites budget_status's query to join budgets to expenses only on user_id and category (ledgerly/reports.py:44-46), with no condition on expenses.spent_on/month, so 'spent' now aggregates a category's expenses across ALL months, not just the requested one. Both test_budget_status (line 96-101) and test_budget_upsert (line 103-107) only add expenses within the same month being queried ('2026-03'), so they cannot detect this regression. A test that adds an expense in a different month (e.g., '2026-04') for the same category and asserts it is excluded from the March budget_status result would fail against the new implementation, but no such test exists, letting the query bug pass CI.

*Verified: Read ledgerly/reports.py:44-46: budget_status's new SQL joins budgets to expenses only on user_id and category, with no filter on expenses.spent_on/month. Reproduced with a script: added a $2.00 March 'food' expense and a $9.00 April 'food' expense with a $10.00 March budget; budget_status(db, user, '2026-03') returned spent='$11.00' (should be '$2.00'), confirming cross-month expenses leak into the result. Ran the existing tests (test_budget_status, test_budget_upsert at lines 96-107) with pytest -k budget: both pass, since they only add expenses within the same queried month ('2026-03'), so they cannot catch this regression. This matches the finding precisely.*

## 3. [MAJOR] Undocumented durability trade-off from PRAGMA synchronous = OFF

`ledgerly/db.py:110` — correctness

The PR silently drops SQLite's fsync-on-commit guarantee (synchronous=OFF means writes are not flushed to disk before the OS reports success), with no comment explaining the trade-off, no mention in the PR description of the durability implications (an OS crash or power loss can now corrupt the database or lose committed transactions), and no accompanying WAL-mode change that is typically paired with this setting. A future maintainer reading this line has no way to know this was an intentional, understood risk versus an oversight, and 'no behavior change intended' in the PR description is misleading since this is a real behavior change for crash safety.

*Verified: Read ledgerly/db.py:110 and confirmed the diff adds `self.conn.execute("PRAGMA synchronous = OFF")` with no accompanying comment. Verified via `python3 -c` that this pragma actually sets synchronous mode to 0 (OFF), which per SQLite semantics means the engine does not wait for data to be flushed to disk before reporting a transaction committed, risking corruption/lost transactions on OS crash or power loss. Grepped the whole repo for 'journal_mode'/'WAL' and found none, confirming no WAL pairing exists anywhere on this code path. Grepped for any other 'synchronous' references and found only this one line, confirming it is new/undocumented.*
