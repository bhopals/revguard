# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case10_note_search/reviewer_tests.jsonl`

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
{"pattern": "search_expenses", "path": "tests/test_ledgerly.py", "-n": true, "-C": 15}
```

**Tool result:**

```
No files found
```

**Assistant:**

No tests reference `search_expenses` at all — the PR adds a new public function with zero test coverage, including a SQL query built via an f-string with the `sort` parameter (a plausible SQL-injection vector), and no test exists that would catch a malformed `sort` value, an empty result set, or incorrect note matching.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/ledgerly/expenses.py"}
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

Confirmed: no test file references `search_expenses`.

**Tool call → Grep**

```json
{"pattern": "def test_", "path": "tests/test_ledgerly.py", "-n": true}
```

**Tool result:**

```
Found 1 file
tests/test_ledgerly.py
```

**Assistant:**

This confirms zero test coverage was added for the new `search_expenses` function.

**Tool call → Grep**

```json
{"pattern": "def test_", "path": "tests/test_ledgerly.py", "-n": true, "output_mode": "content"}
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
90:    def test_monthly_summary(self, db, user):
96:    def test_budget_status(self, db, user):
103:    def test_budget_upsert(self, db, user):
```

**Assistant:**

This confirms the PR added `search_expenses` (including a `sort` parameter interpolated directly into SQL via f-string) with no accompanying test whatsoever.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/tests/test_ledgerly.py", "offset": 1, "limit": 20}
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

I have enough confirmation: the PR's test file (`tests/test_ledgerly.py`) contains no test for `search_expenses`, and no other test file exists.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/tests/test_ledgerly.py", "offset": 58, "limit": 35}
```

**Tool result:**

```
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
73	        eid = expenses.add_expense(db, user, 500, "food", "2026-03-01")
74	        expenses.delete_expense(db, user, eid)
75	        with pytest.raises(expe
… [800 chars truncated]
```

**Assistant:**

Confirmed — the entire `TestExpenses` class has no test method for `search_expenses`.

**Tool call → Grep**

```json
{"pattern": "class Database|def query|def execute", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/ledgerly/db.py", "-n": true}
```

**Tool result:**

```
Found 1 file
ledgerly/db.py
```

**Assistant:**

I have sufficient information to finalize the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/ledgerly/db.py"}
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

This is enough to finalize the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/tests/test_ledgerly.py", "offset": 80, "limit": 10}
```

**Tool result:**

```
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
```

**Assistant:**

I have all the confirmation needed.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/ledgerly/expenses.py", "offset": 63, "limit": 8}
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

{"findings": [{"file": "ledgerly/expenses.py", "line": 63, "category": "test-adequacy", "severity": "major", "title": "No test coverage added for search_expenses()", "description": "The PR adds a new public function `search_expenses(db, user_id, text, sort=\"spent_on\")` (ledgerly/expenses.py:63-70) but tests/test_ledgerly.py's TestExpenses class (the only test file in the repo) has no test exercising it at all — no test verifies note-substring matching, user_id scoping/ownership isolation (unlike test_ownership_enforced for get_expense), the `sort` parameter's effect on ordering, or behavior with an empty/no-match result. Because `sql` builds the ORDER BY clause via an f-string interpolating the caller-supplied `sort` argument directly (line 68), an absent test also fails to catch that passing an untrusted or malformed `sort` value produces a broken/injectable SQL string — a case a single parametrized test would have caught immediately (e.g. sort='id; DROP TABLE expenses--' or sort='nonexistent_col' raising sqlite3.OperationalError). As written, CI passes with zero verification that the newly shipped feature works or is scoped correctly per user."}]}

---
**Final result** (12 turns, 31.5s, $0.085):

{"findings": [{"file": "ledgerly/expenses.py", "line": 63, "category": "test-adequacy", "severity": "major", "title": "No test coverage added for search_expenses()", "description": "The PR adds a new public function `search_expenses(db, user_id, text, sort=\"spent_on\")` (ledgerly/expenses.py:63-70) but tests/test_ledgerly.py's TestExpenses class (the only test file in the repo) has no test exercising it at all — no test verifies note-substring matching, user_id scoping/ownership isolation (unlike test_ownership_enforced for get_expense), the `sort` parameter's effect on ordering, or behavior with an empty/no-match result. Because `sql` builds the ORDER BY clause via an f-string interpolating the caller-supplied `sort` argument directly (line 68), an absent test also fails to catch that passing an untrusted or malformed `sort` value produces a broken/injectable SQL string — a case a single parametrized test would have caught immediately (e.g. sort='id; DROP TABLE expenses--' or sort='nonexistent_col' raising sqlite3.OperationalError). As written, CI passes with zero verification that the newly shipped feature works or is scoped correctly per user."}]}
