# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case15_summary_cache/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case15_summary_cache/ledgerly/reports.py"}
```

**Tool call → Glob**

```json
{"pattern": "**/*.py"}
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

**Tool result:**

```
ledgerly/__init__.py
ledgerly/db.py
ledgerly/utils.py
ledgerly/auth.py
ledgerly/expenses.py
ledgerly/reports.py
tests/test_ledgerly.py
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case15_summary_cache/ledgerly/expenses.py"}
```

**Tool result:**

```
1	"""Expense CRUD and listing. Every operation is scoped to the owning user."""
2	
3	from .utils import parse_iso_date, utcnow_iso
4	
5	VALID_CATEGORIES = {
6	    "food", "transport", "housing", "utilities",
7	    "health", "entertainment", "other",
8	}
9	
10	MAX_NOTE_LEN = 500
11	PAGE_SIZE = 20
12	
13	
14	class ExpenseError(Exception):
15	    pass
16	
17	
18	def add_expense(db, user_id, amount_cents, category, spent_on, note=""):
19	    if category not in VALID_CATEGORIES:
20	        raise ExpenseError(f"unknown category: {category}")
21	    if len(note) > MAX_NOTE_LEN:
22	        raise ExpenseError("note too long")
23	    d = parse_iso_date(spent_on)
24	    return db.execute(
25	        "INSERT INTO expenses (user_id, amount_cents, category, note,"
26	        " spent_on, created_at) VALU
… [1245 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case15_summary_cache/tests/test_ledgerly.py"}
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case15_summary_cache/ledgerly/db.py"}
```

**Tool result:**

```
1	"""SQLite persistence layer.
2	
3	All amounts are stored as integer cents to avoid floating point drift.
4	"""
5	
6	import sqlite3
7	from contextlib import contextmanager
8	
9	SCHEMA = """
10	CREATE TABLE IF NOT EXISTS users (
11	    id INTEGER PRIMARY KEY AUTOINCREMENT,
12	    username TEXT NOT NULL UNIQUE,
13	    password_hash TEXT NOT NULL,
14	    salt TEXT NOT NULL,
15	    created_at TEXT NOT NULL
16	);
17	
18	CREATE TABLE IF NOT EXISTS expenses (
19	    id INTEGER PRIMARY KEY AUTOINCREMENT,
20	    user_id INTEGER NOT NULL REFERENCES users(id),
21	    amount_cents INTEGER NOT NULL,
22	    category TEXT NOT NULL,
23	    note TEXT NOT NULL DEFAULT '',
24	    spent_on TEXT NOT NULL,
25	    created_at TEXT NOT NULL
26	);
27	
28	CREATE TABLE IF NOT EXISTS budgets (
29	    id INTEGER PRIMA
… [1363 chars truncated]
```

**Assistant:**

Confirmed: fresh in-memory `Database()` per test, so autoincrement user ids restart at 1 each time, and `_summary_cache` is a process-wide module global keyed only on `(user_id, month)` — not scoped to the `db` instance at all.

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Cache never invalidated on expense/budget writes, returns stale totals", "severity": "critical", "description": "monthly_summary caches results in a module-level dict keyed by (user_id, month) with no invalidation hook. add_expense, delete_expense, and set_budget never touch _summary_cache. Once a (user_id, month) pair has been queried, every subsequent call — including from budget_status (line 52), which depends on monthly_summary for spend totals — returns the first-ever result for that key, ignoring any expenses added or deleted afterward in that month. E.g.: call monthly_summary(db, user, '2026-03') with no expenses -> caches {}; then add_expense(db, user, 500, 'food', '2026-03-05'); budget_status(db, user, '2026-03') will report spent=$0.00 and over_budget=False even though $5.00 was actually spent, silently breaking the budget-overrun alert the PR's own docs
… [1189 chars truncated]

---
**Final result** (6 turns, 37.5s, $0.081):

Confirmed: fresh in-memory `Database()` per test, so autoincrement user ids restart at 1 each time, and `_summary_cache` is a process-wide module global keyed only on `(user_id, month)` — not scoped to the `db` instance at all.

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Cache never invalidated on expense/budget writes, returns stale totals", "severity": "critical", "description": "monthly_summary caches results in a module-level dict keyed by (user_id, month) with no invalidation hook. add_expense, delete_expense, and set_budget never touch _summary_cache. Once a (user_id, month) pair has been queried, every subsequent call — including from budget_status (line 52), which depends on monthly_summary for spend totals — returns the first-ever result for that key, ignoring any expenses added or deleted afterward in that month. E.g.: call monthly_summary(db, user, '2026-03') with no expenses -> caches {}; then add_expense(db, user, 500, 'food', '2026-03-05'); budget_status(db, user, '2026-03') will report spent=$0.00 and over_budget=False even though $5.00 was actually spent, silently breaking the budget-overrun alert the PR's own docs
… [1189 chars truncated]
