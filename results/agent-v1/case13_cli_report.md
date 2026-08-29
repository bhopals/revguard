# Code review: Command-line interface for Ledgerly

> Adds a ledgerly CLI with register, login, add, list and summary commands so the service can be used without writing Python. Token is cached in the user's home directory between invocations.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Amount parsing bypasses utils.parse_money, reintroducing float drift and negative/zero amounts

`ledgerly/cli.py:56` — correctness

cmd_add computes amount_cents via `int(float(args.amount) * 100)` instead of calling the existing, tested `utils.parse_money`. This reintroduces exactly the floating-point cent-drift bug the codebase's docstring (ledgerly/utils.py:3) says integer-cents storage was designed to avoid: e.g. `ledgerly add 19.99 food 2026-03-01` computes float(19.99)*100 == 1998.9999999999998, and int() truncates to 1998 cents ($19.98) instead of 1999 ($19.99), silently storing the wrong amount. It also drops parse_money's validation: `expenses.add_expense` never checks amount positivity, so `ledgerly add -50 food 2026-03-01` succeeds and inserts a negative expense (int(float('-50'))*100 == -5000), corrupting `reports.monthly_summary` totals and `list` output. Additionally, inputs documented as valid for the domain, like "$12.50" (per utils.py's parse_money docstring and the CLI's own module docstring example `add 12.50 ...`), work only by coincidence for the no-dollar-sign form; a `$`-prefixed amount raises a raw `could not convert string to float` error instead of being accepted.

## 2. [MAJOR] main() always returns exit code 0, even when a command fails

`ledgerly/cli.py:118` — robustness

In main(), any exception from args.func(db, args) — AuthError for bad login/expired token, ExpenseError for invalid category/date, ValueError from the amount parsing bug, etc. — is caught, printed to stderr, and then the function falls through to `return 0` unconditionally. Callers or scripts driving this CLI (e.g. `ledgerly add ... || echo failed`) cannot detect failures via exit status since every invocation exits 0 regardless of success or failure, defeating standard shell error-handling conventions and making automation around this CLI unreliable.
