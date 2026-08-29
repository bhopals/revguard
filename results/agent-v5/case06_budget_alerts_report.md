# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] Integer division computes wrong percentage, alert never fires below 100% of budget

`ledgerly/reports.py:73` — correctness

`pct = spent // b["limit_cents"] * 100` performs integer division before multiplying by 100, instead of `spent * 100 // b["limit_cents"]`. For any spend strictly less than the limit (e.g. spent=9000 cents, limit=10000 cents, i.e. 90% spent), `spent // limit_cents` truncates to 0, so `pct` is 0 regardless of the actual percentage. This means the function never flags a category until spend equals or exceeds the full limit (100%+), completely defeating the PR's stated purpose of warning users at 80% before they go over budget. Additionally, once spend exceeds the limit, the reported `percent` value is wrong/coarse: e.g. spent=25000, limit=10000 gives `25000 // 10000 * 100 = 200`, which happens to be correct here, but spent=19999, limit=10000 gives `1 * 100 = 100` even though actual spend is 199.99% β€” the percent shown to the UI is misleading and inconsistent with the real ratio.

*Verified: Read ledgerly/reports.py:73, confirming `pct = spent // b["limit_cents"] * 100`. Reproduced numerically: spent=9000/limit=10000 (90%) yields pct=0; spent=19999/limit=10000 (199.99%) yields pct=100. Also ran budget_alerts() end-to-end with a fake db where spend is 90% of the limit (9000/10000 cents) and it returned an empty list instead of an alert, proving the described defeat of the PR's 80% threshold purpose. This is a genuine logic bug in new production code, not a test-coverage nitpick, so it passes the policy gate as a real defect.*
