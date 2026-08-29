# Code review: Bulk expense import

> Adds import_expenses() so users can migrate data from other apps. Takes a list of row dicts (as parsed from CSV/JSON uploads) and returns how many were imported, skipping rows that fail validation.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] No tests added for import_expenses despite risky silent-failure behavior

`ledgerly/expenses.py:63` — test-adequacy

The PR adds import_expenses(), which wraps add_expense() in a bare `except Exception: pass` that silently swallows every error (bad category, malformed date, missing dict keys, DB errors) and merely returns a count. No test was added in tests/test_ledgerly.py to exercise this function at all. Because failures are silently discarded, a test is the only way to catch: (1) that valid rows are actually inserted (not just counted), (2) that invalid/malformed rows are skipped rather than raising, (3) that the returned count matches the number of rows actually persisted to the DB, and (4) that a row missing a required key (e.g. no 'amount_cents') is skipped instead of crashing the whole import. Without such a test, a regression that breaks the loop (e.g. changes the except to swallow at the wrong scope, or a typo in a dict key) would go undetected by CI while returning a plausible-looking count.

*Verified: Read ledgerly/expenses.py: import_expenses (lines 63-83) wraps add_expense in a bare `except Exception: pass` exactly as described. Searched tests/test_ledgerly.py (grep for 'import_expenses' and AST scan for function names) and confirmed zero references/tests for this function anywhere in the suite; `pytest -q` shows 16 passing tests, none touching import_expenses. Executed a reproduction: import*

## 2. [MAJOR] import_expenses accepts unvalidated amount_cents (negative, zero, or non-integer), corrupting reports

`ledgerly/expenses.py:75` — correctness

import_expenses passes row["amount_cents"] straight through to add_expense, which never validates the amount at all (it only checks category and note length — see add_expense at expenses.py:18-28). Everywhere else in the app, money enters the system via utils.parse_money(), which rejects non-positive and malformed amounts (utils.py:13-28) before a value ever reaches add_expense; import_expenses is the first path that bypasses that guard entirely. A CSV/JSON row such as {"amount_cents": -5000, "category": "food", "spent_on": "2026-03-01"} or {"amount_cents": 0, ...} will be silently imported and counted as successful. Because reports.monthly_summary just SUMs amount_cents (reports.py:25) and reports.budget_status compares that sum against the budget limit (reports.py:49-55), a negative imported amount will understate a category's spend and can flip over_budget from True to False, while amount_cents given as a float/string like "12.5" (plausible from a CSV parser that doesn't type-cast) will be stored via SQLite's INTEGER-affinity coercion as a REAL 12.5 cents, silently producing fractional-cent totals that violate the app's stated invariant that 'all amounts are stored as integer cents' (db.py:3).

*Verified: Read expenses.py: add_expense (lines 18-28) only validates category membership and note length, never amount_cents; import_expenses (lines 63-83) passes row['amount_cents'] straight to add_expense with no call to utils.parse_money (grep confirms parse_money is never invoked anywhere in the codebase besides its own definition). Executed a reproduction against an in-memory Database: importing rows w*
