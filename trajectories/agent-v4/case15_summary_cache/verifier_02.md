# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case15_summary_cache/verifier_02.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Bash, Glob, Grep, Read

**Tool call → Bash**

```json
{"command": "cat ledgerly/reports.py; echo ---; cat ledgerly/expenses.py"}
```

**Tool result:**

```
"""Monthly summaries and budget tracking."""

from .utils import format_money


class BudgetError(Exception):
    pass


def set_budget(db, user_id, category, month, limit_cents):
    if limit_cents <= 0:
        raise BudgetError("budget limit must be positive")
    db.execute(
        "INSERT INTO budgets (user_id, category, month, limit_cents)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT (user_id, category, month)"
        " DO UPDATE SET limit_cents = excluded.limit_cents",
        (user_id, category, month, limit_cents),
    )


_summary_cache = {}


def monthly_summary(db, user_id, month):
    """Total spend per category for a 'YYYY-MM' month.

    Results are cached per (user, month): the dashboard calls this on
    every page load and the numbers rarely change within a ses
… [3180 chars truncated]
```

**Assistant:**

Confirmed no invalidation exists anywhere on add/delete paths. Let me reproduce the stale-cache behavior directly.

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && python3 -m pytest -q 2>&1 | tail -20; find . -name conftest.py"}
```

**Tool result:**

```
.................                                                        [100%]
17 passed in 1.32s
```

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && find . -name conftest.py -exec cat {} \\;"}
```

**Tool result:**

```
(Bash completed with no output)
```

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && sed -n '1,60p' tests/test_ledgerly.py"}
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
… [856 chars truncated]
```

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, expenses, reports\n\ndb = Database()\nuser = auth.register(db, 'alice', 's3cretpass')\n\neid = expenses.add_expense(db, user, 1500, 'food', '2026-05-02')\nprint('add_expense returned:', eid)\n\ns1 = reports.monthly_summary(db, user, '2026-05')\nprint('before delete:', s1)\n\n# find the expense id to delete\nrows = expenses.list_expenses(db, user)\nprint('rows:', rows)\nexpense_id = rows[0]['id']\n\nexpenses.delete_expense(db, user, expense_id)\n\ns2 = reports.monthly_summary(db, user, '202
… [81 chars truncated]
```

**Tool result:**

```
add_expense returned: 1
before delete: {'food': 1500}
rows: [{'id': 1, 'user_id': 1, 'amount_cents': 1500, 'category': 'food', 'note': '', 'spent_on': '2026-05-02', 'created_at': '2026-08-29T14:18:37+00:00'}]
after delete (cached): {'food': 1500}
```

**Assistant:**

Reproduced exactly: after `delete_expense`, `monthly_summary` still returns the deleted expense's totals due to the stale module-level `_summary_cache`. No invalidation call exists anywhere in `expenses.py` or `reports.py`.

**Tool call → Bash**

```json
{"command": "cd \"$(pwd)\" && grep -rn \"_summary_cache\\|cache\" ledgerly/"}
```

**Tool result:**

```
Binary file ledgerly/__pycache__/reports.cpython-312.pyc matches
ledgerly/reports.py:22:_summary_cache = {}
ledgerly/reports.py:28:    Results are cached per (user, month): the dashboard calls this on
ledgerly/reports.py:32:    if key in _summary_cache:
ledgerly/reports.py:33:        return _summary_cache[key]
ledgerly/reports.py:42:    _summary_cache[key] = totals
```

**Assistant:**

Confirmed: the cache is never touched by `expenses.py` (no import of `reports`, no invalidation), and the only two mutation points in `reports.py` never clear it either.

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/reports.py and ledgerly/expenses.py: _summary_cache is a module-level dict populated in monthly_summary and never cleared anywhere; expenses.py (add_expense/delete_expense) doesn't import or reference reports/_summary_cache at all, and grep confirms no other invalidation site exists. Reproduced live: added an expense, called reports.monthly_summary (caches {'food': 1500}), deleted the expense via expenses.delete_expense (row removed from DB), then called reports.monthly_summary again — it still returned {'food': 1500}, i.e. the deleted expense's amount continues to appear in totals/budget_status for the rest of the process lifetime. This matches the finding exactly.", "adjusted_severity": "major"}

---
**Final result** (7 turns, 24.7s, $0.065):

Confirmed: the cache is never touched by `expenses.py` (no import of `reports`, no invalidation), and the only two mutation points in `reports.py` never clear it either.

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read ledgerly/reports.py and ledgerly/expenses.py: _summary_cache is a module-level dict populated in monthly_summary and never cleared anywhere; expenses.py (add_expense/delete_expense) doesn't import or reference reports/_summary_cache at all, and grep confirms no other invalidation site exists. Reproduced live: added an expense, called reports.monthly_summary (caches {'food': 1500}), deleted the expense via expenses.delete_expense (row removed from DB), then called reports.monthly_summary again — it still returned {'food': 1500}, i.e. the deleted expense's amount continues to appear in totals/budget_status for the rest of the process lifetime. This matches the finding exactly.", "adjusted_severity": "major"}
