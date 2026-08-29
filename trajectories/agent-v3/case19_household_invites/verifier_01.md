# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case19_household_invites/verifier_01.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Bash**

```json
{"command": "cat -n ledgerly/household.py | sed -n '1,130p'"}
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
    24	        "INSERT INTO households (name, owner_id, created_at) VA
… [4658 chars truncated]
```

**Assistant:**

The code confirms the claim exactly: `add_member` checks `count >= MAX_MEMBERS` (lines 58-60) but `accept_invite` (lines 100-115) has no such check, and no code path anywhere sets `used_at`. Let me verify by reproduction with actual test fixtures.

**Tool call → Bash**

```json
{"command": "grep -rn \"used_at\" ledgerly/ ; echo \"---conftest---\"; cat tests/conftest.py 2>/dev/null | head -60"}
```

**Tool result:**

```
ledgerly/db.py:96:    used_at TEXT
---conftest---
import pytest

from ledgerly.db import Database
from ledgerly import auth


@pytest.fixture()
def db():
    d = Database()
    yield d
    d.close()


@pytest.fixture()
def user(db):
    return auth.register(db, "alice", "s3cretpass")


@pytest.fixture()
def bob(db):
    return auth.register(db, "bob", "bobspassword")


@pytest.fixture()
def carol(db):
    return auth.register(db, "carol", "carolspassword")
```

**Assistant:**

`used_at` is indeed never written anywhere except the schema. Now let's write a concrete reproduction script proving the cap bypass.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, household\n\ndb = Database()\nowner = auth.register(db, 'owner', 'ownerpassword')\nhid = household.create_household(db, owner, 'Flat')\n\ncode = household.create_invite(db, hid, owner)\n\nusers = []\nfor i in range(20):\n    u = auth.register(db, f'user{i}', f'password{i}')\n    users.append(u)\n    household.accept_invite(db, code, u)\n\ncount = db.query_one('SELECT COUNT(*) AS n FROM household_members WHERE household_id = ?', (hid,))['n']\nprint('member count:', count, '(cap is', household.MAX_MEMBERS, '
… [205 chars truncated]
```

**Tool result:**

```
member count: 21 (cap is 12 )
used_at: None
```

**Assistant:**

Reproduction confirms both parts of the claim: the household grew to 21 members (well past the `MAX_MEMBERS=12` cap enforced only in `add_member`), and `used_at` remains `NULL` after 20 redemptions of the same code by distinct users, so the same invite is reusable indefinitely by new users.

**Tool call → Bash**

```json
{"command": "python3 -m pytest tests/test_household.py -q 2>&1 | tail -20"}
```

**Tool result:**

```
.............                                                            [100%]
13 passed in 2.37s
```

**Assistant:**

Existing tests pass and don't cover this gap, consistent with the finding. Verdict confirmed.

**Tool call → Bash**

```json
{"command": "true"}
```

**Tool result:**

```
(Bash completed with no output)
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/household.py: add_member() (lines 51-67) enforces MAX_MEMBERS=12 via a COUNT(*) check before inserting into household_members, but accept_invite() (lines 100-115) has no such check before its own INSERT. Grep for 'used_at' shows it's only referenced in the invites table schema (db.py) and never written anywhere in the codebase, so an invite is never marked consumed. Reproduced live: created a household with 1 owner, generated one invite code, then had 20 distinct newly-registered users call accept_invite() with that same code in a loop — all 20 succeeded, growing the household to 21 members (vs. the 12-member cap), and invites.used_at remained NULL throughout. Full test suite (tests/test_household.py) still passes, confirming this gap isn't caught by existing tests.", "adjusted_severity": "major"}

---
**Final result** (6 turns, 24.0s, $0.066):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/household.py: add_member() (lines 51-67) enforces MAX_MEMBERS=12 via a COUNT(*) check before inserting into household_members, but accept_invite() (lines 100-115) has no such check before its own INSERT. Grep for 'used_at' shows it's only referenced in the invites table schema (db.py) and never written anywhere in the codebase, so an invite is never marked consumed. Reproduced live: created a household with 1 owner, generated one invite code, then had 20 distinct newly-registered users call accept_invite() with that same code in a loop — all 20 succeeded, growing the household to 21 members (vs. the 12-member cap), and invites.used_at remained NULL throughout. Full test suite (tests/test_household.py) still passes, confirming this gap isn't caught by existing tests.", "adjusted_severity": "major"}
