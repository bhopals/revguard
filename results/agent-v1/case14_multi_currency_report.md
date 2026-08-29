# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] monthly_summary sums amount_cents across different currencies as if they were the same currency

`ledgerly/reports.py:25` — correctness

add_expense now accepts a currency parameter (ledgerly/expenses.py:18), but monthly_summary's SQL does `SUM(amount_cents) ... GROUP BY category` with no grouping or filtering by currency. If a user records e.g. 100 cents in USD food and 100 units in EUR food, the summary reports total=200 for 'food' as though both were the same currency, silently corrupting the reported total. budget_status (ledgerly/reports.py:34-57) then compares this mixed-currency sum directly against a budget's limit_cents, producing incorrect over_budget flags and remaining amounts (e.g. a user with a $50 USD food budget who also logs a 5000 JPY expense would be flagged over-budget based on a nonsensical cross-currency sum). The PR description claims 'Reporting is unchanged,' but by allowing non-USD data into a reporting path that assumes a single currency, the PR silently breaks the correctness guarantee that totals are meaningful money sums.

## 2. [MAJOR] currency parameter is not validated, unlike category

`ledgerly/expenses.py:18` — robustness

add_expense validates category against VALID_CATEGORIES but performs no validation on the new currency argument (ledgerly/expenses.py:18-20). Any string — empty string, lowercase 'usd', whitespace, or an arbitrary long value — is accepted and persisted verbatim. This lets inconsistent currency codes (e.g. 'USD' vs 'usd') enter the same user's data, which further defeats any future or existing currency-aware aggregation and allows storing garbage values with no error surfaced to the caller.
