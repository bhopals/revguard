# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v5-r2/case19_household_invites/verifier_03.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Bash**

```json
{"command": "find . -name \"conftest.py\" -o -name \"household.py\" | head -20"}
```

**Tool call → Bash**

```json
{"command": "sed -n '1,200p' ledgerly/household.py"}
```

**Tool result:**

```
"""Shared households: several users pooling expenses.

A household has one owner and any number of members. Shared expenses are
paid by one member and split equally; settlement computes who owes whom.
All amounts are integer cents.
"""

import random

from .expenses import VALID_CATEGORIES, ExpenseError
from .utils import parse_iso_date, utcnow_iso

MAX_MEMBERS = 12


class HouseholdError(Exception):
    pass


def create_household(db, owner_id, name):
    if not name.strip():
        raise HouseholdError("household name must not be empty")
    hid = db.execute(
        "INSERT INTO households (name, owner_id, created_at) VALUES (?, ?, ?)",
        (name.strip(), owner_id, utcnow_iso()),
    )
    db.execute(
        "INSERT INTO household_members (household_id, user_id, role, joined_at)"

… [5879 chars truncated]
```

**Tool result:**

```
./tests/conftest.py
./ledgerly/household.py
```

**Tool call → Bash**

```json
{"command": "sed -n '1,40p' tests/conftest.py"}
```

**Tool result:**

```
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

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, household\n\ndb = Database()\nalice = auth.register(db, 'alice', 'password123')\nbob = auth.register(db, 'bob', 'password123')\ndave = auth.register(db, 'dave', 'password123')\n\nhid = household.create_household(db, alice, 'Flat')\ncode = household.create_invite(db, hid, alice)\nhousehold.accept_invite(db, code, bob)\nprint('bob joined, members:', household.members_of(db, hid))\n\n# now try same code with a brand new distinct user\nhousehold.accept_invite(db, code, dave)\nprint('dave joined too! members:',
… [97 chars truncated]
```

**Tool result:**

```
bob joined, members: [{'user_id': 1, 'role': 'owner'}, {'user_id': 2, 'role': 'member'}]
dave joined too! members: [{'user_id': 1, 'role': 'owner'}, {'user_id': 2, 'role': 'member'}, {'user_id': 3, 'role': 'member'}]
INVITE CODE WAS REUSABLE ACROSS DIFFERENT USERS
```

**Tool call → Bash**

```json
{"command": "grep -n \"test_member_cannot_accept_twice\" -A5 tests/test_household.py"}
```

**Tool result:**

```
88:    def test_member_cannot_accept_twice(self, db, user, carol):
89-        hid = household.create_household(db, user, "Flat")
90-        code = household.create_invite(db, hid, user)
91-        household.accept_invite(db, code, carol)
92-        with pytest.raises(household.HouseholdError):
93-            household.accept_invite(db, code, carol)
```

**Assistant:**

Confirmed via execution: `accept_invite` never touches `used_at`, so the same invite code can be redeemed by unlimited distinct new users indefinitely (demonstrated: bob and then dave both joined using the identical code). The test at line 88, despite being named `test_member_cannot_accept_twice`, only re-invokes `accept_invite` with the same user twice, which trips the unrelated "already a member" guard rather than any single-use enforcement — it would pass identically even if the invite system were fully reusable across arbitrary users.

This satisfies the "test whose name/structure promises a check it does not perform" exception to the test-adequacy policy gate, and the underlying functional defect (invite codes never invalidated) is real and independently confirmed.

**Tool call → Bash**

```json
{"command": "grep -n \"used_at\" ledgerly/household.py ledgerly/db.py tests/test_household.py"}
```

**Tool result:**

```
ledgerly/db.py:96:    used_at TEXT
```

**Assistant:**

`used_at` is set nowhere outside the schema definition, confirming it's dead/unused.

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read household.py: create_invite/accept_invite never write or check `used_at` (grep confirms `used_at` appears only in the db.py schema, nowhere else in the codebase). Executed a repro script instantiating Database, registering alice/bob/dave, creating a household+invite, and calling accept_invite(code, bob) then accept_invite(code, dave): both succeeded and both appear as members, proving the same invite code is infinitely reusable across distinct new users. Read tests/test_household.py:88-93: test_member_cannot_accept_twice calls accept_invite twice with the SAME user (carol), which raises HouseholdError via the unrelated 'already a member' check at household.py:108-109 -- not via any single-use/used_at check. The test would pass unchanged even if invite codes were fully reusable, exactly as claimed, and its name promises a single-use check it doesn't perform.", "adjusted_severity": "major"}

---
**Final result** (7 turns, 36.1s, $0.085):

`used_at` is set nowhere outside the schema definition, confirming it's dead/unused.

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read household.py: create_invite/accept_invite never write or check `used_at` (grep confirms `used_at` appears only in the db.py schema, nowhere else in the codebase). Executed a repro script instantiating Database, registering alice/bob/dave, creating a household+invite, and calling accept_invite(code, bob) then accept_invite(code, dave): both succeeded and both appear as members, proving the same invite code is infinitely reusable across distinct new users. Read tests/test_household.py:88-93: test_member_cannot_accept_twice calls accept_invite twice with the SAME user (carol), which raises HouseholdError via the unrelated 'already a member' check at household.py:108-109 -- not via any single-use/used_at check. The test would pass unchanged even if invite codes were fully reusable, exactly as claimed, and its name promises a single-use check it doesn't perform.", "adjusted_severity": "major"}
