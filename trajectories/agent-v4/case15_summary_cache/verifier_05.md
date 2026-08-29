# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case15_summary_cache/verifier_05.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpkq9e3zq8/repo/ledgerly/reports.py"}
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

**Tool call → Grep**

```json
{"pattern": "session|ttl|expire|_cache", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpkq9e3zq8/repo", "output_mode": "content", "-i": true}
```

**Tool result:**

```
ledgerly/reports.py:22:_summary_cache = {}
ledgerly/reports.py:29:    every page load and the numbers rarely change within a session.
ledgerly/reports.py:32:    if key in _summary_cache:
ledgerly/reports.py:33:        return _summary_cache[key]
ledgerly/reports.py:42:    _summary_cache[key] = totals
ledgerly/auth.py:3:Passwords are salted and hashed with PBKDF2. Session tokens are random,
ledgerly/auth.py:15:TOKEN_TTL_HOURS = 24
ledgerly/auth.py:57:    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
ledgerly/auth.py:59:        "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
ledgerly/auth.py:60:        (token, row["id"], expires.replace(microsecond=0).isoformat()),
ledgerly/auth.py:68:        "SELECT user_id, expires_at FROM tokens WHERE token = ?
… [342 chars truncated]
```

**Assistant:**

There's a login-token TTL concept in auth.py, but nothing links that to `_summary_cache` — it's a plain module-level dict with no expiry, no clearing on logout, no per-instance scoping. The docstring's "within a session" phrasing implies bounded staleness that doesn't exist in the code.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nimport sys\nsys.path.insert(0, '.')\n\" 2>&1; ls ledgerly"}
```

**Tool result:**

```
__init__.py
auth.py
db.py
expenses.py
reports.py
utils.py
```

**Tool call → Bash**

```json
{"command": "python3 - <<'EOF'\nimport ledgerly.db as dbmod\nimport ledgerly.reports as reports\nimport ledgerly.expenses as expenses\n\n# simulate \"session 1\"\ndb1 = dbmod.Database(\":memory:\")\ndb1.execute(\"CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)\")\nEOF\n"}
```

**Tool result:**

```
(Bash completed with no output)
```

**Tool call → Bash**

```json
{"command": "find . -name conftest.py -o -name db.py | xargs -I{} echo {}; echo ---; cat ledgerly/db.py"}
```

**Tool result:**

```
./ledgerly/db.py
---
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
    user_id INTEGER NOT NULL REFERE
… [1164 chars truncated]
```

**Assistant:**

Confirms: `Database` has no session/lifecycle concept tied to the cache at all — the cache dict is purely module-global with no reset hook, no TTL, no per-instance/user scoping mechanism. Let me actually execute a repro showing the cache outlives a "session" (new Database instance) and never expires.

**Tool call → Bash**

```json
{"command": "python3 - <<'EOF'\nimport ledgerly.db as dbmod\nimport ledgerly.reports as reports\nimport ledgerly.expenses as expenses\nimport time\n\ndef make_user(db):\n    db.execute(\n        \"INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)\",\n        (\"alice\", \"h\", \"s\", \"2026-01-01T00:00:00\"),\n    )\n    return db.query_one(\"SELECT id FROM users WHERE username='alice'\")[\"id\"]\n\n# \"session 1\"\ndb1 = dbmod.Database(\":memory:\")\nuid1 = make_user(db1)\nexpenses.add_expense(db1, uid1, 500, \"food\", \"2026-05-01\")\ns1 = reports.monthly_summ
… [648 chars truncated]
```

**Tool result:**

```
Exit code 1
session1 summary: {'food': 500}
Traceback (most recent call last):
  File "<stdin>", line 27, in <module>
  File "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/tmpkq9e3zq8/repo/ledgerly/expenses.py", line 20, in add_expense
    raise ExpenseError(f"unknown category: {category}")
ledgerly.expenses.ExpenseError: unknown category: rent
```

**Tool call → Bash**

```json
{"command": "python3 - <<'EOF'\nimport ledgerly.db as dbmod\nimport ledgerly.reports as reports\nimport ledgerly.expenses as expenses\n\ndef make_user(db, name=\"alice\"):\n    db.execute(\n        \"INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)\",\n        (name, \"h\", \"s\", \"2026-01-01T00:00:00\"),\n    )\n    return db.query_one(\"SELECT id FROM users WHERE username=?\", (name,))[\"id\"]\n\ndb1 = dbmod.Database(\":memory:\")\nuid1 = make_user(db1)\nexpenses.add_expense(db1, uid1, 500, \"food\", \"2026-05-01\")\ns1 = reports.monthly_summary(db1, uid1, \
… [467 chars truncated]
```

**Tool result:**

```
session1 summary: {'food': 500}
session2 (independent fresh db, real spend 9999 food) summary: {'food': 500}
Cache leaked stale data across independent Database instances: True
```

**Assistant:**

This confirms the underlying mechanism the docstring misdescribes: the cache is a bare process-global dict with no expiry, no session binding, and no per-`Database`-instance scoping — it leaks stale data across entirely independent `Database` instances (a stand-in for separate sessions/requests). The docstring's "within a session" wording implies bounded staleness tied to some session lifecycle that doesn't exist anywhere in the codebase (grep confirmed no `session`/TTL/expire tie-in to `_summary_cache`).

The claim is accurately characterized: this is a documentation/comment-accuracy issue (docstring overstates a guarantee), not a claim that the caching itself is necessarily catastrophic — correctly scoped as minor.

**Tool call → Bash**

```json
{"command": "python3 -m pytest tests/test_ledgerly.py -k cache -q 2>&1 | tail -20"}
```

**Tool result:**

```
.                                                                        [100%]
1 passed, 16 deselected in 0.12s
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/reports.py: `_summary_cache = {}` is a bare module-level dict with no TTL/expiry and no session hook. Grepped the whole repo for session/ttl/expire/_cache and found the only session/TTL concept (auth.py's token TTL) is completely unrelated to `_summary_cache` — nothing clears or scopes the cache to a session, request, or Database instance. Executed a reproduction: created a Database instance, added an expense, called monthly_summary (caches under key (user_id, month)), closed it, then created a completely independent fresh Database with a new user (autoincrement reused id=1) and a different real expense amount for the same month key — monthly_summary returned the stale cached totals from the first 'session' instead of querying the new database, proving the cache is a global, unbounded, cross-instance leak with no session-scoped expiry as the docstring implies.", "adjusted_severity": "minor"}

---
**Final result** (9 turns, 36.1s, $0.094):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/reports.py: `_summary_cache = {}` is a bare module-level dict with no TTL/expiry and no session hook. Grepped the whole repo for session/ttl/expire/_cache and found the only session/TTL concept (auth.py's token TTL) is completely unrelated to `_summary_cache` — nothing clears or scopes the cache to a session, request, or Database instance. Executed a reproduction: created a Database instance, added an expense, called monthly_summary (caches under key (user_id, month)), closed it, then created a completely independent fresh Database with a new user (autoincrement reused id=1) and a different real expense amount for the same month key — monthly_summary returned the stale cached totals from the first 'session' instead of querying the new database, proving the cache is a global, unbounded, cross-instance leak with no session-scoped expiry as the docstring implies.", "adjusted_severity": "minor"}
