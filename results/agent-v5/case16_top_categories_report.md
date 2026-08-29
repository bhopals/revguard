# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Categories ranked by string comparison of formatted money, not numeric amount

`ledgerly/reports.py:65` — correctness

The sort key is `format_money(kv[1])`, a string like "$95.00" or "$100.00", compared lexicographically instead of comparing the underlying integer cents. Lexicographic string ordering does not match numeric ordering once dollar amounts have different digit counts: e.g. a category with 9500 cents ("$95.00") sorts ahead of one with 10000 cents ("$100.00") when reverse=True, because '9' > '1' as the first character, even though $100 is the larger spend. This produces an incorrectly ordered 'top N' list whenever such digit-length crossovers occur among a user's category totals, which is a core correctness failure for a function whose entire purpose is ranking by spend.

*Verified: Read ledgerly/reports.py:65 — sort key is `format_money(kv[1])`, a string. Read format_money (ledgerly/utils.py:31-35): no zero-padding, e.g. 9500 -> '$95.00', 10000 -> '$100.00'. Directly reproduced: sorted([9500,10000], key=format_money, reverse=True) == [9500, 10000] (wrong order, since '9'>'1' lexicographically). Also monkeypatched monthly_summary to return {'Dining':9500,'Rent':10000,'Groceries':3000} and called top_categories: output ranked Dining ($95) and Groceries ($30) ahead of Rent ($100), the actual top spender, confirming the ranking bug is reachable through the real function, not just a contrived key comparison.*

## 2. [MINOR] Docstring/PR promise of alphabetical tie-breaking is not implemented

`ledgerly/reports.py:60` — correctness

The docstring and PR description state 'Ties are broken alphabetically', but the sort key only ever uses `format_money(kv[1])` (the amount) — category name is never used as a tie-breaker. Python's sort is stable, so equal-amount categories retain whatever order they had in `spend.items()`, which comes from `monthly_summary`'s SQL query ordered by `total DESC` (SQLite's tie order for equal totals is unspecified/insertion-order based), not alphabetical order. Two categories with the same monthly total (e.g. both $50.00) will be rendered in an arbitrary, non-alphabetical order, contradicting the documented and PR-promised stable-alphabetical tie-break behavior relied on for stable widget rendering.

*Verified: Read ledgerly/reports.py:59-71: sort key is `lambda kv: format_money(kv[1])` — only the formatted amount, never the category name (kv[0]), so ties cannot be broken alphabetically. Reproduced with an in-memory DB: inserted three categories ('Zoo', 'Mango', 'Apple') each totaling $50.00, inserted in that non-alphabetical order. `top_categories()` returned them as [Zoo, Mango, Apple] — pure insertion/SQL order, not alphabetical ([Apple, Mango, Zoo] as docstring/PR claim). No test in tests/test_ledgerly.py covers top_categories or this tie-break claim, so nothing masks the bug.*
