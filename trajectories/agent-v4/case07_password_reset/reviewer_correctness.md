# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case07_password_reset/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case07_password_reset/ledgerly/auth.py"}
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

{"findings": [{"file": "ledgerly/auth.py", "line": 17, "category": "correctness", "title": "RESET_CODE_TTL_MINUTES is defined but never enforced", "description": "The constant RESET_CODE_TTL_MINUTES = 15 (line 17) declares that reset codes should expire after 15 minutes, matching the pattern used for session tokens (TOKEN_TTL_HOURS, enforced in authenticate()). However, request_password_reset() (lines 82-89) stores only the code in _reset_codes[username] with no timestamp, and reset_password() (lines 92-103) never checks any expiry — it only compares the code string. As a result, a reset code issued once remains valid indefinitely until a new one is requested or used, contradicting the TTL the code implies. Concretely: a user requests a reset code, doesn't use it, and it leaks (e.g. via a shared/observed inbox) a week later — an attacker can still use it to take over the account, since no expiry check ever rejects it.", "severity": "major"}]}

---
**Final result** (2 turns, 13.0s, $0.034):

{"findings": [{"file": "ledgerly/auth.py", "line": 17, "category": "correctness", "title": "RESET_CODE_TTL_MINUTES is defined but never enforced", "description": "The constant RESET_CODE_TTL_MINUTES = 15 (line 17) declares that reset codes should expire after 15 minutes, matching the pattern used for session tokens (TOKEN_TTL_HOURS, enforced in authenticate()). However, request_password_reset() (lines 82-89) stores only the code in _reset_codes[username] with no timestamp, and reset_password() (lines 92-103) never checks any expiry — it only compares the code string. As a result, a reset code issued once remains valid indefinitely until a new one is requested or used, contradicting the TTL the code implies. Concretely: a user requests a reset code, doesn't use it, and it leaks (e.g. via a shared/observed inbox) a week later — an attacker can still use it to take over the account, since no expiry check ever rejects it.", "severity": "major"}]}
