# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Invite code reuse vulnerability - single code usable by unlimited users

`ledgerly/household.py:100` — security

The invites table schema includes a used_at field (db.py:96) to track single-use semantics, but accept_invite() never checks or updates it. Result: one invite code can be used by multiple different users to join a household. Failure scenario: Owner creates code 'ABC123'. User A accepts and joins. User B accepts the same code 'ABC123' and also joins, when only A should have been able to join. The test test_member_cannot_accept_twice only catches the same user accepting twice (prevented by existing membership check), not different users.

*Verified: Read household.py: accept_invite() only checks `_member_role(db, hid, user_id) is not None` (blocks the *same* user re-joining) but never queries or sets `used_at`. Confirmed `used_at` appears nowhere else in the codebase (grep across ledgerly/*.py only hits the schema definition in db.py). Executed a live repro: created a household as alice, generated one invite code, then had both bob and carol call accept_invite() with that same code — both succeeded and both appear as 'member' in members_of(), proving the same code is reusable by different users indefinitely.*

## 2. [MAJOR] used_at field never populated, allowing code reuse

`ledgerly/household.py:110` — correctness

The schema defines a used_at field (db.py line 96) to track when an invite is consumed, but accept_invite() never sets it. This allows the same invite code to be used multiple times: a user can accept the code, leave the household, and accept the same code again. The implementation should either UPDATE invites SET used_at = utcnow_iso() at line 110, or check that used_at IS NULL before accepting.

*Verified: Read ledgerly/household.py: accept_invite() only checks that the code exists and the user isn't already a member; it never reads or writes invites.used_at. grep confirms used_at (db.py:96) is not referenced anywhere else in the codebase. Reproduced with a live script: created household, invite code, accepted it as carol, had carol leave via remove_member, then accepted the same code again successfully (both calls returned the household id) — confirming the same invite code can be reused indefinitely, e.g. after a member leaves, contrary to the intent implied by the used_at column.*

## 3. [MAJOR] Insecure randomness for invite code generation

`ledgerly/household.py:91` — security

Uses random.randrange() instead of secrets module for generating security-sensitive invite codes. The same codebase (auth.py:36, auth.py:56) correctly uses secrets for tokens and salts. Invite codes are access-control credentials and must use cryptographically secure randomness. Failure scenario: predictable codes can be brute-forced or guessed to join households without authorization.

*Verified: Read ledgerly/household.py:91 — create_invite() generates codes via `random.randrange(16**6)`, i.e. Python's Mersenne Twister PRNG, not a CSPRNG. Confirmed the same codebase already uses `secrets` correctly for equivalent security tokens: auth.py:9 imports secrets, auth.py:36 uses secrets.token_hex(16) for password salts, auth.py:56 uses secrets.token_urlsafe(32) for session tokens — establishing this project's own standard for security-sensitive randomness.*

## 4. [MAJOR] Test avoids code-reuse scenario for different users

`tests/test_household.py:88` — test-adequacy

The test `test_member_cannot_accept_twice` (lines 88-93) uses the same user (carol) both times, thus testing only that a member cannot join their household twice. It deliberately avoids the critical scenario: whether different users can reuse the same invite code. The invites table schema includes a `used_at` field, indicating one-time-use codes were intended. This test gap fails to verify whether the same code can be accepted by multiple different users—a fundamental property of secure invite systems. Concrete failure scenario: User A accepts code X (succeeds), User B accepts code X (should fail if one-time-use, but the test never checks this).

*Verified: Read ledgerly/household.py: accept_invite() never checks or sets the invites.used_at column (grep for 'used_at' in household.py returns nothing), so invite codes never expire after use. Reproduced live: created household, invite code, had two different users (bob, dave) call accept_invite with the SAME code — both succeeded and became members (output: 'bob joins: 1', 'dave joins with SAME code: 1', members list shows both as members).*
