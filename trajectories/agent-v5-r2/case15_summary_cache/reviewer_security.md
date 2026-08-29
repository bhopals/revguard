# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5-r2/case15_summary_cache/reviewer_security.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/ledgerly/reports.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/ledgerly/db.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/ledgerly/auth.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/tests/test_ledgerly.py", "limit": 40}
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
… [316 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/ledgerly/expenses.py"}
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

**Assistant:**

Confirmed: every existing query scopes strictly by `(db, user_id)` and each test/deployment uses its own `Database()` with autoincrementing ids starting at 1, so the same numeric `user_id` recurs across distinct databases/tenants. The new cache breaks that isolation model.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5-r2/case15_summary_cache/ledgerly/__init__.py"}
```

**Tool result:**

```
1	"""Ledgerly: a small expense-tracking service used as the review target."""
2	
3	__version__ = "1.4.0"
4	
```

**Assistant:**

{"findings": [{"file": "ledgerly/reports.py", "line": 22, "category": "security", "severity": "critical", "title": "Process-global cache keyed only by user_id leaks data across database instances/tenants", "description": "`_summary_cache` is a module-level dict keyed only by `(user_id, month)` (reports.py:31-33), with no reference to the `db` argument. Every other query in the codebase (expenses.py, auth.py) scopes strictly by both the specific `db` connection and `user_id`, since `Database()` is per-tenant/per-session and uses SQLite AUTOINCREMENT ids that restart at 1 for each new instance (confirmed by the `db`/`user` fixtures in tests/test_ledgerly.py, which create a fresh `Database()` and register 'alice' as id 1 in every test). Because the cache ignores which `db` object made the call, two different Database instances (e.g. two different tenants, or a test suite reusing ids) whose users happen to share the same integer `user_id` will read each other's cached monthly summaries: calling `monthly_summary(db1, 1, '2026-05')` populates the cache for key `(1, '2026-05')`, and a subsequent unrelated `monthly_summary(db2, 1, '2026-05')` for a completely different user/database return
… [1226 chars truncated]

---
**Final result** (8 turns, 106.0s, $0.093):

{"findings": [{"file": "ledgerly/reports.py", "line": 22, "category": "security", "severity": "critical", "title": "Process-global cache keyed only by user_id leaks data across database instances/tenants", "description": "`_summary_cache` is a module-level dict keyed only by `(user_id, month)` (reports.py:31-33), with no reference to the `db` argument. Every other query in the codebase (expenses.py, auth.py) scopes strictly by both the specific `db` connection and `user_id`, since `Database()` is per-tenant/per-session and uses SQLite AUTOINCREMENT ids that restart at 1 for each new instance (confirmed by the `db`/`user` fixtures in tests/test_ledgerly.py, which create a fresh `Database()` and register 'alice' as id 1 in every test). Because the cache ignores which `db` object made the call, two different Database instances (e.g. two different tenants, or a test suite reusing ids) whose users happen to share the same integer `user_id` will read each other's cached monthly summaries: calling `monthly_summary(db1, 1, '2026-05')` populates the cache for key `(1, '2026-05')`, and a subsequent unrelated `monthly_summary(db2, 1, '2026-05')` for a completely different user/database return
… [1226 chars truncated]
