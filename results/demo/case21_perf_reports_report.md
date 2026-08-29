# Code review: Report performance: single-query budget status

> budget_status did 1 + N queries (a summary plus one per budget). This PR collapses it into a single LEFT JOIN aggregate, adds a covering index for the expense lookup path, and relaxes sqlite synchronous mode for faster writes. No behavior change intended.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] budget_status no longer filters expenses by month, summing all-time spend

`ledgerly/reports.py:44` — correctness

The old code computed spend via monthly_summary(), which filters expenses with `WHERE user_id = ? AND substr(spent_on, 1, 7) = ?` (line 27), i.e. only expenses within the requested month. The new single-query JOIN (lines 40-49) joins budgets to expenses only on `e.user_id = b.user_id AND e.category = b.category` with no constraint on `e.spent_on`/month at all. As a result, `spent` (and therefore `remaining` and `over_budget`) now aggregates the user's entire historical spend in that category across all months, not just the requested month. Example: a user has a '2025-01' budget for 'groceries' with $50 limit, spent $10 in January and $60 in February (different month, same category). budget_status(db, user_id, '2025-01') will report spent=$70 and over_budget=True, even though January spend was only $10 and under budget. This directly contradicts the function's docstring ("Compare spend against each budget set for the month") and the PR's claim of 'No behavior change intended'.

*Verified: Read ledgerly/reports.py lines 40-49: the LEFT JOIN condition is `e.user_id = b.user_id AND e.category = b.category` with no constraint tying e.spent_on to b.month. Reproduced with a live Database instance: inserted a $10 January groceries expense and a $60 February groceries expense, set a $50 January budget, and called budget_status(db, 1, '2025-01'). Output: {'category': 'groceries', 'limit': '$50.00', 'spent': '$70.00', 'remaining': '-$20.00', 'over_budget': True} — confirming spend aggregates across all months instead of just the requested month, exactly as the finding describes.*

## 2. [MAJOR] CREATE INDEX without IF NOT EXISTS crashes on reopening an existing database file

`ledgerly/db.py:100` — robustness

SCHEMA is executed via `self.conn.executescript(SCHEMA)` every time a Database object is constructed (db.py:111), and all table statements use `CREATE TABLE IF NOT EXISTS` so they are idempotent. The newly added `CREATE INDEX idx_expenses_user_category ON expenses (user_id, category, spent_on);` (lines 100-101) omits `IF NOT EXISTS`. For any non-`:memory:` database path, opening a second `Database(path)` against the same file (e.g. app restart, a second process, or any test/code that constructs Database twice against the same file) raises `sqlite3.OperationalError: index idx_expenses_user_category already exists`, since the CREATE TABLE statements succeed silently (already exist) but the index statement does not. This is a regression introduced by this PR: schema initialization was previously always safe to re-run, and now crashes on reopen.

*Verified: Read ledgerly/db.py:100-111, confirming the new CREATE INDEX statement lacks IF NOT EXISTS while all CREATE TABLE statements have it. Reproduced by executing: Database('test_ledgerly.db') twice against the same file path — first open succeeds, second raises sqlite3.OperationalError: index idx_expenses_user_category already exists, exactly as described. Database.__init__ signature (path=':memory:') confirms file-backed usage is a supported, intended code path, not a hypothetical. Existing tests only use in-memory Database() so they don't catch this, but that's incidental to the defect being real and reachable in normal use (app restart / second process opening the same DB file).*

## 3. [MAJOR] PRAGMA synchronous = OFF silently drops crash-durability guarantees

`ledgerly/db.py:110` — robustness

The PR adds `self.conn.execute("PRAGMA synchronous = OFF")` for every Database connection. With synchronous=OFF, SQLite does not fsync after writing to the WAL/rollback journal before continuing, so a power loss or OS crash during or shortly after a commit (e.g. inside `execute()`/`transaction()` at db.py:113-120, used for all budget/expense writes) can corrupt the database file or silently lose committed transactions. The PR description says 'No behavior change intended,' but this removes a durability guarantee the old code provided (default synchronous=FULL/NORMAL), trading correctness-under-crash for write speed without any mention of this tradeoff or exception handling for the corrupted-db case.

*Verified: Read db.py:107-111 confirming the diff: `PRAGMA synchronous = OFF` is newly added to Database.__init__, applied to every connection. Ran the actual code against a real on-disk file: `PRAGMA synchronous` returns 0 (OFF) and `PRAGMA journal_mode` returns 'delete' (default rollback-journal mode, not WAL) — this is exactly the SQLite-documented dangerous combination where the docs state the database file 'could be corrupted' after an OS crash or power loss, since no fsync occurs after writing the rollback journal before committing.*
