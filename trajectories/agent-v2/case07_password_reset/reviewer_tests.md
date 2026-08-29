# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case07_password_reset/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*auth*"}
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

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case07_password_reset/tests/test_ledgerly.py"}
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

**Assistant:**

{"findings": [{"file": "tests/test_ledgerly.py", "line": 108, "category": "test-adequacy", "title": "No tests added for new password-reset API (request_password_reset/reset_password)", "severity": "major", "description": "The PR adds two new public, security-sensitive functions to ledgerly/auth.py (request_password_reset, reset_password) but the test suite (tests/test_ledgerly.py) has no TestAuth cases exercising them at all. There is no test that: (1) a code issued by request_password_reset actually allows reset_password to succeed and that the user can subsequently log in with the new password (verifying the side effect, not just that no exception is raised), (2) an incorrect code raises AuthError, (3) reset_password for an unknown username behaves correctly, or (4) short new_password (<8 chars) is rejected. Because none of this is covered, a regression in the reset flow (e.g. wrong dict key, hashing done incorrectly, code not cleared after use allowing replay) would not be caught by CI."}, {"file": "ledgerly/auth.py", "line": 17, "category": "test-adequacy", "title": "RESET_CODE_TTL_MINUTES is unused and untested, so expired codes are silently accepted forever", "severity": "maj
… [508 chars truncated]

---
**Final result** (4 turns, 18.2s, $0.042):

{"findings": [{"file": "tests/test_ledgerly.py", "line": 108, "category": "test-adequacy", "title": "No tests added for new password-reset API (request_password_reset/reset_password)", "severity": "major", "description": "The PR adds two new public, security-sensitive functions to ledgerly/auth.py (request_password_reset, reset_password) but the test suite (tests/test_ledgerly.py) has no TestAuth cases exercising them at all. There is no test that: (1) a code issued by request_password_reset actually allows reset_password to succeed and that the user can subsequently log in with the new password (verifying the side effect, not just that no exception is raised), (2) an incorrect code raises AuthError, (3) reset_password for an unknown username behaves correctly, or (4) short new_password (<8 chars) is rejected. Because none of this is covered, a regression in the reset flow (e.g. wrong dict key, hashing done incorrectly, code not cleared after use allowing replay) would not be caught by CI."}, {"file": "ledgerly/auth.py", "line": 17, "category": "test-adequacy", "title": "RESET_CODE_TTL_MINUTES is unused and untested, so expired codes are silently accepted forever", "severity": "maj
… [508 chars truncated]
