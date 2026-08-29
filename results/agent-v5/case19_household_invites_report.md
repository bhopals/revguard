# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] accept_invite bypasses the MAX_MEMBERS household cap

`ledgerly/household.py:100` — correctness

add_member() enforces a hard cap of MAX_MEMBERS (12) members per household (household.py:59), but accept_invite() (household.py:100-115) never checks this limit before inserting into household_members. An owner who creates an invite code and shares it publicly (or many owners doing so) can have an unbounded number of users join via accept_invite, silently bypassing the size guarantee that add_member enforces. This is a regression of an existing invariant: the household is supposed to be capped at 12 members, but the new invite path has no equivalent check.

*Verified: Read household.py: add_member() (lines 51-67) checks `count >= MAX_MEMBERS` before inserting into household_members, but accept_invite() (lines 100-115) performs only an invite-code-exists check and an already-a-member check, with no count/cap check before its INSERT. Reproduced with execution: filled a household to 12 members via add_member (correctly blocked with 'household is full' on the 12th add), then created an invite code and looped accept_invite() 20 more times — all succeeded, growing the household to 32 members with the cap completely bypassed. Existing test suite (13 tests) still passes, confirming this gap is unguarded elsewhere.*

## 2. [MAJOR] Invite codes generated with non-cryptographic PRNG

`ledgerly/household.py:91` — security

create_invite() uses `random.randrange(16 ** 6)` to generate the invite code that grants household membership. Python's `random` module is a Mersenne Twister PRNG, not a CSPRNG: it is not suitable for generating security tokens. If an attacker can observe a sequence of generated codes (e.g. via other invites in the same process), they can potentially reconstruct the PRNG state and predict future invite codes, letting them join households they were never invited to. This should use `secrets.token_hex()` / `secrets.randbelow()` instead of `random`.

*Verified: Read ledgerly/household.py:87-97; confirmed create_invite() uses `code = "%06x" % random.randrange(16 ** 6)` with `import random` (Mersenne Twister, not a CSPRNG) to generate the household invite code, which is the sole credential checked in accept_invite() to grant membership (household.py:100-115) — no signature, expiry, or other binding. Grepped the codebase and found no use of `secrets` in household.py, while ledgerly/auth.py in the same PR-adjacent codebase already uses `secrets.token_hex`/`secrets.token_urlsafe` for salts and session tokens, showing the project has an established secure-token convention that create_invite() fails to follow.*

## 3. [MAJOR] test_member_cannot_accept_twice does not test single-use invite codes

`tests/test_household.py:88` — test-adequacy

The test reuses the same accepting user (carol) both times, so the second accept_invite call fails only because of the pre-existing 'already a member' check in accept_invite (household.py:108-109), not because the invite code itself was consumed. The invites table has a `used_at` column (db.py) implying invites are meant to be single-use, but accept_invite never sets used_at, so the same code can be redeemed by any number of distinct users indefinitely. A test that had a second, different user (e.g. a freshly registered user) attempt to accept the same already-used code would successfully join and expose this bug, but no such test exists. The current test's name promises 'cannot accept twice' but only verifies duplicate-membership rejection for a single user, giving false confidence that invite codes are properly single-use.

*Verified: Read ledgerly/household.py: accept_invite() never updates the invites.used_at column and never checks whether an invite was already used — it only checks whether the accepting user is already a household member. Grepped the codebase for 'used_at' and found it referenced only in the db.py schema, never read or written anywhere in household.py. Reproduced with a live script: created a household+invite as alice, had carol accept it (succeeds), then had a distinct third user 'dave' accept the exact same code — this also succeeded and dave was inserted as a household member, proving the code is reusable indefinitely by different users rather than single-use.*
