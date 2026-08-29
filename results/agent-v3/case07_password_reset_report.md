# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Reset code generated with non-cryptographic RNG

`ledgerly/auth.py:87` — security

request_password_reset() uses `random.randint(100000, 999999)` (the standard Mersenne Twister PRNG) instead of the `secrets` module already imported and used elsewhere in this file (secrets.token_hex, secrets.token_urlsafe). random's output is predictable if an attacker can observe a few outputs or knows/guesses the PRNG state, letting them compute future reset codes and take over any account without needing the emailed code. Use secrets.randbelow or secrets.choice to generate the digits.

*Verified: Read ledgerly/auth.py: request_password_reset() at line 87 calls `code = str(random.randint(100000, 999999))`, using the `random` module (Mersenne Twister) added in this PR's diff, while every other security-sensitive value in the same file (salts, session tokens) uses `secrets.token_hex`/`secrets.token_urlsafe` (confirmed via grep, lines 40/60/98). Demonstrated via python3 execution that once an *

## 2. [MAJOR] Reset code never expires despite TTL constant

`ledgerly/auth.py:94` — security

RESET_CODE_TTL_MINUTES is defined (line 17) but _reset_codes only stores the raw code string, not a timestamp, and reset_password() never checks age. A code issued via request_password_reset() remains valid indefinitely until the user requests a new one, so a code leaked (e.g., via email forwarding, shoulder-surfing, log capture, or shared inbox) long in the past can still be used to reset the password at any later time.

*Verified: Read ledgerly/auth.py post-PR: _reset_codes = {} stores only username->code (no timestamp), RESET_CODE_TTL_MINUTES (line 17) is never referenced anywhere else in the codebase (grep confirms), and reset_password() (line 92-103) only checks `_reset_codes.get(username) != code` with no age/expiry check. Wrote a reproduction script instantiating a fake DB, calling request_password_reset then immediate*

## 3. [MAJOR] No tests for the new password reset flow

`tests/test_ledgerly.py:108` — test-adequacy

The PR adds two new public auth functions, request_password_reset() and reset_password(), but tests/test_ledgerly.py is completely unmodified — there are zero tests exercising either function. Concretely, no test verifies that: (1) a correct code actually changes the password (e.g. login with the new password succeeds and the old password fails after reset_password), (2) an incorrect or reused code raises AuthError, (3) request_password_reset raises AuthError for an unknown username, or (4) the code is single-use (calling reset_password twice with the same code should fail the second time, since _reset_codes[username] is deleted). Any regression in this new authentication-critical code path — e.g. a hash/salt mismatch, wrong SQL parameter order, or a code that stays valid after use — would go completely undetected by CI.

*Verified: Grepped tests/test_ledgerly.py for 'reset_password' and 'request_password_reset' — zero matches; the TestAuth class only has test_register_and_login, test_wrong_password, test_bad_token, test_duplicate_username. Ran the full test suite (16 passed) confirming none exercise the new functions. Wrote a standalone repro script exercising request_password_reset/reset_password against a real Database ins*

## 4. [MAJOR] Advertised reset-code TTL is unenforced and untested

`ledgerly/auth.py:17` — test-adequacy

RESET_CODE_TTL_MINUTES = 15 is introduced and implies reset codes expire after 15 minutes, but neither request_password_reset() nor reset_password() ever reads or checks this constant — codes stored in _reset_codes never expire. Because no test asserts that an old code is rejected after the TTL elapses (or checks that a timestamp is even recorded), this dead/broken expiry logic ships silently: a leaked reset code from days ago would remain valid indefinitely for account takeover, and CI gives no signal that the advertised TTL guarantee is missing.

*Verified: Read ledgerly/auth.py: RESET_CODE_TTL_MINUTES (line 17) is defined but never referenced anywhere else (grep confirms auth.py is the only match for RESET_CODE_TTL/_reset_codes). _reset_codes stores only {username: code} with no timestamp; reset_password() only does `_reset_codes.get(username) != code` with no expiry check. Ran a live repro with a fake DB: request_password_reset issues a code, and r*
