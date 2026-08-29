# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case07_password_reset/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case07_password_reset/ledgerly/auth.py"}
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

{"findings": [{"file": "ledgerly/auth.py", "line": 94, "category": "correctness", "title": "reset_password succeeds when no code was ever requested and code is None", "severity": "critical", "description": "`_reset_codes.get(username)` returns `None` when no reset code has been issued for `username` (or after a code was already consumed, since `del` removes the entry). The check `_reset_codes.get(username) != code` only raises when the stored value differs from `code`. If `reset_password` is called with `code=None` (e.g. a caller/web framework passes `None` for a missing/omitted form field, or simply calls the function with the wrong argument), the comparison `None != None` evaluates to `False` and the function proceeds to overwrite the user's password without any valid reset code ever having been issued. This lets an attacker (or a buggy caller) reset any user's password by supplying no code at all."}, {"file": "ledgerly/auth.py", "line": 92, "category": "correctness", "title": "Reset code TTL is never enforced despite RESET_CODE_TTL_MINUTES constant", "severity": "major", "description": "`RESET_CODE_TTL_MINUTES = 15` (line 17) is defined and `_reset_codes` stores only the code st
… [516 chars truncated]

---
**Final result** (2 turns, 21.8s, $0.042):

{"findings": [{"file": "ledgerly/auth.py", "line": 94, "category": "correctness", "title": "reset_password succeeds when no code was ever requested and code is None", "severity": "critical", "description": "`_reset_codes.get(username)` returns `None` when no reset code has been issued for `username` (or after a code was already consumed, since `del` removes the entry). The check `_reset_codes.get(username) != code` only raises when the stored value differs from `code`. If `reset_password` is called with `code=None` (e.g. a caller/web framework passes `None` for a missing/omitted form field, or simply calls the function with the wrong argument), the comparison `None != None` evaluates to `False` and the function proceeds to overwrite the user's password without any valid reset code ever having been issued. This lets an attacker (or a buggy caller) reset any user's password by supplying no code at all."}, {"file": "ledgerly/auth.py", "line": 92, "category": "correctness", "title": "Reset code TTL is never enforced despite RESET_CODE_TTL_MINUTES constant", "severity": "major", "description": "`RESET_CODE_TTL_MINUTES = 15` (line 17) is defined and `_reset_codes` stores only the code st
… [516 chars truncated]
