# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] amount_cents from CSV/JSON rows is passed through unvalidated and unconverted, corrupting stored amounts

`ledgerly/expenses.py:75` — correctness

import_expenses() forwards row["amount_cents"] straight to add_expense() without going through parse_money() or any numeric/sign validation, even though the docstring says rows are 'parsed from CSV/JSON uploads' (i.e. raw strings) and other apps' exports would represent amounts as dollar strings like "12.50", not internal integer cents. Since the expenses.amount_cents column has SQLite INTEGER affinity, a string such as "12.50" is silently coerced to REAL 12.5 on insert (representing 12.5 cents = $0.125 instead of the intended $12.50), corrupting the stored value by two orders of magnitude with no error raised. A non-numeric string is stored as raw TEXT, which reports.monthly_summary()'s SUM(amount_cents) at ledgerly/reports.py:25 silently treats as 0, producing wrong totals with no indication anything went wrong. Additionally, add_expense() (ledgerly/expenses.py:18-28) performs no positivity check on amount_cents (unlike parse_money, which explicitly rejects <=0), so negative or zero amounts from a row are accepted as 'imported' even though they are semantically invalid, contradicting the PR's claim that invalid rows are skipped.

*Verified: Read ledgerly/expenses.py, reports.py, utils.py, db.py to confirm add_expense() passes amount_cents straight into a parameterized INSERT with no call to parse_money and no sign check, and the expenses.amount_cents column has INTEGER affinity. Executed a reproduction: import_expenses with rows amount_cents='12.50' (string), 'garbage' (string), -500, and 0. Result: all 4 rows reported as successfully imported (count=4); row 1 stored as amount_cents=12.5 (REAL, i.e. $0.125 instead of $12.50 — corrupted by 100x exactly as claimed); row 2 stored as raw TEXT 'garbage'; row 3 and 4 stored as -500 and 0 with no rejection.*

## 2. [MAJOR] Bare except Exception swallows systemic failures, not just per-row validation errors

`ledgerly/expenses.py:81` — robustness

The except Exception: pass at line 81 catches everything raised inside the loop, not only the expected validation errors (ExpenseError from add_expense, ValueError from parse_iso_date). It also silently swallows sqlite3.IntegrityError (e.g. a foreign-key violation if user_id does not exist in the users table, since expenses.user_id REFERENCES users(id)), sqlite3.OperationalError (e.g. db locked/disk full), and TypeError/AttributeError from malformed row values (e.g. note=None making len(note) fail). In all these cases import_expenses() just decrements the success count and continues, returning a count that looks like 'some rows had bad data' when in fact the whole import pipeline or database is broken. Callers have no way to distinguish 'user uploaded garbage rows' from 'the import silently failed due to an infrastructure/programming bug', making failures undiagnosable.

*Verified: Read ledgerly/expenses.py:63-83 matching the diff exactly, and ledgerly/db.py which shows PRAGMA foreign_keys = ON and expenses.user_id REFERENCES users(id). Reproduced with python3: add_expense(db, 999, ...) with a nonexistent user_id raises sqlite3.IntegrityError('FOREIGN KEY constraint failed'). Ran import_expenses(db, 999, rows) with one row that would trigger this IntegrityError and another with note=None (causing len(note) to raise TypeError inside add_expense) — both were silently swallowed by the bare except Exception: pass, returning count=0 with zero rows inserted and no way for the caller to distinguish this from 'all uploaded rows had bad data'.*
