# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case07_password_reset/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/test*auth*"}
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
ledgerly/expenses.py
ledgerly/reports.py
tests/test_ledgerly.py
ledgerly/auth.py
```

**Tool result:**

```
No files found
```

**Tool call → Grep**

```json
{"pattern": "reset", "path": "tests/test_ledgerly.py", "-n": true, "-i": true}
```

**Tool result:**

```
No files found
```

**Assistant:**

No tests reference the new reset password functionality at all.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/tests/test_ledgerly.py", "limit": 50}
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
… [692 chars truncated]
```

**Assistant:**

Confirms no tests for `request_password_reset` or `reset_password` exist anywhere in the suite.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/ledgerly/auth.py"}
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
9	import random
10	import secrets
11	from datetime import datetime, timedelta, timezone
12	
13	from .utils import utcnow_iso
14	
15	PBKDF2_ITERATIONS = 200_000
16	TOKEN_TTL_HOURS = 24
17	RESET_CODE_TTL_MINUTES = 15
18	
19	_reset_codes = {}
20	
21	
22	class AuthError(Exception):
23	    pass
24	
25	
26	def _hash_password(password, salt):
27	    dk = hashlib.pbkdf2_hmac(
28	        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
29	    )
30	    return dk.hex()
31	
32	
33	def register(db, username, password):
34	    if not username or not username.
… [2844 chars truncated]
```

**Assistant:**

This PR adds two new public functions (`request_password_reset`, `reset_password`) with no accompanying tests whatsoever.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/tests/test_ledgerly.py", "offset": 50, "limit": 40}
```

**Tool result:**

```
50	    def test_bad_token(self, db):
51	        with pytest.raises(auth.AuthError):
52	            auth.authenticate(db, "not-a-token")
53	
54	    def test_duplicate_username(self, db, user):
55	        with pytest.raises(auth.AuthError):
56	            auth.register(db, "alice", "anotherpass")
57	
58	
59	class TestExpenses:
60	    def test_add_and_get(self, db, user):
61	        eid = expenses.add_expense(db, user, 1250, "food", "2026-03-01", "lunch")
62	        row = expenses.get_expense(db, user, eid)
63	        assert row["amount_cents"] == 1250
64	        assert row["category"] == "food"
65	
66	    def test_ownership_enforced(self, db, user):
67	        other = auth.register(db, "bob", "bobspassword")
68	        eid = expenses.add_expense(db, user, 500, "food", "2026-03-01")
69	      
… [913 chars truncated]
```

**Assistant:**

Confirmed: the test file is untouched by this PR and contains zero tests for the new reset flow.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/tests/test_ledgerly.py", "offset": 89, "limit": 40}
```

**Tool result:**

```
89	class TestReports:
90	    def test_monthly_summary(self, db, user):
91	        expenses.add_expense(db, user, 100, "food", "2026-03-01")
92	        expenses.add_expense(db, user, 250, "food", "2026-03-15")
93	        expenses.add_expense(db, user, 400, "transport", "2026-04-01")
94	        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}
95	
96	    def test_budget_status(self, db, user):
97	        reports.set_budget(db, user, "food", "2026-03", 300)
98	        expenses.add_expense(db, user, 350, "food", "2026-03-10")
99	        status = reports.budget_status(db, user, "2026-03")
100	        assert status[0]["over_budget"] is True
101	        assert status[0]["remaining"] == "-$0.50"
102	
103	    def test_budget_upsert(self, db, user):
104	        reports.set_budget(
… [216 chars truncated]
```

**Assistant:**

This confirms the whole test file — no reset-related tests were added at all. This is a clear test-adequacy gap: risky new behavior (password reset code generation/validation, expiry claim, module-level state) shipped with zero test coverage.

Key untested risky behaviors I can name concrete failures for:
1. `reset_password` success path — never verified that the password actually changes and that a subsequent `login` with the new password works (and old password fails). A bug like the salt/hash swap or wrong SQL binding order would go undetected.
2. `RESET_CODE_TTL_MINUTES` is declared but never used/enforced in `request_password_reset`/`reset_password` — codes never expire. No test would have caught this since there's no test at all.
3. `del _reset_codes[username]` after successful reset — no test that a code can't be reused (replay), which is the core security property of the feature.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/ledgerly/db.py", "limit": 30}
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
… [75 chars truncated]
```

**Assistant:**

I have enough to finalize findings — this PR adds a whole new authentication feature with zero test coverage, and specifically the advertised TTL/expiry behavior is untestable-because-untested and appears unenforced.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/ledgerly/db.py", "offset": 30, "limit": 40}
```

**Tool result:**

```
30	    user_id INTEGER NOT NULL REFERENCES users(id),
31	    category TEXT NOT NULL,
32	    month TEXT NOT NULL,
33	    limit_cents INTEGER NOT NULL,
34	    UNIQUE (user_id, category, month)
35	);
36	
37	CREATE TABLE IF NOT EXISTS tokens (
38	    token TEXT PRIMARY KEY,
39	    user_id INTEGER NOT NULL REFERENCES users(id),
40	    expires_at TEXT NOT NULL
41	);
42	"""
43	
44	
45	class Database:
46	    def __init__(self, path=":memory:"):
47	        self.conn = sqlite3.connect(path)
48	        self.conn.row_factory = sqlite3.Row
49	        self.conn.execute("PRAGMA foreign_keys = ON")
50	        self.conn.executescript(SCHEMA)
51	
52	    @contextmanager
53	    def transaction(self):
54	        try:
55	            yield self.conn
56	            self.conn.commit()
57	        except Exception:

… [356 chars truncated]
```

**Assistant:**

I have enough to write the findings.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/ledgerly/db.py", "offset": 69, "limit": 15}
```

**Tool result:**

```
69	    def execute(self, sql, params=()):
70	        with self.transaction():
71	            cur = self.conn.execute(sql, params)
72	            return cur.lastrowid
73	
74	    def close(self):
75	        self.conn.close()
76	
```

**Assistant:**

{"findings": [{"file": "tests/test_ledgerly.py", "line": 108, "category": "test-adequacy", "title": "No tests for the new password reset flow", "severity": "major", "description": "The PR adds two new public auth functions, request_password_reset() and reset_password(), but tests/test_ledgerly.py is completely unmodified — there are zero tests exercising either function. Concretely, no test verifies that: (1) a correct code actually changes the password (e.g. login with the new password succeeds and the old password fails after reset_password), (2) an incorrect or reused code raises AuthError, (3) request_password_reset raises AuthError for an unknown username, or (4) the code is single-use (calling reset_password twice with the same code should fail the second time, since _reset_codes[username] is deleted). Any regression in this new authentication-critical code path — e.g. a hash/salt mismatch, wrong SQL parameter order, or a code that stays valid after use — would go completely undetected by CI."}, {"file": "ledgerly/auth.py", "line": 17, "category": "test-adequacy", "title": "Advertised reset-code TTL is unenforced and untested", "severity": "major", "description": "RESET_CODE_
… [546 chars truncated]

---
**Final result** (11 turns, 32.9s, $0.088):

{"findings": [{"file": "tests/test_ledgerly.py", "line": 108, "category": "test-adequacy", "title": "No tests for the new password reset flow", "severity": "major", "description": "The PR adds two new public auth functions, request_password_reset() and reset_password(), but tests/test_ledgerly.py is completely unmodified — there are zero tests exercising either function. Concretely, no test verifies that: (1) a correct code actually changes the password (e.g. login with the new password succeeds and the old password fails after reset_password), (2) an incorrect or reused code raises AuthError, (3) request_password_reset raises AuthError for an unknown username, or (4) the code is single-use (calling reset_password twice with the same code should fail the second time, since _reset_codes[username] is deleted). Any regression in this new authentication-critical code path — e.g. a hash/salt mismatch, wrong SQL parameter order, or a code that stays valid after use — would go completely undetected by CI."}, {"file": "ledgerly/auth.py", "line": 17, "category": "test-adequacy", "title": "Advertised reset-code TTL is unenforced and untested", "severity": "major", "description": "RESET_CODE_
… [546 chars truncated]
