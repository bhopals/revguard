# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 3 blocking finding(s), 3 critical.

## 1. [CRITICAL] delete_account deletes the users row before its dependent rows, violating FK constraints

`ledgerly/account.py:17` — correctness

db.py enables `PRAGMA foreign_keys = ON` and expenses/tokens/budgets all declare `user_id INTEGER NOT NULL REFERENCES users(id)`. delete_account() deletes the `users` row first (line 17) and only afterward deletes the user's expenses (line 18) and tokens (line 19). For any user who has at least one expense or token row, the very first statement `DELETE FROM users WHERE id = ?` will raise a sqlite3.IntegrityError (FOREIGN KEY constraint failed) because dependent rows still reference that user id, and the whole operation is rolled back by Database.execute's transaction context manager. The function is therefore broken for the common case of a user with any data, not just an edge case. The order must be reversed: delete dependents (expenses, tokens, budgets) before deleting the users row.

*Verified: Read ledgerly/db.py: PRAGMA foreign_keys = ON is set on connect, and each Database.execute() call runs in its own transaction (commit/rollback per call), so the three DELETEs in delete_account are not atomic as a group but each individually enforces FK constraints. Reproduced with a live sqlite3 database: inserted a user and one expense row referencing it, then called delete_account(db, uid). Got *

## 2. [CRITICAL] delete_expenses_bulk does not scope the delete to the requesting user

`ledgerly/account.py:10` — correctness

Every other expense operation in the codebase (get_expense, delete_expense, list_expenses in ledgerly/expenses.py) filters by `user_id` to enforce that a user can only touch their own rows. delete_expenses_bulk accepts a `user_id` parameter but never uses it in the SQL: `DELETE FROM expenses WHERE id IN (...)` deletes by id alone. If expense_ids passed from the UI includes an id that does not belong to user_id (e.g., a stale/tampered id, or an off-by-one from another account), that other user's expense is silently deleted with no ownership check and no error raised, silently dropping the ownership guarantee that delete_expense enforces via get_expense().

*Verified: Read ledgerly/account.py: delete_expenses_bulk takes user_id but the SQL is `DELETE FROM expenses WHERE id IN (...)` with no user_id filter or WHERE clause tie-in, unlike delete_expense/get_expense/list_expenses in expenses.py which all filter by user_id. Wrote a reproduction using the actual Database class and schema: created two users (alice=1, bob=2), each with one expense; called account.delet*

## 3. [CRITICAL] No test at all for delete_account(), which would have caught an immediate crash

`tests/test_ledgerly.py:1` — test-adequacy

The PR adds ledgerly/account.py with delete_account() but the test suite has zero coverage of it (no import of ledgerly.account, no TestAccount class). This is a critical gap because delete_account() deletes from `users` before deleting the dependent `expenses`/`tokens` rows (account.py lines 17-19), while db.py enables `PRAGMA foreign_keys = ON` and expenses.user_id/tokens.user_id are declared as REFERENCES users(id) with no ON DELETE CASCADE. Calling delete_account(db, user_id) on any user who has at least one expense or token would raise sqlite3.IntegrityError at line 17, before the cleanup deletes even run. A single test like `expenses.add_expense(db, user, ...); account.delete_account(db, user)` would have failed immediately and caught this, but no such test exists.

*Verified: Confirmed db.py sets PRAGMA foreign_keys = ON and expenses/tokens declare user_id REFERENCES users(id) with no ON DELETE CASCADE. Confirmed test_ledgerly.py imports only `auth, expenses, reports` (no `account`) and contains no TestAccount/account-related tests (grep found zero matches). Reproduced the crash directly: inserting a user, adding an expense via expenses.add_expense, then calling accoun*
