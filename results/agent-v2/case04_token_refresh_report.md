# Code review: Sliding session expiry via token refresh

> Adds refresh_token() so clients can extend a session without re-entering a password. Includes a test for the new endpoint.

**Verdict: request changes.** 2 blocking finding(s), 1 critical.

## 1. [CRITICAL] UPDATE statement missing WHERE clause updates every token in the table

`ledgerly/auth.py:70` — correctness

The UPDATE at line 70 has no WHERE clause, so `db.execute("UPDATE tokens SET expires_at = ?", (new_expiry...,))` sets expires_at for every row in the tokens table, not just the token being refreshed. Concrete scenario: user A logs in, then user B logs in (both rows in tokens), then user A calls refresh_token — user B's session expiry also gets overwritten to user A's new expiry. This silently extends (or in other orderings, shortens) other users' sessions as a side effect of one user's refresh call, corrupting session expiry semantics for the whole system.

## 2. [?] New test never verifies the refresh side effect, missing the unscoped UPDATE bug

`tests/test_ledgerly.py:60` — test-adequacy

test_refresh_token only asserts `auth.refresh_token(db, token) == token`, but refresh_token(auth.py:73) always returns the `token` argument unconditionally regardless of what happened in the DB, so this assertion is a tautology that cannot fail. The test never queries the tokens table to check that expires_at was actually extended, and critically never creates a second token/user to detect that the UPDATE statement at auth.py:70 has no WHERE clause and updates every row in the tokens table (silently extending every logged-in user's session whenever any one user refreshes). Because the test fixture only ever has a single token in existence, this severe scoping bug passes CI undetected.
