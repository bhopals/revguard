# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Floating-point multiplication causes off-by-one-cent errors for common amounts

`ledgerly/utils.py:20` — correctness

parse_money now computes cents as int(float(text) * 100). Because decimal fractions like 19.99, 3.35, 8.29, etc. cannot be represented exactly in binary floating point, dollars*100 often lands just below the intended integer (e.g. 19.99*100 == 1998.9999999999998, 3.35*100 == 334.99999999999994). int() truncates toward zero rather than rounding, so parse_money('19.99') returns 1998 cents instead of 1999. Since db.py explicitly stores amounts as integer cents 'to avoid floating point drift' (ledgerly/db.py:3), this reintroduces exactly the drift the schema was designed to prevent, silently under-recording real user-entered expense/budget amounts by a cent. The PR's test additions (12.50, 12, 0.5) all happen to be exact in binary float, so this regression is untested.

*Verified: Ran python3 against post-PR ledgerly/utils.py: parse_money('19.99') returns 1998 (should be 1999), parse_money('8.29') returns 828 (should be 829), due to int(float(text)*100) truncating values like 19.99*100==1998.9999999999998 and 8.29*100==828.9999999999999 toward zero instead of rounding. Confirmed db.py:3 states amounts are stored as integer cents 'to avoid floating point drift', so this reintroduces the exact bug the schema design intended to prevent. The PR's own test additions (12.50, 12, 0.5) are all exact in binary float and don't catch this, matching the claim.*

## 2. [MAJOR] Garbage-input test weakened to hide new parser's failure to reject negative amounts

`tests/test_ledgerly.py:28` — test-adequacy

The old test_parse_money_rejects_garbage list included "-5", asserting that parse_money raises ValueError for negative input (matching the old docstring 'Raises ValueError on malformed input or negative/zero amounts'). The PR removes "-5" from the list. With the new float()-based implementation, parse_money("-5") succeeds and returns -500 (float("-5") == -5.0, int(-5.0*100) == -500) instead of raising, a real behavioral regression versus the old parser and versus what callers (e.g. expenses.add_expense) likely assume about positive amounts. By dropping this case instead of updating it to assert the new (broken) behavior or keep the old contract, the test can no longer catch this regression.

*Verified: Ran `parse_money("-5")` against the post-PR code: it returns -500 instead of raising ValueError, confirming the new float()-based implementation no longer rejects negative amounts (the old docstring explicitly promised 'negative/zero amounts' raise ValueError, and the old regex-based parser enforced total<=0 check). The diff shows tests/test_ledgerly.py:28 removed "-5" from the rejects_garbage list rather than updating it to assert the new (broken) behavior, so pytest now passes despite the regression. Verified test currently passes with `pytest -k rejects_garbage`.*
