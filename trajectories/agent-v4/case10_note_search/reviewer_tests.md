# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case10_note_search/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*"}
```

**Tool result:**

```
tests/test_ledgerly.py
pytest.ini
```

**Tool call → Grep**

```json
{"pattern": "search_expenses", "path": "tests/test_ledgerly.py", "output_mode": "content", "-n": true}
```

**Tool result:**

```
No matches found
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/expenses.py"}
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
… [1603 chars truncated]
```

**Assistant:**

This PR adds `search_expenses` with a `sort` parameter that's interpolated directly into SQL via f-string (SQL injection risk), and there are zero tests for this new function anywhere in the test suite.

**Tool call → Grep**

```json
{"pattern": "list_expenses|def test_", "path": "tests/test_ledgerly.py", "output_mode": "content", "-n": true}
```

**Tool result:**

```
21:    def test_parse_money(self):
27:    def test_parse_money_rejects_garbage(self):
32:    def test_format_money(self):
37:    def test_month_of(self):
42:    def test_register_and_login(self, db, user):
46:    def test_wrong_password(self, db, user):
50:    def test_bad_token(self, db):
54:    def test_duplicate_username(self, db, user):
60:    def test_add_and_get(self, db, user):
66:    def test_ownership_enforced(self, db, user):
72:    def test_delete(self, db, user):
78:    def test_bad_category(self, db, user):
82:    def test_list_filters_by_category(self, db, user):
85:        rows = expenses.list_expenses(db, user, category="food")
90:    def test_monthly_summary(self, db, user):
96:    def test_budget_status(self, db, user):
103:    def test_budget_upsert(self, db, user):
```

**Assistant:**

Confirmed: no test file changes accompany this PR — `search_expenses` has zero test coverage despite introducing a SQL-injectable `sort` parameter and note-matching logic.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/tests/test_ledgerly.py", "offset": 1, "limit": 20}
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
```

**Assistant:**

No existing tests were weakened; this is purely a missing-test issue for genuinely risky new behavior.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/tests/test_ledgerly.py", "offset": 78, "limit": 15}
```

**Tool result:**

```
78	    def test_bad_category(self, db, user):
79	        with pytest.raises(expenses.ExpenseError):
80	            expenses.add_expense(db, user, 500, "yachts", "2026-03-01")
81	
82	    def test_list_filters_by_category(self, db, user):
83	        expenses.add_expense(db, user, 100, "food", "2026-03-01")
84	        expenses.add_expense(db, user, 200, "transport", "2026-03-02")
85	        rows = expenses.list_expenses(db, user, category="food")
86	        assert [r["amount_cents"] for r in rows] == [100]
87	
88	
89	class TestReports:
90	    def test_monthly_summary(self, db, user):
91	        expenses.add_expense(db, user, 100, "food", "2026-03-01")
92	        expenses.add_expense(db, user, 250, "food", "2026-03-15")
```

**Tool call → Grep**

```json
{"pattern": "def query|def execute", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/db.py", "output_mode": "content", "-n": true}
```

**Tool result:**

```
61:    def query(self, sql, params=()):
65:    def query_one(self, sql, params=()):
69:    def execute(self, sql, params=()):
```

**Assistant:**

I have enough to finalize the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/db.py", "offset": 55, "limit": 20}
```

**Tool result:**

```
55	            yield self.conn
56	            self.conn.commit()
57	        except Exception:
58	            self.conn.rollback()
59	            raise
60	
61	    def query(self, sql, params=()):
62	        cur = self.conn.execute(sql, params)
63	        return cur.fetchall()
64	
65	    def query_one(self, sql, params=()):
66	        cur = self.conn.execute(sql, params)
67	        return cur.fetchone()
68	
69	    def execute(self, sql, params=()):
70	        with self.transaction():
71	            cur = self.conn.execute(sql, params)
72	            return cur.lastrowid
73	
74	    def close(self):
```

**Assistant:**

Confirmed sqlite3 is used directly and `sort` is spliced unsanitized into the SQL string via f-string. No test exists to guard against injection or validate ordering behavior.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/tests/test_ledgerly.py", "offset": 55, "limit": 30}
```

**Tool result:**

```
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
69	        with pytest.raises(expenses.ExpenseError):
70	            expenses.get_expense(db, other, eid)
71	
72	    def test_delete(self, db, user):
73	        eid = expenses.add_expense(db, user, 500
… [562 chars truncated]
```

**Assistant:**

This confirms the whole `TestExpenses` class has no new test cases for `search_expenses`. I have sufficient evidence for the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/tests/test_ledgerly.py", "offset": 1, "limit": 140}
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
… [3364 chars truncated]
```

**Assistant:**

This confirms the entire test file (108 lines) has no test additions for `search_expenses`.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/db.py"}
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

I now have everything needed to produce the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/expenses.py", "offset": 63, "limit": 8}
```

**Tool result:**

```
63	def search_expenses(db, user_id, text, sort="spent_on"):
64	    """Search the user's expenses whose note contains `text`."""
65	    pattern = f"%{text}%"
66	    sql = (
67	        "SELECT * FROM expenses WHERE user_id = ? AND note LIKE ?"
68	        f" ORDER BY {sort} DESC"
69	    )
70	    return [dict(r) for r in db.query(sql, (user_id, pattern))]
```

**Assistant:**

Confirmed. Final answer below.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/tests/test_ledgerly.py", "offset": 1, "limit": 1}
```

**Tool result:**

```
1	import pytest
```

**Assistant:**

{"findings": [{"file": "ledgerly/expenses.py", "line": 68, "category": "test-adequacy", "severity": "major", "title": "No test coverage for search_expenses, including its SQL-injectable sort parameter", "description": "The PR adds `search_expenses(db, user_id, text, sort=\"spent_on\")`, which builds SQL with `f\" ORDER BY {sort} DESC\"` (line 68), splicing the caller-supplied `sort` argument directly into the query string with no allowlist/validation. tests/test_ledgerly.py has zero additions for this function — no test exercises basic search matching (note LIKE `%text%`), user-id scoping, the default sort, or a non-default `sort` value. Because there is no test at all, a caller passing an untrusted `sort` value (e.g. `sort=\"id; DROP TABLE expenses;--\"` or any column name that doesn't exist) would only be caught by whatever code calls this function in production, not by CI. A single test asserting correct filtering by user/note and a test that an invalid `sort` value is rejected (or that it can't be attacker-controlled) would have caught this class of regression before merge; as it stands, the function's core behavior and its most dangerous new surface (the `sort` interpolation) 
… [53 chars truncated]

---
**Final result** (14 turns, 38.8s, $0.109):

{"findings": [{"file": "ledgerly/expenses.py", "line": 68, "category": "test-adequacy", "severity": "major", "title": "No test coverage for search_expenses, including its SQL-injectable sort parameter", "description": "The PR adds `search_expenses(db, user_id, text, sort=\"spent_on\")`, which builds SQL with `f\" ORDER BY {sort} DESC\"` (line 68), splicing the caller-supplied `sort` argument directly into the query string with no allowlist/validation. tests/test_ledgerly.py has zero additions for this function — no test exercises basic search matching (note LIKE `%text%`), user-id scoping, the default sort, or a non-default `sort` value. Because there is no test at all, a caller passing an untrusted `sort` value (e.g. `sort=\"id; DROP TABLE expenses;--\"` or any column name that doesn't exist) would only be caught by whatever code calls this function in production, not by CI. A single test asserting correct filtering by user/note and a test that an invalid `sort` value is rejected (or that it can't be attacker-controlled) would have caught this class of regression before merge; as it stands, the function's core behavior and its most dangerous new surface (the `sort` interpolation) 
… [53 chars truncated]
