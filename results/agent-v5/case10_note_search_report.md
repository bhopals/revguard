# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unvalidated `sort` parameter

`ledgerly/expenses.py:68` — security

`search_expenses` builds the SQL string with `f" ORDER BY {sort} DESC"`, directly interpolating the caller-supplied `sort` argument into the query instead of using a parameter or a whitelist of allowed column names. Any caller (e.g., an API endpoint exposing this as a `sort` query parameter) can pass a value like `spent_on; DROP TABLE expenses; --` or a subquery/UNION-based payload (e.g., `(SELECT CASE WHEN (1=1) THEN spent_on ELSE spent_on END)` or a value containing arbitrary SQL) to inject SQL through the ORDER BY clause. Unlike `list_expenses`, which only interpolates a fixed literal `spent_on DESC, id DESC`, this new function passes through an arbitrary user-controlled string, giving an attacker SQL injection scoped to any query surface that forwards a `sort` value to this function.

*Verified: Read ledgerly/expenses.py:63-70: search_expenses builds `f" ORDER BY {sort} DESC"` with the caller-supplied `sort` argument directly interpolated into SQL, with no whitelist check anywhere in the codebase (grepped for whitelist/allowed_sort/'sort in' — none found). Executed a live reproduction against an in-memory sqlite3 DB via ledgerly.db.Database: called search_expenses(db, 1, 'lunch', sort="(SELECT CASE WHEN (SELECT password_hash FROM users LIMIT 1)='h' THEN spent_on ELSE spent_on END)") and the boolean-based subquery payload executed successfully as part of the ORDER BY clause, confirming arbitrary SQL evaluation via the sort parameter (cross-table blind exfiltration is feasible).*
