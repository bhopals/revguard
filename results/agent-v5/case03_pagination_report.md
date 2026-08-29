# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [MAJOR] page_count off-by-one for exact multiples of page_size

`ledgerly/expenses.py:62` — correctness

page_count computes `total // page_size + 1`, which always adds one extra page. For total=40 and page_size=20 (exactly 2 full pages), this returns 3 instead of 2. For total=0, it returns 1 page instead of 0. The correct ceiling-division formula is `(total + page_size - 1) // page_size` (with a special case for total=0 if 0 pages is desired). Any client using this helper to render pagination controls will always show one bogus extra page, and for zero expenses it will show a page 1 that contains no results, contradicting the docstring 'Number of pages needed to show `total` items.'

*Verified: Read ledgerly/expenses.py lines 60-62: page_count(total, page_size) = total // page_size + 1. Executed directly: page_count(40,20) -> 3 (should be 2), page_count(0,20) -> 1 (should be 0), page_count(39,20) -> 2 (correct by luck). This confirms the off-by-one for exact multiples and the total=0 case exactly as described. The function is new in this PR (not pre-existing code), its docstring explicitly states 'Number of pages needed to show total items', and the implementation contradicts that contract. No other in-repo caller currently exists, but it's an exported public helper with incorrect logic, not a missing-test complaint.*
