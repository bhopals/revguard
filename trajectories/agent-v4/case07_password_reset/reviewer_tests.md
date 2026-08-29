# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case07_password_reset/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Glob**

```json
{"pattern": "**/*test*auth*"}
```

**Tool call → Glob**

```json
{"pattern": "**/test_auth*"}
```

**Tool result:**

```
No files found
```

**Tool result:**

```
No files found
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
ledgerly/expenses.py
ledgerly/reports.py
tests/test_ledgerly.py
ledgerly/auth.py
```

**Tool call → Grep**

```json
{"pattern": "reset_password|request_password_reset", "output_mode": "files_with_matches"}
```

**Tool result:**

```
Found 1 file
ledgerly/auth.py
```

**Assistant:**

No tests reference the new `request_password_reset`/`reset_password` functions at all — the entire feature added by this PR has zero test coverage.

**Tool call → Grep**

```json
{"pattern": "def test_|import", "path": "tests/test_ledgerly.py", "output_mode": "content", "-n": true}
```

**Tool result:**

```
1:import pytest
3:from ledgerly.db import Database
4:from ledgerly import auth, expenses, reports
5:from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date
21:    def test_parse_money(self):
27:    def test_parse_money_rejects_garbage(self):
32:    def test_format_money(self):
37:    def test_month_of(self):
42:    def test_register_and_login(self, db, user):
46:    def test_wrong_password(self, db, user):
50:    def test_bad_token(self, db):
54:    def test_duplicate_username(self, db, user):
60:    def test_add_and_get(self, db, user):
66:    def test_ownership_enforced(self, db, user):
72:    def test_delete(self, db, user):
78:    def test_bad_category(self, db, user):
82:    def test_list_filters_by_category(self, db, user):
90:    def test_monthly_summary(self,
… [106 chars truncated]
```

**Assistant:**

Confirmed: no test in `tests/test_ledgerly.py` exercises the new reset-code flow.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case07_password_reset/tests/test_ledgerly.py", "offset": 42, "limit": 15}
```

**Tool result:**

```
42	    def test_register_and_login(self, db, user):
43	        token = auth.login(db, "alice", "s3cretpass")
44	        assert auth.authenticate(db, token) == user
45	
46	    def test_wrong_password(self, db, user):
47	        with pytest.raises(auth.AuthError):
48	            auth.login(db, "alice", "wrongpass1")
49	
50	    def test_bad_token(self, db):
51	        with pytest.raises(auth.AuthError):
52	            auth.authenticate(db, "not-a-token")
53	
54	    def test_duplicate_username(self, db, user):
55	        with pytest.raises(auth.AuthError):
56	            auth.register(db, "alice", "anotherpass")
```

**Assistant:**

This confirms the PR adds a whole new authentication-affecting feature (password reset) with no accompanying test whatsoever — not even a happy-path test verifying `reset_password` actually updates the stored password hash so a subsequent login works, nor a test for expiry, code mismatch, or reuse-after-consumption behavior.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case07_password_reset/ledgerly/auth.py", "offset": 80, "limit": 25}
```

**Tool result:**

```
80	    return row["user_id"]
81	
82	def request_password_reset(db, username):
83	    """Issue a 6-digit reset code for the user. Caller delivers it (email)."""
84	    row = db.query_one("SELECT id FROM users WHERE username = ?", (username,))
85	    if row is None:
86	        raise AuthError("unknown user")
87	    code = str(random.randint(100000, 999999))
88	    _reset_codes[username] = code
89	    return code
90	
91	
92	def reset_password(db, username, code, new_password):
93	    """Set a new password if the reset code matches."""
94	    if _reset_codes.get(username) != code:
95	        raise AuthError("invalid reset code")
96	    if len(new_password) < 8:
97	        raise AuthError("password must be at least 8 characters")
98	    salt = secrets.token_hex(16)
99	    db.execute(
100	      
… [184 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/auth.py", "line": 92, "category": "test-adequacy", "severity": "major", "title": "No tests added for new password reset flow", "description": "This PR adds request_password_reset() and reset_password(), a security-sensitive feature that mutates a user's credentials, but tests/test_ledgerly.py contains no tests exercising either function. In particular, no test verifies that RESET_CODE_TTL_MINUTES (defined at auth.py:17) is actually enforced — reading reset_password(), the code never checks any timestamp/expiry at all, so a reset code issued via request_password_reset() remains valid forever. A test asserting that reset_password() raises AuthError after the TTL elapses would have caught this: the code stores only `_reset_codes[username] = code` with no associated issue time (auth.py:88), so the constant is effectively dead and stale/leaked codes never expire. Additionally there is no test confirming that after a successful reset_password() call, the old password stops working and the new password succeeds via auth.login(), nor a test for the invalid-code or reused-code (code deleted after use) paths."}]}

---
**Final result** (8 turns, 21.5s, $0.051):

{"findings": [{"file": "ledgerly/auth.py", "line": 92, "category": "test-adequacy", "severity": "major", "title": "No tests added for new password reset flow", "description": "This PR adds request_password_reset() and reset_password(), a security-sensitive feature that mutates a user's credentials, but tests/test_ledgerly.py contains no tests exercising either function. In particular, no test verifies that RESET_CODE_TTL_MINUTES (defined at auth.py:17) is actually enforced — reading reset_password(), the code never checks any timestamp/expiry at all, so a reset code issued via request_password_reset() remains valid forever. A test asserting that reset_password() raises AuthError after the TTL elapses would have caught this: the code stores only `_reset_codes[username] = code` with no associated issue time (auth.py:88), so the constant is effectively dead and stale/leaked codes never expire. Additionally there is no test confirming that after a successful reset_password() call, the old password stops working and the new password succeeds via auth.login(), nor a test for the invalid-code or reused-code (code deleted after use) paths."}]}
