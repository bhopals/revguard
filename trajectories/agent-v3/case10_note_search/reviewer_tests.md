# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case10_note_search/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Grep**

```json
{"pattern": "search_expenses", "output_mode": "files_with_matches"}
```

**Tool call → Glob**

```json
{"pattern": "**/*test*"}
```

**Tool result:**

```
tests/test_ledgerly.py
pytest.ini
```

**Tool result:**

```
Found 1 file
ledgerly/expenses.py
```

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case10_note_search/tests/test_ledgerly.py"}
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
… [3364 chars truncated]
```

**Assistant:**

No tests were added for `search_expenses` at all — the PR introduces a new public function, including a `sort` parameter that is interpolated directly into SQL (`ledgerly/expenses.py:69`), with zero test coverage. A test exercising `sort` with an unvalidated/unexpected column name would have caught SQL-injection-shaped misuse or a query error, and a basic search test would have caught note-matching logic bugs (e.g., LIKE wildcard escaping). Since this is a test-adequacy review, I'll flag the missing-test gap for the risky `sort` parameter.

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case10_note_search/ledgerly/expenses.py", "offset": 1, "limit": 70}
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
18	def add_expense(db, user_id, amount_cents, category, spent_on, note=""):
19	    if category not in VALID_CATEGORIES:
20	        raise ExpenseError(f"unknown category: {category}")
21	    if len(note) > MAX_NOTE_LEN:
22	        raise ExpenseError("note too long")
23	    d = parse_iso_date(spent_on)
24	    return db.execute(
25	        "INSERT INTO expenses (user_id, amount_cents, category, note,"
26	        " spent_on, created_at) VALU
… [1599 chars truncated]
```

**Assistant:**

Confirmed: no tests reference `search_expenses` anywhere in the test suite.

**Tool call → Grep**

```json
{"pattern": "search_expenses|sort", "path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v3/case10_note_search/tests/test_ledgerly.py", "output_mode": "content"}
```

**Tool result:**

```
No matches found
```

**Assistant:**

{"findings": [{"file": "ledgerly/expenses.py", "line": 68, "category": "test-adequacy", "severity": "major", "title": "No tests for search_expenses, including its unvalidated `sort` parameter", "description": "The PR adds `search_expenses(db, user_id, text, sort=\"spent_on\")` which interpolates `sort` directly into the SQL string via an f-string (`f\" ORDER BY {sort} DESC\"`, line 68) with no allow-list or validation. No test in tests/test_ledgerly.py exercises this function at all — not the basic note-matching behavior, not the ownership scoping (that user_id filters results), and not the `sort` parameter. A test passing a non-default `sort` value (e.g. a bogus column name, or a value containing extra SQL) would immediately have surfaced that the parameter is concatenated unsafely into the query rather than validated against a safe column set. As written, the entire new public function ships with zero coverage, so any regression in matching, ownership scoping, or the sort-injection behavior would go undetected by CI."}]}

---
**Final result** (6 turns, 19.9s, $0.050):

{"findings": [{"file": "ledgerly/expenses.py", "line": 68, "category": "test-adequacy", "severity": "major", "title": "No tests for search_expenses, including its unvalidated `sort` parameter", "description": "The PR adds `search_expenses(db, user_id, text, sort=\"spent_on\")` which interpolates `sort` directly into the SQL string via an f-string (`f\" ORDER BY {sort} DESC\"`, line 68) with no allow-list or validation. No test in tests/test_ledgerly.py exercises this function at all — not the basic note-matching behavior, not the ownership scoping (that user_id filters results), and not the `sort` parameter. A test passing a non-default `sort` value (e.g. a bogus column name, or a value containing extra SQL) would immediately have surfaced that the parameter is concatenated unsafely into the query rather than validated against a safe column set. As written, the entire new public function ships with zero coverage, so any regression in matching, ownership scoping, or the sort-injection behavior would go undetected by CI."}]}
