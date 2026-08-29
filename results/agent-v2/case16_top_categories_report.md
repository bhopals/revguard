# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] No tests added for new top_categories() function

`tests/test_ledgerly.py:108` — test-adequacy

The PR adds ledgerly/reports.py:59-71 (top_categories) with no accompanying test in TestReports. The function sorts categories by their formatted string (`format_money(kv[1])`) rather than by the numeric cents value, so amounts with differing digit counts sort lexicographically instead of numerically (e.g. a category spending 10000 cents formats to '$100.00' and one spending 9900 cents formats to '$99.00'; '$100.00' < '$99.00' as a string comparison, so with n=1 the function would return the smaller $99.00 category as 'top' instead of $100.00). A test with two categories whose spend differs in digit count (e.g. 10000 vs 9900 cents) would have caught this ordering bug, but no such test — or any test at all — exists for this new function.

## 2. [?] Categories sorted by formatted string instead of numeric cents

`ledgerly/reports.py:65` — correctness

`sorted(spend.items(), key=lambda kv: format_money(kv[1]), reverse=True)` sorts by the string returned by `format_money` (e.g. "$99.00", "$200.00") rather than the numeric amount. Lexicographic comparison of these strings does not match numeric order once dollar amounts have different digit counts: e.g. a category with 9900 cents ("$99.00") sorts ahead of one with 20000 cents ("$200.00") because '9' > '2' as characters, even though $200 is the larger spend. This makes top_categories() return the wrong ranking whenever spend totals cross a digit-length boundary (e.g. two-digit vs three-digit dollar amounts), which is exactly the kind of data a 'top spending categories' widget must get right.
