# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] CSV/JSON amount field passed to add_expense without parsing into integer cents

`ledgerly/expenses.py:75` — correctness

import_expenses() takes row["amount_cents"] straight from a CSV/JSON upload and forwards it verbatim to add_expense(), which just inserts it into the INTEGER amount_cents column with no type coercion or validation (expenses.py:24-28). Unlike every other amount in this codebase, this value never goes through utils.parse_money(), the function whose entire purpose is 'Parse a user-supplied amount into integer cents' from formats like '12.50' or '$12.50' (utils.py:13-28). A CSV export from another app is very likely to contain a dollar amount as a string (e.g. "12.50") rather than pre-computed integer cents; that string gets stored as-is (SQLite's INTEGER affinity only coerces well-formed integer literals, not decimals like '12.50', which are stored as REAL 12.5). This breaks the 'amounts are always integer cents' invariant documented in db.py, and reports.format_money(cents) (utils.py:31-35) then does `cents % 100:02d}` on a float, raising ValueError the next time a user views monthly_summary/budget_status for that data — or, for values that parse as whole-number strings, silently importing an amount 100x smaller than intended (e.g. a row meaning $12.50 gets stored as 12 or 13 cents).

*Verified: Read expenses.py: import_expenses() (lines 63-83) passes row['amount_cents'] straight to add_expense() with no call to utils.parse_money, and add_expense() (lines 18-28) inserts it verbatim into the INTEGER amount_cents column with no coercion. Reproduced end-to-end: created an in-memory DB, called import_expenses(db, 1, [{'amount_cents': '12.50', ...}, {'amount_cents': '13', ...}]). Both rows imported successfully (count=2). SQLite stored '12.50' as REAL 12.5 (confirmed via typeof()), and stored '13' as INTEGER 13.*

## 2. [MAJOR] New import_expenses() function has zero test coverage

`ledgerly/expenses.py:63` — test-adequacy

The PR adds import_expenses(), a public function with nontrivial behavior (bulk insertion, per-row error swallowing via a bare `except Exception: pass`, silent skip counting), but no tests were added in tests/test_ledgerly.py (the only test file, which was not modified by this diff). There is no test verifying: (1) valid rows are actually imported and persisted, (2) invalid rows (bad category, bad date, missing keys) are skipped and counted correctly, (3) the returned count matches the number of successfully imported rows, or (4) rows are correctly scoped to user_id. Because the swallow-all exception handler can silently mask bugs (e.g. a KeyError from a malformed row, or a DB error), the absence of any test means a broken or overly permissive/overly strict implementation would not be caught by CI.

*Verified: Grepped the entire repo for `import_expenses` usage; the only hit is the function definition in ledgerly/expenses.py itself (line 63), with zero references in tests/test_ledgerly.py or anywhere else. Read the full test file: TestExpenses class (lines 59-88) covers add/get/delete/ownership/bad-category/list-filter but has no test for import_expenses, bulk skip-counting, or error swallowing. Ran the existing suite (`pytest -q`) — 16 tests pass, none exercising the new function. This confirms the new public function with a bare `except Exception: pass` and count-based return value has no test coverage at all, matching the finding exactly.*

## 3. [MAJOR] Blanket `except Exception: pass` hides programming and system errors, not just bad input

`ledgerly/expenses.py:81` — robustness

The loop catches every exception type identically, including `KeyError`/`TypeError` from malformed row dicts, `sqlite3` errors from the DB layer, and any future bug in `add_expense`, indistinguishably from the intended `ExpenseError` validation failures. All of these are silently discarded with no logging, no per-row diagnostic, and no way for the caller to tell 'row had a bad category' apart from 'the database connection died mid-import' or 'my code has a bug'. For a bulk-import feature meant to help users migrate data, returning only an opaque success count with zero information about which rows failed or why is a poor error-reporting contract and will make debugging failed imports (e.g. a systematic key-name mismatch causing every row to raise `KeyError`) very difficult — the function would report 0 imported with no indication of the actual cause.

*Verified: Read ledgerly/expenses.py:63-83, which matches the diff exactly. Executed a reproduction: called import_expenses with a row using a mismatched key name ('amt_cents' instead of 'amount_cents'), which raises KeyError inside the loop; the blanket `except Exception: pass` swallows it and the function returns count=0 with no indication of the cause. Grepped the file for logging/error-collection and found none, confirming there is no way to distinguish validation failures (ExpenseError) from KeyError/TypeError/DB errors/bugs — all produce an identical silent skip and an opaque success count.*
