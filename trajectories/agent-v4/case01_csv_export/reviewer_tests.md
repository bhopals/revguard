# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case01_csv_export/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*export*"}
```

**Tool result:**

```
No files found
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
ledgerly/export.py
```

**Tool call → Grep**

```json
{"pattern": "export", "path": "tests/test_ledgerly.py", "-n": true}
```

**Tool result:**

```
No files found
```

**Assistant:**

No tests reference `export` at all — the PR adds a new module with no test coverage. There's no test diff to evaluate for weakened assertions, but the complete absence of tests for risky new behavior (SQL string interpolation via f-string, path joining with caller-supplied filename) is notable. However, per instructions I should only flag missing tests when I can name a specific failure the absent test would catch, and logic/security issues are owned by another reviewer — so I'll note the coverage gap without re-litigating the security issue itself.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case01_csv_export/tests/test_ledgerly.py", "limit": 30}
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
… [17 chars truncated]
```

**Assistant:**

Confirmed: this PR adds `ledgerly/export.py` entirely without any accompanying tests in `tests/test_ledgerly.py`.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case01_csv_export/ledgerly/export.py"}
```

**Tool result:**

```
1	"""CSV export for a user's expenses."""
2	
3	import csv
4	import os
5	
6	EXPORT_DIR = "exports"
7	
8	
9	def export_expenses_csv(db, user_id, filename, category=None):
10	    """Write the user's expenses to exports/<filename> and return the path."""
11	    os.makedirs(EXPORT_DIR, exist_ok=True)
12	    path = os.path.join(EXPORT_DIR, filename)
13	    sql = (
14	        "SELECT spent_on, category, amount_cents, note FROM expenses"
15	        " WHERE user_id = ?"
16	    )
17	    if category is not None:
18	        sql += f" AND category = '{category}'"
19	    sql += " ORDER BY spent_on"
20	    rows = db.query(sql, (user_id,))
21	    with open(path, "w", newline="") as fh:
22	        writer = csv.writer(fh)
23	        writer.writerow(["date", "category", "amount", "note"])
24	        for r in
… [231 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case01_csv_export/ledgerly/db.py"}
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

I have enough to answer. This is entirely new, untested code with risky behavior (SQL string interpolation for the `category` filter, and unsanitized `filename`/`path.join` for file writes) — no test exists to catch either category-filter SQL injection or path traversal via filename.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case01_csv_export/tests/test_ledgerly.py", "offset": 1, "limit": 1}
```

**Tool result:**

```
1	import pytest
```

**Assistant:**

{"findings": [{"file": "ledgerly/export.py", "line": 18, "category": "test-adequacy", "severity": "major", "title": "No tests for export_expenses_csv, missing coverage would have caught SQL injection via category filter", "description": "The PR adds ledgerly/export.py with export_expenses_csv(), which builds SQL by directly f-string-interpolating the caller-supplied `category` parameter into the query (line 18: `sql += f\" AND category = '{category}'\"`) instead of using a parameterized placeholder like the rest of the query does. tests/test_ledgerly.py has zero tests for this new module (no import of ledgerly.export, no test class/function referencing export_expenses_csv). A test that calls export_expenses_csv(db, user_id, filename, category=\"food' OR '1'='1\") and asserts the returned CSV only contains that user's food expenses (not all expenses/rows) would have caught this injection bug immediately. As it stands, nothing in the suite exercises the category-filter code path or verifies the CSV file's actual contents, so this defect ships without any red test."}]}

---
**Final result** (8 turns, 21.7s, $0.055):

{"findings": [{"file": "ledgerly/export.py", "line": 18, "category": "test-adequacy", "severity": "major", "title": "No tests for export_expenses_csv, missing coverage would have caught SQL injection via category filter", "description": "The PR adds ledgerly/export.py with export_expenses_csv(), which builds SQL by directly f-string-interpolating the caller-supplied `category` parameter into the query (line 18: `sql += f\" AND category = '{category}'\"`) instead of using a parameterized placeholder like the rest of the query does. tests/test_ledgerly.py has zero tests for this new module (no import of ledgerly.export, no test class/function referencing export_expenses_csv). A test that calls export_expenses_csv(db, user_id, filename, category=\"food' OR '1'='1\") and asserts the returned CSV only contains that user's food expenses (not all expenses/rows) would have caught this injection bug immediately. As it stands, nothing in the suite exercises the category-filter code path or verifies the CSV file's actual contents, so this defect ships without any red test."}]}
