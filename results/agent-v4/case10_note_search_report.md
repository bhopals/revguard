# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unvalidated `sort` column parameter

`ledgerly/expenses.py:68` — security

The `sort` argument is interpolated directly into the SQL string with an f-string (`f" ORDER BY {sort} DESC"`) without any allow-list validation or parameterization. If `search_expenses` is reachable with caller-controlled input (e.g., a `sort` query parameter from an API endpoint), an attacker can pass a value like `1; DROP TABLE expenses;--` or, more relevantly for SQLite, a subquery/UNION-style expression (SQLite permits expressions in ORDER BY, e.g. `(SELECT password FROM users LIMIT 1)`) to exfiltrate data from other tables or corrupt the database. This is a classic SQL injection via an unvalidated ORDER BY clause, and it's the exact pattern the codebase avoids elsewhere via parameterized `?` placeholders.

*Verified: Read ledgerly/expenses.py: search_expenses() builds `sql += f" ORDER BY {sort} DESC"` with the caller-supplied `sort` parameter interpolated directly, no allow-list/validation anywhere in the file or codebase (grepped for any sort validation, found none). Wrote and ran a live exploit against the actual Database class: inserted a `users` row with password_hash 'SUPERSECRETHASH', then called search_expenses(db, 1, '', sort="(CASE WHEN (SELECT substr(password_hash,1,1) FROM users LIMIT 1)='S' THEN id ELSE -id END)") vs the same with a wrong guess 'X'.*

## 2. [MINOR] search_expenses has no pagination/limit unlike list_expenses

`ledgerly/expenses.py:63` — correctness

Every other listing helper in this module (`list_expenses`) enforces `PAGE_SIZE` via LIMIT/OFFSET to bound result size and matches the module's paging conventions, but `search_expenses` returns every matching row unbounded. A user with many matching notes (or a broad `text` value like a single common character) gets the entire table back in one call, inconsistent with the established pattern in this file and a likely performance/memory issue as data grows.

*Verified: Read ledgerly/expenses.py: search_expenses (lines 63-70) builds 'SELECT * FROM expenses WHERE user_id = ? AND note LIKE ? ORDER BY {sort} DESC' with no LIMIT/OFFSET, unlike list_expenses which appends 'LIMIT ? OFFSET ?' with PAGE_SIZE=20. Grepped the codebase for other callers/wrappers of search_expenses and found none, and db.query()/Database.query() (ledgerly/db.py) applies no default row cap (plain cur.fetchall()). Executed a reproduction: inserted 100 matching expense rows via add_expense and called search_expenses(db, 1, 'coffee') vs list_expenses(db, 1) — search_expenses returned all 100 rows while list_expenses returned exactly PAGE_SIZE=20.*
