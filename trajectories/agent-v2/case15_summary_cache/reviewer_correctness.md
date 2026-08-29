# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case15_summary_cache/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/ledgerly/reports.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/tests/test_ledgerly.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/ledgerly/expenses.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/ledgerly/db.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/ledgerly/auth.py"}
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

**Tool call → Grep**

```json
{"pattern": "monthly_summary|_summary_cache", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache", "output_mode": "content", "-n": true}
```

**Tool result:**

```
ledgerly/reports.py:22:_summary_cache = {}
ledgerly/reports.py:25:def monthly_summary(db, user_id, month):
ledgerly/reports.py:32:    if key in _summary_cache:
ledgerly/reports.py:33:        return _summary_cache[key]
ledgerly/reports.py:42:    _summary_cache[key] = totals
ledgerly/reports.py:52:    spend = monthly_summary(db, user_id, month)
tests/test_ledgerly.py:90:    def test_monthly_summary(self, db, user):
tests/test_ledgerly.py:94:        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}
tests/test_ledgerly.py:109:    def test_summary_cache_consistent(self, db, user):
tests/test_ledgerly.py:111:        first = reports.monthly_summary(db, user, "2026-05")
tests/test_ledgerly.py:112:        second = reports.monthly_summary(db, user, "2026-05")
.pytest_cache/v/cache
… [74 chars truncated]
```

**Assistant:**

Confirmed: no invalidation hooks exist anywhere in `expenses.py` or `reports.py` for `_summary_cache` — it's purely additive.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case15_summary_cache/ledgerly/reports.py", "offset": 40, "limit": 30}
```

**Tool result:**

```
40	    )
41	    totals = {r["category"]: r["total"] for r in rows}
42	    _summary_cache[key] = totals
43	    return totals
44	
45	
46	def budget_status(db, user_id, month):
47	    """Compare spend against each budget set for the month.
48	
49	    Returns a list of dicts with category, limit, spent, remaining and
50	    an over-budget flag. Categories without a budget are omitted.
51	    """
52	    spend = monthly_summary(db, user_id, month)
53	    budgets = db.query(
54	        "SELECT category, limit_cents FROM budgets"
55	        " WHERE user_id = ? AND month = ?",
56	        (user_id, month),
57	    )
58	    out = []
59	    for b in budgets:
60	        spent = spend.get(b["category"], 0)
61	        remaining = b["limit_cents"] - spent
62	        out.append({
63	            "category": 
… [256 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Stale cache: monthly_summary never invalidated after expenses change, causing wrong totals and wrong budget_status", "severity": "critical", "description": "_summary_cache is a module-level dict keyed only on (user_id, month) that is populated on first call and never invalidated. expenses.add_expense/delete_expense (ledgerly/expenses.py) and reports.set_budget perform no cache eviction. Concrete scenario: dashboard calls monthly_summary(db, user, '2026-03') which caches {'food': 100}; the user then adds another $50 food expense for March via add_expense; the dashboard reloads and calls monthly_summary(db, user, '2026-03') again, but instead of querying the DB it returns the stale cached {'food': 100}, silently dropping the new expense from the displayed total. Because budget_status (line 52) calls monthly_summary internally, this also makes 'spent', 'remaining', and 'over_budget' in budget_status stale/wrong after any new expense is added for a month that was previously summarized (e.g. a user who is now over budget will still show under_budget). The PR's own docstring claim that data is 
… [390 chars truncated]

---
**Final result** (9 turns, 34.2s, $0.092):

{"findings": [{"file": "ledgerly/reports.py", "line": 32, "category": "correctness", "title": "Stale cache: monthly_summary never invalidated after expenses change, causing wrong totals and wrong budget_status", "severity": "critical", "description": "_summary_cache is a module-level dict keyed only on (user_id, month) that is populated on first call and never invalidated. expenses.add_expense/delete_expense (ledgerly/expenses.py) and reports.set_budget perform no cache eviction. Concrete scenario: dashboard calls monthly_summary(db, user, '2026-03') which caches {'food': 100}; the user then adds another $50 food expense for March via add_expense; the dashboard reloads and calls monthly_summary(db, user, '2026-03') again, but instead of querying the DB it returns the stale cached {'food': 100}, silently dropping the new expense from the displayed total. Because budget_status (line 52) calls monthly_summary internally, this also makes 'spent', 'remaining', and 'over_budget' in budget_status stale/wrong after any new expense is added for a month that was previously summarized (e.g. a user who is now over budget will still show under_budget). The PR's own docstring claim that data is 
… [390 chars truncated]
