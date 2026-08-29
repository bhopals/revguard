# Code review: Command-line interface for Ledgerly

> Adds a ledgerly CLI with register, login, add, list and summary commands so the service can be used without writing Python. Token is cached in the user's home directory between invocations.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Ad-hoc float-based money parsing bypasses parse_money, causing cent-level rounding errors and allowing negative/zero amounts

`ledgerly/cli.py:56` — correctness

cmd_add computes amount_cents with `int(float(args.amount) * 100)` instead of calling the existing `utils.parse_money`, which is the codebase's designated helper for exactly this conversion. Two concrete failures result: (1) Floating point imprecision plus truncation (not rounding) means common inputs lose a cent, e.g. `ledgerly add 19.99 food 2026-03-01` — `float('19.99') * 100` evaluates to 1998.9999999999998 in IEEE-754 double precision, and `int()` truncates toward zero, storing amount_cents=1998 ($19.98) instead of 1999 ($19.99). This silently corrupts the ledger's monetary records. (2) parse_money explicitly rejects non-positive amounts ('amount must be positive'), but the CLI's inline conversion has no such check, so `ledgerly add -5.00 food 2026-03-01` or `ledgerly add 0 food 2026-03-01` succeeds and inserts a negative or zero expense, corrupting `reports.monthly_summary` totals and budget_status comparisons for that user/month.

*Verified: Confirmed both sub-claims by direct execution. (1) `int(float('19.99')*100)` evaluates to 1998 in Python (float imprecision + truncation), reproducing the cent-loss bug exactly as described. (2) Ran cmd_add end-to-end against a real Database/auth flow: adding amount '19.99' printed 'added expense #1: $19.98 food' (off by a cent), and adding '-5.00' and '0' both succeeded silently, printing '-$5.00*

## 2. [MAJOR] Password passed as CLI positional argument leaks credentials

`ledgerly/cli.py:90` — security

register/login take `password` as a plain positional argument (lines 90-91, 95-96, invoked as e.g. `ledgerly register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process lifetime, and is written verbatim into the shell history file (~/.bash_history, ~/.zsh_history). The existing auth.py takes care to hash passwords with PBKDF2 and compare tokens in constant time, but this CLI undoes that protection by exposing the raw password on the command line before it ever reaches auth.register/auth.login. severity=major.

*Verified: Read ledgerly/cli.py: register/login subparsers define `password` as a plain positional argparse argument (lines 90-91, 95-96), consistent with the module's own docstring example `ledgerly register alice mypassword`. Grepped the file for getpass/masking and found none — there is no alternative secure input path. Demonstrated via a live subprocess + `ps -o command=` that a positional CLI argument i*

## 3. [MAJOR] No tests at all for new cli.py, including the always-succeeds exit code

`ledgerly/cli.py:118` — test-adequacy

This PR adds a full CLI module (register/login/add/list/summary) but the test suite (tests/test_ledgerly.py) has zero references to `cli` — none of the new commands are exercised. In particular, `main()` (ledgerly/cli.py:118-125) catches every exception from `args.func(db, args)`, prints it to stderr, and then unconditionally `return 0`s, so a failed `add` (e.g. bad amount format), failed `login` (bad password), or `_require_user` AuthError (not logged in) all report a process exit code of 0/success. Any script or CI job invoking `ledgerly` would see a false success. No test exercises this path, so a regression or the introduction of this exact silent-failure behavior would not be caught by CI.

*Verified: Read ledgerly/cli.py:118-125 confirming main() catches Exception, prints to stderr, and unconditionally returns 0 in all paths (including via `finally` for db.close()). Executed the actual CLI: `python3 -m ledgerly.cli add 12.50 food 2026-03-01 --note lunch` without logging in printed 'error: not logged in...' to stderr but exited with code 0; `python3 -m ledgerly.cli login nosuchuser wrongpass` s*

## 4. [MINOR] Auth token file briefly created world/group-readable before chmod

`ledgerly/cli.py:32` — security

_save_token() calls TOKEN_PATH.write_text(token) which creates/truncates the file using the process umask (typically 0o644, world-readable) and only restricts permissions afterward via chmod(0o600) on the next line. Between the write and the chmod there is a window in which the plaintext session token is readable by any other local user on a multi-user host (and if the token file already exists as a symlink planted by another local user, write_text follows it, writing the token to the symlink target). The token should be created with 0600 permissions atomically (e.g., os.open with O_CREAT and mode 0o600 before writing) rather than relying on a post-hoc chmod.

*Verified: Read ledgerly/cli.py:31-33, matching the diff exactly: _save_token calls TOKEN_PATH.write_text(token) then TOKEN_PATH.chmod(0o600). Reproduced with python3: under default umask 0o022, write_text() creates the file with mode 0o644 (verified via os.stat before chmod), and only the subsequent chmod call restricts it to 0o600. This confirms a real TOCTOU window where the plaintext token is world/group*
