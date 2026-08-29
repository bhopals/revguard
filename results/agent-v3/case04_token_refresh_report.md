# Code review: Sliding session expiry via token refresh

> Adds refresh_token() so clients can extend a session without re-entering a password. Includes a test for the new endpoint.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] UPDATE statement missing WHERE clause updates every token in the table

`ledgerly/auth.py:70` — correctness

The UPDATE in refresh_token has no WHERE clause, so `db.execute("UPDATE tokens SET expires_at = ?", (new_expiry,))` sets expires_at for every row in the tokens table, not just the token being refreshed. Concrete scenario: user A logs in (token_a expires in 24h), user B logs in later (token_b expires in 24h + delta). If user A calls refresh_token, every session in the system — including user B's and any other logged-in user's — gets its expiry overwritten to A's new refresh time. This silently extends (or in other orderings, could shorten) other users' sessions and defeats per-session expiry entirely. The statement should be `"UPDATE tokens SET expires_at = ? WHERE token = ?"` with token bound as a parameter.

*Verified: Read ledgerly/auth.py:65-73, confirmed the diff exactly: refresh_token() runs `db.execute("UPDATE tokens SET expires_at = ?", (new_expiry,))` with no WHERE clause. Wrote a reproduction script registering two users (alice, bob), logging both in to create two token rows, then calling auth.refresh_token(db, token_a). Query of the tokens table before/after showed both token_a's AND token_b's expires_a*

## 2. [MAJOR] New test only checks a tautological return value, never verifies the refresh side effect

`tests/test_ledgerly.py:60` — test-adequacy

refresh_token() always returns the token argument unconditionally (ledgerly/auth.py:73), regardless of whether the UPDATE statement matched any rows or whether the new expiry is even valid. The test `assert auth.refresh_token(db, token) == token` therefore cannot fail even if the UPDATE is a no-op, updates the wrong row, or corrupts the expiry. The test never queries the tokens table to check that expires_at actually advanced, and never calls auth.authenticate(db, token) afterward to confirm the token is still usable. This masks a real bug: refresh_token writes a naive datetime.now() (auth.py:68) into expires_at, while authenticate() (auth.py:83-84) compares it against an offset-aware datetime.now(timezone.utc), which raises TypeError on the very next authenticate call after a refresh — a failure this test would have caught had it re-authenticated.

*Verified: Read ledgerly/auth.py: refresh_token() (line 68) writes datetime.now() (naive) into expires_at, while authenticate() (line 84) compares against datetime.now(timezone.utc) (aware). Reproduced live: after auth.login -> auth.refresh_token -> auth.authenticate raises TypeError: can't compare offset-naive and offset-aware datetimes. Ran the actual new test (tests/test_ledgerly.py::TestAuth::test_refres*
