# Code review: Household invite codes

> Owners can now invite people without knowing their user id: create_invite() issues a short shareable code, accept_invite() joins the caller to the household. Includes schema and tests.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] accept_invite bypasses the MAX_MEMBERS household cap

`ledgerly/household.py:108` — correctness

add_member() enforces a 12-member cap (household.py:59-60, 'household is full'), but accept_invite() never performs this check before inserting into household_members. A household owner can hand out (or a leaked/guessed) invite code and an unbounded number of users can join via accept_invite(), silently exceeding MAX_MEMBERS and breaking the invariant that add_member relies on and that balances()/settlement_plan() are presumably sized/tested around. No test exercises a household at capacity accepting an invite.

## 2. [MAJOR] Invite codes never expire or become single-use despite the used_at column

`ledgerly/household.py:102` — correctness

The invites table (db.py:91-97) has a used_at column, implying invites are meant to be consumed once, but accept_invite()'s SELECT (household.py:102-104) never filters on used_at and the INSERT at lines 110-114 never sets it. The only reuse guard is 'already a member' for the *same* user (household.py:108-109). Any number of different users can call accept_invite with the same code indefinitely, and the code never expires. A once-shared invite code (e.g., pasted in a group chat) grants permanent, unlimited join access to the household with no way for the owner to revoke it, and this behavior is neither tested nor documented as intended.

## 3. [MAJOR] Invite codes generated with non-cryptographic PRNG and small keyspace

`ledgerly/household.py:91` — security

create_invite() uses `random.randrange(16 ** 6)` to build a 6-hex-character code — Python's `random` module is not cryptographically secure and is unsuitable for generating access tokens. Combined with the finding that codes never expire or become single-use (household.py:102-114), an attacker who can make repeated accept_invite() calls only needs to search a 16.7M-value keyspace (or predict the PRNG state) to join an arbitrary household without authorization. This should use `secrets.token_hex()` or similar with a larger keyspace.
