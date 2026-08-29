# Code review: Sliding session expiry via token refresh

> Adds refresh_token() so clients can extend a session without re-entering a password. Includes a test for the new endpoint.

**Verdict: request changes.** 1 blocking finding(s), 1 critical.

## 1. [CRITICAL] UPDATE statement missing WHERE clause updates every token in the table

`ledgerly/auth.py:70` — correctness

The UPDATE in refresh_token has no WHERE clause: `db.execute("UPDATE tokens SET expires_at = ?", (new_expiry...,))`. Since `tokens` is a table shared by all users' sessions (ledgerly/db.py:37-41), calling refresh_token for one user's token sets expires_at on EVERY row in the tokens table, including other users' unrelated sessions. In production, any single client hitting the refresh endpoint silently extends every other logged-in user's session expiry, defeating the TTL-based expiry mechanism entirely (a compromised/stale token elsewhere would also get renewed by an unrelated refresh call). The test only checks the return value equals the input token and never inspects other rows or calls authenticate on a second token, so it does not catch this.
