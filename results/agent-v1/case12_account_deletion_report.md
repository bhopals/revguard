# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 3 blocking finding(s), 2 critical.

## 1. [CRITICAL] delete_expenses_bulk lacks ownership check (IDOR)

`ledgerly/account.py:10` — security

The DELETE statement filters only by `id IN (...)` and never checks `user_id`, unlike every other expense operation in the codebase (see expenses.py's get_expense/delete_expense, which both scope by `WHERE id = ? AND user_id = ?`). Any authenticated user can call delete_expenses_bulk(db, their_own_user_id, [other_users_expense_ids]) and permanently delete another user's expenses, since expense_ids supplied by the (untrusted) UI are never validated against the caller's user_id. This is a broken-access-control/IDOR bug that lets one user destroy another user's data.

## 2. [CRITICAL] delete_account deletes parent row before children, violating FK constraints

`ledgerly/account.py:17` — correctness

db.py enables `PRAGMA foreign_keys = ON`, and expenses/tokens/budgets all declare `user_id INTEGER NOT NULL REFERENCES users(id)` with no ON DELETE CASCADE. delete_account deletes the users row first (line 17) while the user's expenses/tokens (and budgets) rows still reference it, so this DELETE will raise sqlite3.IntegrityError (FOREIGN KEY constraint failed) for any user who has ever added an expense, logged in (creating a token), or set a budget — i.e. essentially every real user. The function as written cannot succeed for a normal account.

## 3. [MAJOR] No tests cover delete_expenses_bulk or delete_account

`ledgerly/account.py:4` — test-adequacy

tests/test_ledgerly.py has no test cases for either new function. Given both functions have critical bugs (IDOR in delete_expenses_bulk, guaranteed FK-violation failure in delete_account for any user with real data), even a minimal test using a populated database (a user with an expense/token/budget) would have caught these issues before merge.
