# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Integer division performed before multiplication, breaking threshold detection

`ledgerly/reports.py:73` — correctness

`pct = spent // b["limit_cents"] * 100` computes the floor division first, so pct is 0 for any spend strictly less than the limit (e.g. spent=90, limit_cents=100 gives 90//100=0, then 0*100=0), and jumps straight to 100 once spend reaches the limit, then 200 at 2x the limit, etc. This means the function can never detect the intended 'reached 80% of budget' warning case at all — it only ever fires once a category is already fully at or over 100% of its budget (in multiples of 100%), which defeats the entire purpose of an early warning described in the PR ('so the UI can warn users before they go over'). The correct computation is `spent * 100 // b['limit_cents']` (or float division) to get the true percentage.

## 2. [MAJOR] New budget_alerts() has zero test coverage, missing a test that would have caught its broken percentage math

`ledgerly/reports.py:62` — test-adequacy

The PR adds a new public function budget_alerts() but the test suite (tests/test_ledgerly.py) contains no test for it at all. This is risky new behavior: line 73 computes `pct = spent // b["limit_cents"] * 100`, which does integer division before multiplying, so any spend strictly less than the full limit (e.g. spent=90, limit_cents=100) yields pct=0 regardless of how close to the threshold it is — the alert can never fire for partial overspend, defeating the feature's purpose of warning users before they go over budget. A single test exercising a category at, say, 85% of its budget and asserting it appears in the returned alerts would have failed against this implementation and caught the bug before merge.
