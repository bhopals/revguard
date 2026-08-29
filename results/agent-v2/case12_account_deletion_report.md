# Code review: Bulk delete and account deletion

> Adds delete_expenses_bulk() for multi-select delete in the UI and delete_account() for GDPR-style full account removal.

**Verdict: request changes.** 3 blocking finding(s), 2 critical.

## 1. [CRITICAL] delete_account deletes parent row before children, violating FK constraints

`ledgerly/account.py:17` — correctness

db.py enables `PRAGMA foreign_keys = ON` (ledgerly/db.py:49), and expenses.user_id, budgets.user_id, and tokens.user_id all have `REFERENCES users(id)`. delete_account() issues `DELETE FROM users WHERE id = ?` first (line 17) before deleting the dependent expenses/tokens rows (lines 18-19). For any user who has ever logged in (which creates a tokens row via auth.login) or logged an expense, this first DELETE will raise sqlite3.IntegrityError because child rows still reference the user, and the whole account deletion aborts on line 17 before expenses/tokens are ever removed. The function as written cannot succeed for a realistic account with any activity, contradicting its purpose of removing the user.

## 2. [CRITICAL] Bulk expense delete lacks ownership scoping (IDOR)

`ledgerly/account.py:9` — security

delete_expenses_bulk() deletes rows solely by `id IN (...)` with no `user_id = ?` filter, unlike every other expense query in this codebase (see expenses.py get_expense/delete_expense/list_expenses, all scoped by user_id). Any caller (e.g. an authenticated user hitting the bulk-delete UI action) can pass arbitrary expense_ids — including IDs belonging to other users — and have them deleted, since the user_id parameter is accepted but never used in the query. This is a broken access control / IDOR vulnerability allowing cross-tenant data destruction.

## 3. [MAJOR] No test verifying delete_expenses_bulk respects expense ownership

`ledgerly/account.py:4` — test-adequacy

delete_expenses_bulk(db, user_id, expense_ids) accepts a user_id parameter but the DELETE statement (lines 9-12) filters only by `id IN (...)` with no `user_id` condition, so it will delete expenses belonging to other users if their ids are passed in. The existing test suite establishes an ownership-enforcement pattern for expense operations (test_ownership_enforced in tests/test_ledgerly.py), but no equivalent test was added for this new bulk-delete function. A test that creates expenses for two different users and calls delete_expenses_bulk with another user's expense ids would have caught that cross-user deletion is currently unguarded.
