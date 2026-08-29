# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 2 blocking finding(s), 0 critical.

## 1. [MAJOR] Categories ranked by lexicographic string comparison instead of numeric amount

`ledgerly/reports.py:65` — correctness

The sort key is `format_money(kv[1])`, a dollar string like "$12.50", instead of the raw integer cents. Python compares these as strings, so amounts with different digit counts sort incorrectly: e.g. spend of $9.00 in one category and $10.00 in another yields keys "$9.00" and "$10.00"; comparing character by character, '9' > '1', so "$9.00" sorts ahead of "$10.00" even though $10.00 is the larger amount. With reverse=True this means top_categories([...]) will list the $9 category as bigger than the $10 category, producing a wrong 'top spending categories' widget any time totals cross a digit-count boundary (9→10, 99→100, etc.).

*Verified: Read ledgerly/reports.py:59-71 confirming the sort key is `format_money(kv[1])`, a formatted string like "$9.00". Verified `'$9.00' > '$10.00'` evaluates to True in Python (lexicographic comparison). Reproduced with a fake DB returning categories Coffee=$9, Groceries=$10, Rent=$1000: `top_categories` returned order [Coffee $9.00, Rent $1000.00, Groceries $10.00] — clearly wrong, since Rent ($1000) should rank first and Groceries ($10) should outrank Coffee ($9). This confirms the widget produces incorrect top-spending rankings whenever amounts cross a digit-count boundary.*

## 2. [MINOR] Docstring promises alphabetical tie-break that is not implemented

`ledgerly/reports.py:61` — correctness

The docstring states 'Ties are broken alphabetically for stable rendering,' but the sort key is only `format_money(kv[1])` (spent amount) with no category name in the key. Because Python's sort is stable, equal-spend categories retain their order from `spend.items()`, which reflects `monthly_summary`'s SQL result ordering (ORDER BY total DESC, with unspecified tie order from the DB) — not alphabetical order. Two categories with identical totals (e.g. 'transport' and 'food' both at $50.00) can appear in DB/insertion order rather than alphabetical order, contradicting the documented and presumably widget-relied-upon guarantee of stable alphabetical tie-breaking.

*Verified: Read ledgerly/reports.py: top_categories sorts spend.items() with key=lambda kv: format_money(kv[1]) only — no category name in the key, so ties are resolved solely by Python's stable sort preserving spend.items() order (which comes from monthly_summary's SQL 'ORDER BY total DESC' with unspecified tie order). Reproduced with a FakeDB returning rows [transport:5000, food:5000, groceries:3000]; top_categories(...) returned transport before food despite both being $50.00, i.e. non-alphabetical, directly contradicting the docstring 'Ties are broken alphabetically for stable rendering.' This is a genuine mismatch between documented and actual behavior, not an absence-of-test complaint.*
