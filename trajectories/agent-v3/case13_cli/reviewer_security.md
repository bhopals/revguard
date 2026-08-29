# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case13_cli/reviewer_security.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/auth.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/expenses.py"}
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/reports.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/db.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/cli.py"}
```

**Tool result:**

```
1	"""Command-line interface for Ledgerly.
2	
3	Examples:
4	    python -m ledgerly.cli register alice mypassword
5	    python -m ledgerly.cli login alice mypassword
6	    python -m ledgerly.cli add 12.50 food 2026-03-01 --note "lunch"
7	    python -m ledgerly.cli list --category food --page 1
8	    python -m ledgerly.cli summary 2026-03
9	"""
10	
11	import argparse
12	import json
13	import os
14	import sys
15	from pathlib import Path
16	
17	from . import auth, expenses, reports
18	from .db import Database
19	from .utils import format_money
20	
21	DB_PATH = os.environ.get("LEDGERLY_DB", str(Path.home() / ".ledgerly.db"))
22	TOKEN_PATH = Path.home() / ".ledgerly_token"
23	
24	
25	def _load_token():
26	    if TOKEN_PATH.exists():
27	        return TOKEN_PATH.read_text().strip()
28	    return N
… [3322 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case13_cli/ledgerly/utils.py"}
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
ledgerly/cli.py
```

**Assistant:**

{"findings": [{"file": "ledgerly/cli.py", "line": 90, "category": "security", "title": "Password passed as CLI positional argument leaks credentials", "description": "register/login take `password` as a plain positional argument (lines 90-91, 95-96, invoked as e.g. `ledgerly register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process lifetime, and is written verbatim into the shell history file (~/.bash_history, ~/.zsh_history). The existing auth.py takes care to hash passwords with PBKDF2 and compare tokens in constant time, but this CLI undoes that protection by exposing the raw password on the command line before it ever reaches auth.register/auth.login. severity=major.", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 32, "category": "security", "title": "Auth token file briefly created world/group-readable before chmod", "description": "_save_token() calls TOKEN_PATH.write_text(token) which creates/truncates the file using the process umask (typically 0o644, world-readable) and only restricts permissions afterward via chmod(0o
… [499 chars truncated]

---
**Final result** (8 turns, 49.1s, $0.112):

{"findings": [{"file": "ledgerly/cli.py", "line": 90, "category": "security", "title": "Password passed as CLI positional argument leaks credentials", "description": "register/login take `password` as a plain positional argument (lines 90-91, 95-96, invoked as e.g. `ledgerly register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process lifetime, and is written verbatim into the shell history file (~/.bash_history, ~/.zsh_history). The existing auth.py takes care to hash passwords with PBKDF2 and compare tokens in constant time, but this CLI undoes that protection by exposing the raw password on the command line before it ever reaches auth.register/auth.login. severity=major.", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 32, "category": "security", "title": "Auth token file briefly created world/group-readable before chmod", "description": "_save_token() calls TOKEN_PATH.write_text(token) which creates/truncates the file using the process umask (typically 0o644, world-readable) and only restricts permissions afterward via chmod(0o
… [499 chars truncated]
