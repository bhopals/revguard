# Code review: Command-line interface for Ledgerly

> Adds a ledgerly CLI with register, login, add, list and summary commands so the service can be used without writing Python. Token is cached in the user's home directory between invocations.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] Amount parsing bypasses utils.parse_money, causing wrong cent values and allowing non-positive amounts

`ledgerly/cli.py:56` — correctness

cmd_add computes `amount_cents = int(float(args.amount) * 100)` instead of calling `utils.parse_money`, which the module docstring says is the correct way to convert user-supplied amounts to integer cents. This has two concrete failure modes: (1) float imprecision silently corrupts the stored amount, e.g. `python -m ledgerly.cli add 19.99 food 2026-03-01` computes float(19.99)*100 == 1998.9999999999998, and int() truncates it to 1998 cents ($19.98) instead of 1999 cents ($19.99) — the expense is recorded and echoed back as $19.98, one cent short of what the user typed, with no error. This happens for many two-decimal amounts (e.g. 29.99, 8.99) due to standard binary floating point representation. (2) parse_money explicitly rejects zero/negative amounts ('amount must be positive'), but the hand-rolled conversion does not: `add -5.00 food 2026-03-01` produces amount_cents = -500, and expenses.add_expense has no positivity check, so a negative expense is silently inserted into the database, corrupting monthly_summary totals and budget_status comparisons for that user/month.

## 2. [MAJOR] Token file created world/group-readable before permissions are restricted

`ledgerly/cli.py:31` — security

`_save_token` calls `TOKEN_PATH.write_text(token)` (line 32) before `TOKEN_PATH.chmod(0o600)` (line 33). `write_text` creates the file (if it doesn't already exist) with permissions governed by the process umask — typically 0644 on most systems — and the session token is written to disk in that window before the chmod call restricts access. On a multi-user machine, any other local user can read `~/.ledgerly_token` during that window (or via a race that repeatedly triggers `login`) and obtain a valid 24-hour bearer token for the victim's account, since `auth.authenticate` only checks token equality/expiry with no additional binding to the requesting user. The fix is to create the file with restrictive permissions atomically, e.g. via `os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)` before writing, rather than chmod-ing after the fact.

## 3. [MAJOR] Passwords accepted as plaintext CLI positional arguments

`ledgerly/cli.py:91` — security

`register` and `login` take `password` as a positional argv argument (lines 90-91, 96, consumed at lines 44 and 49). Command-line arguments are visible to every other local user via `ps aux` / `/proc/<pid>/cmdline` while the process runs, and are also written verbatim into the user's shell history file (e.g. `~/.zsh_history`) since the examples in the module docstring itself recommend invoking it this way. This leaks the plaintext account password to any co-resident user or anyone who later reads the shell history/history-sync backups, defeating the PBKDF2 hashing done server-side. Secrets like passwords should be read via an interactive, non-echoing prompt (e.g. `getpass.getpass`) rather than accepted as a CLI argument.
