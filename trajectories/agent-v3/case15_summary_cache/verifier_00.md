# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case15_summary_cache/verifier_00.jsonl`

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

Confirmed by reading: no code anywhere invalidates `_summary_cache`, and `expenses.py` has no reference to it. Let me execute a concrete reproduction.

**Tool call → Bash**

```json
{"command": "find . -path ./node_modules -prune -o -name conftest.py -print -o -name \"test_ledgerly.py\" -print 2>/dev/null; echo ---; cat tests/conftest.py 2>/dev/null | head -50"}
```

**Tool result:**

```
./tests/test_ledgerly.py
---
```

**Tool call → Bash**

```json
{"command": "sed -n '1,40p' tests/test_ledgerly.py; echo ---; find . -iname \"*.py\" | xargs grep -l \"class .*db\\|def db\\b\\|fixture\" 2>/dev/null"}
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
… [234 chars truncated]
```

**Assistant:**

Now let's write a reproduction script demonstrating the stale cache issue.

**Tool call → Bash**

```json
{"command": "python3 -c \"\nfrom ledgerly.db import Database\nfrom ledgerly import auth, expenses, reports\n\ndb = Database()\nuser = auth.register(db, 'alice', 's3cretpass')\n\nexpenses.add_expense(db, user, 700, 'transport', '2026-05-02')\nfirst = reports.monthly_summary(db, user, '2026-05')\nprint('first:', first)\n\nexpenses.add_expense(db, user, 5000, 'transport', '2026-05-10')\nsecond = reports.monthly_summary(db, user, '2026-05')\nprint('second (after add):', second)\n\nreports.set_budget(db, user, 'transport', '2026-05', 1000)\nstatus = reports.budget_status(db, user, '2026-05')\nprint
… [34 chars truncated]
```

**Tool result:**

```
first: {'transport': 700}
second (after add): {'transport': 700}
budget status: [{'category': 'transport', 'limit': '$10.00', 'spent': '$7.00', 'remaining': '$3.00', 'over_budget': False}]
```

**Tool call → Bash**

```json
{"command": "grep -n \"_summary_cache\" -r ledgerly/"}
```

**Tool result:**

```
Binary file ledgerly/__pycache__/reports.cpython-312.pyc matches
ledgerly/reports.py:22:_summary_cache = {}
ledgerly/reports.py:32:    if key in _summary_cache:
ledgerly/reports.py:33:        return _summary_cache[key]
ledgerly/reports.py:42:    _summary_cache[key] = totals
```

**Assistant:**

Reproduction confirms the exact failure: after caching, a new expense is added but `monthly_summary` keeps returning the stale total, and `budget_status` reports `over_budget: False` when the true spend (5700) actually exceeds the 1000 limit. No invalidation exists anywhere in the codebase (`_summary_cache` is only referenced in `reports.py`).

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read reports.py: `_summary_cache` is a module-level dict, populated in monthly_summary and never cleared; grep across ledgerly/ shows no other reference to it (expenses.py's add_expense/delete_expense and reports.py's set_budget never touch it). Executed a reproduction: added a $7 transport expense, called monthly_summary (cached {transport:700}), added a second $50 expense, called monthly_summary again -> still returns {transport:700} (stale). Then set a $10 budget and called budget_status: it returned spent=$7.00, over_budget=False, even though true spend is $57.00 which exceeds the $10 limit. This directly confirms the described silent-stale-cache / wrong-budget-status defect.", "adjusted_severity": "critical"}

---
**Final result** (6 turns, 23.3s, $0.061):

Reproduction confirms the exact failure: after caching, a new expense is added but `monthly_summary` keeps returning the stale total, and `budget_status` reports `over_budget: False` when the true spend (5700) actually exceeds the 1000 limit. No invalidation exists anywhere in the codebase (`_summary_cache` is only referenced in `reports.py`).

{"verdict": "CONFIRMED", "confidence": "high", "evidence": "Read reports.py: `_summary_cache` is a module-level dict, populated in monthly_summary and never cleared; grep across ledgerly/ shows no other reference to it (expenses.py's add_expense/delete_expense and reports.py's set_budget never touch it). Executed a reproduction: added a $7 transport expense, called monthly_summary (cached {transport:700}), added a second $50 expense, called monthly_summary again -> still returns {transport:700} (stale). Then set a $10 budget and called budget_status: it returned spent=$7.00, over_budget=False, even though true spend is $57.00 which exceeds the $10 limit. This directly confirms the described silent-stale-cache / wrong-budget-status defect.", "adjusted_severity": "critical"}
