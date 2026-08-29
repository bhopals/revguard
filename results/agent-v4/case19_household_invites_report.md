# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 5 blocking finding(s), 2 critical.

## 1. [CRITICAL] Invite code generated with non-cryptographic RNG

`ledgerly/household.py:91` — security

create_invite() uses random.randrange (Python's Mersenne Twister, not cryptographically secure) to generate the invite code, which functions as a bearer credential granting household membership. Mersenne Twister output is predictable if an attacker observes enough outputs, and even without that, the codespace is only 16^6 = 16,777,216 possibilities with no rate limiting on accept_invite(). An attacker can script repeated calls to accept_invite() with random/sequential 6-hex-digit codes and, within a feasible number of attempts, join arbitrary households (gaining access to their shared expenses and member list). This should use the `secrets` module (e.g. secrets.token_hex) with a materially larger code space.

*Verified: Read ledgerly/household.py: create_invite() (line 91 area) generates the invite code via random.randrange(16**6) (stdlib random, Mersenne Twister, explicitly documented as not suitable for security use), giving a codespace of 16,777,216. accept_invite() (and the rest of the codebase, confirmed via grep for rate/limit/throttle/lockout/attempt across ledgerly/) has no rate limiting, attempt counting, or lockout of any kind.*

## 2. [CRITICAL] Invite codes never expire and are never invalidated after use

`ledgerly/household.py:100` — security

The invites table has a used_at column but accept_invite() (lines 100-115) never checks it or sets it, and there is no created_at/expiry check either. This means a single invite code created by an owner remains valid forever and can be redeemed by an unlimited number of different users at any time in the future — not just the one person the owner intended to invite. Combined with the small, guessable codespace (line 91), this turns invite codes into a permanent, brute-forceable backdoor into any household: once a code is guessed or leaked once, it keeps working for every subsequent attacker, and the owner has no way to revoke it. accept_invite() should mark the invite as used (UPDATE invites SET used_at = ? WHERE code = ?) and reject already-used or expired codes.

*Verified: Read ledgerly/household.py accept_invite()/create_invite() (lines 90-115): the invites row is only SELECTed by code, never UPDATEd, and used_at/created_at are never checked. Ran a live repro: created a household+invite as alice, then had bob accept the invite, then had carol accept the SAME code afterward — both succeeded and both appear as members. Grepped ledgerly/*.py for 'used_at'/'expir' and found no expiry/consumption logic anywhere outside auth tokens; invites.used_at is written to schema but never referenced in code.*

## 3. [MAJOR] accept_invite bypasses the household member cap enforced by add_member

`ledgerly/household.py:108` — correctness

add_member() enforces MAX_MEMBERS=12 (household.py:59) before inserting a new household_members row, but accept_invite() (household.py:100-115) performs the same insert without any count check. Since accept_invite is just another path to add a member, any owner can create_invite() and share the code with unlimited people; each accept_invite() call only checks that the accepting user isn't already a member, never that the household is full. This silently drops the size cap the PR's own sibling function enforces, letting a household grow past 12 members via invites.

*Verified: Read household.py: add_member() (lines 51-67) enforces MAX_MEMBERS=12 via a COUNT(*) check before insert, but accept_invite() (lines 100-115) only checks _member_role() for the accepting user and never checks household size before inserting into household_members. Reproduced with a live script: created a household, then looped creating invites and accepting them for 20 new users — final household_members count reached 21, exceeding MAX_MEMBERS=12, with no HouseholdError raised. Existing test suite (13 tests, all passing) has no test exercising this cap-via-invite path, confirming it's an unguarded gap.*

## 4. [MAJOR] test_member_cannot_accept_twice does not test invite-code reuse

`tests/test_household.py:88` — test-adequacy

The test name and the `used_at` column added in db.py (ledgerly/db.py:93) imply invite codes are meant to be single-use, but accept_invite() (ledgerly/household.py:100-115) never writes to used_at or otherwise invalidates the code after use. The test only re-invokes accept_invite with the *same* user (carol), which raises HouseholdError purely because carol is already a member (household.py:108-109) — a check that exists independently of any invite-consumption logic. It never exercises a second, different user attempting to redeem the already-used code. As written, this test would still pass even if create_invite/accept_invite allowed the same code to be used by unlimited different users, so it gives no coverage of the intended single-use guarantee and would not catch a regression (or the current absence of that guarantee) where one invite code lets an unbounded number of distinct users join.

*Verified: Read ledgerly/household.py: accept_invite() never writes used_at or otherwise invalidates the invite row after use; grep confirms used_at is referenced only in the db.py schema, nowhere else in ledgerly/ or tests/. Reproduced with a live script: created an invite code, had carol accept it, then had a distinct user dave accept the SAME code successfully (both appear as members afterward) — proving unlimited distinct users can redeem one invite code.*

## 5. [MINOR] invites.used_at column is dead: never written, giving a false impression that codes are single-use

`ledgerly/db.py:96` — robustness

The invites table adds a `used_at TEXT` column suggesting invite codes are marked consumed after use, but neither create_invite() nor accept_invite() (ledgerly/household.py:87-115) ever sets it. Combined with the fact that accept_invite() never deletes or invalidates the row, a single invite code can be redeemed by an unlimited number of distinct users indefinitely (only the 'already a member' check stops the same user from reusing it twice). The unused column is misleading to future readers/maintainers who will assume single-use semantics are enforced, and the actual multi-use behavior is undocumented in both docstrings.

*Verified: Read ledgerly/household.py: create_invite() only inserts a row (code, household_id, created_by, created_at) and accept_invite() only checks existence and membership, then inserts into household_members — neither ever touches used_at nor deletes/invalidates the invites row. Grep confirms 'used_at' appears nowhere else in the codebase (only its column definition in db.py). Executed a reproduction: created a household, generated one invite code, and called accept_invite() with three different users (bob, carol, dave) — all three succeeded and joined the household using the same code, and the invites row's used_at remained None throughout.*
