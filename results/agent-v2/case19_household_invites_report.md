# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 4 blocking finding(s), 0 critical.

## 1. [MAJOR] accept_invite bypasses the MAX_MEMBERS household size cap

`ledgerly/household.py:110` — correctness

add_member (household.py:55-59) enforces that a household cannot exceed MAX_MEMBERS (12) members, but accept_invite contains no equivalent count check before inserting into household_members at line 110-114. An owner can create_invite() once and share the code publicly (or an attacker who obtains a leaked code can accept it repeatedly with different user_ids); every distinct user_id that calls accept_invite with that code successfully joins, growing the household past the 12-member limit that is otherwise guaranteed everywhere else in this module. This silently drops a size guarantee the rest of the codebase (and balances()/settlement_plan() which iterate all members) relies on.

## 2. [MAJOR] Invite codes are never consumed, so a single code can be reused by unlimited distinct users

`ledgerly/household.py:100` — correctness

The invites table (db.py:91-97) has a used_at column clearly intended to mark a code as spent, but accept_invite never UPDATEs used_at (or otherwise invalidates the invite) after a successful join, and never checks it before honoring a code. The only reuse guard is the 'already a member' check at household.py:108, which only blocks the same user_id from accepting twice — it does nothing to stop a second, third, or Nth distinct user from accepting the exact same code indefinitely. The test suite only covers the same-user-twice case (test_member_cannot_accept_twice), so this gap is untested and the function's implicit contract (a shareable one-time invite) is not enforced at all: the code behaves as a permanent, unlimited-use household join link.

## 3. [MAJOR] Invite codes use insecure, small-keyspace randomness

`ledgerly/household.py:91` — security

create_invite() generates the code with `random.randrange(16 ** 6)`, using Python's `random` module (Mersenne Twister), which is not cryptographically secure and whose output can be predicted if internal state is inferred from other outputs. Additionally the keyspace is only 16^6 = 16,777,216 possibilities. Combined with the fact that codes never expire or become single-use (see accept_invite), an attacker can script repeated calls to accept_invite() with random 6-hex-char guesses and, given enough time/attempts, join an arbitrary household without ever seeing the real invite. This should use `secrets.token_hex`/`secrets.choice` and a materially larger code space.

## 4. [MAJOR] Test name implies invite single-use is enforced, but it only exercises the pre-existing 'already a member' guard

`tests/test_household.py:88` — test-adequacy

test_member_cannot_accept_twice (tests/test_household.py:88-93) reuses the same code with the SAME user (carol) twice. The second call raises HouseholdError, but only because accept_invite's pre-existing `_member_role(...) is not None` check (household.py:108-109) rejects carol as an already-existing member — not because the invite code itself was consumed. accept_invite never writes to the `used_at` column added in db.py:96, so the invites row is never marked used. No test calls accept_invite with the same code and a DIFFERENT second user (e.g. bob) after carol already joined; that call would succeed silently, letting one invite code be redeemed by an unbounded number of distinct users forever. The test suite gives false confidence that invites are single-use when the schema's used_at column (clearly intended for that purpose) is dead code, and the actual security-relevant reuse scenario is completely unverified.
