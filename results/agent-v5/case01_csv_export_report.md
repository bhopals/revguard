# Code review: Add CSV export for expenses

> Adds a new export module so users can download their expenses as a CSV file. Supports an optional category filter and writes into an exports/ directory using the caller-supplied filename.

**Verdict: request changes.** 3 blocking finding(s), 2 critical.

## 1. [CRITICAL] SQL injection via category parameter

`ledgerly/export.py:18` — security

The `category` argument is interpolated directly into the SQL string with an f-string instead of being passed as a bound parameter, even though `user_id` on the same query correctly uses a `?` placeholder. Any caller that passes user-controlled category text (e.g. a web form field) allows SQL injection: a value like `x' OR '1'='1' --` breaks out of the quoted literal, and a value like `x'; DROP TABLE expenses; --` (if the driver permits statement stacking) or a UNION-based payload can be used to read or corrupt other users' data. This defeats the `user_id = ?` scoping entirely since the injected clause can be crafted to bypass or extend the WHERE condition.

*Verified: Read ledgerly/export.py and ledgerly/db.py: db.query() executes raw SQL via sqlite3 with no sanitization, and export_expenses_csv builds `sql += f" AND category = '{category}'"` while user_id correctly uses a `?` placeholder. Wrote and ran a live exploit: seeded a DB with expenses for user_id=1 (alice) and user_id=2 (bob), then called export_expenses_csv(db, 1, 'exploit.csv', category="nonexistent' OR user_id=2 --") as alice. The exported CSV contained bob's 'secret' expense despite alice's user_id scoping, proving the injection bypasses the WHERE user_id = ? filter and leaks cross-user data.*

## 2. [CRITICAL] Path traversal via caller-supplied filename

`ledgerly/export.py:12` — security

`filename` is joined into `EXPORT_DIR` with `os.path.join` without any sanitization or basename restriction. If `filename` originates from user input (e.g. an API request parameter), a value like `../../etc/cron.d/evil` or an absolute path such as `/etc/passwd`-style path (os.path.join replaces the whole path when the second argument is absolute) lets the caller write the CSV file outside the `exports/` directory, overwriting arbitrary files reachable by the process, or escape into arbitrary locations on disk. There is no use of `os.path.basename(filename)` or validation against path separators/`..` segments.

*Verified: Read ledgerly/export.py: filename is passed directly into os.path.join(EXPORT_DIR, filename) with no basename/sanitization anywhere in the codebase (grep for basename/sanitize/secure_filename found nothing). Reproduced with python: os.path.join('exports', '../../etc/cron.d/evil') and os.path.join('exports', '/tmp/absolute_evil.csv') confirm Python's documented join behavior (absolute path discards the base, '..' segments escape the dir). Then actually called export_expenses_csv(FakeDB(), 1, '../evil_outside.csv') in a temp dir and confirmed the CSV file was written one directory above exports/, outside the intended export directory.*

## 3. [MINOR] Money reintroduced as floating point instead of using the integer-cents convention

`ledgerly/export.py:28` — correctness

The codebase's documented invariant (ledgerly/db.py:3, "All amounts are stored as integer cents to avoid floating point drift") and its existing helper `format_money` in ledgerly/utils.py compute dollars using pure integer arithmetic (`cents // 100`, `cents % 100`). export_expenses_csv instead performs `r['amount_cents'] / 100` (true division producing a float) and formats it with `:.2f`. This bypasses the project's established float-avoidance convention for money; for sufficiently large amount_cents values the binary float division loses precision relative to the exact integer-cents value, so the exported CSV amount can silently diverge from the true stored amount instead of being derived via the same exact integer-based formatting used everywhere else in the app (e.g. reports.py's budget_status output).

*Verified: Read ledgerly/db.py (documented invariant: amounts stored as integer cents to avoid float drift) and ledgerly/utils.py's format_money, which does cents//100 / cents%100 integer arithmetic; reports.py/budget_status likewise operates purely on integer cents. export.py:28 instead does r['amount_cents']/100 formatted with :.2f. Wrote a Python script comparing the exact integer-based formatting vs the float-division formatting across many amount_cents values; for magnitudes below ~10^16 they always agreed, but starting at 10^16 (e.g. 10000000000000001, 10000000000000004, ...) the float-division output diverges from the exact value (e.g.*
