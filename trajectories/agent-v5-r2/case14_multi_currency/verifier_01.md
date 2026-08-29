# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5-r2/case14_multi_currency/verifier_01.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmp7qsmv42g/repo/ledgerly/expenses.py"}
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

The claim accurately reflects the code: `currency` at line 18 is accepted with no validation whatsoever (no whitelist, no case normalization, no length check), unlike `category`. Let me verify with actual execution to confirm garbage values are silently persisted.

**Tool call → Bash**

```json
{"command": "find . -name \"conftest.py\" -o -name \"db.py\" | head -20"}
```

**Tool result:**

```
./ledgerly/db.py
```

**Tool call → Bash**

```json
{"command": "cat tests/test_ledgerly.py | head -40"}
```

**Tool result:**

```
import pytest

from ledgerly.db import Database
from ledgerly import auth, expenses, reports
from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date


@pytest.fixture()
def db():
    d = Database()
    yield d
    d.close()


@pytest.fixture()
def user(db):
    return auth.register(db, "alice", "s3cretpass")


class TestUtils:
    def test_parse_money(self):
        assert parse_money("12.50") == 1250
        assert parse_money("$12.50") == 1250
        assert parse_money("12") == 1200
        assert parse_money("0.5") == 50

    def test_parse_money_rejects_garbage(self):
        for bad in ["", "abc", "-5", "12.345", "1,000"]:
            with pytest.raises(ValueError):
                parse_money(bad)

    def test_format_money(self):
        assert format_money(1
… [203 chars truncated]
```

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, expenses\n\ndb = Database()\nu = auth.register(db, 'alice', 's3cretpass')\n\n# garbage currency values\nfor bad in ['', 'usd', 'not-a-currency', 'X'*500, '\ud83d\udcb0', None]:\n    try:\n        eid = expenses.add_expense(db, u, 100, 'food', '2026-03-01', currency=bad)\n        row = expenses.get_expense(db, u, eid)\n        print(repr(bad), '-> stored as', repr(row['currency']))\n    except Exception as e:\n        print(repr(bad), '-> raised', type(e).__name__, e)\ndb.close()\n\"\n"}
```

**Tool result:**

```
'' -> stored as ''
'usd' -> stored as 'usd'
'not-a-currency' -> stored as 'not-a-currency'
'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' -> stored as 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
… [406 chars truncated]
```

**Assistant:**

This confirms the claim empirically: arbitrary garbage strings (empty, lowercase, non-currency text, 500-char strings, emoji) are all silently persisted into `currency` with zero validation, in stark contrast to `category` which raises `ExpenseError` for invalid values.

Now let's check the policy gate — is this a genuine code defect (not just "missing test") and is it more than pure style/speculation, given reporting code depends on consistent currency values.

**Tool call → Bash**

```json
{"command": "cat ledgerly/reports.py 2>/dev/null | head -60"}
```

**Tool result:**

```
"""Monthly summaries and budget tracking."""

from .utils import format_money


class BudgetError(Exception):
    pass


def set_budget(db, user_id, category, month, limit_cents):
    if limit_cents <= 0:
        raise BudgetError("budget limit must be positive")
    db.execute(
        "INSERT INTO budgets (user_id, category, month, limit_cents)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT (user_id, category, month)"
        " DO UPDATE SET limit_cents = excluded.limit_cents",
        (user_id, category, month, limit_cents),
    )


def monthly_summary(db, user_id, month):
    """Total spend per category for a 'YYYY-MM' month."""
    rows = db.query(
        "SELECT category, SUM(amount_cents) AS total"
        " FROM expenses"
        " WHERE user_id = ? AND substr(spent_on, 1, 
… [997 chars truncated]
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/expenses.py: add_expense (line 18) validates category against VALID_CATEGORIES and note length, but the new currency parameter (added in this PR) is passed directly into the INSERT with no check at all. Reproduced with actual execution: inserting expenses with currency='', 'usd', 'not-a-currency', a 500-char string, and an emoji all succeeded and were persisted verbatim (confirmed via get_expense), while category validation correctly rejects invalid values elsewhere in the same function. This is an asymmetry in the actual production code path introduced by this PR, not a missing-test complaint — the PR's own test only exercises the happy path ('EUR' roundtrip) and never exercises invalid input.", "adjusted_severity": "minor"}

---
**Final result** (6 turns, 28.2s, $0.069):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/expenses.py: add_expense (line 18) validates category against VALID_CATEGORIES and note length, but the new currency parameter (added in this PR) is passed directly into the INSERT with no check at all. Reproduced with actual execution: inserting expenses with currency='', 'usd', 'not-a-currency', a 500-char string, and an emoji all succeeded and were persisted verbatim (confirmed via get_expense), while category validation correctly rejects invalid values elsewhere in the same function. This is an asymmetry in the actual production code path introduced by this PR, not a missing-test complaint — the PR's own test only exercises the happy path ('EUR' roundtrip) and never exercises invalid input.", "adjusted_severity": "minor"}
