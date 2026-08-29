# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 3 blocking finding(s), 3 critical.

## 1. [CRITICAL] Reset code TTL is declared but never enforced

`ledgerly/auth.py:94` — correctness

RESET_CODE_TTL_MINUTES = 15 (line 17) is defined but never referenced anywhere in the module. request_password_reset() (lines 82-89) stores only the code string in _reset_codes, with no timestamp. reset_password() (line 94) only checks that the code matches, never that it was issued recently. Consequence: a 6-digit reset code issued today remains valid indefinitely (until another reset is requested for the same username or the process restarts), directly contradicting the promised 15-minute TTL implied by the constant. A code that leaks (e.g. via email forwarding, shoulder-surfing, or log capture) months later can still be used to take over the account.

*Verified: Read ledgerly/auth.py in full and grepped the whole repo for RESET_CODE_TTL_MINUTES and _reset_codes: the constant (line 17) is assigned but never read anywhere; _reset_codes stores only the code string (line 88), with no timestamp; reset_password (lines 92-103) only does a dict lookup/string compare, no expiry check. Executed a script simulating request_password_reset/reset_password against a fake DB: reset succeeded using the original code with no time-based rejection, confirming the TTL is entirely unenforced (dead constant). This is a real, reachable behavioral defect (indefinite validity of a reset code contradicting the documented 15-minute TTL), not a test-coverage nitpick.*

## 2. [CRITICAL] Reset code generated with non-cryptographic PRNG

`ledgerly/auth.py:87` — security

request_password_reset() uses `random.randint(100000, 999999)` (Python's Mersenne Twister PRNG) to generate the password reset code, instead of a cryptographically secure source like `secrets.randbelow`. The rest of the module correctly uses `secrets` for tokens/salts, showing the security-sensitive intent was known. `random`'s internal state can be recovered from a small number of outputs, or is otherwise statistically predictable, letting an attacker who observes other random-derived values (or brute-forces the generator state) predict reset codes and take over accounts without ever receiving the emailed code.

*Verified: Read ledgerly/auth.py lines 82-89: request_password_reset() computes `code = str(random.randint(100000, 999999))` using the `random` module (Mersenne Twister, not cryptographically secure), while the rest of the file (register/login) correctly uses `secrets.token_hex`/`secrets.token_urlsafe` for salts and session tokens — confirming security-sensitive intent was known elsewhere. There is also no rate limiting/lockout on reset_password's code comparison, compounding brute-forceability of a 6-digit space. Verified with `random.seed(12345); random.randint(100000,999999)` producing a fully deterministic value, illustrating MT19937 state-recovery/predictability risk.*

## 3. [CRITICAL] Reset code TTL constant defined but never enforced

`ledgerly/auth.py:17` — security

RESET_CODE_TTL_MINUTES is declared but request_password_reset() stores only the code in `_reset_codes[username]` with no timestamp, and reset_password() never checks any expiry. A reset code issued once remains valid forever until a new one is requested for the same user, so an old code leaked via logs, shoulder-surfing, or an intercepted/forwarded email months earlier can still be used to reset the password at any time in the future.

*Verified: Read ledgerly/auth.py in full and grepped for RESET_CODE_TTL_MINUTES/_reset_codes usage: the constant (line 17) is never referenced anywhere else in the file or repo. request_password_reset() stores only `_reset_codes[username] = code` with no timestamp, and reset_password() only does `_reset_codes.get(username) != code` with no time-based check. Wrote a runnable repro using a FakeDB: generated a reset code via request_password_reset, then called reset_password with that code and it succeeded — there is no mechanism by which the code could ever expire, confirming the TTL constant is fully dead code and reset codes are valid indefinitely until superseded by a new request.*
