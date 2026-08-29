# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] monthly_summary sums amount_cents across different currencies as if they were the same unit

`ledgerly/reports.py:25` — correctness

Before this PR every expense was implicitly USD, so SUM(amount_cents) was a valid total. This PR adds a `currency` column and lets `add_expense` insert expenses in any currency (e.g. EUR, JPY), but `monthly_summary` (used directly and via `budget_status`) still does `SUM(amount_cents) ... GROUP BY category` with no `currency` filter or conversion. For a user who logs 1000 cents in USD and 1000 cents in EUR for 'food' in the same month, the summary reports 2000 as the category total, silently treating unlike currencies as equal. `budget_status` then compares this nonsensical mixed-currency total against a USD `limit_cents`, producing wrong `spent`/`remaining`/`over_budget` values (e.g. flagging a user as over/under budget incorrectly). The PR description claims 'Reporting is unchanged', but by introducing multi-currency data it exposes reporting as now financially incorrect for any user with non-USD expenses, and no test covers this scenario.

*Verified: Read ledgerly/reports.py: monthly_summary does `SUM(amount_cents) ... GROUP BY category` with no currency filter/grouping, and budget_status compares that raw sum against a single limit_cents. Grepped the whole repo for 'currency' and found it's only used for storage/roundtrip (db.py, expenses.py, and a roundtrip test) — no conversion or currency-aware filtering exists anywhere. Reproduced live: added a $10 USD and a €10 EUR expense to category 'food' in the same month, then called monthly_summary -> {'food': 2000}, and budget_status against a $15 limit -> spent '$20.00', remaining '-$5.00', over_budget True — incorrectly flagging over-budget based on a nonsensical mixed-currency sum.*

## 2. [MINOR] currency parameter accepts and stores any unvalidated string

`ledgerly/expenses.py:18` — correctness

`add_expense` validates `category` against `VALID_CATEGORIES` but performs no validation on the new `currency` argument (no whitelist, no case normalization, no format check), and the DB schema has no CHECK constraint either. Callers can pass an empty string, lowercase codes like 'usd', or arbitrary garbage (e.g. 'US Dollar', '123'), which is stored verbatim in the `currency` column. This produces inconsistent data (e.g. 'USD' vs 'usd' treated as distinct currencies by any downstream grouping/reporting) and no error is raised for clearly invalid input, unlike the analogous `category` check the PR left untouched.

*Verified: Read expenses.py: add_expense validates category against VALID_CATEGORIES but has no equivalent check for the new currency parameter. Grepped db.py schema: currency column has no CHECK constraint, just DEFAULT 'USD'. Ran a live repro against an in-memory Database: add_expense(db, 1, 500, 'food', '2026-03-01', currency='garbage 123 !!!') succeeded and stored 'garbage 123 !!!' verbatim; currency='' stored as empty string; currency='usd' stored as lowercase 'usd' (distinct from 'USD'). Confirms no whitelist, no case normalization, and no format/empty check exists anywhere on the currency code path.*

## 3. [MINOR] new currency test only covers the happy path

`tests/test_ledgerly.py:82` — test-adequacy

test_currency_roundtrip only checks that an explicitly-supplied uppercase currency ('EUR') is stored and read back. There is no test asserting the default 'USD' is actually persisted when the currency argument is omitted, and no test for rejection/normalization of invalid or lowercase currency input, so the absence of validation noted in expenses.py is not caught by the suite.

*Verified: Read expenses.py/db.py: no validation or normalization of the currency parameter anywhere in the code path. Only one new test, test_currency_roundtrip (line 82-87), exists and it only passes currency='EUR' (uppercase, valid) and checks roundtrip. Ran a live repro: add_expense with no currency arg stores 'USD' (untested by suite), currency='eur' is stored verbatim as lowercase 'eur', and currency='NOTREAL' is stored verbatim as 'NOTREAL' — confirming both the missing validation and the missing test coverage for default/invalid/lowercase cases exactly as described.*
