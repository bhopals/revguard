# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 3 blocking finding(s), 3 critical.

## 1. [CRITICAL] delete_expenses_bulk lacks user_id filter

`ledgerly/account.py:10` — correctness

The DELETE statement only filters by `id IN (...)` and never checks `user_id`, even though `user_id` is accepted as a parameter and every other expense operation in ledgerly/expenses.py (get_expense, delete_expense, list_expenses) scopes by `user_id`. Any caller can pass expense_ids belonging to a different user (e.g. IDs guessed or enumerated in the UI) and they will be deleted regardless of ownership, unlike `delete_expense` which raises `ExpenseError` on cross-user access via `get_expense`. Concrete scenario: user A calls delete_expenses_bulk(db, user_A_id, [expense_id_owned_by_B]) and expense_id is deleted even though it belongs to user B.

*Verified: Read ledgerly/account.py: delete_expenses_bulk builds `DELETE FROM expenses WHERE id IN (...)` using only expense_ids, never referencing the user_id parameter, unlike expenses.py's get_expense/delete_expense/list_expenses which all scope by user_id. Reproduced concretely with sqlite: created user B's expense (id=1), then called delete_expenses_bulk(db, user_id=1 [user A], [1]) — the row was deleted despite belonging to user B, confirming the cross-user IDOR. No caller in the repo adds an external user_id filter, so the defect is unconditional.*

## 2. [CRITICAL] delete_account deletes users before dependent rows, violating FK constraints

`ledgerly/account.py:17` — correctness

ledgerly/db.py enables `PRAGMA foreign_keys = ON` (db.py:49) and expenses.user_id, budgets.user_id, and tokens.user_id all declare `REFERENCES users(id)` without ON DELETE CASCADE. delete_account deletes from `users` first (line 17) while the user's expenses/budgets/tokens rows still reference that user id, so SQLite raises `sqlite3.IntegrityError: FOREIGN KEY constraint failed` on this very first statement whenever the account has any expenses, budgets, or tokens (e.g. any user who has ever logged in and has an active token, per auth.login). The function will fail for virtually every real account instead of performing 'full account removal' as described.

*Verified: Read ledgerly/db.py: PRAGMA foreign_keys = ON is set (line 49), and expenses.user_id/budgets.user_id/tokens.user_id all declare REFERENCES users(id) with no ON DELETE CASCADE. Read ledgerly/account.py: delete_account deletes from users first, then expenses, then tokens (budgets not even touched). Executed a live repro: created a user with one expense row and called delete_account(db, uid) — it raised sqlite3.IntegrityError: FOREIGN KEY constraint failed on the very first statement, exactly as claimed.*

## 3. [CRITICAL] delete_expenses_bulk lacks ownership scoping (IDOR)

`ledgerly/account.py:4` — security

delete_expenses_bulk(db, user_id, expense_ids) accepts a user_id parameter but never uses it in the SQL statement. The DELETE at line 10 (`DELETE FROM expenses WHERE id IN (...)`) matches purely on expense id with no `AND user_id = ?` filter. Every other expense-mutating function in the codebase (expenses.py delete_expense, get_expense, list_expenses) scopes by user_id to enforce ownership. Any authenticated user who supplies expense_ids belonging to another user (e.g. sequential/guessable integer IDs from an autoincrement primary key) can delete other users' expense records they do not own, since the function performs no ownership check before deleting.

*Verified: Read ledgerly/account.py: delete_expenses_bulk(db, user_id, expense_ids) builds `DELETE FROM expenses WHERE id IN (...)` using only expense_ids, never referencing the user_id parameter. Confirmed via reproduction: created expense id=1 owned by user_id=2 (bob), then called delete_expenses_bulk(db, 1, [1]) as user_id=1 (alice) — the row was deleted despite belonging to a different user. Grepped the rest of the codebase (auth.py, expenses.py, reports.py) and confirmed every other user-scoped query/mutation includes `AND user_id = ?` (e.g. expenses.py delete_expense uses `WHERE id = ? AND user_id = ?`), showing this omission breaks an established, deliberate ownership-scoping convention.*
