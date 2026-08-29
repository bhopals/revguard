# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] Reset code generated with insecure PRNG (random.randint)

`ledgerly/auth.py:87` — security

request_password_reset() uses Python's `random` module (Mersenne Twister) to generate the 6-digit reset code instead of a cryptographically secure source like `secrets`. The rest of the file correctly uses `secrets.token_hex`/`secrets.token_urlsafe` for salts and session tokens, showing this is a regression in this PR. Mersenne Twister state can be recovered from a modest number of outputs, letting an attacker who observes a few generated codes (e.g. via timing, logs, or repeated requests) predict future reset codes for other accounts and take them over.

*Verified: Read ledgerly/auth.py:87 directly; confirmed request_password_reset() uses `random.randint(100000, 999999)` (Python's Mersenne Twister-based `random` module) to generate the reset code, while reset_password and the rest of the file use `secrets.token_hex`/`secrets` elsewhere for salts/tokens. Verified via python3 that `random` is indeed the standard non-CSPRNG module. The finding accurately describes the code: this is a real regression introducing a predictable PRNG for a security-sensitive password reset code, consistent with the diff.*

## 2. [CRITICAL] No expiry enforced on reset codes despite TTL constant being defined

`ledgerly/auth.py:94` — security

RESET_CODE_TTL_MINUTES (line 17) is defined but never used. `_reset_codes[username] = code` (line 88) stores only the code with no timestamp, and reset_password() (line 94) only checks `_reset_codes.get(username) != code` with no expiry check. A reset code issued once remains valid forever (until a new one is requested or used), giving an attacker unlimited time to brute-force or otherwise obtain the code, e.g. from an old email, shoulder-surfing, or a leaked log, and take over the account long after the intended 15-minute window.

*Verified: Read ledgerly/auth.py in full and grepped repo-wide for RESET_CODE_TTL_MINUTES/_reset_codes: the constant is defined (line 17) but never referenced anywhere else, _reset_codes maps username->code only with no timestamp (line 88), and reset_password (line 94) only checks code equality with no expiry logic anywhere in the file or codebase. Executed a reproduction script calling request_password_reset then reset_password after a delay with no time-based invalidation in between — the reset succeeded, confirming codes never expire.*

## 3. [MAJOR] RESET_CODE_TTL_MINUTES is defined but never enforced

`ledgerly/auth.py:17` — correctness

The constant RESET_CODE_TTL_MINUTES = 15 (line 17) declares that reset codes should expire after 15 minutes, matching the pattern used for session tokens (TOKEN_TTL_HOURS, enforced in authenticate()). However, request_password_reset() (lines 82-89) stores only the code in _reset_codes[username] with no timestamp, and reset_password() (lines 92-103) never checks any expiry — it only compares the code string. As a result, a reset code issued once remains valid indefinitely until a new one is requested or used, contradicting the TTL the code implies. Concretely: a user requests a reset code, doesn't use it, and it leaks (e.g. via a shared/observed inbox) a week later — an attacker can still use it to take over the account, since no expiry check ever rejects it.

*Verified: Read ledgerly/auth.py: request_password_reset() stores only `_reset_codes[username] = code` (no timestamp), and reset_password() only does `_reset_codes.get(username) != code` with no expiry check. Grep across the repo shows RESET_CODE_TTL_MINUTES and _reset_codes are referenced nowhere else. Ran a live reproduction instantiating auth.request_password_reset/reset_password with a fake DB: a code issued once was successfully consumed by reset_password with no time constraint enforced, confirming the code never expires regardless of the declared 15-minute TTL.*

## 4. [MAJOR] No test coverage for the new password-reset flow

`ledgerly/auth.py:82` — test-adequacy

request_password_reset() and reset_password() introduce new security-sensitive behavior (code issuance, code matching, password mutation) but tests/test_ledgerly.py has no tests referencing 'reset' at all. There is no coverage for the happy path, unknown-username handling, wrong-code rejection, short-new-password rejection, or the code being consumed (deleted) after a successful reset — so a regression in any of this logic (e.g. the TTL never being enforced, or the code not being invalidated) would not be caught by CI.

*Verified: Read ledgerly/auth.py in full and confirmed request_password_reset()/reset_password() are new (lines 82-103) with no TTL enforcement anywhere despite declaring RESET_CODE_TTL_MINUTES=15 (grep shows it's referenced only at its definition, never used). Ran grep -rn 'reset' on tests/test_ledgerly.py and it returned zero matches; listed all 16 test function names in the file (test_register_and_login, test_wrong_password, test_bad_token, etc.) and none relate to password reset.*
