# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] SQL injection via category parameter

`ledgerly/export.py:18` — security

The `category` argument is spliced directly into the SQL string with an f-string (`sql += f" AND category = '{category}'"`) instead of being bound as a parameter, unlike every other query in this codebase (see expenses.py, reports.py, auth.py, all of which use `?` placeholders). A caller that passes user-controlled input as `category` (e.g. from an API query parameter) enables classic SQL injection, e.g. `category = "x' OR '1'='1"` bypasses the filter and can be extended to exfiltrate data from other tables (`x' UNION SELECT username, password_hash, salt, id FROM users --`) or corrupt data via stacked/derived queries depending on driver behavior. Since `db.query` already supports parameter binding (see db.py:61-63), this should use `sql += " AND category = ?"` with `category` appended to the params tuple, exactly as `list_expenses` does in expenses.py:56-58.

## 2. [CRITICAL] Path traversal / arbitrary file write via filename

`ledgerly/export.py:12` — security

`filename` is joined into the export path with `os.path.join(EXPORT_DIR, filename)` with no validation. If `filename` contains path traversal sequences (e.g. `"../../ledgerly/expenses.py"`) the write escapes the `exports/` directory and can overwrite arbitrary files the process has permission to write. Worse, if `filename` is an absolute path (e.g. `"/etc/cron.d/evil"` or any absolute path), `os.path.join` discards `EXPORT_DIR` entirely per Python semantics and writes directly to that absolute location, giving a caller (or anything that forwards a user-controlled filename to this function) arbitrary file write/overwrite. The function should reject filenames containing path separators or `..`, or use `os.path.basename(filename)` combined with a check that the resolved path stays under `EXPORT_DIR`.
