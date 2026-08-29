# Code review: Budget alert threshold

> Adds budget_alerts() which flags every category whose spend has reached a configurable percentage of its monthly budget (default 80%), so the UI can warn users before they go over.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Integer division order truncates percentage to multiples of 100, defeating the 80% early-warning threshold

`ledgerly/reports.py:73` — correctness

`pct = spent // b["limit_cents"] * 100` performs integer floor division of spent by limit BEFORE multiplying by 100, instead of `spent * 100 // limit_cents`. For any spend strictly less than the limit (spent < limit_cents), `spent // limit_cents` is 0, so `pct` is always 0 regardless of how close spend is to the limit. E.g. spent=7900 cents, limit=10000 cents (79% actually spent) yields pct=0, not 79, so no alert fires even though the category is at 79% of budget. The function only ever produces pct values that are multiples of 100 (0, 100, 200, ...), meaning with the default threshold_pct=80 an alert can never fire until spend has reached or exceeded 100% of the budget (pct=100 or more) — the entire purpose of the feature, warning users before they go over budget, is defeated. Users will get zero alerts for spend at 80%, 90%, or even 99% of budget.

*Verified: Read ledgerly/reports.py:73, matches diff exactly: `pct = spent // b["limit_cents"] * 100`. Executed budget_alerts with a fake db: spent=7900/limit=10000 (79%) and spent=9900/limit=10000 (99%) both return `[]` (no alerts), confirming pct floors to 0 for any spend < limit. Correct formula `spent*100//limit_cents` gives 79 as expected. No other definition or safeguard for budget_alerts exists in the*

## 2. [MAJOR] No test added for new budget_alerts() function

`tests/test_ledgerly.py:94` — test-adequacy

The PR adds `budget_alerts()` in ledgerly/reports.py but the test suite (tests/test_ledgerly.py) contains no test exercising it at all — the only budget-related test is `test_monthly_summary` (line 90-94) and `budget_status` tests, neither of which call `budget_alerts`. This absence let a serious bug ship undetected: `pct = spent // b['limit_cents'] * 100` (reports.py:73) uses integer division before multiplying, so any spend below 100% of the limit truncates to 0 (e.g. spent=8000, limit_cents=10000 yields pct=0 instead of 80), meaning the function can never alert at the documented 80% default threshold for any realistic spend/limit ratio less than 100%. A single test with a category at, say, 80-99% of its budget would have caught this immediately by asserting the category appears in the returned alerts list, but no such test exists.

*Verified: Grepped tests/ and ledgerly/ for 'budget_alerts' — only the definition in reports.py matches; no test references it. Read tests/test_ledgerly.py:89-108 confirming TestReports only has test_monthly_summary, test_budget_status, test_budget_upsert, none of which call budget_alerts. Reproduced the cited bug directly: `8000 // 10000 * 100` evaluates to 0 in Python (integer division truncates before mul*
