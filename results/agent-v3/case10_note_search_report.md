# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unvalidated `sort` column name

`ledgerly/expenses.py:68` — security

`sort` is f-string interpolated directly into the SQL ORDER BY clause with no allow-list check or quoting: `f" ORDER BY {sort} DESC"`. Any caller (e.g. an API endpoint exposing a `sort`/`sort_by` query param) that passes user-controlled text through to `search_expenses` enables SQL injection. Since SQLite (and the `db.query` wrapper used elsewhere in this file) does not support stacked queries via parameter binding, an attacker is still able to perform boolean/UNION-based injection through ORDER BY, e.g. `sort="(SELECT CASE WHEN (SELECT password FROM users WHERE id=1) LIKE 'a%' THEN spent_on ELSE id END)"` or `sort="id) UNION SELECT ... --"` depending on how the surrounding query is structured, allowing extraction of data from other tables/users. Every other query in this module (get_expense, delete_expense, list_expenses) uses bound parameters for all user-influenced values; this function breaks that pattern for the one column that is string-interpolated. Fix by validating `sort` against an explicit allow-list of known column names (e.g. `{'spent_on', 'amount_cents', 'category', 'id'}`) before interpolating it.

*Verified: Read ledgerly/expenses.py: search_expenses builds `sql += f" ORDER BY {sort} DESC"` with `sort` f-string interpolated and never validated against an allow-list (confirmed via grep that no other reference to `sort` exists anywhere in the repo). Wrote and ran a live exploit against the actual Database/search_expenses code: inserted a `users` row with password_hash='SECRETHASH', then called search_ex*
