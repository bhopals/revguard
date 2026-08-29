# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Categories ranked by lexicographic string comparison, not by amount

`ledgerly/reports.py:65` — correctness

The sort key is `format_money(kv[1])`, a formatted string like "$12.50", not the numeric cents value. Python compares these strings character-by-character, so amounts with different numbers of digits before the decimal point sort incorrectly: e.g. spend of $9.00 vs $100.00 produces key strings "$9.00" and "$100.00"; lexicographically "$9" > "$1", so with reverse=True the $9.00 category is ranked above the $100.00 category even though it is more than ten times smaller. Any month where the top categories' totals differ in digit-count of the dollar part (e.g. $8.xx vs $10.xx, $99.xx vs $100.xx) will produce a wrong 'top n' list on the dashboard widget, which is the entire purpose of this function. This is untested (no test references top_categories in the suite) so CI does not catch it.

## 2. [MINOR] Docstring claims alphabetical tie-break, but implementation does not sort alphabetically

`ledgerly/reports.py:61` — correctness

The docstring states 'Ties are broken alphabetically for stable rendering,' but the sort key only depends on the formatted spend amount, never the category name. When two categories have equal spend, Python's stable sort preserves their relative order from `spend.items()`, which comes from `monthly_summary`'s SQL query (`ORDER BY total DESC`) — an order that is not alphabetical and not guaranteed stable across equal totals by SQLite. Callers relying on the documented alphabetical tie-break for consistent widget rendering across requests/deployments will see non-alphabetical, potentially unstable ordering for tied categories.
