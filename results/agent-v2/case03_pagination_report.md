# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] No test added for page_count, missing off-by-one bug coverage

`ledgerly/expenses.py:62` — test-adequacy

The PR adds `page_count(total, page_size=PAGE_SIZE)` (ledgerly/expenses.py:60-62) with zero test coverage. The implementation `total // page_size + 1` is off by one whenever `total` is an exact multiple of `page_size` (e.g. `page_count(20, 20)` returns 2 instead of the correct 1, and `page_count(0)` returns 1 instead of 0). A single added test asserting `page_count(20, 20) == 1` or `page_count(0) == 0` would have caught this and blocked the merge; instead the buggy helper ships untested, and downstream UI pagination controls built on it will render a phantom extra empty page for any user whose expense count lands exactly on a page boundary.

## 2. [MINOR] No test added for count_expenses

`ledgerly/expenses.py:50` — test-adequacy

The new `count_expenses(db, user_id, category=None)` function (ledgerly/expenses.py:50-57), including its category-filtering branch, has no test in tests/test_ledgerly.py. Since it's new SQL-building logic (mirroring the filter logic in list_expenses) and is presumably meant to be used together with page_count for pagination, an error in the WHERE clause or parameter binding (e.g. wrong column, missed filter) would go undetected.
