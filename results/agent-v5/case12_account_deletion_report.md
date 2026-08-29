# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] delete_account deletes parent row before children, violating FK constraints

`ledgerly/account.py:17` — correctness

delete_account() issues `DELETE FROM users WHERE id = ?` (line 17) before deleting the user's expenses (line 18) and tokens (line 19). The schema (ledgerly/db.py) defines expenses.user_id and tokens.user_id as `REFERENCES users(id)` with no ON DELETE CASCADE, and Database.__init__ runs `PRAGMA foreign_keys = ON`. For any user who has at least one expense or token row, the first DELETE will raise sqlite3.IntegrityError ('FOREIGN KEY constraint failed'), which propagates out of delete_account since db.execute's transaction() context manager rolls back and re-raises. The function therefore crashes and removes nothing for exactly the users it's meant to serve (those who 'own' data), contradicting its own docstring 'Remove the user and everything they own.' It only succeeds as a no-op for users with zero expenses/tokens. The deletes must be reordered to delete children (expenses, tokens) before the parent (users).

*Verified: Read ledgerly/db.py confirming expenses.user_id and tokens.user_id are FK REFERENCES users(id) with no ON DELETE CASCADE, and PRAGMA foreign_keys = ON is set in Database.__init__. Reproduced with python3: created a user with one expense row and called delete_account(db, uid) — it raised sqlite3.IntegrityError('FOREIGN KEY constraint failed'), and afterward both the user and expense rows remained (transaction rolled back), i.e., the function crashed and deleted nothing. For a user with zero owned rows, delete_account succeeded and removed the user.*

## 2. [CRITICAL] delete_expenses_bulk does not scope deletion to the requesting user

`ledgerly/account.py:9` — correctness

delete_expenses_bulk(db, user_id, expense_ids) accepts a user_id parameter but never uses it in the SQL: `DELETE FROM expenses WHERE id IN ({placeholders})` (lines 9-12) filters only by expense id, with no `AND user_id = ?` clause. Every other expense operation in the codebase scopes by user_id (e.g. get_expense/delete_expense/list_expenses in ledgerly/expenses.py, whose module docstring states 'Every operation is scoped to the owning user'). As written, if a caller (e.g. the bulk-delete UI action) invokes delete_expenses_bulk with an expense_id belonging to a different user, that other user's expense will be deleted, since ownership is never checked. This breaks the per-user isolation guarantee every other expense function in the codebase enforces.

*Verified: Read ledgerly/account.py: delete_expenses_bulk builds `DELETE FROM expenses WHERE id IN (...)` using only expense_ids, never referencing the user_id parameter, unlike every other function in ledgerly/expenses.py (get_expense, delete_expense, list_expenses) which all include `AND user_id = ?`. Executed a live reproduction with sqlite3: created expenses belonging to user 100 and user 200, then called delete_expenses_bulk(db, 100, [2]) where id 2 belongs to user 200 — the expense was deleted despite belonging to a different user, confirming cross-user deletion is possible with no ownership check.*
