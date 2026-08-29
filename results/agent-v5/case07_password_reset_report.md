# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] Reset code generated with non-cryptographic RNG

`ledgerly/auth.py:87` — security

request_password_reset() uses random.randint(100000, 999999) (Mersenne Twister, not cryptographically secure) to generate the reset code, while the rest of the module (secrets.token_hex, secrets.token_urlsafe) correctly uses the `secrets` module. random's internal state can be recovered from a handful of outputs and its output is predictable, letting an attacker who observes other random-derived values (or brute-forces the 32-bit MT19937 state via other leaked outputs) predict or narrow down reset codes for arbitrary usernames, enabling account takeover without ever receiving the emailed code.

*Verified: Read ledgerly/auth.py lines 82-89: request_password_reset() generates the 6-digit reset code via `random.randint(100000, 999999)` (stdlib `random`, backed by MT19937), while every other credential in the same module (session tokens, salts) uses `secrets.token_hex`/`secrets.token_urlsafe`. Grepped the package and confirmed this is the only use of `random.` anywhere in ledgerly/. Verified via `python3 -c` that `random`'s internal generator state is fully deterministic/observable (getstate() exposes the MT19937 state vector), consistent with the well-documented fact that MT19937 outputs are predictable/invertible given enough samples — it is not appropriate for security-sensitive tokens.*

## 2. [CRITICAL] RESET_CODE_TTL_MINUTES defined but never enforced

`ledgerly/auth.py:17` — security

RESET_CODE_TTL_MINUTES is declared but reset_password() never checks any timestamp against it; _reset_codes only stores {username: code} with no issued-at time. A reset code therefore remains valid indefinitely until overwritten by a new request or consumed, contradicting the declared 15-minute TTL and letting an attacker who obtains an old/leaked code (e.g. from logs, a shared inbox, or a shoulder-surf) use it to take over the account long after it should have expired.

*Verified: Read ledgerly/auth.py: RESET_CODE_TTL_MINUTES (line 17) is declared but grep shows it is referenced nowhere else in the repo. _reset_codes only stores {username: code} (line 88) with no issued-at timestamp, and reset_password() (lines 92-103) only does a string comparison of the code with no time check. Executed a reproduction: issued a reset code via request_password_reset, then called reset_password successfully with no time-based rejection possible since no timestamp is ever stored or checked — the code remains valid until overwritten or consumed, confirming indefinite validity contradicting the declared 15-minute TTL.*

## 3. [MAJOR] Password reset does not invalidate existing session tokens

`ledgerly/auth.py:103` — robustness

`reset_password` updates `password_hash`/`salt` in the `users` table (lines 99-102) but never touches the `tokens` table. Any token previously issued via `login()` remains valid and `authenticate()` (lines 69-80) will continue to accept it after the password has been reset, since `authenticate` only checks token existence/expiry, not password freshness. Concrete scenario: an attacker who has stolen a valid session token keeps full access even after the legitimate user notices the compromise and resets their password via this new flow — the reset provides no actual guarantee of terminating existing sessions, undermining the intended security purpose of a password-reset feature.

*Verified: Read ledgerly/auth.py: reset_password (lines 92-103) only updates users.password_hash/salt and deletes the in-memory reset code; it never touches the tokens table. grep confirms the only 'DELETE FROM tokens' in the codebase is the expiry-cleanup in authenticate(), not in reset_password. Reproduced end-to-end with sqlite Database: registered a user, logged in to obtain a token, confirmed authenticate() succeeds, called request_password_reset + reset_password to change the password, then called authenticate() again with the old token — it still succeeded and returned the same user_id, proving a stolen token remains valid after password reset.*

## 4. [MINOR] Reset code compared with non-constant-time equality

`ledgerly/auth.py:94` — security

reset_password() compares the stored code to the caller-supplied code with `_reset_codes.get(username) != code`, a plain string comparison that short-circuits on the first differing character. Unlike login(), which uses hmac.compare_digest for the password hash comparison, this leaks timing information proportional to the number of correct leading digits, allowing an attacker to incrementally brute-force the 6-digit code via a timing side-channel.

*Verified: Read ledgerly/auth.py: line 94 `if _reset_codes.get(username) != code:` uses plain string inequality, while login() at line 58 uses `hmac.compare_digest(expected, actual)` for the analogous secret comparison — confirming the described inconsistency exists in this exact PR's code. Grep across the repo shows no rate-limiting or other mitigation for reset attempts. This is a factual, code-level defect (not a missing-test complaint), and it directly contradicts the file's own documented security posture ('compared in constant time' per the module docstring).*
