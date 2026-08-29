# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] amount_cents from import rows is never validated or converted, breaking the app's integer-cents invariant

`ledgerly/expenses.py:75` — correctness

import_expenses() forwards row["amount_cents"] straight into add_expense() (ledgerly/expenses.py:18-28), which does zero validation on amount_cents — no type check, no positivity check. Unlike the rest of the app, which funnels user-entered amounts through utils.parse_money() (ledgerly/utils.py:13-28) to convert dollar strings into validated positive integer cents, import_expenses has no equivalent step. Since rows are described as 'parsed from a CSV/JSON upload', amount_cents will typically arrive as a string (e.g. "12.50" or "$12.50") or could be negative/zero. Because the expenses.amount_cents column has INTEGER affinity but SQLite only converts text that is a losslessly-representable integer literal, a value like "12.50" is stored verbatim as TEXT. This corrupts ledgerly/reports.py:25's `SUM(amount_cents)` monthly summary (non-numeric-looking cells are treated as 0, silently dropping the expense from totals) and violates the module docstring in ledgerly/utils.py:3 ('Money is always integer cents internally'). Negative or zero amounts are also accepted and imported even though the app's own convention (parse_money) explicitly rejects amounts <= 0, contradicting the import docstring's promise that 'Invalid rows are skipped'.

*Verified: Read expenses.py: import_expenses (lines 63-83) passes row['amount_cents'] straight to add_expense, which (lines 18-28) only validates category, note length, and spent_on — never amount_cents, unlike parse_money (utils.py:13-28) used elsewhere which rejects non-numeric and <=0 amounts. Reproduced end-to-end with sqlite3: imported rows with amount_cents='12.50', '$12.50', -500, 0, and 1250 all succeeded (import_expenses returned count=5, none skipped) despite the docstring's 'Invalid rows are skipped' promise.*

## 2. [MINOR] Bare except Exception silently swallows non-validation errors with no distinction or reporting

`ledgerly/expenses.py:81` — robustness

The except clause at lines 81-82 catches *any* exception raised while importing a row — not just ExpenseError from validation — and discards it with no logging. This means database-level failures (e.g. sqlite3.IntegrityError from a NOT NULL/foreign-key violation, sqlite3.OperationalError from a locked/corrupt DB, or an unexpected TypeError from malformed row data) are treated identically to a normal validation failure. A caller has no way to tell 'the CSV had 5 malformed rows' apart from 'the database connection failed mid-import and the remaining 995 rows were never attempted', since both simply reduce the returned count with zero diagnostic information. This is a regression in error signaling compared to add_expense(), which normally raises ExpenseError with a specific reason for callers to handle or surface to the user.

*Verified: Read ledgerly/expenses.py lines 63-83: import_expenses wraps add_expense in `except Exception: pass` with no logging/reporting. Reproduced with python3: add_expense(db, 1, 300, 'food', '2024-01-01', None) raises TypeError (len(None) on note check), and add_expense(db, 999, ...) with a non-existent user_id raises sqlite3.IntegrityError (FOREIGN KEY constraint failed) since db.py enables PRAGMA foreign_keys=ON. Running import_expenses with a mix of a valid row, an ExpenseError-triggering row (bad category), a TypeError-triggering row (note=None), and a real DB error all reduced to a single silently-skipped count with zero diagnostics -- e.g.*
