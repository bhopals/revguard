# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [MAJOR] Categories ranked by lexicographic string comparison instead of numeric cents

`ledgerly/reports.py:65` — correctness

The sort key is `format_money(kv[1])`, a dollar-formatted string like "$99.00", not the underlying integer. Python compares these strings character-by-character, so e.g. a category totaling $99.00 (9900 cents) sorts ABOVE a category totaling $100.00 (10000 cents) because '9' > '1' at the second character. Any month where a category's total crosses a power-of-ten boundary relative to another (e.g. $9 vs $10, $99 vs $100, $999 vs $1000) will produce a widget that shows the wrong 'top' categories or the wrong order, contradicting the function's purpose of showing the n biggest spending categories.

*Verified: Read ledgerly/reports.py:59-71 and ledgerly/utils.py format_money(). Executed the exact sort logic from top_categories: sorted({'A':9900,'B':10000,'C':5000}.items(), key=lambda kv: format_money(kv[1]), reverse=True) produced [('A',9900),('C',5000),('B',10000)] — i.e. B ($100.00, the true largest) sorted last, below A ($99.00) and even below C ($50.00), purely because '$99.00' > '$50.00' > '$100.00*
