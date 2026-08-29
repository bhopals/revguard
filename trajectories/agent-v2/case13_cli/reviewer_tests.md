# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case13_cli/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*cli*"}
```

**Tool call → Glob**

```json
{"pattern": "**/test*.py"}
```

**Tool result:**

```
No files found
```

**Tool result:**

```
tests/test_ledgerly.py
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case13_cli/tests/test_ledgerly.py"}
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

**Tool call → Grep**

```json
{"pattern": "def parse_money|def add_expense", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case13_cli/ledgerly", "output_mode": "content", "-A": 10}
```

**Tool result:**

```
ledgerly/expenses.py:18:def add_expense(db, user_id, amount_cents, category, spent_on, note=""):
ledgerly/expenses.py-19-    if category not in VALID_CATEGORIES:
ledgerly/expenses.py-20-        raise ExpenseError(f"unknown category: {category}")
ledgerly/expenses.py-21-    if len(note) > MAX_NOTE_LEN:
ledgerly/expenses.py-22-        raise ExpenseError("note too long")
ledgerly/expenses.py-23-    d = parse_iso_date(spent_on)
ledgerly/expenses.py-24-    return db.execute(
ledgerly/expenses.py-25-        "INSERT INTO expenses (user_id, amount_cents, category, note,"
ledgerly/expenses.py-26-        " spent_on, created_at) VALUES (?, ?, ?, ?, ?, ?)",
ledgerly/expenses.py-27-        (user_id, amount_cents, category, note, d.isoformat(), utcnow_iso()),
ledgerly/expenses.py-28-    )
--
ledgerly/ut
… [555 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/cli.py", "line": 34, "category": "test-adequacy", "severity": "major", "title": "No tests added for cli.py; amount-parsing reimplementation is untested and would fail an obvious case", "description": "This PR introduces ledgerly/cli.py (131 new lines: register/login/add/list/summary commands, token caching, argument parsing) but tests/test_ledgerly.py is unchanged \u2014 zero tests exercise any cli.py behavior. In particular, cmd_add computes amount_cents via `int(float(args.amount) * 100)` instead of calling the existing, already-tested `utils.parse_money` (which the test suite verifies handles rounding correctly and rejects invalid/negative input in TestUtils.test_parse_money and test_parse_money_rejects_garbage). Because there is no test invoking `ledgerly.cli.cmd_add` or `main([\"add\", ...])`, nothing catches that this reimplementation both loses validation (e.g. `ledgerly add -5 food 2026-03-01` silently records a negative expense instead of raising) and is subject to float imprecision (e.g. `float(\"2.90\")*100` == 289.99999999999994, so `int(...)` truncates to 289 cents instead of 290). A single test asserting `cmd_add` with amount \"2.90\" 
… [119 chars truncated]

---
**Final result** (5 turns, 23.1s, $0.060):

{"findings": [{"file": "ledgerly/cli.py", "line": 34, "category": "test-adequacy", "severity": "major", "title": "No tests added for cli.py; amount-parsing reimplementation is untested and would fail an obvious case", "description": "This PR introduces ledgerly/cli.py (131 new lines: register/login/add/list/summary commands, token caching, argument parsing) but tests/test_ledgerly.py is unchanged \u2014 zero tests exercise any cli.py behavior. In particular, cmd_add computes amount_cents via `int(float(args.amount) * 100)` instead of calling the existing, already-tested `utils.parse_money` (which the test suite verifies handles rounding correctly and rejects invalid/negative input in TestUtils.test_parse_money and test_parse_money_rejects_garbage). Because there is no test invoking `ledgerly.cli.cmd_add` or `main([\"add\", ...])`, nothing catches that this reimplementation both loses validation (e.g. `ledgerly add -5 food 2026-03-01` silently records a negative expense instead of raising) and is subject to float imprecision (e.g. `float(\"2.90\")*100` == 289.99999999999994, so `int(...)` truncates to 289 cents instead of 290). A single test asserting `cmd_add` with amount \"2.90\" 
… [119 chars truncated]
