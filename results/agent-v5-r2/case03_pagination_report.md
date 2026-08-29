# Code review: Configurable page size for expense listing

> Lets API callers choose a page size when listing expenses and adds a page_count helper so clients can render pagination controls.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [MAJOR] page_count off-by-one for exact multiples and zero total

`ledgerly/expenses.py:62` — correctness

page_count(total, page_size) computes `total // page_size + 1`, which is not ceil(total/page_size). For total=0 it returns 1 (implying there is a page to render even though there are no expenses), and for any total that is an exact multiple of page_size (e.g. total=20, page_size=20) it returns 2 instead of 1, adding a phantom empty trailing page. A client rendering pagination controls with this helper (the stated purpose in the PR description) will show an extra, empty last page whenever the item count is a multiple of the page size, or a page indicator when there are zero items.

*Verified: Extracted and ran page_count(total, page_size) = total // page_size + 1 directly: page_count(0,20)=1 (should be 0, no pages for zero items) and page_count(20,20)=2 (should be 1, exact multiple shouldn't add a phantom page), while page_count(19,20)=1 and page_count(21,20)=2 are correct. Confirmed via grep that page_count has no other internal caller performing correction, and there are no existing tests for expenses.py. This is a genuine off-by-one in new public API code shipped in this PR (not a test-coverage complaint), directly affecting the stated pagination-UI purpose of the PR.*
