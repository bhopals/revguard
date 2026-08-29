# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] SQL injection via category filter

`ledgerly/export.py:18` — security

The `category` parameter is interpolated directly into the SQL string with an f-string instead of being passed as a bound parameter (unlike `user_id` on line 15, which correctly uses `?`). Any caller that passes a category value derived from user input (e.g., a web request query param) allows SQL injection, e.g. category = "x' OR '1'='1" or a UNION-based injection to exfiltrate data from other tables/users, or a stacked query depending on the driver. This directly contradicts the parameterization pattern already used one line above for user_id, showing this is an inconsistency introduced by the PR rather than a pre-existing pattern.

## 2. [CRITICAL] Path traversal via caller-supplied filename

`ledgerly/export.py:12` — security

`filename` is joined onto EXPORT_DIR with os.path.join and used directly to open a file for writing, with no validation or sanitization. If `filename` originates from user input (e.g., an API request parameter, as is typical for an export feature), a value like `../../etc/cron.d/evil` or an absolute path `/etc/passwd` (os.path.join drops the base dir when the second component is absolute) lets the caller write the CSV to an arbitrary filesystem location outside exports/, enabling file overwrite attacks on other users' exports or system files the process can write to.
