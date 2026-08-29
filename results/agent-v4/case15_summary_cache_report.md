# Code review: Cache monthly summaries

> monthly_summary is the hottest query in the dashboard, so cache its result per (user, month). Includes a test showing the cache returns consistent results.

**Verdict: request changes.** 6 blocking finding(s), 2 critical.

## 1. [CRITICAL] Cache never invalidated on expense/budget writes, returns stale totals

`ledgerly/reports.py:32` — correctness

monthly_summary caches results in a module-level dict keyed by (user_id, month) with no invalidation hook. add_expense, delete_expense, and set_budget never touch _summary_cache. Once a (user_id, month) pair has been queried, every subsequent call — including from budget_status (line 52), which depends on monthly_summary for spend totals — returns the first-ever result for that key, ignoring any expenses added or deleted afterward in that month. E.g.: call monthly_summary(db, user, '2026-03') with no expenses -> caches {}; then add_expense(db, user, 500, 'food', '2026-03-05'); budget_status(db, user, '2026-03') will report spent=$0.00 and over_budget=False even though $5.00 was actually spent, silently breaking the budget-overrun alert the PR's own docstring on budget_status still promises.

*Verified: Read ledgerly/reports.py: _summary_cache is a module-level dict populated by monthly_summary and never cleared or updated by add_expense/delete_expense/set_budget in expenses.py or reports.py (confirmed via grep -rn '_summary_cache' across ledgerly/, only hits are the cache's own definition/read/write in reports.py). Reproduced live: calling monthly_summary(db, user, '2026-03') with no expenses caches {}; then set_budget(..., 300) and add_expense(..., 500, 'food', '2026-03-05'); a subsequent monthly_summary call still returns {} and budget_status returns spent='$0.00', over_budget=False despite the $5.00 expense exceeding the $3.00 budget — exactly as described.*

## 2. [CRITICAL] Cache key not scoped to db instance, causing cross-database data leakage

`ledgerly/reports.py:22` — correctness

_summary_cache is a single process-wide dict keyed only by (user_id, month), with no reference to which Database/connection produced the cached rows. user_id is an autoincrement integer that restarts at 1 for every new Database() instance (see ledgerly/db.py SCHEMA, id INTEGER PRIMARY KEY AUTOINCREMENT). Any two distinct Database instances (e.g. two tenants' SQLite files, or two test/service instances in the same process) that happen to assign the same user_id will collide on the cache key and one instance's monthly_summary results leak into the other's. Concretely: Database A registers user 'alice' (id=1), calls monthly_summary(dbA, 1, '2026-03') -> caches {'food': 350}. Database B (different db, e.g. different tenant or a later request cycle) registers its own user 'bob' as id=1 and calls monthly_summary(dbB, 1, '2026-03'); the cache hit returns dbA's alice totals instead of querying dbB, so bob sees another tenant's spending data.

*Verified: Read ledgerly/db.py (confirms user_id is AUTOINCREMENT INTEGER PRIMARY KEY, restarting at 1 per new Database/sqlite file) and ledgerly/reports.py (confirms _summary_cache is a bare module-level dict keyed only by (user_id, month), with no db/connection identity in the key). Reproduced the exact scenario in the finding with a live script: created dbA, registered 'alice' (id=1), added a $350 food expense, called monthly_summary(dbA, 1, '2026-03') -> {'food': 35000}. Created a second independent Database() dbB, registered 'bob' (also id=1, since AUTOINCREMENT restarts per DB), added a $1 transport expense, called monthly_summary(dbB, 1, '2026-03').*

## 3. [MAJOR] Cached summary is never invalidated after expense deletion, exposing deleted financial data

`ledgerly/reports.py:42` — security

expenses.delete_expense() verifies ownership and removes a row from `expenses`, but `monthly_summary`'s cache at line 42 is never invalidated by any write path (add_expense, delete_expense). Once a user views their dashboard for a given month (populating `_summary_cache[(user_id, month)]`), deleting an expense for that month no longer changes what `monthly_summary`/`budget_status` report for the remainder of the process's lifetime: the deleted transaction's amount keeps being included in category totals and budget 'spent'/'remaining' figures served back to the user. A user who deletes an expense specifically to remove sensitive or erroneous financial data from view will continue to see (and have exposed via budget_status) totals that reflect the deleted record, which is a meaningful data-exposure regression introduced by this PR since no caching existed before.

*Verified: Read ledgerly/reports.py and ledgerly/expenses.py: _summary_cache is a module-level dict populated in monthly_summary and never cleared anywhere; expenses.py (add_expense/delete_expense) doesn't import or reference reports/_summary_cache at all, and grep confirms no other invalidation site exists. Reproduced live: added an expense, called reports.monthly_summary (caches {'food': 1500}), deleted the expense via expenses.delete_expense (row removed from DB), then called reports.monthly_summary again — it still returned {'food': 1500}, i.e. the deleted expense's amount continues to appear in totals/budget_status for the rest of the process lifetime. This matches the finding exactly.*

## 4. [MAJOR] New cache test cannot detect a caching bug

`tests/test_ledgerly.py:109` — test-adequacy

test_summary_cache_consistent (lines 109-113) only asserts that two consecutive calls to monthly_summary return equal dicts. Since the underlying data doesn't change between the two calls, the un-cached code path (a plain SQL query) would return the exact same dict on both calls too — the test passes identically whether or not the new _summary_cache logic in reports.py is present or working at all. It never verifies the actual behavior the PR introduces (e.g. that a second call skips the DB query, or that the cache is returning a stored value rather than re-querying), so it cannot fail if the caching implementation is broken, e.g. if the cache key were wrong or the cache silently no-op'd.

*Verified: Read reports.py and test_ledgerly.py to confirm the test as described (lines 109-113: adds one expense, calls monthly_summary twice, asserts equality). Ran the test with the original code: passes. Then edited reports.py to strip out the entire _summary_cache logic (reverting monthly_summary to the plain uncached SQL query on every call, i.e. simulating a completely broken/no-op cache), and reran test_summary_cache_consistent — it still PASSED, because the DB data is unchanged between the two calls so the query returns the same dict regardless of caching. This directly proves the test cannot detect a totally absent or broken cache.*

## 5. [MAJOR] No test covers cache staleness, the main risk introduced by this PR

`tests/test_ledgerly.py:113` — test-adequacy

The PR adds an unbounded, never-invalidated module-level cache (_summary_cache in reports.py) keyed by (user_id, month). The obvious risk of this design is that monthly_summary will keep returning stale results after new expenses are added for an already-cached (user, month) pair. No test exercises this: calling monthly_summary, then adding another expense for the same user/month, then calling monthly_summary again to check whether the new expense is (incorrectly) reflected or (per current implementation) silently dropped. Such a test would have caught that the cache returns outdated totals indefinitely within a process lifetime, which is the central behavioral change this PR makes.

*Verified: Read reports.py: _summary_cache is a module-level dict keyed by (user_id, month), populated in monthly_summary and never invalidated or cleared anywhere in the codebase (grep for _summary_cache shows only definition/read/write sites in reports.py; expenses.add_expense and other mutators have no cache-clearing logic). Reproduced with a live script: added an expense, called monthly_summary (got {'food':100}), added another expense for the same user/month, called monthly_summary again and got the identical stale {'food':100} instead of the updated total — confirming indefinite staleness within the process lifetime.*

## 6. [MINOR] Docstring claims a caching guarantee the code does not implement

`ledgerly/reports.py:28` — correctness

The docstring says results are cached because "the numbers rarely change within a session," implying the cache is scoped to some session and expires with it. There is no session concept anywhere in this codebase (no session object, no per-request/per-login scope, no TTL) — the cache is a bare process-global dict that lives forever and is shared across all users, requests, and even independent `Database` instances (see the cross-instance leak above). The comment misleads future maintainers into thinking staleness is bounded when it is not.

*Verified: Read ledgerly/reports.py: `_summary_cache = {}` is a bare module-level dict with no TTL/expiry and no session hook. Grepped the whole repo for session/ttl/expire/_cache and found the only session/TTL concept (auth.py's token TTL) is completely unrelated to `_summary_cache` — nothing clears or scopes the cache to a session, request, or Database instance.*
