# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case15_summary_cache/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case15_summary_cache/ledgerly/reports.py"}
```

**Tool result:**

```
1	"""Monthly summaries and budget tracking."""
2	
3	from .utils import format_money
4	
5	
6	class BudgetError(Exception):
7	    pass
8	
9	
10	def set_budget(db, user_id, category, month, limit_cents):
11	    if limit_cents <= 0:
12	        raise BudgetError("budget limit must be positive")
13	    db.execute(
14	        "INSERT INTO budgets (user_id, category, month, limit_cents)"
15	        " VALUES (?, ?, ?, ?)"
16	        " ON CONFLICT (user_id, category, month)"
17	        " DO UPDATE SET limit_cents = excluded.limit_cents",
18	        (user_id, category, month, limit_cents),
19	    )
20	
21	
22	_summary_cache = {}
23	
24	
25	def monthly_summary(db, user_id, month):
26	    """Total spend per category for a 'YYYY-MM' month.
27	
28	    Results are cached per (user, month): the dashboard c
… [1510 chars truncated]
```

**Tool call → Grep**

```json
{"pattern": "monthly_summary", "output_mode": "content", "-n": true}
```

**Tool result:**

```
ledgerly/reports.py:25:def monthly_summary(db, user_id, month):
ledgerly/reports.py:52:    spend = monthly_summary(db, user_id, month)
tests/test_ledgerly.py:90:    def test_monthly_summary(self, db, user):
tests/test_ledgerly.py:94:        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}
tests/test_ledgerly.py:111:        first = reports.monthly_summary(db, user, "2026-05")
tests/test_ledgerly.py:112:        second = reports.monthly_summary(db, user, "2026-05")
.pytest_cache/v/cache/nodeids:13:  "tests/test_ledgerly.py::TestReports::test_monthly_summary",
```

**Tool call → Grep**

```json
{"pattern": "def add_expense|_summary_cache", "output_mode": "content", "-n": true, "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case15_summary_cache/ledgerly"}
```

**Tool result:**

```
ledgerly/reports.py:22:_summary_cache = {}
ledgerly/reports.py:32:    if key in _summary_cache:
ledgerly/reports.py:33:        return _summary_cache[key]
ledgerly/reports.py:42:    _summary_cache[key] = totals
ledgerly/expenses.py:18:def add_expense(db, user_id, amount_cents, category, spent_on, note=""):
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case15_summary_cache/tests/test_ledgerly.py"}
```

**Tool result:**

```
1	import pytest
2	
3	from ledgerly.db import Database
4	from ledgerly import auth, expenses, reports
5	from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date
6	
7	
8	@pytest.fixture()
9	def db():
10	    d = Database()
11	    yield d
12	    d.close()
13	
14	
15	@pytest.fixture()
16	def user(db):
17	    return auth.register(db, "alice", "s3cretpass")
18	
19	
20	class TestUtils:
21	    def test_parse_money(self):
22	        assert parse_money("12.50") == 1250
23	        assert parse_money("$12.50") == 1250
24	        assert parse_money("12") == 1200
25	        assert parse_money("0.5") == 50
26	
27	    def test_parse_money_rejects_garbage(self):
28	        for bad in ["", "abc", "-5", "12.345", "1,000"]:
29	            with pytest.raises(ValueError):
30	               
… [3669 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "severity": "critical", "title": "Cache never invalidated on writes, causing stale monthly summaries and budget status", "description": "`_summary_cache` (line 22) is populated on first call and never cleared or updated by `set_budget`, `add_expense`, or `delete_expense` (checked in ledgerly/expenses.py — none of them touch `_summary_cache`). Once `monthly_summary(db, user_id, month)` is called for a given (user_id, month), any subsequent expense added, edited, or deleted for that same month is invisible: the function keeps returning the old totals for the lifetime of the process. Since `budget_status` (line 52) calls `monthly_summary` internally, this also makes `over_budget`/`remaining` calculations silently wrong after any edit — e.g. a user adds an expense that pushes them over budget, but the dashboard (which the PR description says calls this 'on every page load') keeps reporting them under budget because it hits the stale cache entry."}, {"file": "ledgerly/reports.py", "line": 31, "category": "correctness", "severity": "critical", "title": "Cache key omits db instance, leaking results across
… [1115 chars truncated]

---
**Final result** (5 turns, 46.2s, $0.077):

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "severity": "critical", "title": "Cache never invalidated on writes, causing stale monthly summaries and budget status", "description": "`_summary_cache` (line 22) is populated on first call and never cleared or updated by `set_budget`, `add_expense`, or `delete_expense` (checked in ledgerly/expenses.py — none of them touch `_summary_cache`). Once `monthly_summary(db, user_id, month)` is called for a given (user_id, month), any subsequent expense added, edited, or deleted for that same month is invisible: the function keeps returning the old totals for the lifetime of the process. Since `budget_status` (line 52) calls `monthly_summary` internally, this also makes `over_budget`/`remaining` calculations silently wrong after any edit — e.g. a user adds an expense that pushes them over budget, but the dashboard (which the PR description says calls this 'on every page load') keeps reporting them under budget because it hits the stale cache entry."}, {"file": "ledgerly/reports.py", "line": 31, "category": "correctness", "severity": "critical", "title": "Cache key omits db instance, leaking results across
… [1115 chars truncated]
