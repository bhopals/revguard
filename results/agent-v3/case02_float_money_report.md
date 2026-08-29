# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Float rounding causes wrong cent amounts

`ledgerly/utils.py:20` — correctness

int(dollars * 100) truncates a binary float rather than rounding a decimal value. Many common two-decimal amounts are not exactly representable in binary floating point and land just below the intended value, so truncation loses a cent. E.g. parse_money("0.29") -> float("0.29")*100 == 28.999999999999996 -> int(...) == 28 (should be 29 cents); parse_money("19.99") -> 19.99*100 == 1998.9999999999998 -> int(...) == 1998 (should be 1999 cents). Since this is a ledger app that stores amount_cents used for balances/reports, every such input silently records one cent less than the user entered, and the error is systematic (always rounds down) rather than random, so it accumulates. The old regex-based implementation parsed the integer and fractional digits directly and never touched floating point, so this is a regression introduced by the PR, not a pre-existing issue.

*Verified: Read ledgerly/utils.py:20, confirms `int(dollars * 100)` with no rounding. Executed the function directly: parse_money('0.29') returns 28 (should be 29) and parse_money('19.99') returns 1998 (should be 1999), reproducing the exact failure described. This is a genuine regression versus the old regex-based digit parsing which never touched floating point.*

## 2. [MAJOR] parse_money no longer rejects negative or zero amounts

`ledgerly/utils.py:15` — correctness

The old implementation explicitly rejected totals <= 0 (docstring: "Raises ValueError on malformed input or negative/zero amounts"), and the removed test asserted parse_money("-5") raised ValueError. The new implementation drops that check entirely and its docstring was edited to remove the guarantee: parse_money("-5") now returns -500, and parse_money("0") returns 0, both silently accepted instead of raising. Any caller that relied on parse_money to enforce a positive amount invariant (e.g. rejecting a $0 or negative expense entry at the input-validation boundary) will now let invalid data through unvalidated, since the contract stated in the function's own docstring was silently weakened.

*Verified: Ran parse_money('-5') and parse_money('0') directly against the post-PR ledgerly/utils.py; both returned -500 and 0 respectively instead of raising ValueError. Diff confirms the `if total <= 0: raise ValueError(...)` check was removed and the docstring was edited from 'malformed input or negative/zero amounts' to just 'malformed input', and the corresponding test case for '-5' was deleted from tes*

## 3. [MAJOR] Removed regression-catching assertions for negative and over-precision amounts

`tests/test_ledgerly.py:28` — test-adequacy

The old test_parse_money_rejects_garbage asserted that '-5' and '12.345' raise ValueError. The PR deletes these two cases from the list instead of keeping them, which is the only reason the test still passes: the new float()-based parse_money no longer rejects negative amounts (parse_money('-5') now returns -500 instead of raising) nor over-precision fractions (parse_money('12.345') now returns 1234 via truncation instead of raising, since int(12.345*100) truncates rather than validating 2-decimal precision). By quietly dropping these cases rather than updating them to reflect intentionally new behavior, the test suite loses its ability to catch this regression, and the docstring change ('Raises ValueError on malformed input.' with 'negative/zero amounts' wording removed) is not accompanied by any test asserting the new, weaker contract, so nothing in the suite documents or verifies what happens for negative/zero/high-precision inputs anymore.

*Verified: Ran parse_money('-5') and parse_money('12.345') against post-PR ledgerly/utils.py: they return -500 and 1234 respectively instead of raising ValueError, confirming the new float()-based implementation silently accepts negative and over-precision amounts. Ran the full test suite (pytest tests/test_ledgerly.py -v): all 16 tests pass, including test_parse_money_rejects_garbage, because the PR removed*
