# Code review: Command-line interface for Ledgerly

> Adds a ledgerly CLI with register, login, add, list and summary commands so the service can be used without writing Python. Token is cached in the user's home directory between invocations.

**Verdict: request changes.** 6 blocking finding(s), 0 critical.

## 1. [MAJOR] Amount parsing bypasses the validated cents parser and uses lossy float arithmetic

`ledgerly/cli.py:56` — correctness

cmd_add computes `amount_cents = int(float(args.amount) * 100)` instead of calling `utils.parse_money`, which the codebase already provides specifically 'to avoid floating point drift' (see db.py and utils.py docstrings). Float multiplication of values like `19.99 * 100` does not always land exactly on an integer (e.g. results such as 1998.9999999999998), and `int()` truncates toward zero rather than rounding, so a user running `ledgerly add 19.99 food 2026-03-01` can silently have the expense recorded as $19.98 instead of $19.99. Over many entries this produces systematic off-by-one-cent errors in stored amounts and downstream summaries/budgets.

*Verified: Reproduced empirically: python3 -c 'print(int(float("19.99")*100))' yields 1998, not 1999, because 19.99*100 == 1998.9999999999998 in IEEE float and int() truncates toward zero. Read ledgerly/utils.py and confirmed parse_money(text) exists exactly to avoid this (docstring: 'Money is always integer cents internally... to avoid floating point drift' behavior, correctly does regex-based integer parsing to cents). Grep for 'parse_money' across ledgerly/ shows it is defined in utils.py but never called anywhere in the codebase, including cli.py line 56 which instead does `amount_cents = int(float(args.amount) * 100)` — reachable directly from cmd_add, the handler for `ledgerly add`.*

## 2. [MAJOR] main() always returns exit code 0 even when a command fails

`ledgerly/cli.py:127` — robustness

In main(), any exception raised by args.func(db, args) (AuthError for bad credentials/expired token/not logged in, ExpenseError for invalid category/date/page, ValueError from parse_iso_date, etc.) is caught, an 'error: ...' message is printed to stderr, and then `return 0` is reached unconditionally after the except block. Since `sys.exit(main())` uses this return value, the process exits with status 0 on failure just as on success. A shell script or CI step doing `ledgerly login alice wrongpass || fail` (or checking `$?` after `ledgerly add ...`) cannot detect the failure and will proceed as though the operation succeeded.

*Verified: Read ledgerly/cli.py:118-127, matching the diff exactly. Ran `python3 -m ledgerly.cli login alice wrongpass` against an empty temp DB/home: printed 'error: unknown user' to stderr but exited with status 0. Also ran `python3 -m ledgerly.cli list` without logging in first: printed 'error: not logged in...' but exited 0. This confirms main() unconditionally returns 0 after the except block, so sys.exit(main()) always yields a success exit code even on failure — a genuine, reachable robustness bug affecting any script/CI checking $? after a ledgerly invocation.*

## 3. [MAJOR] Passwords accepted as plaintext CLI positional arguments

`ledgerly/cli.py:90` — security

register and login take `password` as a positional argparse argument (lines 91 and 96, invoked as `python -m ledgerly.cli register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process's lifetime, and is also persisted in plaintext in the user's shell history file (e.g. ~/.bash_history, ~/.zsh_history) since most shells log the whole invoked command line. This directly exposes credentials that the rest of the codebase otherwise protects with PBKDF2 hashing and constant-time comparison.

*Verified: Read ledgerly/cli.py lines 88-98: `register` and `login` subparsers add `password` as a plain positional argparse argument (add_reg.add_argument("password"); add_login.add_argument("password")), with no use of getpass or any masked-input mechanism anywhere in the repo (grepped for 'getpass' - zero hits). Confirmed by execution: ran `python3 -m ledgerly.cli register dave PlainTextPW777 &` and captured `ps -ww -p $PID -o pid,command` while the process was live - the plaintext password `PlainTextPW777` appeared verbatim in the process listing.*

## 4. [MINOR] Over-broad except swallows all exceptions, including programming errors

`ledgerly/cli.py:123` — robustness

`except Exception as e` in main() catches not only expected domain errors (AuthError, ExpenseError, ValueError from bad input) but also unrelated bugs such as AttributeError/TypeError/sqlite3.Error from db access. All are reduced to a generic 'error: {e}' message with no traceback, and (combined with the exit-code-0 bug) the process reports success regardless. This hides real defects from users and from any automation invoking the CLI, since there is no way to distinguish an expected validation failure from an internal crash.

*Verified: Read ledgerly/cli.py:118-127 confirming `except Exception as e:` catches everything and `main()` unconditionally `return 0`s afterward (no re-raise, no traceback, no differentiated exit code). Reproduced via python3: monkeypatched expenses.add_expense to raise AttributeError (simulating an internal/programming bug unrelated to domain validation) and ran cli.main(['add', '12.5', 'food', '2026-01-01']); output was `error: 'NoneType' object has no attribute 'execute'` with return code 0, identical in shape/exit behavior to genuine domain errors (e.g. 'not logged in', 'unknown user').*

## 5. [MINOR] summary month argument is not validated before being used as a string-prefix filter

`ledgerly/cli.py:77` — robustness

cmd_summary passes args.month straight to reports.monthly_summary, which matches it against `substr(spent_on, 1, 7)` with a plain string comparison — no format check is performed anywhere in the new CLI path. If a user supplies a malformed month (e.g. '2026-3', '26-03', or 'March-2026'), the query simply matches zero rows and cmd_summary prints an empty summary (or `{}` with --json) instead of surfacing an error, silently masking a user typo as 'no expenses for that month'.

*Verified: Read reports.monthly_summary: it does `WHERE user_id = ? AND substr(spent_on, 1, 7) = ?` with the raw args.month, no format validation anywhere in cli.py, reports.py, or utils.py (grepped for 'month' across ledgerly/). Executed the actual CLI: registered a user, added an expense dated 2026-03-01, then ran `summary 2026-3`, `summary 26-03`, and `summary not-a-month` — all silently printed nothing (or `{}` with --json) instead of an error, exactly as described, while `summary 2026-03` correctly showed the expense.*

## 6. [MINOR] Token file created with default (world/group-readable) permissions before being locked down

`ledgerly/cli.py:32` — security

_save_token calls TOKEN_PATH.write_text(token) which creates the file (if it doesn't already exist) using the process's default umask-derived mode (commonly 0644), and only afterward calls chmod(0o600). Between the write and the chmod call there is a window where the freshly created ~/.ledgerly_token file containing a live, unexpired 24-hour bearer token is readable by other local users on a shared/multi-user system. A file that already existed with looser permissions from a prior write in a permissive umask environment is fixed up, but the initial creation is still briefly exposed, letting a local attacker who wins the race read the session token and impersonate the user for up to TOKEN_TTL_HOURS.

*Verified: Read ledgerly/cli.py:31-33, matching the diff exactly: `_save_token` calls `TOKEN_PATH.write_text(token)` then `TOKEN_PATH.chmod(0o600)`. Reproduced with `umask 022; Path.write_text(...)` then checked stat before chmod: file mode is 0o100644 (world/group-readable) immediately after write_text, and only 0o100600 after the subsequent chmod call. This confirms a real TOCTOU window during which a freshly-created ~/.ledgerly_token (containing a live bearer token) is readable by other local users before permissions are locked down. This is a genuine security defect in newly introduced code, not a test-coverage gripe, so it passes the policy gate.*
