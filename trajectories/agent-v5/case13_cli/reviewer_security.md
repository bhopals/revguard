# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5/case13_cli/reviewer_security.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "ledgerly/*.py"}
```

**Tool result:**

```
ledgerly/__init__.py
ledgerly/db.py
ledgerly/utils.py
ledgerly/auth.py
ledgerly/expenses.py
ledgerly/reports.py
ledgerly/cli.py
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/auth.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/expenses.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/reports.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/db.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/cli.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/utils.py"}
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

**Tool call → Grep**

```json
{"pattern": "history|HISTFILE", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli"}
```

**Tool result:**

```
No files found
```

**Assistant:**

Based on my review, the underlying `auth`, `expenses`, `reports`, and `db` modules already use parameterized queries, ownership scoping, PBKDF2 with constant-time comparison, and server-side token expiry — none of that is broken by this PR. The CLI itself introduces two concrete security issues around credential/token handling.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/cli.py", "offset": 85, "limit": 15}
```

**Tool result:**

```
85	def build_parser():
86	    parser = argparse.ArgumentParser(prog="ledgerly")
87	    sub = parser.add_subparsers(dest="command", required=True)
88	
89	    add_reg = sub.add_parser("register", help="create an account")
90	    add_reg.add_argument("username")
91	    add_reg.add_argument("password")
92	    add_reg.set_defaults(func=cmd_register)
93	
94	    add_login = sub.add_parser("login", help="log in and cache a token")
95	    add_login.add_argument("username")
96	    add_login.add_argument("password")
97	    add_login.set_defaults(func=cmd_login)
98	
99	    add_add = sub.add_parser("add", help="record an expense")
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v5/case13_cli/ledgerly/cli.py", "offset": 31, "limit": 3}
```

**Tool result:**

```
31	def _save_token(token):
32	    TOKEN_PATH.write_text(token)
33	    TOKEN_PATH.chmod(0o600)
```

**Assistant:**

{"findings": [{"file": "ledgerly/cli.py", "line": 90, "category": "security", "title": "Passwords accepted as plaintext CLI positional arguments", "severity": "major", "description": "register and login take `password` as a positional argparse argument (lines 91 and 96, invoked as `python -m ledgerly.cli register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process's lifetime, and is also persisted in plaintext in the user's shell history file (e.g. ~/.bash_history, ~/.zsh_history) since most shells log the whole invoked command line. This directly exposes credentials that the rest of the codebase otherwise protects with PBKDF2 hashing and constant-time comparison."}, {"file": "ledgerly/cli.py", "line": 32, "category": "security", "title": "Token file created with default (world/group-readable) permissions before being locked down", "severity": "minor", "description": "_save_token calls TOKEN_PATH.write_text(token) which creates the file (if it doesn't already exist) using the process's default umask-derived mode (commonly 0644), and only afte
… [534 chars truncated]

---
**Final result** (11 turns, 57.7s, $0.136):

{"findings": [{"file": "ledgerly/cli.py", "line": 90, "category": "security", "title": "Passwords accepted as plaintext CLI positional arguments", "severity": "major", "description": "register and login take `password` as a positional argparse argument (lines 91 and 96, invoked as `python -m ledgerly.cli register alice mypassword`). On any multi-user or shared system, the full command line — including the plaintext password — is visible to other local users via `ps`/`/proc/<pid>/cmdline` for the process's lifetime, and is also persisted in plaintext in the user's shell history file (e.g. ~/.bash_history, ~/.zsh_history) since most shells log the whole invoked command line. This directly exposes credentials that the rest of the codebase otherwise protects with PBKDF2 hashing and constant-time comparison."}, {"file": "ledgerly/cli.py", "line": 32, "category": "security", "title": "Token file created with default (world/group-readable) permissions before being locked down", "severity": "minor", "description": "_save_token calls TOKEN_PATH.write_text(token) which creates the file (if it doesn't already exist) using the process's default umask-derived mode (commonly 0644), and only afte
… [534 chars truncated]
