# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 3 blocking finding(s), 3 critical.

## 1. [CRITICAL] delete_expenses_bulk has no ownership scoping (IDOR)

`ledgerly/account.py:9` — security

The DELETE statement `DELETE FROM expenses WHERE id IN ({placeholders})` filters only by `id`, never by `user_id`, even though `user_id` is passed into the function. Every other expense mutation in the codebase (see delete_expense in ledgerly/expenses.py, which does `WHERE id = ? AND user_id = ?`) scopes by the owning user. Here, an authenticated user can pass expense_ids belonging to other users (e.g. sequential/guessed IDs) and delete_expenses_bulk will delete them, since the SQL has no clause restricting to the caller's own rows. This is a broken-object-level-authorization (IDOR) vulnerability allowing any user to delete any other user's expense records via the bulk-delete UI/API.

*Verified: Read ledgerly/account.py: delete_expenses_bulk accepts user_id but never uses it in the SQL (`DELETE FROM expenses WHERE id IN (...)`), unlike delete_expense in ledgerly/expenses.py which correctly scopes by `id = ? AND user_id = ?`. Wrote and ran a reproduction with an in-memory sqlite DB containing expense id=1 owned by user 100 and id=2 owned by user 200; calling delete_expenses_bulk(db, 200, [1]) as attacker user 200 deleted victim user 100's expense (id=1), leaving only (2, 200, 999) — confirming cross-user deletion is possible.*

## 2. [CRITICAL] delete_account deletes users row before dependent rows, violating FK constraints and contradicting its own docstring

`ledgerly/account.py:17` — correctness

db.py enables `PRAGMA foreign_keys = ON` and expenses/tokens/budgets all declare `user_id INTEGER NOT NULL REFERENCES users(id)` with no ON DELETE action, so SQLite enforces referential integrity immediately. delete_account() deletes the `users` row first (line 17) before deleting `expenses` (line 18) or `tokens` (line 19), so for any user that still has at least one expense or token row, the very first DELETE raises sqlite3.IntegrityError and the function aborts — the account is never actually deleted. The docstring 'Remove the user and everything they own' is also inaccurate: `budgets` rows referencing the user (see ledgerly/db.py schema and ledgerly/reports.py) are never deleted, so even if the delete order were fixed, budgets would either block the users delete via the same FK constraint or be silently left orphaned. The deletion order should be children-first (expenses, tokens, budgets) then users, and budgets must be included.

*Verified: Executed delete_account() against a real in-memory Database with PRAGMA foreign_keys=ON (as configured in ledgerly/db.py) after inserting a user with one expense, one token, and one budget row. The very first statement `DELETE FROM users WHERE id = ?` raised sqlite3.IntegrityError: FOREIGN KEY constraint failed, and the transaction context manager rolled it back, so all rows (users, expenses, tokens, budgets) remained in the DB afterward — the account was not deleted. Confirmed the delete order in account.py is users->expenses->tokens (children after parent).*

## 3. [CRITICAL] delete_expenses_bulk accepts user_id but never uses it to scope the delete, allowing cross-user deletion

`ledgerly/account.py:4` — security

The function signature `delete_expenses_bulk(db, user_id, expense_ids)` implies the deletion is scoped to the caller's account, mirroring delete_expense() in ledgerly/expenses.py which filters by `WHERE id = ? AND user_id = ?`. Instead, the generated SQL is `DELETE FROM expenses WHERE id IN (...)` with no user_id predicate at all — the user_id parameter is dead/unused. Any authenticated user who can guess or enumerate expense ids belonging to another user can delete them via the bulk endpoint, since ownership is never checked. This is both a real IDOR vulnerability and a misleading API: the parameter's presence implies a safety guarantee that the implementation doesn't provide.

*Verified: Read ledgerly/account.py: delete_expenses_bulk(db, user_id, expense_ids) builds `DELETE FROM expenses WHERE id IN (...)` using only expense_ids; user_id is never referenced in the SQL or params. Confirmed via grep that the function has no other callers/wrappers anywhere in the repo that could add scoping, and no tests exercise it. Wrote a concrete reproduction: created two users (alice=1, bob=2) each with one expense (ids 100 and 200 respectively), then called `account.delete_expenses_bulk(db, 2, [100])` (bob's user_id, alice's expense id). Result: alice's expense (id=100, user_id=1) was deleted even though it belongs to a different user than the one passed in.*
