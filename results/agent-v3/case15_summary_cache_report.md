# Code review: Cache monthly summaries

> monthly_summary is the hottest query in the dashboard, so cache its result per (user, month). Includes a test showing the cache returns consistent results.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Cache never invalidated on writes, causing stale monthly summaries and budget status

`ledgerly/reports.py:32` — correctness

`_summary_cache` (line 22) is populated on first call and never cleared or updated by `set_budget`, `add_expense`, or `delete_expense` (checked in ledgerly/expenses.py — none of them touch `_summary_cache`). Once `monthly_summary(db, user_id, month)` is called for a given (user_id, month), any subsequent expense added, edited, or deleted for that same month is invisible: the function keeps returning the old totals for the lifetime of the process. Since `budget_status` (line 52) calls `monthly_summary` internally, this also makes `over_budget`/`remaining` calculations silently wrong after any edit — e.g. a user adds an expense that pushes them over budget, but the dashboard (which the PR description says calls this 'on every page load') keeps reporting them under budget because it hits the stale cache entry.

*Verified: Read reports.py: `_summary_cache` is a module-level dict, populated in monthly_summary and never cleared; grep across ledgerly/ shows no other reference to it (expenses.py's add_expense/delete_expense and reports.py's set_budget never touch it). Executed a reproduction: added a $7 transport expense, called monthly_summary (cached {transport:700}), added a second $50 expense, called monthly_summary*

## 2. [MAJOR] New cache test cannot detect stale-cache bugs

`tests/test_ledgerly.py:109` — test-adequacy

test_summary_cache_consistent only calls monthly_summary twice with no state change in between and asserts the two results are equal. This assertion would pass identically even if the caching code in reports.py did not exist at all, since re-querying unchanged data returns the same totals. The test never exercises the actual risky new behavior introduced by this PR: that the cache is never invalidated when expenses are added/edited/deleted after the first call. A test that adds an expense, calls monthly_summary once to populate the cache, adds another expense for the same user/month, and calls monthly_summary again would have caught the real bug (stale totals returned forever within a process) and would fail against the current implementation. As written, the test is a tautology with respect to the caching behavior it claims to verify.

*Verified: Read reports.py: _summary_cache has no invalidation anywhere in the codebase (grep confirms only set/get). Ran the test as written (test_summary_cache_consistent) — it passes, but by construction (no state change between the two monthly_summary calls) it would pass identically with no caching at all. Reproduced the reviewer's proposed stronger scenario via python -c: add expense -> call monthly_su*
