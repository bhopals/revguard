# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case14_multi_currency/verifier_02.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Bash**

```json
{"command": "grep -n \"currency\" -r ledgerly tests"}
```

**Tool result:**

```
ledgerly/db.py:22:    currency TEXT NOT NULL DEFAULT 'USD',
ledgerly/expenses.py:18:def add_expense(db, user_id, amount_cents, category, spent_on, note="", currency="USD"):
ledgerly/expenses.py:25:        "INSERT INTO expenses (user_id, amount_cents, currency, category,"
ledgerly/expenses.py:27:        (user_id, amount_cents, currency, category, note,
tests/test_ledgerly.py:82:    def test_currency_roundtrip(self, db, user):
tests/test_ledgerly.py:84:            db, user, 999, "food", "2026-03-01", currency="EUR"
tests/test_ledgerly.py:87:        assert row["currency"] == "EUR"
```

**Assistant:**

Confirmed by inspection: no validation/normalization of currency anywhere in `expenses.py`, and only one test exists covering the explicit-uppercase happy path.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nimport sqlite3, sys\nsys.path.insert(0, '.')\nfrom ledgerly import db as dbmod, expenses\n\nconn = sqlite3.connect(':memory:')\ndbmod.init_db(conn) if hasattr(dbmod, 'init_db') else None\n\" 2>&1 | head -30\nls ledgerly\n"}
```

**Tool result:**

```
__init__.py
__pycache__
auth.py
db.py
expenses.py
reports.py
utils.py
```

**Tool call → Bash**

```json
{"command": "python3 -m pytest tests/test_ledgerly.py -k currency -q 2>&1 | tail -20"}
```

**Tool result:**

```
.                                                                        [100%]
1 passed, 16 deselected in 0.12s
```

**Tool call → Bash**

```json
{"command": "python3 -c \"\nimport sys\nsys.path.insert(0,'.')\nimport sqlite3\nimport tests.test_ledgerly as t\n\" 2>&1 | head -20\nsed -n '1,40p' tests/test_ledgerly.py"}
```

**Tool result:**

```
import pytest

from ledgerly.db import Database
from ledgerly import auth, expenses, reports
from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date


@pytest.fixture()
def db():
    d = Database()
    yield d
    d.close()


@pytest.fixture()
def user(db):
    return auth.register(db, "alice", "s3cretpass")


class TestUtils:
    def test_parse_money(self):
        assert parse_money("12.50") == 1250
        assert parse_money("$12.50") == 1250
        assert parse_money("12") == 1200
        assert parse_money("0.5") == 50

    def test_parse_money_rejects_garbage(self):
        for bad in ["", "abc", "-5", "12.345", "1,000"]:
            with pytest.raises(ValueError):
                parse_money(bad)

    def test_format_money(self):
        assert format_money(1
… [203 chars truncated]
```

**Assistant:**

Now let me directly verify the two sub-claims: default currency isn't tested, and invalid/lowercase currency isn't rejected.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nimport sys\nsys.path.insert(0,'.')\nfrom ledgerly.db import Database\nfrom ledgerly import auth, expenses\n\ndb = Database()\nuid = auth.register(db, 'bob', 's3cretpass')\n\n# default currency, not specified in PR test\neid = expenses.add_expense(db, uid, 100, 'food', '2026-03-01')\nrow = expenses.get_expense(db, uid, eid)\nprint('default currency:', row['currency'])\n\n# lowercase / invalid currency - is it rejected?\neid2 = expenses.add_expense(db, uid, 100, 'food', '2026-03-01', currency='eur')\nrow2 = expenses.get_expense(db, uid, eid2)\nprint('lowercase currenc
… [225 chars truncated]
```

**Tool result:**

```
default currency: USD
lowercase currency stored as: eur
bogus currency stored as: NOTREAL
```

**Assistant:**

This confirms exactly what the finding describes: the code has no validation/normalization of currency (lowercase and bogus values pass through unchanged), and the sole new test (`test_currency_roundtrip`) only exercises the explicit uppercase 'EUR' happy path — it doesn't test the default, lowercase, or invalid cases, so this gap is untested/uncaught.

**Tool call → Bash**

```json
{"command": "grep -n \"def test_\" tests/test_ledgerly.py | grep -i currency"}
```

**Tool result:**

```
82:    def test_currency_roundtrip(self, db, user):
```

**Assistant:**

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read expenses.py/db.py: no validation or normalization of the currency parameter anywhere in the code path. Only one new test, test_currency_roundtrip (line 82-87), exists and it only passes currency='EUR' (uppercase, valid) and checks roundtrip. Ran a live repro: add_expense with no currency arg stores 'USD' (untested by suite), currency='eur' is stored verbatim as lowercase 'eur', and currency='NOTREAL' is stored verbatim as 'NOTREAL' — confirming both the missing validation and the missing test coverage for default/invalid/lowercase cases exactly as described.", "adjusted_severity": "minor"}

---
**Final result** (7 turns, 24.0s, $0.061):

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read expenses.py/db.py: no validation or normalization of the currency parameter anywhere in the code path. Only one new test, test_currency_roundtrip (line 82-87), exists and it only passes currency='EUR' (uppercase, valid) and checks roundtrip. Ran a live repro: add_expense with no currency arg stores 'USD' (untested by suite), currency='eur' is stored verbatim as lowercase 'eur', and currency='NOTREAL' is stored verbatim as 'NOTREAL' — confirming both the missing validation and the missing test coverage for default/invalid/lowercase cases exactly as described.", "adjusted_severity": "minor"}
