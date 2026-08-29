# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Integer division order truncates percentage, defeating the 80% early-warning purpose

`ledgerly/reports.py:73` — correctness

`pct = spent // b["limit_cents"] * 100` performs integer division before multiplying by 100, so `pct` can only ever be 0, 100, 200, ... (a multiple of 100) for any spend strictly between multiples of the limit. E.g. limit_cents=10000, spent=9500 (95% of budget) gives spent // limit_cents == 0, so pct == 0, and the category is never flagged even though it's well past the 80% threshold. The function only starts alerting once spend reaches or exceeds 100% of the budget (spent >= limit_cents), which contradicts both the docstring ('reached threshold_pct of their budget') and the PR's stated goal of warning users 'before they go over.' The correct computation is `(spent * 100) // b["limit_cents"]` (multiply before dividing) to get an accurate percentage.

*Verified: Read ledgerly/reports.py line 73: `pct = spent // b["limit_cents"] * 100`. Ran budget_alerts with a fake db returning spent=9500, limit_cents=10000 (95% of budget): result was `[]`, i.e., no alert despite being well past the 80% threshold. Verified `(spent*100)//limit_cents` gives the correct 95%, confirming integer-division-before-multiply truncates pct to multiples of 100 and the function only ever fires once spend >= limit_cents (100%+), defeating the early-warning purpose described in the docstring and PR title.*

## 2. [MAJOR] No test coverage added for budget_alerts()

`tests/test_ledgerly.py:1` — test-adequacy

The PR introduces a new public function `budget_alerts` with threshold logic and a default constant, but the test suite (tests/test_ledgerly.py) contains no tests referencing `budget_alerts` or `ALERT_THRESHOLD_PCT` at all. This is why the critical percent-calculation bug (floor division before scaling) shipped undetected — a single test asserting an alert fires at, say, 85% spend against a budget would have caught it immediately.

*Verified: Grepped tests/test_ledgerly.py for 'budget_alerts' and 'ALERT_THRESHOLD_PCT' — zero matches. Ran the full test suite (pytest): 16 passed, none exercising the new function. Verified the underlying bug is real: `spent // limit * 100` with spent=8500, limit=10000 (85% spend) yields pct=0 due to integer floor division happening before scaling, versus correct 85.0 — exactly the class of bug a single alert-threshold test would catch. The finding accurately describes a genuine, reachable test-coverage gap tied to a real logic defect.*
