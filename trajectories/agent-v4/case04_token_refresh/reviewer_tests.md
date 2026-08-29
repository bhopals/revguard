# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case04_token_refresh/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case04_token_refresh/ledgerly/auth.py"}
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
… [2190 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case04_token_refresh/tests/test_ledgerly.py"}
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
… [3533 chars truncated]
```

**Assistant:**

{"findings": [{"file": "tests/test_ledgerly.py", "line": 60, "category": "test-adequacy", "title": "Test only checks trivial return value, never verifies the actual expiry side effect or token scoping", "severity": "major", "description": "test_refresh_token only asserts `auth.refresh_token(db, token) == token`. Looking at the implementation (ledgerly/auth.py:65-73), refresh_token unconditionally returns the same token it was given as long as authenticate() doesn't raise — so this assertion is guaranteed to pass regardless of whether the expiry was actually extended, or even whether the UPDATE statement is correct at all. The test never queries the tokens table to confirm expires_at was moved forward, and it uses only a single token in the database, so it cannot detect that the UPDATE statement in auth.py:70 has no WHERE clause and therefore blindly rewrites expires_at for every row in the tokens table (i.e., refreshing one user's token silently extends every other logged-in user's session too). A test that created two tokens (e.g., for two different users), called refresh_token on only one, and then asserted the other token's expiry was unchanged would have caught this; as written
… [69 chars truncated]

---
**Final result** (3 turns, 18.8s, $0.045):

{"findings": [{"file": "tests/test_ledgerly.py", "line": 60, "category": "test-adequacy", "title": "Test only checks trivial return value, never verifies the actual expiry side effect or token scoping", "severity": "major", "description": "test_refresh_token only asserts `auth.refresh_token(db, token) == token`. Looking at the implementation (ledgerly/auth.py:65-73), refresh_token unconditionally returns the same token it was given as long as authenticate() doesn't raise — so this assertion is guaranteed to pass regardless of whether the expiry was actually extended, or even whether the UPDATE statement is correct at all. The test never queries the tokens table to confirm expires_at was moved forward, and it uses only a single token in the database, so it cannot detect that the UPDATE statement in auth.py:70 has no WHERE clause and therefore blindly rewrites expires_at for every row in the tokens table (i.e., refreshing one user's token silently extends every other logged-in user's session too). A test that created two tokens (e.g., for two different users), called refresh_token on only one, and then asserted the other token's expiry was unchanged would have caught this; as written
… [69 chars truncated]
