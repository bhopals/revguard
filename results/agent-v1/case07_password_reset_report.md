# Code review: Password reset codes

> Adds a two-step password reset flow: request_password_reset() issues a 6-digit code (delivery handled by the caller, e.g. email), and reset_password() sets a new password when the code matches.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] Reset codes never expire despite RESET_CODE_TTL_MINUTES constant

`ledgerly/auth.py:88` — correctness

RESET_CODE_TTL_MINUTES=15 is defined (line 17) but no timestamp is ever stored or checked. _reset_codes[username] = code (line 88) stores only the code, and reset_password() (line 94) only compares the code with no expiry check. A code issued days ago remains valid forever until the user requests a new one, contradicting the intended 15-minute window and giving an attacker who obtains/guesses a leaked code an unbounded window to use it (e.g. via a leaked email, shoulder-surfing, or log exposure).

## 2. [MAJOR] No rate limiting or attempt cap on reset code verification

`ledgerly/auth.py:94` — security

reset_password() (line 94) performs an unlimited number of comparisons of the submitted code against _reset_codes.get(username) with no lockout, delay, or attempt counter. Combined with the 6-digit code space (900,000 possibilities) and the missing TTL enforcement (see other finding), an attacker can brute-force a user's reset code with repeated calls to reset_password and take over the account without ever needing the emailed code.
