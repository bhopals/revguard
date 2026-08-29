# Code review: Sliding session expiry via token refresh

> Adds refresh_token() so clients can extend a session without re-entering a password. Includes a test for the new endpoint.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] UPDATE tokens missing WHERE clause updates every session in the table

`ledgerly/auth.py:69` — correctness

The UPDATE statement `UPDATE tokens SET expires_at = ?` has no WHERE token = ? clause, so calling refresh_token() for one user's token extends the expires_at of every token row in the tokens table for every logged-in user. Concretely: user A logs in (token A, expiry T+24h), user B logs in (token B, expiry T+24h). If A calls refresh_token(db, tokenA), B's token expiry is also silently reset to now+24h, and this happens on every refresh call by any user. The single-user test (test_refresh_token) only ever has one row in the tokens table, so it cannot detect this — with two or more concurrent sessions the bug corrupts other users' session expiry, defeating expiry-based session invalidation entirely.

*Verified: Read ledgerly/auth.py lines 65-73: refresh_token() executes `UPDATE tokens SET expires_at = ?` with only one bound parameter and no WHERE clause. Reproduced with python3 -c script: registered alice and bob, logged both in (two distinct token rows with distinct expires_at), called auth.refresh_token(db, tokenA), then re-queried both rows. Bob's (untouched user's) expires_at changed from '2026-08-30T14:40:44+00:00' to '2026-08-30T10:40:44', identical to Alice's new expiry — proving the UPDATE hits every row in the tokens table, not just the refreshed token.*

## 2. [MAJOR] test_refresh_token asserts a tautology and misses the missing-WHERE-clause bug

`tests/test_ledgerly.py:60` — test-adequacy

refresh_token() (ledgerly/auth.py:65-73) always returns the `token` argument it was passed, unconditionally, regardless of what the UPDATE statement did or whether it succeeded. So `auth.refresh_token(db, token) == token` on line 60 is true by construction and can never fail, no matter how the UPDATE is written. In particular, the underlying UPDATE query has no WHERE clause (`UPDATE tokens SET expires_at = ?` at ledgerly/auth.py:70) and therefore rewrites the expiry of every row in the tokens table, not just the caller's token — a single-user, single-token test setup can never expose this because there is only one row in the table. The test does not query the database to verify the new expires_at value on the refreshed token, nor does it create a second user/token to confirm that unrelated sessions are left untouched, so it exercises none of the behavior the docstring promises ('Extend a valid session token's lifetime') and would still pass if refresh_token expired every other user's session as a side effect.

*Verified: Read ledgerly/auth.py:65-73: refresh_token() calls authenticate() then unconditionally executes 'UPDATE tokens SET expires_at = ?' (no WHERE clause) and always `return token` regardless of the UPDATE's outcome. Read tests/test_ledgerly.py:58-60: the sole test only asserts `auth.refresh_token(db, token) == token`, which is true by construction since the function always returns its argument.*
