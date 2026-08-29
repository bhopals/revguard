# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] SQL injection via category filter

`ledgerly/export.py:18` — security

The `category` parameter is interpolated directly into the SQL string with an f-string (`sql += f" AND category = '{category}'"`) instead of being passed as a bound parameter. Any caller-supplied category value containing a single quote or SQL metacharacters (e.g. `category="' OR '1'='1"` or `category="x'; DROP TABLE expenses;--"`) will be executed as part of the query, allowing data exfiltration across users (bypassing the `user_id = ?` scoping) or destructive SQL execution. The `user_id` parameter correctly uses a placeholder, showing the intended safe pattern was not applied to `category`.

*Verified: Read ledgerly/export.py and confirmed the exact f-string interpolation `sql += f" AND category = '{category}'"` with no sanitization anywhere. db.py uses a real sqlite3 connection with no escaping layer. Executed a live reproduction: seeded two users (alice=1, bob=2) each with an expense row, then called export_expenses_csv(db, user_id=1, filename='out.csv', category="x' OR '1'='1") as alice. The exported CSV contained BOTH alice's and bob's expense rows, proving the `user_id = ?` scoping was fully bypassed via classic boolean-based SQL injection — exactly the cross-user exfiltration the finding describes.*

## 2. [CRITICAL] Path traversal via caller-supplied filename

`ledgerly/export.py:12` — security

`filename` is joined into the export path with `os.path.join(EXPORT_DIR, filename)` without any validation or sanitization. If `filename` contains path traversal sequences (e.g. `../../etc/cron.d/evil`) or is an absolute path (e.g. `/etc/passwd`), `os.path.join` will resolve outside the intended `exports/` directory (an absolute path argument even overrides `EXPORT_DIR` entirely), allowing the caller to write the CSV file to an arbitrary location on the filesystem, potentially overwriting sensitive files.

*Verified: Read ledgerly/export.py: line 12 does `path = os.path.join(EXPORT_DIR, filename)` with zero sanitization (no basename/secure_filename/validation anywhere in the file or repo per grep). Executed a live repro: calling export_expenses_csv(db, 1, '/tmp/pwned_evil_abs.csv') wrote directly to /tmp/pwned_evil_abs.csv (absolute path fully overrides EXPORT_DIR, per Python os.path.join semantics), and calling it with a correctly-depth-counted '../'*N + 'tmp/pwned_evil_rel.csv' traversal string escaped the exports/ directory and wrote to /tmp/pwned_evil_rel.csv as well.*
