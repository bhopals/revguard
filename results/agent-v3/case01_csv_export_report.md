# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] SQL injection via category filter

`ledgerly/export.py:18` — security

The `category` parameter is interpolated directly into the SQL string with an f-string instead of being passed as a bound parameter, while `user_id` correctly uses a placeholder. A caller-supplied category such as `' OR '1'='1` or `' UNION SELECT ... --` is spliced verbatim into the query, allowing an attacker who controls the category value (e.g., via an API endpoint that exposes this filter) to read other users' expenses or arbitrary table data, bypassing the `user_id` scoping entirely. Fix by binding category as a second parameter (e.g., `AND category = ?` with `(user_id, category)`).

*Verified: Read ledgerly/export.py: category is spliced into SQL via f-string (`sql += f" AND category = '{category}'"`) while user_id uses a `?` placeholder. Confirmed db.py uses real sqlite3.execute(sql, params), so this is genuine SQL, not an ORM-escaped string. Reproduced the exploit end-to-end: created two users (alice=id1, bob=id2) where bob has an expense and alice has none, then called export_expense*

## 2. [CRITICAL] Path traversal via caller-supplied filename

`ledgerly/export.py:12` — security

`filename` is joined into `EXPORT_DIR` with `os.path.join` without any sanitization. If `filename` contains path traversal sequences (e.g., `../../etc/cron.d/evil`) or is an absolute path (e.g., `/etc/passwd`), `os.path.join` will honor it and the resulting `path` escapes the `exports/` directory, letting a caller overwrite arbitrary files on disk with CSV-formatted expense data. This is a write-primitive that can be used for file overwrite/corruption or, in some deployments, code execution (e.g., writing into a cron directory or web root). The filename should be restricted to a safe basename (e.g., via `os.path.basename` plus an allow-list/regex check) before being joined into the export path.

*Verified: Read ledgerly/export.py: line 12 does `path = os.path.join(EXPORT_DIR, filename)` with no sanitization (no os.path.basename, no allow-list/regex, no realpath containment check) anywhere in the file or repo. Confirmed via python3 that os.path.join('exports', '../../etc/cron.d/evil') and os.path.join('exports', '/etc/passwd') both escape/override the base dir. Then actually invoked export_expenses_c*
