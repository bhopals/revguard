# Code review: Top spending categories widget

> Adds top_categories() for the dashboard widget: the user's n biggest categories for a month, formatted for display. Ties are broken alphabetically for stable rendering.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Categories ranked by lexicographic string comparison of formatted money, not numeric amount

`ledgerly/reports.py:65` — correctness

The sort key is `format_money(kv[1])`, which returns strings like "$9.00" or "$10.50". Sorting these as strings (with `reverse=True`) compares character by character, so e.g. a category with $9.00 spent will rank above one with $10.50 spent because '9' > '1' lexicographically, even though $10.50 > $9.00 numerically. Any month where a smaller-total category's dollar amount starts with a higher leading digit than a larger-total category (e.g. totals crossing the 10/100/1000 dollar boundary, such as $95.00 vs $120.00) will produce a widget that shows categories in the wrong order and can even drop a genuinely top category out of the top-n list.

*Verified: Read ledgerly/reports.py:59-71 and ledgerly/utils.py's format_money (produces unpadded strings like '$95.00' vs '$120.00'). Reproduced with Python: sorted({'A':9500,'B':12000}.items(), key=lambda kv: format_money(kv[1]), reverse=True) yields [('A',9500),('B',12000)] — A ($95.00) ranks above B ($120.00) despite being numerically smaller, because '$95.00' > '$120.00' lexicographically. Also reproduced the top-n-drop scenario: with spend {'A':9500,'B':9400,'C':12000}, ranked[:2] = [A,B], excluding C even though C ($120.00) is the actual highest spender. Both failure modes described in the finding are real and directly reachable via the diff's sort key.*

## 2. [MINOR] Docstring claims alphabetical tie-breaking that the implementation does not perform

`ledgerly/reports.py:61` — correctness

The docstring states "Ties are broken alphabetically for stable rendering," but the sort key at line 65 only uses `format_money(kv[1])` — there is no secondary key on category name. Since Python's `sorted` is stable, tied amounts retain whatever order they had in `spend.items()`, which comes from `monthly_summary`'s dict built from a SQL query ordered by `total DESC` with no tiebreaker (line 28), so the relative order of tied categories is whatever the database happens to return, not alphabetical. This means the documented and load-bearing guarantee ("for stable rendering") does not hold: two categories with equal spend can render in an order that changes between runs/DB engines, contradicting the docstring and the PR's stated design goal.

*Verified: Read ledgerly/reports.py: top_categories docstring says 'Ties are broken alphabetically' but the sort call at line 63-67 uses only key=lambda kv: format_money(kv[1]) with no secondary key on category name. Confirmed via execution with a FakeDB returning two tied categories ('Zoo' and 'Apples', both $50.00) in non-alphabetical row order: top_categories returned [{'category': 'Zoo', ...}, {'category': 'Apples', ...}], i.e. NOT alphabetically ordered, directly contradicting the docstring. Grep confirms no other secondary sort key exists in the function.*
