# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] monthly_summary/budget_status sum amount_cents across different currencies as if they were all USD

`ledgerly/reports.py:25` — correctness

add_expense (ledgerly/expenses.py:18) now accepts a `currency` parameter and stores non-USD amounts in the same `amount_cents` column used everywhere for arithmetic, but monthly_summary's `SUM(amount_cents)` (reports.py:25) and budget_status's comparison against `limit_cents` (reports.py:49-55) never filter or convert by currency. If a user records e.g. 999 cents in EUR and 999 cents in USD in the same month/category, monthly_summary returns 1998 as a single USD-denominated total, and budget_status compares that mixed sum directly against a USD budget limit, silently producing a financially meaningless total and a wrong over_budget flag. Before this PR all rows were implicitly USD so the sum was valid; now that arbitrary currencies can be inserted, the unchanged reporting code produces incorrect results without any error or warning.

## 2. [MAJOR] currency parameter accepted and persisted without validation

`ledgerly/expenses.py:18` — correctness

add_expense validates `category` against VALID_CATEGORIES and validates note length, but the new `currency` parameter is inserted into the database unchecked (expenses.py:25-28). Callers can pass an empty string, lowercase codes like "usd", or arbitrary garbage (e.g. "XYZ123"), all of which are stored as-is in a NOT NULL TEXT column. This lets inconsistent/invalid currency values (e.g. "USD" vs "usd" for the same real currency) coexist for the same user, so any future currency-aware grouping or filtering will silently split what should be one currency into two, and get_expense/list_expenses will surface non-standard currency codes to callers with no indication they are invalid.

## 3. [MAJOR] No test guards against silent cross-currency summation in reports

`tests/test_ledgerly.py:97` — test-adequacy

The PR's whole purpose is to let add_expense record amounts in currencies other than USD (expenses.py:18), but reports.monthly_summary (reports.py:22-31) and budget_status still do a plain SUM(amount_cents) with no currency filter or conversion, so USD and EUR expenses in the same month are silently added together as if they were the same unit. The PR description explicitly claims 'Reporting is unchanged,' but no test in TestReports (test_ledgerly.py:97-114) exercises a scenario where an expense has a non-USD currency alongside a USD one. If a caller adds a 100 EUR and a 100 USD expense in the same category/month, monthly_summary silently returns 200 as a single total, and budget_status compares that meaningless mixed total against a limit — a real financial correctness bug that the test suite cannot detect because TestExpenses.test_currency_roundtrip (test_ledgerly.py:82-87) only checks that the currency column round-trips, never that it interacts correctly (or is guarded) with the reporting/aggregation code the PR's new capability directly affects.
