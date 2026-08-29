# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status sums all-time spend, not month-scoped spend

`ledgerly/reports.py:44` — correctness

The new LEFT JOIN joins expenses to budgets only on user_id and category (`e.user_id = b.user_id AND e.category = b.category`), with no condition on `e.spent_on` matching the requested month. The old code computed spend via `monthly_summary`, which filtered expenses with `substr(spent_on, 1, 7) = ?` (the month param). The rewrite drops that filter entirely, so `spent` is now the lifetime total for the category across all months, not the spend for the queried month. Example: a user sets a $50 food budget for 2026-03, spends $10 in 2026-03 and $60 in 2026-01 (a prior month). `budget_status(db, user, '2026-03')` will report spent=$70 and over_budget=True even though March spend is only $10. This also feeds `notify.run_budget_alerts` (ledgerly/notify.py:54), causing spurious 'over budget' notifications based on unrelated months' spending. This directly contradicts the PR's 'No behavior change intended' claim and the function's docstring ('Compare spend against each budget set for the month').

*Verified: Read ledgerly/reports.py:37-63: the new SQL LEFT JOINs expenses to budgets only on user_id and category, with no condition tying e.spent_on to the requested month; only budgets.month is filtered. Reproduced with a live sqlite3-backed Database: created a user, a $50 'food' budget for 2026-03, a $10 expense in 2026-03 and a $60 expense in 2026-01. Calling budget_status(db, 1, '2026-03') returned spent='$70.00', remaining='-$20.00', over_budget=True — i.e. it summed the unrelated January expense into March's total, exactly as the finding describes.*

## 2. [MAJOR] New index lacks IF NOT EXISTS, causing crash on reopening an existing database file

`ledgerly/db.py:100` — robustness

SCHEMA is executed via `executescript` every time a `Database` is constructed (ledgerly/db.py:111), and every CREATE TABLE statement uses `IF NOT EXISTS` to make this idempotent for existing files. The new `CREATE INDEX idx_expenses_user_category ON expenses (...)` statement omits `IF NOT EXISTS`. Opening a `Database` a second time against the same on-disk file (e.g. restarting the app against its persistent .db file) will raise `sqlite3.OperationalError: index idx_expenses_user_category already exists`, crashing initialization. In-memory test fixtures (tests/conftest.py:9) never reopen the same connection, so this regression is not caught by the test suite.

*Verified: Read ledgerly/db.py: SCHEMA is executed via executescript() on every Database() construction, and every other DDL statement uses 'CREATE TABLE IF NOT EXISTS', but the new 'CREATE INDEX idx_expenses_user_category' (added in this PR at line 100-101) omits 'IF NOT EXISTS'. Reproduced by executing: create Database('/tmp/test_ledgerly.db'), close it, then construct Database('/tmp/test_ledgerly.db') again — this raised sqlite3.OperationalError: index idx_expenses_user_category already exists, exactly as claimed.*

## 3. [MAJOR] synchronous=OFF drops crash-safety durability guarantee

`ledgerly/db.py:110` — robustness

Setting `PRAGMA synchronous = OFF` disables SQLite's fsync calls on commit, so a power loss or OS crash immediately after a transaction commits can corrupt the database or silently lose committed data (per SQLite docs, this is the one syncing mode where corruption after a crash is possible). Previously, no override was set, meaning SQLite's default (FULL for rollback-journal mode) durability applied. This is applied globally to every `Database` instance, including the on-disk ledger deployments (`db.execute`/`transaction` in ledgerly/db.py:113-120), silently dropping the durability guarantee financial ledger data previously had, in exchange for write speed.

*Verified: Read ledgerly/db.py:105-111: Database.__init__ unconditionally runs `self.conn.execute("PRAGMA synchronous = OFF")` on every connection, regardless of whether `path` is ':memory:' or a real on-disk file — there is no guard scoping this to non-persistent DBs (grepped repo, only one occurrence). Reproduced with `python3 -c` that this pragma actually takes effect (PRAGMA synchronous returns 0/OFF), confirming SQLite's documented behavior that OFF disables fsync-on-commit and can corrupt the DB or lose committed data on power loss/OS crash.*
