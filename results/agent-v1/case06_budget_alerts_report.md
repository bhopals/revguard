# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] Operator precedence bug makes threshold check ineffective until spend fully reaches/exceeds budget

`ledgerly/reports.py:73` — correctness

The percentage is computed as `spent // b["limit_cents"] * 100` — integer floor division happens BEFORE the multiplication by 100, so `pct` can only ever be 0, 100, 200, etc. For any spend strictly between 0% and 100% of the budget (e.g. spent=$85 of a $100 limit), `spent // limit_cents` evaluates to 0, giving `pct = 0`, so `0 > 80` is False and no alert fires. The alert only starts firing once spend reaches/exceeds 100% of the budget (pct becomes 100), which is exactly the case the feature was meant to warn about *before* it happens. This defeats the entire purpose of the PR ('flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over') — users will never be warned at 80%, only after they've already hit or exceeded their budget. The fix is to compute `pct = spent * 100 // b["limit_cents"]` (or use float division) so the multiplication happens before the floor division. There is also no test coverage for `budget_alerts` in tests/test_ledgerly.py, so this bug was not caught by CI.
