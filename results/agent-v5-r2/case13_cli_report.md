# Code review: Command-line interface for Ledgerly

> Adds a ledgerly CLI with register, login, add, list and summary commands so the service can be used without writing Python. Token is cached in the user's home directory between invocations.

**Verdict: request changes.** 4 blocking finding(s), 0 critical.

## 1. [MAJOR] `add` command bypasses utils.parse_money, introducing float drift and allowing negative/zero amounts

`ledgerly/cli.py:56` — correctness

cmd_add computes `amount_cents = int(float(args.amount) * 100)` instead of using the existing `utils.parse_money` helper (which the codebase's own db.py docstring says exists specifically "to avoid floating point drift"). Two concrete failures result: (1) floating point rounding: `float("19.99") * 100` == 1998.9999999999998, so `int(...)` truncates to 1998 cents instead of 1999, silently undercharging the user by a cent (this happens for many two-decimal amounts, e.g. 0.10, 1.01, 5.75 in some cases). (2) missing validation: `parse_money` rejects zero/negative amounts and things like a leading '$', but `float()` accepts a leading '-' (argparse permits negative-number-looking positionals since no option strings in the `add` subparser resemble negative numbers), so `ledgerly add -12.50 food 2026-03-01` silently inserts an expense with amount_cents = -1250, corrupting monthly_summary totals (reports.py simply SUMs amount_cents) and violating the invariant that expenses are positive spend records. `float('$12.50')` also raises an unhandled ValueError caught only by the generic exception handler in main(), producing an unhelpful message instead of the clear error parse_money would have given.

*Verified: Reproduced both failure modes directly: (1) `int(float('19.99')*100)` == 1998 (should be 1999), confirming float truncation drift for the amount cli.py uses instead of utils.parse_money; (2) `build_parser().parse_args(['add','-12.50','food','2026-03-01'])` parses cleanly with amount='-12.50' since argparse allows negative-looking positionals when no option strings look like negative numbers, and expenses.add_expense/db.py perform no positivity check on amount_cents (confirmed by reading expenses.py — add_expense only validates category, note length, and date).*

## 2. [MAJOR] Passwords accepted as plaintext command-line arguments

`ledgerly/cli.py:4` — security

The `register` and `login` subcommands (cli.py:90-97) take `password` as a positional argparse argument, and the module docstring explicitly documents this usage (`python -m ledgerly.cli register alice mypassword`, line 4-5). Command-line arguments are visible to any other local user via `ps`/`/proc/<pid>/cmdline` while the process runs, and are typically persisted in plaintext in the user's shell history file (e.g. ~/.zsh_history). This exposes the account password outside of the auth module's otherwise careful handling (PBKDF2 hashing, constant-time comparison) and is a new attack surface introduced entirely by this CLI. The commands should instead prompt for the password interactively (e.g. via `getpass`) rather than accepting it as an argv token.

*Verified: Read ledgerly/cli.py and confirmed it matches the diff exactly: register/login subparsers define `password` as a positional argparse argument (build_parser, lines ~90-97), and the module docstring at line 4-5 explicitly documents `python -m ledgerly.cli register alice mypassword`. Reproduced at runtime: launched `python3 -m ledgerly.cli register alice supersecretpw` as a subprocess and ran `ps -o pid,command -p <pid>` while it was running — the full command line including the plaintext password `supersecretpw` was visible in ps output, confirming the described attack surface (also would be persisted in shell history).*

## 3. [MINOR] main() always returns exit code 0, even when the command failed

`ledgerly/cli.py:123` — robustness

In main(), any exception raised by args.func(db, args) — including AuthError for wrong password, not-logged-in, unknown category, invalid date, etc. — is caught, printed to stderr, and then `return 0` executes unconditionally after the try/finally block. This means `ledgerly login alice wrongpass`, `ledgerly add abc food 2026-13-40`, or any other failing invocation exits with status 0. Any shell script or CI step that chains commands with `&&` or checks `$?` to detect failure (e.g. `ledgerly login $U $P && ledgerly add ...`) will incorrectly proceed as if the prior command succeeded.

*Verified: Read ledgerly/cli.py: main() (lines 118-127) catches any exception from args.func(), prints to stderr, and then unconditionally executes `return 0` after the try/finally block — there is no return of a non-zero code on the exception path. Reproduced at runtime: `python3 -m ledgerly.cli login alice wrongpass` printed 'error: unknown user' to stderr but exited with code 0. Confirmed the shell-chaining failure mode directly: `python3 -m ledgerly.cli login alice wrongpass && echo SHELL THINKS SUCCESS` printed 'SHELL THINKS SUCCESS', proving a failed login is treated as success by `&&`/`$?` checks, exactly as described in the finding.*

## 4. [MINOR] Session token briefly written world/group-readable before permissions are tightened

`ledgerly/cli.py:32` — security

`_save_token` calls `TOKEN_PATH.write_text(token)` (which creates/truncates the file using the process umask, typically 0o644 or 0o664) and only restricts permissions afterward with `TOKEN_PATH.chmod(0o600)` on line 33. Between the write and the chmod there is a window where the plaintext session token (a 24h-valid bearer credential per auth.py TOKEN_TTL_HOURS) is readable by other local users on a shared/multi-user machine. The file should be created with restrictive permissions from the start (e.g. open with os.open using O_CREAT and mode 0o600, or chmod the empty file before writing) rather than tightened after the fact.

*Verified: Read ledgerly/cli.py: _save_token does TOKEN_PATH.write_text(token) followed by TOKEN_PATH.chmod(0o600) on the next line. Reproduced with python3: under a typical umask of 0o022, write_text() creates the file with mode 0o644 (world/group-readable) and it stays that way until chmod(0o600) executes afterward -- a real, demonstrable TOCTOU window. Confirmed auth.py sets TOKEN_TTL_HOURS = 24, so the exposed token is a valid 24h bearer credential. This is a genuine code-behavior flaw (not a missing-test complaint) with a standard, well-known fix (os.open with O_CREAT and mode 0o600, or chmod-before-write).*
