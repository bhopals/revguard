# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case19_household_invites/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case19_household_invites/ledgerly/household.py"}
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
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case19_household_invites/tests/test_household.py"}
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

{"findings": [{"file": "tests/test_household.py", "line": 88, "category": "test-adequacy", "title": "test_member_cannot_accept_twice does not test invite-code reuse", "severity": "major", "description": "The test name and the `used_at` column added in db.py (ledgerly/db.py:93) imply invite codes are meant to be single-use, but accept_invite() (ledgerly/household.py:100-115) never writes to used_at or otherwise invalidates the code after use. The test only re-invokes accept_invite with the *same* user (carol), which raises HouseholdError purely because carol is already a member (household.py:108-109) — a check that exists independently of any invite-consumption logic. It never exercises a second, different user attempting to redeem the already-used code. As written, this test would still pass even if create_invite/accept_invite allowed the same code to be used by unlimited different users, so it gives no coverage of the intended single-use guarantee and would not catch a regression (or the current absence of that guarantee) where one invite code lets an unbounded number of distinct users join."}]}

---
**Final result** (3 turns, 23.3s, $0.062):

{"findings": [{"file": "tests/test_household.py", "line": 88, "category": "test-adequacy", "title": "test_member_cannot_accept_twice does not test invite-code reuse", "severity": "major", "description": "The test name and the `used_at` column added in db.py (ledgerly/db.py:93) imply invite codes are meant to be single-use, but accept_invite() (ledgerly/household.py:100-115) never writes to used_at or otherwise invalidates the code after use. The test only re-invokes accept_invite with the *same* user (carol), which raises HouseholdError purely because carol is already a member (household.py:108-109) — a check that exists independently of any invite-consumption logic. It never exercises a second, different user attempting to redeem the already-used code. As written, this test would still pass even if create_invite/accept_invite allowed the same code to be used by unlimited different users, so it gives no coverage of the intended single-use guarantee and would not catch a regression (or the current absence of that guarantee) where one invite code lets an unbounded number of distinct users join."}]}
