# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Float multiplication + truncation produces wrong cent totals for common prices

`ledgerly/utils.py:20` — correctness

parse_money now computes cents as int(float(text) * 100). Many common two-decimal amounts are not exactly representable in binary floating point, and the multiplication can land just below the intended integer (e.g. float('19.99') * 100 evaluates to 1998.9999999999998 in Python, not 1999.0). Since int() truncates toward zero rather than rounding, parse_money('19.99') returns 1998 cents instead of 1999 — the stored amount is silently off by one cent. This is a classic float-money pitfall that the previous regex/integer-based parser avoided entirely by parsing digits directly. The PR description's claim of 'same behavior for normal inputs' is false for exactly this class of everyday input (X.99 style prices), and no existing test (12.50, 0.5, 12) exercises a value that exposes the truncation, so CI passes despite the bug.

*Verified: Ran `parse_money('19.99')` from ledgerly/utils.py directly: it returned 1998 instead of 1999, because `float('19.99') * 100 == 1998.9999999999998` and `int()` truncates. Verified the bug is systemic, not a one-off: '9.99'->999 (should be 999, correct by luck), but '19.99'->1998 (wrong), '29.99'->2999 (correct), '1.99'->199 (correct), '0.29'->28 (wrong, should be 29). So the failure is silent and data-dependent, matching the finding's description exactly at ledgerly/utils.py:20 (`return int(dollars * 100)`). The old regex-based parser (removed in this diff) avoided this entirely by parsing digit strings directly. No rounding (e.g. round()) is used anywhere on this path.*

## 2. [MAJOR] Negative and zero amounts silently accepted, dropping a previously documented guarantee

`ledgerly/utils.py:15` — correctness

The old implementation explicitly rejected non-positive totals (`if total <= 0: raise ValueError("amount must be positive")`) and the old docstring promised this. The new implementation removes that check entirely: parse_money("-5") now returns -500 and parse_money("0") returns 0 instead of raising. The function docstring was quietly downgraded to "Raises ValueError on malformed input" without any note that the positive-amount guarantee was dropped. Callers that rely on parse_money to enforce a valid, positive expense amount (mirroring the `limit_cents <= 0` check that reports.set_budget still performs) can now receive negative or zero amounts to store as expenses, with no validation error to catch the mistake.

*Verified: Ran `parse_money('-5')` and `parse_money('0')` directly against the post-PR code: they return -500 and 0 respectively instead of raising ValueError. Diff confirms the `if total <= 0: raise ValueError(...)` check was deleted, the docstring was changed from 'malformed input or negative/zero amounts' to just 'malformed input', and the test case `-5` was removed from `test_parse_money_rejects_garbage`. Grepped the codebase for other validation on parse_money's output and found none — reports.py has its own separate `limit_cents <= 0` check unrelated to parse_money's return value.*

## 3. [MAJOR] Regression tests for negative and multi-decimal amounts removed instead of updated

`tests/test_ledgerly.py:28` — test-adequacy

The PR removes "-5" and "12.345" from `test_parse_money_rejects_garbage` rather than asserting the new (changed) behavior for them. This means the test suite no longer exercises the case where the new float()-based parser silently accepts a negative amount ("-5" -> -500 cents) or truncates excess decimal precision ("12.345" -> 1234 cents, silently dropping a half-cent). Simply deleting the cases hides a real behavior change from CI and future reviewers instead of documenting/guarding it, defeating the purpose of the regression test.

*Verified: Ran python3 -c to call parse_money('-5') and parse_money('12.345') against the post-PR ledgerly/utils.py: they return -500 and 1234 respectively instead of raising ValueError, confirming silent acceptance of negative amounts and silent truncation of sub-cent precision. Read tests/test_ledgerly.py lines 20-30 and confirmed test_parse_money_rejects_garbage was narrowed from 5 cases to 3, dropping '-5' and '12.345' entirely rather than asserting new behavior. Ran full test suite (16 passed) confirming no other test exercises these cases, so the behavior change is unguarded by CI.*
