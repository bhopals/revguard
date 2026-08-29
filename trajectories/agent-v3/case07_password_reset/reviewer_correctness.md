# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case07_password_reset/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case07_password_reset/ledgerly/auth.py"}
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
9	import random
10	import secrets
11	from datetime import datetime, timedelta, timezone
12	
13	from .utils import utcnow_iso
14	
15	PBKDF2_ITERATIONS = 200_000
16	TOKEN_TTL_HOURS = 24
17	RESET_CODE_TTL_MINUTES = 15
18	
19	_reset_codes = {}
20	
21	
22	class AuthError(Exception):
23	    pass
24	
25	
26	def _hash_password(password, salt):
27	    dk = hashlib.pbkdf2_hmac(
28	        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
29	    )
30	    return dk.hex()
31	
32	
33	def register(db, username, password):
34	    if not username or not username.
… [2844 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/auth.py", "line": 88, "category": "correctness", "title": "Reset codes never expire despite RESET_CODE_TTL_MINUTES constant", "severity": "major", "description": "The PR introduces `RESET_CODE_TTL_MINUTES = 15` (line 17) implying reset codes are time-limited, but `_reset_codes[username] = code` (line 88) stores only the code with no timestamp, and `reset_password` (lines 92-103) never checks any expiry — it only compares the code value (line 94). A code issued via `request_password_reset` remains valid indefinitely until it is either replaced by a new request or consumed by a successful reset. This contradicts the declared TTL constant and the guarantee pattern already established for session tokens in `authenticate()` (lines 76-79), where expiry is actively checked and enforced. Concrete scenario: a user requests a reset code, doesn't use it, and days later that same code (e.g. recovered from an old email) still successfully resets the password."}]}

---
**Final result** (2 turns, 22.5s, $0.041):

{"findings": [{"file": "ledgerly/auth.py", "line": 88, "category": "correctness", "title": "Reset codes never expire despite RESET_CODE_TTL_MINUTES constant", "severity": "major", "description": "The PR introduces `RESET_CODE_TTL_MINUTES = 15` (line 17) implying reset codes are time-limited, but `_reset_codes[username] = code` (line 88) stores only the code with no timestamp, and `reset_password` (lines 92-103) never checks any expiry — it only compares the code value (line 94). A code issued via `request_password_reset` remains valid indefinitely until it is either replaced by a new request or consumed by a successful reset. This contradicts the declared TTL constant and the guarantee pattern already established for session tokens in `authenticate()` (lines 76-79), where expiry is actively checked and enforced. Concrete scenario: a user requests a reset code, doesn't use it, and days later that same code (e.g. recovered from an old email) still successfully resets the password."}]}
