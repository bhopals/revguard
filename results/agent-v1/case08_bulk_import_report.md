# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] Bulk import bypasses amount validation, allowing corrupt/invalid amounts

`ledgerly/expenses.py:75` — correctness

import_expenses passes row["amount_cents"] straight to add_expense() without going through parse_money() or any type/sign check. add_expense itself performs no validation on amount_cents (it only validates category, note length, and date), relying on callers to pre-validate via parse_money as done elsewhere in the app. Since import_expenses is the first entry point that feeds untrusted, externally-supplied CSV/JSON data directly into add_expense, a row like {"amount_cents": -500, ...} or {"amount_cents": 0, ...} is accepted and silently inserted into the expenses table, and a row with a non-numeric amount_cents (e.g. "12.50" as a string) is written into the INTEGER column relying on SQLite's loose type affinity, potentially storing a TEXT value that later breaks numeric aggregation in reports.py. This lets an uploaded file corrupt a user's ledger with negative, zero, or non-numeric amounts that the normal add-expense path would never allow.

## 2. [MAJOR] Bare except silently swallows all errors, not just validation failures

`ledgerly/expenses.py:81` — robustness

The `except Exception: pass` on line 81 catches everything, not just validation errors from add_expense (ExpenseError, ValueError from parse_iso_date). A missing key on a malformed row raises KeyError, a row that isn't a dict (e.g. a stray list/string mixed into the upload) raises TypeError, and any transient DB error from db.execute would also be swallowed here. The function has no way to distinguish 'row failed validation' from 'programming bug' or 'database failure', and the caller only gets back an integer count with zero information about which rows failed or why. For a bulk-import feature meant to help users migrate real financial data, silently dropping rows on unexpected errors (e.g. a DB connectivity blip mid-loop) with no error list or exception propagation makes failures undiagnosable and risks users believing all their data imported when it silently did not.

## 3. [MINOR] No tests for import_expenses

`ledgerly/expenses.py:63` — test-adequacy

The new public function import_expenses (lines 63-83) has zero test coverage in tests/test_ledgerly.py — no test exercises the success path, the partial-skip-on-invalid-row path, or the returned count. Given this function is the primary way untrusted external data (CSV/JSON uploads) enters the ledger, the lack of any test asserting correct skip/count behavior or validating that invalid rows (bad category, bad date, negative amount) are actually rejected is a meaningful gap that let the amount-validation and error-swallowing issues above ship undetected.
