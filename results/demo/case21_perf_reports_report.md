# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] budget_status sums all-time expenses instead of the requested month

`ledgerly/reports.py:44` — correctness

The new LEFT JOIN in budget_status joins expenses to budgets on user_id and category only (lines 44-45), with no filter on expenses.spent_on. The old implementation computed spend via monthly_summary(), which filtered with `substr(spent_on, 1, 7) = ?` (reports.py:27) to restrict totals to the requested month. Now, for a budget on category 'food' for month '2026-03', the query sums every expense ever recorded in that category for that user, across all months, not just March. For example, a user with $50 spent in food in January and a $30 budget set for March with no March expenses would now show spent=$50 and over_budget=True for March, even though March spend is $0. This directly contradicts the function's docstring ('Compare spend against each budget set for the month') and the PR's explicit claim of 'No behavior change intended'. The bug is not caught by tests because every existing budget_status test only adds expenses within the same month being queried (tests/test_ledgerly.py:96-107).

*Verified: Read ledgerly/reports.py:40-49: the new LEFT JOIN in budget_status joins expenses to budgets on user_id and category only, with no spent_on/month filter on the expenses side (only budgets.month is filtered in WHERE). Reproduced with a live script: created a user, added a $50 'food' expense dated 2026-01-15, set a $30 'food' budget for month 2026-03, then called budget_status(db, user, '2026-03'). Output: {'category': 'food', 'limit': '$30.00', 'spent': '$50.00', 'remaining': '-$20.00', 'over_budget': True} — despite zero March expenses, confirming the query sums all-time spend for the category rather than just the requested month.*

## 2. [CRITICAL] New CREATE INDEX lacks IF NOT EXISTS, crashing on reopen of a persistent database

`ledgerly/db.py:100` — robustness

SCHEMA is executed via executescript() every time a Database is constructed (db.py:111), and every CREATE TABLE statement uses 'IF NOT EXISTS' to make this idempotent for existing database files. The newly added 'CREATE INDEX idx_expenses_user_category ON expenses (...)' statement omits 'IF NOT EXISTS'. For any file-backed database (Database(path) with a real path, the normal production use case since the constructor accepts an arbitrary path), the first run creates the index successfully, but any subsequent process start against the same database file raises sqlite3.OperationalError: index idx_expenses_user_category already exists, since executescript() runs unconditionally on init. This is a crash-on-reopen regression introduced by this PR; it is masked in the test suite because tests only use the in-memory default (':memory:'), which never persists the index across Database() instantiations.

*Verified: Read ledgerly/db.py: SCHEMA (lines 9-102) has all CREATE TABLE statements using 'IF NOT EXISTS' but the new CREATE INDEX at line 100-101 omits it, and __init__ (line 111) runs executescript(SCHEMA) unconditionally on every Database() construction. Reproduced with a real script: created a file-backed Database('/tmp/test_ledgerly.db'), closed it, then reopened Database() against the same path -> raised sqlite3.OperationalError: index idx_expenses_user_category already exists, exactly as described.*
