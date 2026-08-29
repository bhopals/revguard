# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 4 blocking finding(s), 0 critical.

## 1. [MAJOR] page_count off-by-one when total is an exact multiple of page_size

`ledgerly/expenses.py:62` — correctness

`page_count` computes `total // page_size + 1`, which always adds an extra page even when `total` divides evenly by `page_size`. E.g. total=40, page_size=20 (two full pages) returns 3 instead of 2; total=0 returns 1 instead of 0. Clients using this helper to render 'Page X of N' pagination controls will show a phantom last page that, when requested via `list_expenses`, returns an empty result set. The correct formula is `-(-total // page_size)` or `(total + page_size - 1) // page_size` for total>0, with 0 handled specially. This is a new function introduced by this PR with no boundary-case test coverage.

*Verified: Read ledgerly/expenses.py:60-62, confirming page_count(total, page_size) = total // page_size + 1. Executed it directly: page_count(40,20) -> 3 (should be 2), page_count(0,20) -> 1 (should be 0), page_count(20,20) -> 2 (should be 1). Grepped the repo for other usages/tests of page_count and found none, confirming it's untested. The off-by-one is real and reachable exactly as described.*

## 2. [MAJOR] Unvalidated page_size lets callers bypass pagination limit entirely

`ledgerly/expenses.py:75` — security

list_expenses() (line 65) accepts a caller-supplied page_size with no bounds checking, unlike the page parameter which is validated (line 67-68). If a caller passes page_size=0 or a negative value, it is placed directly into the SQL LIMIT clause (line 75). SQLite treats a negative LIMIT as 'no limit' (LIMIT -1 returns all matching rows), so a caller invoking list_expenses(db, user_id, page_size=-1) gets every expense row for that user in a single query, completely defeating the pagination the PR is meant to enforce. There is also no upper bound, so a caller can request an arbitrarily large page_size (e.g. 10**9) to force the DB to materialize and return the user's entire expense history in one call. Since the PR description states this page_size is meant to be caller/API-controlled, an API endpoint built on this function would let any authenticated user force unbounded result sets, which can be used for resource-exhaustion (memory/CPU/DB load) against the service. Fix by validating 1 <= page_size <= some MAX_PAGE_SIZE before building the query.

*Verified: Read ledgerly/expenses.py: list_expenses (line 65-76) validates `page < 1` but never validates `page_size`, which flows straight into the SQL LIMIT clause built with plain sqlite3 (ledgerly/db.py). Reproduced with a live in-memory DB seeded with 50 rows: list_expenses(db,1) with default page_size=20 returns 20 rows; list_expenses(db,1,page_size=-1) returns all 50 rows (confirms SQLite's LIMIT -1 = unlimited, bypassing pagination); list_expenses(db,1,page_size=10**9) also returns the full set with no clamping. Grep confirms no MAX_PAGE_SIZE/upper-bound check exists anywhere in the module.*

## 3. [MAJOR] No tests added for count_expenses, page_count, or the new page_size parameter

`tests/test_ledgerly.py:108` — test-adequacy

The PR adds three new/changed pieces of public behavior in ledgerly/expenses.py — count_expenses() (line 50), page_count() (line 60), and the new page_size parameter on list_expenses() (line 65) — but tests/test_ledgerly.py has no new test cases for any of them (TestExpenses still ends at test_list_filters_by_category, line 82-86, unchanged). This leaves an off-by-one defect in page_count undetected: page_count(20, page_size=20) returns 2 (should be 1) and page_count(0) returns 1 (should be 0), because `total // page_size + 1` always adds one page even when total is an exact multiple of page_size or zero. A single test asserting page_count(0) == 0 or page_count(page_size, page_size) == 1 would have caught this before merge, but no such test exists.

*Verified: Read ledgerly/expenses.py: page_count(total, page_size) = total // page_size + 1. Executed python3: page_count(20, page_size=20) returns 2 (should be 1) and page_count(0) returns 1 (should be 0), confirming the off-by-one bug exactly as described. Grepped tests/test_ledgerly.py for 'count_expenses|page_count|page_size' — zero matches, confirming no tests exist for any of the new public functions/parameter added in this PR.*

## 4. [MINOR] No tests added for the new public functions

`ledgerly/expenses.py:50` — test-adequacy

This PR adds `count_expenses`, `page_count`, and a new `page_size` parameter on `list_expenses`, but tests/test_ledgerly.py has no new test cases exercising any of them (only the pre-existing category-filter test remains). The off-by-one bug in `page_count` and the missing page_size validation would both have been caught by even minimal coverage (e.g. total that's an exact multiple of page_size, or page_size=0).

*Verified: Grepped tests/test_ledgerly.py for count_expenses/page_count/page_size — zero matches, confirming no new tests were added for the three new public API surfaces. Executed the code: page_count(20, 20) returns 2 instead of the correct 1 (off-by-one when total is an exact multiple of page_size), and page_count(0, 20) returns 1 instead of 0. Also confirmed list_expenses has no page_size validation (unlike its `page < 1` check) — page_size=0 passes through silently to 'LIMIT 0 OFFSET 0' rather than raising ExpenseError. Both bugs are real and reachable, and are exactly the kind minimal test coverage would catch, matching the finding's description.*
