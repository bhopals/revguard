# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] monthly_summary sums amounts across currencies as if they were the same currency

`ledgerly/reports.py:25` — correctness

add_expense now accepts a currency parameter (ledgerly/expenses.py:18) and stores it per-row, but monthly_summary's SQL still does `SUM(amount_cents) ... GROUP BY category` with no grouping or filtering by currency (reports.py:24-31). If a user records e.g. 350 USD and 350 EUR in 'food' during the same month, the query returns {'food': 700}, silently mixing currencies into one meaningless cents total. This propagates into budget_status (reports.py:34-57), which compares that mixed total against a budget limit and computes 'remaining'/'over_budget' as if all spend were in one currency — producing wrong budget alerts (e.g. falsely flagging over-budget, or masking a real overspend) as soon as any expense uses a non-USD currency. The PR description claims 'Reporting is unchanged', but the schema/behavior change it introduces breaks the previously-valid invariant that all amount_cents in a sum share a currency.

*Verified: Read reports.py: monthly_summary (lines 22-31) does SUM(amount_cents) GROUP BY category only, with no currency grouping/filter, despite expenses.py:18 now accepting a currency param stored per-row (db.py schema change). Reproduced with actual execution: added a 350 USD and a 350 EUR expense in category 'food' for the same month; monthly_summary returned {'food': 70000} (i.e. 700.00), conflating two different currencies into one meaningless total. Then set a $500 budget for 'food' and called budget_status, which returned over_budget: True with remaining: -$200.00 — a false over-budget alert, since the USD-only spend (350) was actually under the 500 budget.*

## 2. [MINOR] currency parameter is stored without any validation

`ledgerly/expenses.py:18` — robustness

Unlike category, which is validated against VALID_CATEGORIES (expenses.py:19-20), the new currency argument is passed straight into the INSERT with no whitelist, format, or normalization check (expenses.py:24-29). Callers can pass an empty string, arbitrary text, mixed case ('usd' vs 'USD'), or overly long strings, all of which are persisted as-is. Because reporting/grouping logic elsewhere in the codebase (and any future currency-aware code) would rely on currency values being consistent codes, this lets inconsistent or garbage values into the expenses table with no error signaled to the caller, unlike every other validated field on this row.

*Verified: Read ledgerly/expenses.py: add_expense (line 18) validates category against VALID_CATEGORIES and note length, but the new currency parameter (added in this PR) is passed directly into the INSERT with no check at all. Reproduced with actual execution: inserting expenses with currency='', 'usd', 'not-a-currency', a 500-char string, and an emoji all succeeded and were persisted verbatim (confirmed via get_expense), while category validation correctly rejects invalid values elsewhere in the same function.*
