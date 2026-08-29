# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] Integer division truncates percentage before multiplying, breaking threshold detection

`ledgerly/reports.py:73` — correctness

`pct = spent // b["limit_cents"] * 100` performs integer floor division of spent by limit_cents *before* multiplying by 100, instead of `spent * 100 // limit_cents`. Since spent and limit_cents are both in cents, `spent // limit_cents` truncates to 0 for any spend strictly less than the full limit, so `pct` collapses to 0 whenever spend < 100% of budget, and jumps straight to 100 (or higher multiples of 100) once spend reaches or exceeds the limit. For example, spent=8000 cents against a limit of 10000 cents (80% spent, which should trigger the default 80% alert) yields `8000 // 10000 * 100 = 0`, so no alert fires. The function can never alert at the intended 80% threshold — it only ever reports categories that are already at or beyond 100% of budget, directly contradicting the PR's stated goal of warning users 'before they go over' and the docstring's promise to flag spend that has 'reached threshold_pct'.

*Verified: Read ledgerly/reports.py:73 confirming `pct = spent // b["limit_cents"] * 100`. Wrote a reproduction with a fake DB simulating spend at various levels against a 10000-cent budget and called budget_alerts(). Results: spent=8000 (80%) -> [] (no alert), spent=9999 (99.99%) -> [] (no alert), spent=10000 (100%) -> alert fires with pct=100. Confirms floor division truncates the ratio to 0 for any spend strictly below the limit, so the 80% threshold introduced by this PR can never trigger before spend reaches/exceeds 100%, directly contradicting the docstring and PR intent. Also verified `spent * 100 // limit` yields the correct 80 for the same inputs.*
