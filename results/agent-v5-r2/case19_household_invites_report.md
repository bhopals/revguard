# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Invite codes generated with non-cryptographic PRNG

`ledgerly/household.py:91` — security

create_invite() uses Python's `random.randrange()` (Mersenne Twister, not a CSPRNG) to generate the 6-hex-digit invite code that grants household membership. The codebase's own auth.py uses `secrets.token_urlsafe(32)` for session tokens, showing this is the established secure pattern for credential-like values. `random`'s output is predictable once enough outputs are observed (Mersenne Twister state can be recovered from 624 consecutive 32-bit outputs) and is not suitable for security tokens. An attacker who can observe a sequence of previously issued invite codes (e.g. by creating throwaway households and repeatedly calling create_invite) could reconstruct the PRNG state and predict future invite codes for other households, allowing unauthorized self-invitation into households they were never invited to.

*Verified: Read ledgerly/household.py: create_invite() (line ~91) imports and uses `random.randrange(16**6)` to build the 6-hex invite code stored in invites.code, and accept_invite() grants household membership solely on presenting a matching code. Grepped ledgerly/*.py and confirmed auth.py uses `secrets.token_hex(16)` and `secrets.token_urlsafe(32)` for salts/session tokens — the established secure pattern in this codebase — while household.py instead does `import random` and uses the plain `random` module.*

## 2. [MAJOR] accept_invite never marks invite codes as used, so they never expire

`ledgerly/household.py:100` — correctness

The invites table has a `used_at` column (ledgerly/db.py:96) implying single-use invite codes, but accept_invite() (household.py:100-115) never sets it after a successful join. As a result, a single invite code remains valid indefinitely and can be accepted by an unlimited number of *different* users (the 'already a member' check at line 108 only blocks the same user from joining twice, not other users). A code shared once (e.g. pasted in a group chat) lets anyone who sees it join the household at any time in the future, and a removed member could rejoin later using an old code they saved. This contradicts the evident intent of the schema and the PR's framing of a 'shareable code' for onboarding specific invitees.

*Verified: Read household.py: accept_invite() never checks or sets invites.used_at, and only blocks the *same* user from joining twice via the household_members check (line 108), not other users. Reproduced live: created an invite code, had bob accept it, removed bob from the household, then had carol accept the *same* code (succeeded), then had bob rejoin using the *same* stale code after removal (succeeded). Queried invites.used_at afterward — still NULL. This is a genuine logic defect (missing single-use enforcement), not a test-coverage complaint; the existing test suite passes because it never exercises reuse by a different user or reuse after removal.*

## 3. [MAJOR] accept_invite bypasses the MAX_MEMBERS household size cap

`ledgerly/household.py:108` — correctness

add_member() enforces a 12-member cap via `if count >= MAX_MEMBERS: raise HouseholdError('household is full')` (household.py:59-60), but accept_invite() (lines 100-115) performs no such check before inserting into household_members. A household at capacity can still grow without bound: the owner (or anyone with a leaked/stale code, compounded by the missing used_at invalidation) can have arbitrarily many users call accept_invite() with the same code, each successfully joining regardless of household size. This silently drops a guarantee the existing add_member() path enforces.

*Verified: Read household.py: add_member() (lines 51-67) enforces MAX_MEMBERS=12 via a COUNT query and raises HouseholdError when full. accept_invite() (lines 100-115), added by this PR, only checks for invalid code and existing membership, with no count/cap check before INSERT into household_members. Reproduced via python3: created a household, filled it to exactly 12 members using add_member, verified add_member then correctly raises 'household is full' for a 13th member, then called accept_invite() with a still-valid invite code for 5 more distinct users — all 5 succeeded, growing household_members to 17 rows for that household_id, with no error raised.*

## 4. [MAJOR] test_member_cannot_accept_twice does not test invite-code single-use; masks that used_at is never set

`tests/test_household.py:88` — test-adequacy

The `invites` schema (ledgerly/db.py:96) has a `used_at` column implying invite codes are meant to be single-use/consumed, and `accept_invite` (ledgerly/household.py:100-115) never writes to `used_at` or otherwise invalidates a code after use — a code remains valid forever and can be redeemed by any number of distinct new users. The test named `test_member_cannot_accept_twice` (lines 88-93) calls `accept_invite` twice with the SAME code and the SAME user (carol); it only exercises the pre-existing 'already a member' check at household.py:108-109, which triggers regardless of whether the invite was ever consumed. It never calls `accept_invite(db, code, some_other_new_user)` to check whether a used code can be redeemed again by a different person — the actual scenario that would expose the missing `used_at` enforcement. As written, the test would pass identically even if invite codes were fully reusable across arbitrary users, so it gives false confidence that invites are single-use.

*Verified: Read household.py: create_invite/accept_invite never write or check `used_at` (grep confirms `used_at` appears only in the db.py schema, nowhere else in the codebase). Executed a repro script instantiating Database, registering alice/bob/dave, creating a household+invite, and calling accept_invite(code, bob) then accept_invite(code, dave): both succeeded and both appear as members, proving the same invite code is infinitely reusable across distinct new users.*
