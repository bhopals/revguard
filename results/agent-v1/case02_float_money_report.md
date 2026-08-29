# Code review: Simplify money parsing

> Replaces the regex-based amount parser with a much simpler float() based implementation and updates the parser tests to match. Less code, same behavior for normal inputs.

**Verdict: request changes.** 1 blocking finding(s), 0 critical.

## 1. [?] Float rounding error silently produces wrong cent amounts

`ledgerly/utils.py:20` — correctness

parse_money now computes `int(dollars * 100)` using binary floats. Due to standard float imprecision, this truncates to the wrong integer for common inputs, e.g. parse_money("19.99") returns 1998 instead of 1999 because 19.99*100 == 1998.9999999999998 in Python floats, and int() truncates toward zero. Similarly parse_money("0.29") returns 28 instead of 29. This is exactly the class of bug integer-cents storage is meant to avoid, and it silently shortchanges users/records instead of raising. The regression is undetected because the test suite only checks amounts (12.50, 12, 0.5) whose float products happen to be exact.
