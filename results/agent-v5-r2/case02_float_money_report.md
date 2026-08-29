# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Float rounding produces wrong cent values for common amounts

`ledgerly/utils.py:20` — correctness

`int(dollars * 100)` truncates towards zero on a binary float, and many decimal cent values are not exactly representable in binary floating point. E.g. `parse_money("19.99")`: float("19.99") * 100 == 1998.9999999999998, so int() truncates to 1998 instead of 1999 — a one-cent-low result. Same failure for e.g. "0.29" -> 28 instead of 29, "12.34" -> 1233 instead of 1234. This corrupts stored amount_cents for a module whose entire premise (per its own module docstring) is 'Money is always integer cents internally.' The previous regex+integer implementation computed cents exactly and never had this problem. None of the new/kept tests (12.50, 0.5, 12) happen to trigger the FP error since those values are exactly representable, so the bug is undetected by the test suite but will silently corrupt real user-entered amounts like "19.99" or "4.99".

*Verified: Ran python3 against ledgerly/utils.py post-PR: parse_money("19.99") returns 1998 (should be 1999) and parse_money("0.29") returns 28 (should be 29), because float("19.99")*100 == 1998.9999999999998 and int() truncates. Confirmed the underlying float arithmetic directly. This silently corrupts stored amount_cents for common real-world inputs, contradicting the module's documented invariant that money is integer cents internally, and none of the existing/kept tests (12.50, 0.5, 12) happen to trigger it since those are exactly representable in binary float.*

## 2. [MAJOR] parse_money now silently accepts negative and zero amounts, dropping a previously-enforced invariant

`ledgerly/utils.py:15` — correctness

The old implementation explicitly rejected non-positive totals ('amount must be positive'), and this was documented in the docstring. The new implementation removes that check entirely (and the docstring was edited to drop the mention of negative/zero rejection), so `parse_money("-5")` now returns -500 and `parse_money("0")` returns 0 instead of raising. Since parse_money is the boundary validator for user-entered amounts before they reach amount_cents storage (expenses.add_expense takes amount_cents directly and performs no positivity check itself), a negative or zero amount can now flow into the expenses table, silently corrupting SUM(amount_cents) aggregates in reports.monthly_summary and reports.budget_status (e.g. a negative expense would reduce a category's reported spend or even make 'over_budget' calculations misleading).

*Verified: Ran parse_money('-5') and parse_money('0') directly against post-PR ledgerly/utils.py: they return -500 and 0 respectively instead of raising ValueError, confirming the positivity check present in the old regex-based implementation (and its docstring guarantee) was dropped. Read ledgerly/expenses.py::add_expense and ledgerly/reports.py::monthly_summary/budget_status: add_expense inserts amount_cents with no positivity validation, and monthly_summary/budget_status use SUM(amount_cents) directly with no filtering, so a negative parsed amount flows straight into aggregate reports, corrupting spend totals and over_budget flags as described.*

## 3. [MAJOR] Rejection test weakened to hide broken validation for negative and over-precise amounts

`tests/test_ledgerly.py:28` — test-adequacy

The old test asserted parse_money("-5") and parse_money("12.345") raise ValueError; the PR removes both cases from the list, leaving only ["", "abc", "1,000"]. With the new float()-based implementation, parse_money("-5") returns -500 (a negative amount, previously explicitly rejected per the old docstring 'Raises ValueError on malformed input or negative/zero amounts') and parse_money("12.345") returns int(1234.5) = 1234 (silently truncating fractional cents) instead of raising. The test was edited to stop covering exactly the two behaviors that changed/broke, so it passes without verifying the parser's actual (regressed) behavior on these inputs.

*Verified: Ran `parse_money("-5")` -> -500 and `parse_money("12.345")` -> 1234 in the post-PR repo; neither raises ValueError, contradicting the still-present docstring intent (old version explicitly documented negative/zero rejection, and the old regex capped fractional digits at 2). The diff shows the test list `["", "abc", "-5", "12.345", "1,000"]` was trimmed to `["", "abc", "1,000"]`, removing exactly the two cases whose behavior broke, and `pytest tests/test_ledgerly.py` passes 16/16 without exercising either regressed path. This is a test edited to stop covering behavior that changed/broke in the same PR, not a mere missing-coverage complaint.*
