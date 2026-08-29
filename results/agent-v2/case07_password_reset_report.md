# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] reset_password succeeds when no code was ever requested and code is None

`ledgerly/auth.py:94` — correctness

`_reset_codes.get(username)` returns `None` when no reset code has been issued for `username` (or after a code was already consumed, since `del` removes the entry). The check `_reset_codes.get(username) != code` only raises when the stored value differs from `code`. If `reset_password` is called with `code=None` (e.g. a caller/web framework passes `None` for a missing/omitted form field, or simply calls the function with the wrong argument), the comparison `None != None` evaluates to `False` and the function proceeds to overwrite the user's password without any valid reset code ever having been issued. This lets an attacker (or a buggy caller) reset any user's password by supplying no code at all.

## 2. [CRITICAL] Reset code generated with non-cryptographic PRNG

`ledgerly/auth.py:87` — security

request_password_reset() uses `random.randint(100000, 999999)` (Mersenne Twister) instead of `secrets`, which the rest of the module already uses for tokens/salts (secrets.token_urlsafe, secrets.token_hex). Python's `random` module is not cryptographically secure; its internal state can be recovered from a small number of outputs and future/past values predicted. An attacker who can observe a few generated codes (e.g. by requesting resets for accounts they control) can predict codes issued to other users, bypassing the reset flow entirely to take over arbitrary accounts.

## 3. [MAJOR] No tests added for new password-reset API (request_password_reset/reset_password)

`tests/test_ledgerly.py:108` — test-adequacy

The PR adds two new public, security-sensitive functions to ledgerly/auth.py (request_password_reset, reset_password) but the test suite (tests/test_ledgerly.py) has no TestAuth cases exercising them at all. There is no test that: (1) a code issued by request_password_reset actually allows reset_password to succeed and that the user can subsequently log in with the new password (verifying the side effect, not just that no exception is raised), (2) an incorrect code raises AuthError, (3) reset_password for an unknown username behaves correctly, or (4) short new_password (<8 chars) is rejected. Because none of this is covered, a regression in the reset flow (e.g. wrong dict key, hashing done incorrectly, code not cleared after use allowing replay) would not be caught by CI.

## 4. [MAJOR] RESET_CODE_TTL_MINUTES is unused and untested, so expired codes are silently accepted forever

`ledgerly/auth.py:17` — test-adequacy

RESET_CODE_TTL_MINUTES = 15 is introduced but never referenced anywhere in request_password_reset or reset_password — no timestamp is stored or checked. No test asserts that a reset code expires after the advertised 15 minutes (e.g. by mocking time or checking stored expiry), so this silent gap (codes valid indefinitely, contradicting the documented 15-minute TTL) is not caught by the test suite despite being a specific, nameable, testable behavior implied by the added constant.
