# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [MAJOR] page_count off-by-one when total is an exact multiple of page_size

`ledgerly/expenses.py:62` — correctness

`total // page_size + 1` always adds one extra page. If a user has exactly 20 expenses and page_size is 20, page_count(20, 20) returns 2 instead of 1, so a client rendering pagination controls will show a bogus second page that, when requested via list_expenses, returns an empty list. Similarly total=0 returns 1 instead of 0 pages. The correct formula is ceiling division, e.g. `(total + page_size - 1) // page_size` (with a total==0 special case).
