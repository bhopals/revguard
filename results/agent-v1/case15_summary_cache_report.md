# Code review: Cache monthly summaries

> monthly_summary is the hottest query in the dashboard, so cache its result per (user, month). Includes a test showing the cache returns consistent results.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Cache never invalidated on expense mutations, returns stale totals

`ledgerly/reports.py:32` — correctness

`monthly_summary` caches results in the module-level `_summary_cache` dict keyed by (user_id, month), but `add_expense`, `delete_expense` (ledgerly/expenses.py) and `set_budget` never invalidate or update this cache. Once a user's monthly summary has been computed for a given month, any subsequent expense added, edited, or deleted in that same month will be invisible: `monthly_summary` (and therefore `budget_status`, which calls it at reports.py:52) keeps returning the old totals for the lifetime of the process. E.g. a user adds a $10 food expense in March, views the dashboard (cache populated), then adds a $50 food expense in March and reloads the dashboard — the summary still shows only $10 of food spend, and `budget_status` will under-report spend and can wrongly report 'not over budget' when the user actually is.

## 2. [MAJOR] Cache key omits database identity, causing cross-database data leakage

`ledgerly/reports.py:22` — correctness

`_summary_cache` is a process-global dict keyed only by `(user_id, month)`, not by which `Database`/connection the data came from. Since user ids are autoincrement integers starting at 1 per database (ledgerly/db.py), two different `Database` instances (e.g. separate test runs, separate in-memory DBs, or any multi-tenant/multi-connection deployment) will collide on the same key. A summary computed for user 1 in one database will be silently returned for user 1 in a completely different database that happens to share the same (user_id, month) key, leaking one tenant's/session's financial data into another's view. This is demonstrable in the test suite itself: TestReports::test_monthly_summary and test_budget_status both use a fresh in-memory db with user id 1 and month '2026-03'; the second test's call to budget_status (via monthly_summary) actually reads the cached result left behind by the first test's db rather than recomputing from its own db, and only passes because the two computed totals coincidentally match ($3.50 in both cases).
