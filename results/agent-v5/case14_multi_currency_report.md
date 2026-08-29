# Code review: Multi-currency expenses

> Lets users record expenses in a currency other than USD. Adds a currency column (default USD) and a currency parameter to add_expense, with a test covering the new parameter. Reporting is unchanged.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] monthly_summary sums amount_cents across mixed currencies as if they were all the same currency

`ledgerly/reports.py:25` — correctness

add_expense now lets callers store expenses in any currency (e.g. EUR, GBP) via the new currency column, but monthly_summary does `SELECT category, SUM(amount_cents) ... GROUP BY category` with no filter or conversion by currency. If a user records 500 cents USD and 900 cents EUR in the same category/month, the query returns total=1400, which is neither a valid USD nor EUR amount. budget_status (reports.py:40-56) then feeds this tainted total into format_money (which always renders a '$' prefix) and into the over_budget comparison against limit_cents (assumed USD), producing a nonsensical dollar figure and a potentially wrong over/under-budget flag. The PR description states 'Reporting is unchanged,' but by introducing per-row currencies without updating reporting, it silently converts previously-correct USD totals into meaningless mixed-currency sums as soon as any non-USD expense exists.

*Verified: Read ledgerly/reports.py: monthly_summary (line 25) does SELECT category, SUM(amount_cents) GROUP BY category with no currency filter/conversion anywhere in the file or codebase (grep for 'currency' in reports.py returns nothing). Reproduced live: added a 500-cent USD expense and a 900-cent EUR expense to the same category/month via expenses.add_expense (which now accepts a currency param per this PR's diff), then called reports.monthly_summary -> {'food': 1400}, and reports.budget_status -> spent formatted as '$14.00' with over_budget=True against a $10.00 limit.*

## 2. [MINOR] currency parameter is stored without any validation, unlike category

`ledgerly/expenses.py:18` — robustness

add_expense validates category against VALID_CATEGORIES and note length, but the new currency argument is inserted directly into the database with no checks at all (lines 18-27). Callers can pass an empty string, lowercase codes ('usd' vs 'USD'), arbitrary garbage strings, or even non-string types, and the value is persisted as-is. This further fragments monthly_summary's GROUP BY behavior (case/format variants of the same currency won't aggregate together) and allows invalid currency codes to accumulate in the ledger with no error raised to the caller, unlike the existing category/note validation pattern this function otherwise follows.

*Verified: Read expenses.py: add_expense validates `category` against VALID_CATEGORIES and checks note length, but the new `currency` parameter (line 18) is passed straight into the INSERT with zero checks. Executed a reproduction against the real Database/add_expense: empty string '', garbage 'NOT_A_CURRENCY_XYZ', lowercase 'usd', and even a non-string int 12345 were all accepted and persisted with no ExpenseError, while a bogus category value correctly raised 'unknown category: not_a_category'. This confirms the core claim: currency lacks any validation unlike category.*

## 3. [MINOR] Passing currency=None raises an uncaught sqlite3.IntegrityError instead of ExpenseError

`ledgerly/expenses.py:27` — robustness

The currency column is defined NOT NULL (ledgerly/db.py:22). Because add_expense performs no validation on currency before binding it into the INSERT (expenses.py:24-29), calling add_expense(db, user_id, amount, category, spent_on, currency=None) bypasses the default 'USD' (defaults only apply when the argument is omitted entirely) and lets None flow straight into the parameterized INSERT, causing sqlite3 to raise a raw IntegrityError. This breaks the established convention in this function of surfacing input problems as ExpenseError, and would propagate an unexpected low-level DB exception to callers that only catch ExpenseError.

*Verified: Read expenses.py and db.py: add_expense validates category and note but performs no check on currency before binding it into the parameterized INSERT (expenses.py:18-29); the currency column is NOT NULL (db.py:22). Reproduced by executing: Database() + auth.register + expenses.add_expense(db, u, 500, 'food', '2026-03-01', currency=None) — this raised sqlite3.IntegrityError: 'NOT NULL constraint failed: expenses.currency' instead of expenses.ExpenseError, exactly as claimed. Grep confirms no currency validation exists anywhere in the module.*
