# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unsanitized `sort` parameter

`ledgerly/expenses.py:68` — security

The `sort` argument is interpolated directly into the SQL string with an f-string (`f" ORDER BY {sort} DESC"`) instead of being parameterized or validated against an allow-list of column names. Since `search_expenses` is a public function likely reachable from user-facing search input (e.g., a sort-by query parameter), an attacker can pass a value like `sort="id; DROP TABLE expenses;--"` or, more realistically for SQLite (which doesn't support stacked queries via the DB driver in most cases), a subquery-based payload such as `sort="(CASE WHEN (SELECT 1 FROM users WHERE password_hash LIKE 'a%') THEN spent_on ELSE id END)"` to perform boolean/blind SQL injection and exfiltrate data from other tables (e.g., other users' password hashes), bypassing the user_id scoping entirely. Unlike every other query in this file, which uses parameterized placeholders (`?`), this is the only place where caller-controlled input is spliced into the SQL text, and there is no validation that `sort` is one of a fixed set of legitimate column names.

## 2. [MAJOR] No test coverage added for search_expenses()

`ledgerly/expenses.py:63` — test-adequacy

The PR adds a new public function `search_expenses(db, user_id, text, sort="spent_on")` (ledgerly/expenses.py:63-70) but tests/test_ledgerly.py's TestExpenses class (the only test file in the repo) has no test exercising it at all — no test verifies note-substring matching, user_id scoping/ownership isolation (unlike test_ownership_enforced for get_expense), the `sort` parameter's effect on ordering, or behavior with an empty/no-match result. Because `sql` builds the ORDER BY clause via an f-string interpolating the caller-supplied `sort` argument directly (line 68), an absent test also fails to catch that passing an untrusted or malformed `sort` value produces a broken/injectable SQL string — a case a single parametrized test would have caught immediately (e.g. sort='id; DROP TABLE expenses--' or sort='nonexistent_col' raising sqlite3.OperationalError). As written, CI passes with zero verification that the newly shipped feature works or is scoped correctly per user.
