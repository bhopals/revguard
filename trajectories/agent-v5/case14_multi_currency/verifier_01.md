# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5/case14_multi_currency/verifier_01.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpt8fojlql/repo/ledgerly/expenses.py"}
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
18	def add_expense(db, user_id, amount_cents, category, spent_on, note="", currency="USD"):
19	    if category not in VALID_CATEGORIES:
20	        raise ExpenseError(f"unknown category: {category}")
21	    if len(note) > MAX_NOTE_LEN:
22	        raise ExpenseError("note too long")
23	    d = parse_iso_date(spent_on)
24	    return db.execute(
25	        "INSERT INTO expenses (user_id, amount_cents, currency, category,"
26	        " note, 
… [1296 chars truncated]
```

**Assistant:**

This confirms exactly what the finding describes: `category` is validated against `VALID_CATEGORIES` and `note` length is checked, but `currency` is inserted directly with zero validation. Let me confirm this is exploitable at runtime.

**Tool call → Bash**

```json
{"command": "grep -n \"monthly_summary\" -r ledgerly/ | head -20"}
```

**Tool result:**

```
ledgerly/reports.py:22:def monthly_summary(db, user_id, month):
ledgerly/reports.py:40:    spend = monthly_summary(db, user_id, month)
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpt8fojlql/repo/ledgerly/reports.py"}
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
22	def monthly_summary(db, user_id, month):
23	    """Total spend per category for a 'YYYY-MM' month."""
24	    rows = db.query(
25	        "SELECT category, SUM(amount_cents) AS total"
26	        
… [1163 chars truncated]
```

**Tool call → Bash**

```json
{"command": "python3 -c \"\nimport sys\nsys.path.insert(0, '.')\nfrom ledgerly import db as dbmod, expenses\n\nd = dbmod.Db(':memory:') if hasattr(dbmod, 'Db') else None\nprint(dir(dbmod))\n\"\n"}
```

**Tool result:**

```
['Database', 'SCHEMA', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__', 'contextmanager', 'sqlite3']
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpt8fojlql/repo/ledgerly/db.py"}
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
22	    currency TEXT NOT NULL DEFAULT 'USD',
23	    category TEXT NOT NULL,
24	    note TEXT NOT NULL DEFAULT '',
25	    spent_on TEXT NOT NULL,
26	    created_at TEXT NOT NULL
27	);
28	
29	CREATE TABLE IF
… [1408 chars truncated]
```

**Assistant:**

Now let me execute a reproduction confirming currency accepts garbage/empty/non-string values with no error.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import expenses\n\ndb = Database(':memory:')\ndb.execute(\\\"INSERT INTO users (username, password_hash, salt, created_at) VALUES ('a','h','s','2026-01-01')\\\")\nuid = 1\n\n# empty string\neid1 = expenses.add_expense(db, uid, 100, 'food', '2026-03-01', currency='')\nrow1 = expenses.get_expense(db, uid, eid1)\nprint('empty string currency:', repr(row1['currency']))\n\n# garbage string\neid2 = expenses.add_expense(db, uid, 100, 'food', '2026-03-01', currency='NOT_A_CURRENCY_XYZ')\nrow2 = expenses.get_expense(db, uid, ei
… [859 chars truncated]
```

**Tool result:**

```
empty string currency: ''
garbage currency: 'NOT_A_CURRENCY_XYZ'
lowercase currency: 'usd'
int currency stored as: '12345' <class 'str'>
category garbage correctly raised: unknown category: not_a_category
```

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import expenses, reports\n\ndb = Database(':memory:')\ndb.execute(\\\"INSERT INTO users (username, password_hash, salt, created_at) VALUES ('a','h','s','2026-01-01')\\\")\nuid = 1\nexpenses.add_expense(db, uid, 100, 'food', '2026-03-01', currency='USD')\nexpenses.add_expense(db, uid, 200, 'food', '2026-03-02', currency='EUR')\nprint(reports.monthly_summary(db, uid, '2026-03'))\n\"\n"}
```

**Tool result:**

```
{'food': 300}
```

**Tool call → Bash**

```json
{"command": "python3 -m pytest tests/test_ledgerly.py -q 2>&1 | tail -20"}
```

**Tool result:**

```
.................                                                        [100%]
17 passed in 1.28s
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read expenses.py: add_expense validates `category` against VALID_CATEGORIES and checks note length, but the new `currency` parameter (line 18) is passed straight into the INSERT with zero checks. Executed a reproduction against the real Database/add_expense: empty string '', garbage 'NOT_A_CURRENCY_XYZ', lowercase 'usd', and even a non-string int 12345 were all accepted and persisted with no ExpenseError, while a bogus category value correctly raised 'unknown category: not_a_category'. This confirms the core claim: currency lacks any validation unlike category. One inaccuracy in the reviewer's supporting rationale: I also ran monthly_summary with mixed USD/EUR rows and found it GROUPs BY category only (not currency), so it silently sums different currencies together rather than 'fragmenting' due to case variants as described — the real downstream consequence is worse than stated, but this doesn't undermine the central, verified claim about missing input validation on currency.", "adjusted_severity": "minor"}

---
**Final result** (9 turns, 52.1s, $0.111):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read expenses.py: add_expense validates `category` against VALID_CATEGORIES and checks note length, but the new `currency` parameter (line 18) is passed straight into the INSERT with zero checks. Executed a reproduction against the real Database/add_expense: empty string '', garbage 'NOT_A_CURRENCY_XYZ', lowercase 'usd', and even a non-string int 12345 were all accepted and persisted with no ExpenseError, while a bogus category value correctly raised 'unknown category: not_a_category'. This confirms the core claim: currency lacks any validation unlike category. One inaccuracy in the reviewer's supporting rationale: I also ran monthly_summary with mixed USD/EUR rows and found it GROUPs BY category only (not currency), so it silently sums different currencies together rather than 'fragmenting' due to case variants as described — the real downstream consequence is worse than stated, but this doesn't undermine the central, verified claim about missing input validation on currency.", "adjusted_severity": "minor"}
