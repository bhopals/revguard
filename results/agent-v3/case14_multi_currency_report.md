# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 3 blocking finding(s), 2 critical.

## 1. [CRITICAL] monthly_summary sums amount_cents across different currencies as if they were the same unit

`ledgerly/reports.py:25` — correctness

add_expense now accepts a currency parameter (ledgerly/expenses.py:18) that stores an arbitrary currency alongside amount_cents, but monthly_summary does `SELECT category, SUM(amount_cents) ... GROUP BY category` with no reference to currency at all. If a user records e.g. 100 EUR-cents (currency='EUR') and 100 USD-cents (currency='USD') in the same category/month, the summary reports {'food': 200} and format_money renders it as '$2.00' — silently treating EUR and USD as fungible. This corrupts monthly_summary for any user who records expenses in more than one currency, which is exactly the scenario this PR introduces.

*Verified: Read ledgerly/reports.py:22-31 — monthly_summary's SQL groups only by category, never currency. Reproduced live: inserted 100 EUR-cents and 100 USD-cents into the same user/category/month via expenses.add_expense, then called reports.monthly_summary — output was {'food': 200}, and format_money(200) rendered '$2.00', exactly as the finding describes. Confirmed format_money (ledgerly/utils.py:31-35)*

## 2. [CRITICAL] budget_status compares mixed-currency spend against a single-currency limit

`ledgerly/reports.py:49` — correctness

budget_status computes `spent = spend.get(b['category'], 0)` from monthly_summary's currency-blind sum, then does `remaining = b['limit_cents'] - spent` and `over_budget = spent > b['limit_cents']`. limit_cents is implicitly in USD (set via set_budget with no currency concept), but spent may now include amounts recorded in EUR, JPY, etc. via add_expense's new currency parameter. A user who sets a $50 USD food budget and logs a 4000-cent (¥40) expense would have it added directly to the USD-denominated spent total, producing a wrong over_budget flag and a wrong 'remaining'/'spent' dollar figure without any currency conversion or warning.

*Verified: Read ledgerly/reports.py: monthly_summary (line 25) sums amount_cents grouped only by category, ignoring the new currency column entirely; budget_status (lines 48-55) subtracts/compares this currency-blind sum directly against limit_cents. Grepped the whole repo for 'currency' usage — it appears only in db.py's schema and expenses.py's add_expense/get_expense; there is no conversion or currency-ch*

## 3. [MAJOR] No test covers reports mixing currencies, though PR enables it

`tests/test_ledgerly.py:82` — test-adequacy

The PR adds a currency parameter to add_expense (ledgerly/expenses.py:18) and claims 'reporting is unchanged', but reports.monthly_summary (ledgerly/reports.py:22-31) sums amount_cents per category with no currency grouping or conversion. If a user adds a USD expense and an EUR expense in the same category/month, monthly_summary and budget_status will silently add the raw cent values together as though they were the same currency, producing a meaningless total. The only new test, test_currency_roundtrip, checks that the currency string round-trips through get_expense but never calls monthly_summary or budget_status with mixed-currency data, so this incorrect aggregation is completely unverified and would not be caught by the test suite.

*Verified: Read ledgerly/reports.py: monthly_summary (lines 22-31) groups only by category and SUMs amount_cents with no currency awareness; budget_status calls monthly_summary directly. Reproduced with actual execution: adding a 100-cent USD expense and a 200-cent EUR expense in the same category/month yields monthly_summary == {'food': 300}, silently mixing currencies. Grepped tests/test_ledgerly.py for 'c*
