# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] amount_cents from upload rows is never parsed/validated before insert

`ledgerly/expenses.py:75` — correctness

import_expenses() forwards row["amount_cents"] straight into add_expense() without going through parse_money() (the codebase's existing helper for turning user-supplied amount text into validated integer cents) and add_expense() itself performs no type or positivity check on amount_cents (it only validates category, note length, and spent_on). Since rows are documented as 'parsed from CSV/JSON uploads', amount_cents will typically arrive as a string (e.g. '12.50', '-500', or 'abc'). Numeric-looking strings like '12.50' or '-500' are silently accepted by SQLite's INTEGER-affinity coercion and stored without the positive-amount check that parse_money() enforces elsewhere, while non-numeric strings like 'abc' are stored as-is with no exception raised, so the row is counted as successfully imported even though the value is garbage. Because SQLite's SUM() treats non-numeric TEXT as 0, this silently corrupts monthly_summary()/budget_status() totals (ledgerly/reports.py:25) for any category containing a bad import, with no error surfaced anywhere and the import report claiming success for that row.

## 2. [MAJOR] No tests added for import_expenses despite risky broad exception handling

`ledgerly/expenses.py:63` — test-adequacy

import_expenses() is a new public function that swallows *all* exceptions (`except Exception: pass`) while importing rows, silently discarding failures and only returning a count. No test exists anywhere in tests/test_ledgerly.py that calls import_expenses. This means: (1) there is no test verifying that valid rows are actually persisted to the database (only checking the returned count would already be insufficient, but not even that exists) — a bug that causes add_expense's DB write to silently fail or be swallowed by the broad except would go undetected; (2) there is no test confirming that a mix of valid and invalid rows results in the correct subset being imported and the invalid ones truly skipped (e.g. a row missing 'amount_cents', which raises KeyError, is caught by the bare except along with unrelated bugs like a TypeError from bad db wiring, but no test distinguishes 'expected validation skip' from 'this masked a real bug'). Given the PR explicitly describes this as a bulk-import feature meant to migrate user financial data, and the implementation uses a blanket except that could mask programming errors as 'skipped invalid rows', the complete absence of any test is a significant coverage gap that would let a broken import (e.g. one that silently imports zero rows or double-imports) pass CI undetected.
