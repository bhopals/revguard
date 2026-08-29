# Code review: Cache monthly summaries

> monthly_summary is the hottest query in the dashboard, so cache its result per (user, month). Includes a test showing the cache returns consistent results.

**Verdict: request changes.** 3 blocking finding(s), 2 critical.

## 1. [CRITICAL] Cache never invalidated on expense writes, returns stale totals

`ledgerly/reports.py:32` — correctness

monthly_summary caches its result keyed only on (user_id, month) and is never invalidated by add_expense or delete_expense in ledgerly/expenses.py, which have no awareness of _summary_cache. If a dashboard session calls monthly_summary(db, user, '2026-05') and the user then adds or deletes an expense for that same month, a subsequent call within the same process returns the old cached dict instead of the updated totals. Since budget_status (reports.py:52) also calls monthly_summary, this stale data silently propagates into budget remaining/over_budget calculations, giving users incorrect spend figures for the rest of the process lifetime for that (user, month) key. This directly contradicts the intent of a 'hot query' cache feeding a live dashboard.

*Verified: Read ledgerly/reports.py and expenses.py: _summary_cache (module-level dict) is populated in monthly_summary and never touched by add_expense/delete_expense in expenses.py (grep confirms no reference to _summary_cache outside reports.py). Reproduced live: after caching {'food': 100} for (user, '2026-05'), adding another $5 food expense in that month and re-calling monthly_summary still returned stale {'food': 100} instead of {'food': 600}. Also reproduced the downstream effect on budget_status: after deleting the only expense in a budgeted month, budget_status still reported spent=$3.50/over_budget=True instead of reflecting the deletion.*

## 2. [CRITICAL] Process-global cache keyed only by user_id leaks data across database instances/tenants

`ledgerly/reports.py:22` — security

`_summary_cache` is a module-level dict keyed only by `(user_id, month)` (reports.py:31-33), with no reference to the `db` argument. Every other query in the codebase (expenses.py, auth.py) scopes strictly by both the specific `db` connection and `user_id`, since `Database()` is per-tenant/per-session and uses SQLite AUTOINCREMENT ids that restart at 1 for each new instance (confirmed by the `db`/`user` fixtures in tests/test_ledgerly.py, which create a fresh `Database()` and register 'alice' as id 1 in every test). Because the cache ignores which `db` object made the call, two different Database instances (e.g. two different tenants, or a test suite reusing ids) whose users happen to share the same integer `user_id` will read each other's cached monthly summaries: calling `monthly_summary(db1, 1, '2026-05')` populates the cache for key `(1, '2026-05')`, and a subsequent unrelated `monthly_summary(db2, 1, '2026-05')` for a completely different user/database returns db1's cached financial totals instead of querying db2. This is a cross-tenant authorization/data-isolation failure introduced by the PR: the cache silently bypasses the per-connection scoping that the rest of the application relies on for correctness and privacy.

*Verified: Read ledgerly/reports.py: _summary_cache is a module-level dict keyed solely by (user_id, month), with no reference to db. Read ledgerly/db.py: Database() defaults to sqlite3.connect(':memory:'), so each instance is an independent in-memory DB with AUTOINCREMENT ids restarting at 1; confirmed via tests/test_ledgerly.py fixtures that create a fresh Database() and register 'alice' as id 1 each time.*

## 3. [MAJOR] Cache test has no write between reads, so it can't catch staleness

`tests/test_ledgerly.py:109` — test-adequacy

test_summary_cache_consistent adds an expense once, then calls monthly_summary(db, user, "2026-05") twice with no mutation between the two calls. This assertion (first == second) would pass identically even if _summary_cache did not exist at all, since the underlying DB rows haven't changed between the calls. The test name and PR description ('the cache returns consistent results') imply the cache is being exercised, but the one behavior a cache actually changes — returning a stale value after the underlying data changes — is never exercised. A test that added a second expense (or called reports.monthly_summary again after another expenses.add_expense) between the two reads would expose that the new cache has no invalidation and silently serves stale totals to the dashboard, which is exactly the kind of regression this feature risks.

*Verified: Read tests/test_ledgerly.py:109-113: test_summary_cache_consistent adds one expense then calls monthly_summary twice with no mutation in between. Ran python3 -c reproduction showing the real bug: after add_expense(700) -> monthly_summary() -> add_expense(300) -> monthly_summary(), the second call still returns {'transport': 700}, proving _summary_cache in ledgerly/reports.py has no invalidation and silently serves stale totals. Then swapped in a version of reports.py with the cache code fully stripped out (dict/lookup/store removed, function behaves exactly as pre-PR) and ran test_summary_cache_consistent against it: it still passes (1 passed).*
