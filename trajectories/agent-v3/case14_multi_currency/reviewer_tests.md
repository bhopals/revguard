# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case14_multi_currency/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/expenses.py"}
```

**Tool result:**

```
1	"""Expense CRUD and listing. Every operation is scoped to the owning user."""
2	
3	from .utils import parse_iso_date, utcnow_iso
4	
5	VALID_CATEGORIES = {
6	    "food", "transport", "housing", "utilities",
7	    "health", "entertainment", "other",
8	}
9	
10	MAX_NOTE_LEN = 500
11	PAGE_SIZE = 20
12	
13	
14	class ExpenseError(Exception):
15	    pass
16	
17	
18	def add_expense(db, user_id, amount_cents, category, spent_on, note="", currency="USD"):
19	    if category not in VALID_CATEGORIES:
20	        raise ExpenseError(f"unknown category: {category}")
21	    if len(note) > MAX_NOTE_LEN:
22	        raise ExpenseError("note too long")
23	    d = parse_iso_date(spent_on)
24	    return db.execute(
25	        "INSERT INTO expenses (user_id, amount_cents, currency, category,"
26	        " note, 
… [1296 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/tests/test_ledgerly.py"}
```

**Tool result:**

```
1	import pytest
2	
3	from ledgerly.db import Database
4	from ledgerly import auth, expenses, reports
5	from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date
6	
7	
8	@pytest.fixture()
9	def db():
10	    d = Database()
11	    yield d
12	    d.close()
13	
14	
15	@pytest.fixture()
16	def user(db):
17	    return auth.register(db, "alice", "s3cretpass")
18	
19	
20	class TestUtils:
21	    def test_parse_money(self):
22	        assert parse_money("12.50") == 1250
23	        assert parse_money("$12.50") == 1250
24	        assert parse_money("12") == 1200
25	        assert parse_money("0.5") == 50
26	
27	    def test_parse_money_rejects_garbage(self):
28	        for bad in ["", "abc", "-5", "12.345", "1,000"]:
29	            with pytest.raises(ValueError):
30	               
… [3642 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case14_multi_currency/ledgerly/reports.py"}
```

**Tool result:**

```
1	"""Monthly summaries and budget tracking."""
2	
3	from .utils import format_money
4	
5	
6	class BudgetError(Exception):
7	    pass
8	
9	
10	def set_budget(db, user_id, category, month, limit_cents):
11	    if limit_cents <= 0:
12	        raise BudgetError("budget limit must be positive")
13	    db.execute(
14	        "INSERT INTO budgets (user_id, category, month, limit_cents)"
15	        " VALUES (?, ?, ?, ?)"
16	        " ON CONFLICT (user_id, category, month)"
17	        " DO UPDATE SET limit_cents = excluded.limit_cents",
18	        (user_id, category, month, limit_cents),
19	    )
20	
21	
22	def monthly_summary(db, user_id, month):
23	    """Total spend per category for a 'YYYY-MM' month."""
24	    rows = db.query(
25	        "SELECT category, SUM(amount_cents) AS total"
26	        
… [1163 chars truncated]
```

**Assistant:**

Confirmed: `monthly_summary` sums `amount_cents` across all currencies without conversion, and no test in this PR exercises that scenario.

```json
{"findings": [{"file": "tests/test_ledgerly.py", "line": 82, "category": "test-adequacy", "title": "No test covers reports mixing currencies, though PR enables it", "severity": "major", "description": "The PR adds a currency parameter to add_expense (ledgerly/expenses.py:18) and claims 'reporting is unchanged', but reports.monthly_summary (ledgerly/reports.py:22-31) sums amount_cents per category with no currency grouping or conversion. If a user adds a USD expense and an EUR expense in the same category/month, monthly_summary and budget_status will silently add the raw cent values together as though they were the same currency, producing a meaningless total. The only new test, test_currency_roundtrip, checks that the currency string round-trips through get_expense but never calls monthly_summary or budget_status with mixed-currency data, so this incorrect aggregation is completely unverified and would not be caught by the test suite."}]}
```

---
**Final result** (4 turns, 16.6s, $0.054):

Confirmed: `monthly_summary` sums `amount_cents` across all currencies without conversion, and no test in this PR exercises that scenario.

```json
{"findings": [{"file": "tests/test_ledgerly.py", "line": 82, "category": "test-adequacy", "title": "No test covers reports mixing currencies, though PR enables it", "severity": "major", "description": "The PR adds a currency parameter to add_expense (ledgerly/expenses.py:18) and claims 'reporting is unchanged', but reports.monthly_summary (ledgerly/reports.py:22-31) sums amount_cents per category with no currency grouping or conversion. If a user adds a USD expense and an EUR expense in the same category/month, monthly_summary and budget_status will silently add the raw cent values together as though they were the same currency, producing a meaningless total. The only new test, test_currency_roundtrip, checks that the currency string round-trips through get_expense but never calls monthly_summary or budget_status with mixed-currency data, so this incorrect aggregation is completely unverified and would not be caught by the test suite."}]}
```
