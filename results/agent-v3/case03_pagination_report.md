# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [MAJOR] page_count off-by-one when total is an exact multiple of page_size (and for total=0)

`ledgerly/expenses.py:62` — correctness

page_count computes `total // page_size + 1` unconditionally, so it always adds one extra page even when `total` divides evenly by `page_size`. For example, with the default PAGE_SIZE=20 and a user who has exactly 20 expenses, page_count(20) returns 2 (20//20 + 1 = 2) even though all 20 items fit on a single page — the second page would come back empty from list_expenses. Likewise page_count(0) returns 1 instead of 0, implying a page of results exists when there are none. The correct formula is `(total + page_size - 1) // page_size` (or `-(-total // page_size)`), and total=0 should special-case to 0 pages. This directly contradicts the function's own docstring ('Number of pages needed to show total items') and will cause clients rendering pagination controls (the PR's stated purpose) to always show one bogus trailing page.

*Verified: Read ledgerly/expenses.py:60-61: `def page_count(total, page_size=PAGE_SIZE): return total // page_size + 1`. Ran it directly: page_count(20)=2 (should be 1), page_count(0)=1 (should be 0), page_count(21)=2 (correct), page_count(19)=1 (correct) — confirming the unconditional off-by-one for exact multiples and for total=0, exactly as described. Grepped the whole repo for `page_count` usage and foun*
