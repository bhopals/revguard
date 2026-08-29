# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case15_summary_cache/verifier_01.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Bash**

```json
{"command": "cat ledgerly/db.py"}
```

**Tool result:**

```
"""SQLite persistence layer.

All amounts are stored as integer cents to avoid floating point drift.
"""

import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    spent_on TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    c
… [1143 chars truncated]
```

**Tool call → Bash**

```json
{"command": "cat ledgerly/reports.py"}
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


_summary_cache = {}


def monthly_summary(db, user_id, month):
    """Total spend per category for a 'YYYY-MM' month.

    Results are cached per (user, month): the dashboard calls this on
    every page load and the numbers rarely change within a ses
… [1308 chars truncated]
```

**Assistant:**

Confirmed by code reading: `_summary_cache` is a module-level dict keyed only by `(user_id, month)`, with no db reference. Let me verify with actual execution using two separate `Database` instances.

**Tool call → Bash**

```json
{"command": "find . -iname \"*expenses*\" -o -iname \"*users*\" | grep -v test | head -20 && cat ledgerly/expenses.py 2>/dev/null; cat ledgerly/users.py 2>/dev/null; cat ledgerly/auth.py 2>/dev/null | head -40"}
```

**Tool result:**

```
./ledgerly/expenses.py
"""Expense CRUD and listing. Every operation is scoped to the owning user."""

from .utils import parse_iso_date, utcnow_iso

VALID_CATEGORIES = {
    "food", "transport", "housing", "utilities",
    "health", "entertainment", "other",
}

MAX_NOTE_LEN = 500
PAGE_SIZE = 20


class ExpenseError(Exception):
    pass


def add_expense(db, user_id, amount_cents, category, spent_on, note=""):
    if category not in VALID_CATEGORIES:
        raise ExpenseError(f"unknown category: {category}")
    if len(note) > MAX_NOTE_LEN:
        raise ExpenseError("note too long")
    d = parse_iso_date(spent_on)
    return db.execute(
        "INSERT INTO expenses (user_id, amount_cents, category, note,"
        " spent_on, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amou
… [2272 chars truncated]
```

**Assistant:**

Now let's write a concrete reproduction with two separate `Database` instances (two tenants), both registering a user that gets id=1.

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, expenses, reports\n\ndbA = Database()\nalice_id = auth.register(dbA, 'alice', 'password123')\nexpenses.add_expense(dbA, alice_id, 35000, 'food', '2026-03-05')\nsumA = reports.monthly_summary(dbA, alice_id, '2026-03')\nprint('alice_id', alice_id, 'sumA', sumA)\n\ndbB = Database()\nbob_id = auth.register(dbB, 'bob', 'password123')\nexpenses.add_expense(dbB, bob_id, 100, 'transport', '2026-03-06')\nsumB = reports.monthly_summary(dbB, bob_id, '2026-03')\nprint('bob_id', bob_id, 'sumB (should b
… [239 chars truncated]
```

**Tool result:**

```
alice_id 1 sumA {'food': 35000}
bob_id 1 sumB (should be transport 100, but check leak) {'food': 35000}
LEAK CONFIRMED: bob sees alice data
```

**Assistant:**

The reproduction confirms the exact scenario described: two independent `Database()` instances, both assigning `user_id=1` to their first registered user, and `bob`'s `monthly_summary` call returns `alice`'s cached `{'food': 35000}` instead of his own `{'transport': 100}` data.

**Tool call → Bash**

```json
{"command": "grep -rn \"Database(\" ledgerly/*.py tests/*.py 2>/dev/null | grep -v \"class Database\""}
```

**Tool result:**

```
tests/test_ledgerly.py:10:    d = Database()
```

**Tool call → Bash**

```json
{"command": "grep -n \"def db\\b\\|def user\\b\\|fixture\" tests/test_ledgerly.py | head -20"}
```

**Tool result:**

```
8:@pytest.fixture()
9:def db():
15:@pytest.fixture()
16:def user(db):
```

**Assistant:**

This confirms every test gets a fresh `Database()` instance, all within the same test process — meaning the module-global `_summary_cache` bleeds across tests too, not just across tenants in production. The claim is fully substantiated by direct execution.

**Tool call → Bash**

```json
{"command": "echo done"}
```

**Tool result:**

```
done
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/db.py (confirms user_id is AUTOINCREMENT INTEGER PRIMARY KEY, restarting at 1 per new Database/sqlite file) and ledgerly/reports.py (confirms _summary_cache is a bare module-level dict keyed only by (user_id, month), with no db/connection identity in the key). Reproduced the exact scenario in the finding with a live script: created dbA, registered 'alice' (id=1), added a $350 food expense, called monthly_summary(dbA, 1, '2026-03') -> {'food': 35000}. Created a second independent Database() dbB, registered 'bob' (also id=1, since AUTOINCREMENT restarts per DB), added a $1 transport expense, called monthly_summary(dbB, 1, '2026-03'). Result: bob's call returned {'food': 35000} (alice's data from dbA) instead of his own {'transport': 100}, printing 'LEAK CONFIRMED: bob sees alice data'. This is a genuine cross-instance cache-key collision causing real data leakage, exactly as described.", "adjusted_severity": "critical"}

---
**Final result** (8 turns, 24.3s, $0.076):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/db.py (confirms user_id is AUTOINCREMENT INTEGER PRIMARY KEY, restarting at 1 per new Database/sqlite file) and ledgerly/reports.py (confirms _summary_cache is a bare module-level dict keyed only by (user_id, month), with no db/connection identity in the key). Reproduced the exact scenario in the finding with a live script: created dbA, registered 'alice' (id=1), added a $350 food expense, called monthly_summary(dbA, 1, '2026-03') -> {'food': 35000}. Created a second independent Database() dbB, registered 'bob' (also id=1, since AUTOINCREMENT restarts per DB), added a $1 transport expense, called monthly_summary(dbB, 1, '2026-03'). Result: bob's call returned {'food': 35000} (alice's data from dbA) instead of his own {'transport': 100}, printing 'LEAK CONFIRMED: bob sees alice data'. This is a genuine cross-instance cache-key collision causing real data leakage, exactly as described.", "adjusted_severity": "critical"}
