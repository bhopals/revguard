# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/baseline-r2/case15_summary_cache.jsonl`

**Session init** — model `claude-sonnet-5`, tools: none

**Assistant:**

{"findings": [{"file": "ledgerly/reports.py", "line": 33, "category": "correctness", "title": "Cache never invalidated, returns stale data", "description": "monthly_summary now returns whatever was cached for (user_id, month) forever. If an expense is added, edited, or deleted for that month after the first call, the cached totals are stale and the dashboard will show incorrect numbers for the rest of the process lifetime. There is no invalidation hook in add_expense/set_budget or anywhere else, so this is a real correctness regression, not just a performance optimization.", "severity": "critical"}, {"file": "ledgerly/reports.py", "line": 31, "category": "correctness", "title": "Cache key omits db instance", "description": "The cache key is (user_id, month) only, not including the db connection/instance. Any two different database instances (e.g. separate test fixtures, separate SQLite files, or a prod db vs a per-request db handle) sharing the same user_id and month will incorrectly return each other's cached results. Since _summary_cache is a module-level global, this also leaks state across test runs sharing a user id/month, causing test order-dependent flakiness and, in a multi
… [1304 chars truncated]

---
**Final result** (1 turns, 27.7s, $0.042):

{"findings": [{"file": "ledgerly/reports.py", "line": 33, "category": "correctness", "title": "Cache never invalidated, returns stale data", "description": "monthly_summary now returns whatever was cached for (user_id, month) forever. If an expense is added, edited, or deleted for that month after the first call, the cached totals are stale and the dashboard will show incorrect numbers for the rest of the process lifetime. There is no invalidation hook in add_expense/set_budget or anywhere else, so this is a real correctness regression, not just a performance optimization.", "severity": "critical"}, {"file": "ledgerly/reports.py", "line": 31, "category": "correctness", "title": "Cache key omits db instance", "description": "The cache key is (user_id, month) only, not including the db connection/instance. Any two different database instances (e.g. separate test fixtures, separate SQLite files, or a prod db vs a per-request db handle) sharing the same user_id and month will incorrectly return each other's cached results. Since _summary_cache is a module-level global, this also leaks state across test runs sharing a user id/month, causing test order-dependent flakiness and, in a multi
… [1304 chars truncated]
