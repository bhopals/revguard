# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] parse_money no longer rejects negative or zero amounts

`ledgerly/utils.py:20` — correctness

The old implementation raised ValueError when total <= 0 (docstring: 'Raises ValueError on malformed input or negative/zero amounts'). That check was deleted; the new docstring even drops the 'negative/zero' clause. Now parse_money("-5") returns -500 and parse_money("0") returns 0 without error (the test suite even removed "-5" from the rejection list, confirming this). Callers like ledgerly.expenses.add_expense() take amount_cents as-is and insert it directly into the DB with no re-validation, so a user-supplied negative or zero amount is silently persisted, corrupting SUM(amount_cents) totals in ledgerly/reports.py. This is a guarantee the old code enforced that is now silently dropped.

## 2. [?] Negative-amount rejection test silently deleted instead of updated

`tests/test_ledgerly.py:28` — test-adequacy

The old test asserted parse_money('-5') raises ValueError (enforcing 'amount must be positive'). The PR removes '-5' from the garbage list because the new float-based implementation no longer rejects negative amounts (parse_money('-5') now returns -500 instead of raising). The PR deletes the assertion rather than adding a test that documents/verifies this behavior change, so the regression (money parser now accepts negative amounts, e.g. an expense entry of '-5' would silently create a -$5.00 record) is invisible to the test suite.
