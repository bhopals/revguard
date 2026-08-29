# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status no longer filters expenses by month, summing all-time spend

`ledgerly/reports.py:44` — correctness

The rewritten query joins expenses to budgets on user_id and category only (`e.user_id = b.user_id AND e.category = b.category`), with no filter on `spent_on`/month. The original code computed spend via `monthly_summary`, which filters expenses to `substr(spent_on, 1, 7) = month`. Now every expense ever recorded in that category (across all months) is summed into `spent`, so budget_status for March will include expenses from January, February, next year, etc. Example: user has a $50 food budget for 2026-03 with a single $10 March expense, but also has a $40 February food expense; budget_status now reports spent=$50 (over_budget True) instead of the correct spent=$10. This directly contradicts the PR's 'no behavior change intended' claim and silently inflates spend/over-budget flags for any user with expense history in more than one month. The existing test (test_budget_status) only has expenses in the queried month, so it doesn't catch this.

## 2. [MAJOR] New CREATE INDEX statement is not idempotent, breaking schema re-initialization

`ledgerly/db.py:100` — robustness

Every other DDL statement in SCHEMA uses `CREATE TABLE IF NOT EXISTS`, so `executescript(SCHEMA)` is safe to run repeatedly against the same on-disk database file (e.g. app restart re-instantiating `Database(path)`). The new `CREATE INDEX idx_expenses_user_category ON expenses (...)` lacks `IF NOT EXISTS`, so the second time a process opens an existing persistent database file, `executescript` raises `sqlite3.OperationalError: index idx_expenses_user_category already exists` and `Database.__init__` fails entirely, taking down the whole app on restart. This is masked by tests because they only use the in-memory default (`Database()`), which never has a pre-existing index to collide with.

## 3. [MAJOR] synchronous=OFF risks losing/corrupting committed financial data on crash

`ledgerly/db.py:110` — robustness

Setting `PRAGMA synchronous = OFF` tells SQLite to skip fsync-ing at critical points; on an OS crash or power loss, a committed transaction can be silently lost or, in the worst case, the database file can be left corrupted (not just missing recent writes, unlike NORMAL/FULL where corruption is not possible). For a financial ledger recording money amounts, this trades correctness/durability guarantees for write speed with no compensating safeguard (e.g. WAL mode plus synchronous=NORMAL would be a safer speed/durability tradeoff). This was introduced in the same PR as an unrelated 'performance' change and isn't mentioned as a risk in the PR description ('No behavior change intended'), but it is a durability behavior change that can cause committed expense/budget writes to vanish or the DB file to corrupt after a crash.
