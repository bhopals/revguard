# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5/case15_summary_cache/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/reports.py"}
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

**Tool call → Glob**

```json
{"pattern": "**/*.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/tests/test_ledgerly.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/expenses.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/auth.py"}
```

**Tool result:**

```
1	"""User accounts and token authentication.
2	
3	Passwords are salted and hashed with PBKDF2. Session tokens are random,
4	stored server-side with an expiry, and compared in constant time.
5	"""
6	
7	import hashlib
8	import hmac
9	import secrets
10	from datetime import datetime, timedelta, timezone
11	
12	from .utils import utcnow_iso
13	
14	PBKDF2_ITERATIONS = 200_000
15	TOKEN_TTL_HOURS = 24
16	
17	
18	class AuthError(Exception):
19	    pass
20	
21	
22	def _hash_password(password, salt):
23	    dk = hashlib.pbkdf2_hmac(
24	        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
25	    )
26	    return dk.hex()
27	
28	
29	def register(db, username, password):
30	    if not username or not username.isalnum():
31	        raise AuthError("username must be non-empty and alp
… [1819 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/db.py"}
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/__init__.py"}
```

**Tool result:**

```
1	"""Ledgerly: a small expense-tracking service used as the review target."""
2	
3	__version__ = "1.4.0"
4	
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case15_summary_cache/ledgerly/reports.py", "offset": 20, "limit": 25}
```

**Tool result:**

```
20	
21	
22	_summary_cache = {}
23	
24	
25	def monthly_summary(db, user_id, month):
26	    """Total spend per category for a 'YYYY-MM' month.
27	
28	    Results are cached per (user, month): the dashboard calls this on
29	    every page load and the numbers rarely change within a session.
30	    """
31	    key = (user_id, month)
32	    if key in _summary_cache:
33	        return _summary_cache[key]
34	    rows = db.query(
35	        "SELECT category, SUM(amount_cents) AS total"
36	        " FROM expenses"
37	        " WHERE user_id = ? AND substr(spent_on, 1, 7) = ?"
38	        " GROUP BY category ORDER BY total DESC",
39	        (user_id, month),
40	    )
41	    totals = {r["category"]: r["total"] for r in rows}
42	    _summary_cache[key] = totals
43	    return totals
44	
```

**Assistant:**

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Cache is never invalidated when expenses/budgets change, returning stale monthly totals", "severity": "critical", "description": "monthly_summary caches results in the module-level _summary_cache keyed by (user_id, month) but nothing clears or updates that entry when the underlying data changes: add_expense, delete_expense (ledgerly/expenses.py) and set_budget (ledgerly/reports.py:10) never touch _summary_cache. Concrete scenario: the dashboard calls monthly_summary(db, user, '2026-05') once (e.g. before any expenses exist, caching {}); the user then adds an expense for May via add_expense; the dashboard reloads and calls monthly_summary(db, user, '2026-05') again — because the key is already cached, the new expense is silently omitted from the totals returned, and any budget_status() call for that month (reports.py:52) will also report the wrong 'spent'/'remaining'/'over_budget' values. This directly contradicts the docstring's premise that the cache exists because 'numbers rarely change within a session' — no invalidation path is provided for when they do change, so any edit produces pe
… [2084 chars truncated]

---
**Final result** (10 turns, 64.4s, $0.131):

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Cache is never invalidated when expenses/budgets change, returning stale monthly totals", "severity": "critical", "description": "monthly_summary caches results in the module-level _summary_cache keyed by (user_id, month) but nothing clears or updates that entry when the underlying data changes: add_expense, delete_expense (ledgerly/expenses.py) and set_budget (ledgerly/reports.py:10) never touch _summary_cache. Concrete scenario: the dashboard calls monthly_summary(db, user, '2026-05') once (e.g. before any expenses exist, caching {}); the user then adds an expense for May via add_expense; the dashboard reloads and calls monthly_summary(db, user, '2026-05') again — because the key is already cached, the new expense is silently omitted from the totals returned, and any budget_status() call for that month (reports.py:52) will also report the wrong 'spent'/'remaining'/'over_budget' values. This directly contradicts the docstring's premise that the cache exists because 'numbers rarely change within a session' — no invalidation path is provided for when they do change, so any edit produces pe
… [2084 chars truncated]
