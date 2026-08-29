# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case19_household_invites/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case19_household_invites/ledgerly/household.py"}
```

**Tool result:**

```
1	"""Shared households: several users pooling expenses.
2	
3	A household has one owner and any number of members. Shared expenses are
4	paid by one member and split equally; settlement computes who owes whom.
5	All amounts are integer cents.
6	"""
7	
8	import random
9	
10	from .expenses import VALID_CATEGORIES, ExpenseError
11	from .utils import parse_iso_date, utcnow_iso
12	
13	MAX_MEMBERS = 12
14	
15	
16	class HouseholdError(Exception):
17	    pass
18	
19	
20	def create_household(db, owner_id, name):
21	    if not name.strip():
22	        raise HouseholdError("household name must not be empty")
23	    hid = db.execute(
24	        "INSERT INTO households (name, owner_id, created_at) VALUES (?, ?, ?)",
25	        (name.strip(), owner_id, utcnow_iso()),
26	    )
27	    db.execute(
28	      
… [6560 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case19_household_invites/tests/test_household.py"}
```

**Tool result:**

```
1	import pytest
2	
3	from ledgerly import household
4	
5	
6	@pytest.fixture()
7	def home(db, user, bob):
8	    hid = household.create_household(db, user, "Flat 4B")
9	    household.add_member(db, hid, user, bob)
10	    return hid
11	
12	
13	class TestMembership:
14	    def test_owner_is_member(self, db, user):
15	        hid = household.create_household(db, user, "Home")
16	        assert household.require_member(db, hid, user) == "owner"
17	
18	    def test_only_owner_adds(self, db, home, user, bob, carol):
19	        with pytest.raises(household.HouseholdError):
20	            household.add_member(db, home, bob, carol)
21	        household.add_member(db, home, user, carol)
22	        assert len(household.members_of(db, home)) == 3
23	
24	    def test_member_can_leave(self, db, home, bob)
… [3278 chars truncated]
```

**Assistant:**

{"findings": [{"file": "tests/test_household.py", "line": 88, "category": "test-adequacy", "title": "Test name implies single-use invite codes but never verifies it", "description": "The invites table adds a `used_at` column (ledgerly/db.py) suggesting invite codes are meant to be single-use, but accept_invite() never sets `used_at` or otherwise invalidates the code after use. test_member_cannot_accept_twice (lines 88-93) reuses the same code with the same user and expects HouseholdError, but that error actually comes from the pre-existing 'already a member' check in accept_invite (line 108-109 of household.py), not from any invite-exhaustion logic. No test exercises the real risk: the same code being redeemed by a second, different user after the first has already joined. As written, accept_invite would let unlimited distinct users join a household with one leaked/shared invite code, and the test suite gives no signal of this because the only 'reuse' test happens to hit an unrelated guard."}, {"file": "tests/test_household.py", "line": 73, "category": "test-adequacy", "title": "No test that accept_invite respects the household member cap", "description": "add_member() enforces MAX
… [424 chars truncated]

---
**Final result** (3 turns, 24.4s, $0.062):

{"findings": [{"file": "tests/test_household.py", "line": 88, "category": "test-adequacy", "title": "Test name implies single-use invite codes but never verifies it", "description": "The invites table adds a `used_at` column (ledgerly/db.py) suggesting invite codes are meant to be single-use, but accept_invite() never sets `used_at` or otherwise invalidates the code after use. test_member_cannot_accept_twice (lines 88-93) reuses the same code with the same user and expects HouseholdError, but that error actually comes from the pre-existing 'already a member' check in accept_invite (line 108-109 of household.py), not from any invite-exhaustion logic. No test exercises the real risk: the same code being redeemed by a second, different user after the first has already joined. As written, accept_invite would let unlimited distinct users join a household with one leaked/shared invite code, and the test suite gives no signal of this because the only 'reuse' test happens to hit an unrelated guard."}, {"file": "tests/test_household.py", "line": 73, "category": "test-adequacy", "title": "No test that accept_invite respects the household member cap", "description": "add_member() enforces MAX
… [424 chars truncated]
