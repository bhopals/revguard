# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 5 blocking finding(s), 1 critical.

## 1. [CRITICAL] Invite codes generated with non-cryptographic RNG and tiny keyspace

`ledgerly/household.py:91` — security

create_invite() derives the code from Python's `random` module (Mersenne Twister, seeded from OS entropy but not a CSPRNG) instead of `secrets`, which the codebase already uses for session tokens in auth.py (`secrets.token_urlsafe(32)`). Worse, the code is only 6 hex characters (`random.randrange(16 ** 6)`), i.e. 2^24 ≈ 16.7M possible values. Combined with accept_invite() having no rate limiting and the invite never expiring or being consumed (see used_at, never set), an attacker who knows/guesses a household exists can script accept_invite() with random 6-hex-char strings and, within a practically small number of attempts, join any household as a member — gaining access to that household's shared expenses and the ability to add/see financial data they were never authorized to see.

*Verified: Read ledgerly/household.py: create_invite() uses `random.randrange(16 ** 6)` (Mersenne Twister, not secrets) formatted as 6 hex chars, giving a keyspace of 16,777,216 (16**6=16777216, confirmed via python3). accept_invite() only checks `SELECT household_id FROM invites WHERE code = ?` and inserts membership — it never reads or sets `used_at`, and there is no expiry check, so invites are reusable i*

## 2. [MAJOR] accept_invite bypasses the household member cap enforced by add_member

`ledgerly/household.py:110` — correctness

add_member() (line 59) enforces MAX_MEMBERS=12 before inserting a new household_members row, but accept_invite() (lines 100-115) never checks this limit before its own INSERT at line 110-113. Since an owner can call create_invite() repeatedly (the code is never marked used — the invites.used_at column is written by no code path) and share the same or new codes, any number of users can call accept_invite() and join a household past the 12-member cap, silently dropping a guarantee the pre-existing add_member() path enforced. This also means a single invite code can be redeemed by unlimited distinct users indefinitely (only same-user re-acceptance is blocked via the 'already a member' check at line 108), since used_at is never set to mark the invite consumed.

*Verified: Read ledgerly/household.py: add_member() (lines 51-67) enforces MAX_MEMBERS=12 via a COUNT(*) check before inserting into household_members, but accept_invite() (lines 100-115) has no such check before its own INSERT. Grep for 'used_at' shows it's only referenced in the invites table schema (db.py) and never written anywhere in the codebase, so an invite is never marked consumed. Reproduced live: *

## 3. [MAJOR] Invite codes never expire or become single-use, unlike session tokens

`ledgerly/household.py:100` — security

accept_invite() only checks that the code exists in the invites table and that the caller isn't already a member; it never checks an expiry (auth.py's tokens table enforces TOKEN_TTL_HOURS and deletes expired tokens) and never marks the invite consumed even though the schema has a `used_at` column for exactly that purpose (ledgerly/db.py:96). As a result, a single 6-character code created once by an owner remains valid forever and can be redeemed by an unlimited number of distinct users indefinitely. This removes any time bound on brute-force guessing (finding above) and means a leaked/shared code (e.g. pasted in a group chat, screenshot) grants household access to anyone who finds it at any point in the future, with no way for the owner to revoke it short of manual DB access.

*Verified: Read household.py: accept_invite() only does a SELECT by code and a membership check; it never sets used_at or checks any expiry/created_at window, unlike auth.py tokens which enforce TOKEN_TTL_HOURS and reject expired rows. Confirmed via in-memory sqlite execution: created one invite code, then had 5 distinct newly-created users each call accept_invite() with the same code -- all 5 succeeded and *

## 4. [MAJOR] Test name implies single-use invite codes but never verifies it

`tests/test_household.py:88` — test-adequacy

The invites table adds a `used_at` column (ledgerly/db.py) suggesting invite codes are meant to be single-use, but accept_invite() never sets `used_at` or otherwise invalidates the code after use. test_member_cannot_accept_twice (lines 88-93) reuses the same code with the same user and expects HouseholdError, but that error actually comes from the pre-existing 'already a member' check in accept_invite (line 108-109 of household.py), not from any invite-exhaustion logic. No test exercises the real risk: the same code being redeemed by a second, different user after the first has already joined. As written, accept_invite would let unlimited distinct users join a household with one leaked/shared invite code, and the test suite gives no signal of this because the only 'reuse' test happens to hit an unrelated guard.

*Verified: Read household.py: create_invite/accept_invite never reference used_at (confirmed via grep -n 'used_at' ledgerly/*.py, only hit is the schema column in db.py). Reproduced with a live script: created a household, issued one invite code, and had two distinct users (bob, carol) each successfully call accept_invite with the identical code — both joined with no error, household ended up with 3 members *

## 5. [MAJOR] No test that accept_invite respects the household member cap

`tests/test_household.py:73` — test-adequacy

add_member() enforces MAX_MEMBERS (household.py:59-60), but the new accept_invite() path (household.py:100-115) performs no such check, letting a household exceed MAX_MEMBERS when members join via invite code. The TestInvites class adds no test covering a household at capacity, so this behavioral gap between the two join paths ships without any test coverage that would catch a full household silently accepting more members through an invite.

*Verified: Read ledgerly/household.py: add_member() checks `count >= MAX_MEMBERS` (line 59) before inserting, but accept_invite() (lines 100-115) has no such check. Grepped the whole codebase for MAX_MEMBERS and it appears only twice, both in add_member's definition/check — confirming no safeguard exists on the invite path. Wrote and ran a reproduction script: filled a household to MAX_MEMBERS=12 via add_mem*
