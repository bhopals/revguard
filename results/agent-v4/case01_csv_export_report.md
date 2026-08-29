# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] SQL injection via unparameterized category filter

`ledgerly/export.py:18` — security

The `category` parameter is interpolated directly into the SQL string with an f-string (`f" AND category = '{category}'"`) instead of being passed as a bound parameter, unlike the equivalent filter in `expenses.list_expenses` (ledgerly/expenses.py:57) which correctly uses `?` placeholders. Any caller that passes a category value derived from user input (e.g., a web handler forwarding a query-string `category` param) allows classic SQL injection, e.g. `category = "x' UNION SELECT username, password_hash, salt, 1 FROM users --"` would let an attacker exfiltrate other users' password hashes and salts into the exported CSV, bypassing the `user_id` ownership scoping entirely.

*Verified: Read ledgerly/export.py: line 18 builds SQL with f" AND category = '{category}'" (raw string interpolation), unlike the parameterized `? ` used in expenses.py:57 (list_expenses) and everywhere else in db.py/expenses.py. Confirmed no validation/allowlisting of category exists in export.py (expenses.py's add_expense has a VALID_CATEGORIES check but export.py has no such guard).*

## 2. [MAJOR] Path traversal via caller-supplied filename

`ledgerly/export.py:12` — security

`filename` is joined directly into `EXPORT_DIR` with `os.path.join(EXPORT_DIR, filename)` and never validated or sanitized. If `filename` originates from user input (e.g. a web request parameter, which is plausible for an export feature), a value like `../../etc/cron.d/evil` or an absolute path `/etc/passwd`-style string (os.path.join discards the first component when the second is absolute) lets the caller write the CSV file anywhere on the filesystem the process can reach, overwriting arbitrary files rather than being confined to the exports/ directory.

*Verified: Read ledgerly/export.py: `filename` param flows unchanged into `os.path.join(EXPORT_DIR, filename)` at line 12 with no sanitization anywhere in the file or module. Verified by execution: called export_expenses_csv(db, 1, "../outside_exports.csv") with a fake DB in a temp cwd — the CSV was written one directory above exports/ (confirmed via os.path.exists on the escaped path), proving traversal is not prevented. Also confirmed via python3 that os.path.join('exports', '/etc/passwd') discards the base and returns '/etc/passwd', so an absolute-path filename bypasses EXPORT_DIR entirely.*
