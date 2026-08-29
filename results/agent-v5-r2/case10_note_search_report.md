# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unvalidated `sort` column name

`ledgerly/expenses.py:68` — security

The `sort` parameter is interpolated directly into the SQL string with an f-string (`f" ORDER BY {sort} DESC"`) without any whitelist check or parameterization. If `sort` is derived from user/caller-supplied input (e.g., a query-string sort parameter in an API layer calling `search_expenses`), an attacker can pass a value like `id; DROP TABLE expenses;--` or, more realistically for SQLite (which typically doesn't support stacked statements via most drivers but does support expression subqueries in ORDER BY), something like `(SELECT CASE WHEN (SELECT substr(password,1,1) FROM users WHERE id=1)='a' THEN id ELSE amount_cents END)` to perform boolean/blind SQL injection and exfiltrate data from other tables, bypassing the user_id scoping entirely. Even without stacked queries, this allows arbitrary expression injection into ORDER BY, enabling data exfiltration from other tables/users. All other query-building code in this file uses parameterized `?` placeholders for values, but none of them interpolate identifiers - this is the first place raw string interpolation is used for SQL structure, and it has no allowlist of valid column names (unlike category/date fields elsewhere).

*Verified: Read ledgerly/expenses.py: search_expenses (new in this PR) builds SQL as f"... ORDER BY {sort} DESC" with sort a plain function parameter (default 'spent_on'), no whitelist, unlike category which is checked against VALID_CATEGORIES elsewhere in the same file.*

## 2. [MINOR] search_expenses has no pagination, unlike list_expenses

`ledgerly/expenses.py:63` — robustness

list_expenses enforces PAGE_SIZE/OFFSET pagination (line 59-60), but search_expenses issues an unbounded query with no LIMIT/OFFSET. A user with many matching expenses (e.g. a common note substring) will have the entire result set loaded into memory and returned in one call, which can grow unbounded as the expenses table grows, unlike every other listing function in this module.

*Verified: Read ledgerly/expenses.py: list_expenses (lines 50-61) applies `LIMIT ? OFFSET ?` with PAGE_SIZE, while the new search_expenses (lines 63-70) builds a query with only `ORDER BY {sort} DESC` and no LIMIT/OFFSET. Confirmed no caller anywhere wraps or paginates the result (grep for search_expenses found only its own definition). Reproduced at runtime: inserted 500 matching expense rows into an in-memory Database and called search_expenses(db, 1, 'coffee') -> returned all 500 rows, while list_expenses(db, 1) on the same data correctly capped at PAGE_SIZE=20. This is a genuine unbounded-query defect in the new function's code, not a test-coverage complaint.*
