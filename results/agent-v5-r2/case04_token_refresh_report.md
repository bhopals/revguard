# Code review: Sliding session expiry via token refresh

> Adds refresh_token() so clients can extend a session without re-entering a password. Includes a test for the new endpoint.

**Verdict: request changes.** 2 blocking finding(s), 2 critical.

## 1. [CRITICAL] UPDATE tokens missing WHERE clause extends expiry of every session, not just the caller's

`ledgerly/auth.py:69` — security

refresh_token() runs `db.execute("UPDATE tokens SET expires_at = ?", (new_expiry,))` with no WHERE clause (compare authenticate()'s DELETE at line 85 and login()'s scoped INSERT, which properly target a single token). Because sqlite3 executes this exactly as written (ledgerly/db.py execute() is a thin passthrough), calling refresh_token() with any single valid token updates the `expires_at` column for EVERY row in the `tokens` table — i.e. every other user's active session is also extended by TOKEN_TTL_HOURS. This breaks session expiry as a security control: any authenticated user (or an attacker holding one valid token) can keep every other user's session (including sessions that should have expired, or belong to different accounts) alive indefinitely by periodically calling refresh_token. The included test only asserts the return value equals the input token and does not check that other tokens are unaffected, so it does not catch this. The fix is `UPDATE tokens SET expires_at = ? WHERE token = ?` scoped to the specific token.

*Verified: Read ledgerly/auth.py:65-73 and confirmed the UPDATE statement `UPDATE tokens SET expires_at = ?` has no WHERE clause, and db.py's execute() is a thin passthrough to sqlite3 with no implicit scoping. Reproduced the exploit: registered two users (alice, bob), logged both in to get distinct tokens with distinct expiries, then called auth.refresh_token(db, tok_alice) using only Alice's token. Bob's row (which Alice never touched) had its expires_at overwritten too — before: '2026-08-30T15:39:27+00:00', after: '2026-08-30T11:39:27' (identical to Alice's new expiry).*

## 2. [CRITICAL] test_refresh_token never verifies the update is scoped to the given token

`tests/test_ledgerly.py:60` — test-adequacy

auth.refresh_token executes `UPDATE tokens SET expires_at = ?` with no WHERE clause (ledgerly/auth.py:69-72), so it rewrites expires_at for every row in the tokens table, not just the caller's token. The test only creates a single token (via the `user` fixture's one login plus one more `auth.login` call... actually only one active token exists at test time), so a query that updates all rows is indistinguishable from one that updates just the target row. The test cannot fail even though the UPDATE statement is missing its WHERE clause, which would silently extend every other user's session on any refresh call in production.

*Verified: Read ledgerly/auth.py:65-73: refresh_token runs `UPDATE tokens SET expires_at = ?` with no WHERE clause. Reproduced live: registered/logged in two users (alice, bob), captured both tokens' expires_at, called auth.refresh_token(db, alice_token), then re-queried both rows — bob's expires_at changed identically to alice's, proving the UPDATE hits every row in the table.*
