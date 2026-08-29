# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case13_cli/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*cli*"}
```

**Tool result:**

```
No files found
```

**Tool call → Glob**

```json
{"pattern": "**/test_*.py"}
```

**Tool result:**

```
tests/test_ledgerly.py
```

**Tool call → Grep**

```json
{"pattern": "cli", "path": "tests/test_ledgerly.py", "-i": true}
```

**Tool result:**

```
No files found
```

**Assistant:**

No tests exist at all for the new `ledgerly/cli.py` — the test file has zero references to it. This is a no-test-coverage PR, but per instructions I should only flag missing tests when I can name a specific failure an absent test would catch, so let me confirm there's genuinely no coverage before writing that up.

**Tool call → Read**

```json
{"file_path": "tests/test_ledgerly.py", "limit": 30}
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

{"findings": [{"file": "ledgerly/cli.py", "line": 118, "category": "test-adequacy", "severity": "major", "title": "No tests at all for new cli.py, including the always-succeeds exit code", "description": "This PR adds a full CLI module (register/login/add/list/summary) but the test suite (tests/test_ledgerly.py) has zero references to `cli` \u2014 none of the new commands are exercised. In particular, `main()` (ledgerly/cli.py:118-125) catches every exception from `args.func(db, args)`, prints it to stderr, and then unconditionally `return 0`s, so a failed `add` (e.g. bad amount format), failed `login` (bad password), or `_require_user` AuthError (not logged in) all report a process exit code of 0/success. Any script or CI job invoking `ledgerly` would see a false success. No test exercises this path, so a regression or the introduction of this exact silent-failure behavior would not be caught by CI."}]}

---
**Final result** (5 turns, 24.0s, $0.048):

{"findings": [{"file": "ledgerly/cli.py", "line": 118, "category": "test-adequacy", "severity": "major", "title": "No tests at all for new cli.py, including the always-succeeds exit code", "description": "This PR adds a full CLI module (register/login/add/list/summary) but the test suite (tests/test_ledgerly.py) has zero references to `cli` \u2014 none of the new commands are exercised. In particular, `main()` (ledgerly/cli.py:118-125) catches every exception from `args.func(db, args)`, prints it to stderr, and then unconditionally `return 0`s, so a failed `add` (e.g. bad amount format), failed `login` (bad password), or `_require_user` AuthError (not logged in) all report a process exit code of 0/success. Any script or CI job invoking `ledgerly` would see a false success. No test exercises this path, so a regression or the introduction of this exact silent-failure behavior would not be caught by CI."}]}
