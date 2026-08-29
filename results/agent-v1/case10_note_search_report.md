# Code review: Search expenses by note

> Adds search_expenses() so users can find expenses by note text, with a configurable sort column for the results.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unvalidated `sort` parameter

`ledgerly/expenses.py:68` — security

search_expenses() builds the ORDER BY clause with an f-string using the caller-supplied `sort` argument directly: f" ORDER BY {sort} DESC" (line 68), with no whitelist check against actual column names (contrast with `category` in list_expenses/add_expense, which is validated against VALID_CATEGORIES). Any caller that exposes `sort` from user input (e.g. a `?sort=` query parameter on a search endpoint, which is the obvious use case for this PR) allows arbitrary SQL injection, e.g. sort="id; DROP TABLE expenses; --" or a UNION-based injection to exfiltrate data from other tables/users (bypassing the user_id scoping entirely). Because params are otherwise parameterized correctly, this is the sole injection point and must be fixed by validating `sort` against a fixed set of allowed column names before interpolating it.
