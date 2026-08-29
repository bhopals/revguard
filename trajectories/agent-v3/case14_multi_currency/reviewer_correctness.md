# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case14_multi_currency/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/expenses.py"}
```

**Tool call → Glob**

```json
{"pattern": "ledgerly/*.py"}
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

**Tool result:**

```
ledgerly/__init__.py
ledgerly/utils.py
ledgerly/auth.py
ledgerly/reports.py
ledgerly/db.py
ledgerly/expenses.py
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/reports.py"}
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/utils.py"}
```

**Tool result:**

```
1	"""Parsing and formatting helpers.
2	
3	Money is always integer cents internally. Parsing accepts "12.50", "12",
4	"$12.50". Dates are ISO "YYYY-MM-DD"; months are "YYYY-MM".
5	"""
6	
7	import re
8	from datetime import date, datetime, timezone
9	
10	_MONEY_RE = re.compile(r"^\$?(\d+)(?:\.(\d{1,2}))?$")
11	
12	
13	def parse_money(text):
14	    """Parse a user-supplied amount into integer cents.
15	
16	    Raises ValueError on malformed input or negative/zero amounts.
17	    """
18	    text = text.strip()
19	    m = _MONEY_RE.match(text)
20	    if not m:
21	        raise ValueError(f"invalid amount: {text!r}")
22	    dollars = int(m.group(1))
23	    frac = m.group(2) or "0"
24	    cents = int(frac) if len(frac) == 2 else int(frac) * 10
25	    total = dollars * 100 + cents
26	    if total <
… [857 chars truncated]
```

**Assistant:**

This confirms the docstring "Money is always integer cents internally" — the module assumes a single currency, and `format_money` always renders with `$`.

Findings confirmed: the PR allows `amount_cents` to represent non-USD amounts, but `reports.py` sums and compares `amount_cents` across currencies without any conversion or filtering, silently mixing currencies into a single total.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/db.py"}
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

This corroborates the finding — `amount_cents` is documented as always cents in a single unit, and reports naively `SUM(amount_cents)` and compare against `limit_cents` regardless of currency.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/tests/test_ledgerly.py", "offset": 1, "limit": 100}
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
… [2902 chars truncated]
```

**Assistant:**

I now have enough to confirm the finding.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/tests/test_ledgerly.py", "offset": 100, "limit": 50}
```

**Tool result:**

```
100	        expenses.add_expense(db, user, 400, "transport", "2026-04-01")
101	        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}
102	
103	    def test_budget_status(self, db, user):
104	        reports.set_budget(db, user, "food", "2026-03", 300)
105	        expenses.add_expense(db, user, 350, "food", "2026-03-10")
106	        status = reports.budget_status(db, user, "2026-03")
107	        assert status[0]["over_budget"] is True
108	        assert status[0]["remaining"] == "-$0.50"
109	
110	    def test_budget_upsert(self, db, user):
111	        reports.set_budget(db, user, "food", "2026-03", 300)
112	        reports.set_budget(db, user, "food", "2026-03", 500)
113	        status = reports.budget_status(db, user, "2026-03")
114	        assert status[0]["limit"] =
… [14 chars truncated]
```

**Assistant:**

Confirmed — no test exercises mixed currencies with reports, so this gap wasn't caught by CI.

```json
{"findings": [{"file": "ledgerly/reports.py", "line": 25, "category": "correctness", "title": "monthly_summary sums amount_cents across different currencies as if they were the same unit", "severity": "critical", "description": "add_expense now accepts a currency parameter (ledgerly/expenses.py:18) that stores an arbitrary currency alongside amount_cents, but monthly_summary does `SELECT category, SUM(amount_cents) ... GROUP BY category` with no reference to currency at all. If a user records e.g. 100 EUR-cents (currency='EUR') and 100 USD-cents (currency='USD') in the same category/month, the summary reports {'food': 200} and format_money renders it as '$2.00' — silently treating EUR and USD as fungible. This corrupts monthly_summary for any user who records expenses in more than one currency, which is exactly the scenario this PR introduces."}, {"file": "ledgerly/reports.py", "line": 49, "category": "correctness", "title": "budget_status compares mixed-currency spend against a single-currency limit", "severity": "critical", "description": "budget_status computes `spent = spend.g
… [613 chars truncated]

---
**Final result** (8 turns, 31.1s, $0.085):

Confirmed — no test exercises mixed currencies with reports, so this gap wasn't caught by CI.

```json
{"findings": [{"file": "ledgerly/reports.py", "line": 25, "category": "correctness", "title": "monthly_summary sums amount_cents across different currencies as if they were the same unit", "severity": "critical", "description": "add_expense now accepts a currency parameter (ledgerly/expenses.py:18) that stores an arbitrary currency alongside amount_cents, but monthly_summary does `SELECT category, SUM(amount_cents) ... GROUP BY category` with no reference to currency at all. If a user records e.g. 100 EUR-cents (currency='EUR') and 100 USD-cents (currency='USD') in the same category/month, the summary reports {'food': 200} and format_money renders it as '$2.00' — silently treating EUR and USD as fungible. This corrupts monthly_summary for any user who records expenses in more than one currency, which is exactly the scenario this PR introduces."}, {"file": "ledgerly/reports.py", "line": 49, "category": "correctness", "title": "budget_status compares mixed-currency spend against a single-currency limit", "severity": "critical", "description": "budget_status computes `spent = spend.g
… [613 chars truncated]
