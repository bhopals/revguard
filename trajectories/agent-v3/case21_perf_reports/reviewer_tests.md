# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v3/case21_perf_reports/reviewer_tests.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Grep**

```json
{"pattern": "budget_status", "output_mode": "files_with_matches"}
```

**Tool call → Glob**

```json
{"pattern": "**/test*report*"}
```

**Tool result:**

```
No files found
```

**Tool result:**

```
Found 5 files
ledgerly/reports.py
.pytest_cache/v/cache/nodeids
ledgerly/api.py
ledgerly/notify.py
tests/test_ledgerly.py
```

**Tool call → Grep**

```json
{"pattern": "budget_status|monthly_summary", "path": "tests/test_ledgerly.py", "output_mode": "content", "-n": true, "-C": 15}
```

**Tool result:**

```
75-        with pytest.raises(expenses.ExpenseError):
76-            expenses.get_expense(db, user, eid)
77-
78-    def test_bad_category(self, db, user):
79-        with pytest.raises(expenses.ExpenseError):
80-            expenses.add_expense(db, user, 500, "yachts", "2026-03-01")
81-
82-    def test_list_filters_by_category(self, db, user):
83-        expenses.add_expense(db, user, 100, "food", "2026-03-01")
84-        expenses.add_expense(db, user, 200, "transport", "2026-03-02")
85-        rows = expenses.list_expenses(db, user, category="food")
86-        assert [r["amount_cents"] for r in rows] == [100]
87-
88-
89-class TestReports:
90:    def test_monthly_summary(self, db, user):
91-        expenses.add_expense(db, user, 100, "food", "2026-03-01")
92-        expenses.add_expense(db
… [837 chars truncated]
```

**Tool call → Read**

```json
{"file_path": "ledgerly/reports.py"}
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
… [1308 chars truncated]
```

**Assistant:**

Confirmed: the new JOIN in `budget_status` has no filter on `e.spent_on`/month, unlike the old `monthly_summary`-based implementation, so it now sums expenses across ALL months for that category, not just the queried month. This is a real behavior change despite the PR claiming "no behavior change intended."

**Tool call → Read**

```json
{"file_path": "tests/test_ledgerly.py", "offset": 88, "limit": 30}
```

**Tool result:**

```
88	
89	class TestReports:
90	    def test_monthly_summary(self, db, user):
91	        expenses.add_expense(db, user, 100, "food", "2026-03-01")
92	        expenses.add_expense(db, user, 250, "food", "2026-03-15")
93	        expenses.add_expense(db, user, 400, "transport", "2026-04-01")
94	        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}
95	
96	    def test_budget_status(self, db, user):
97	        reports.set_budget(db, user, "food", "2026-03", 300)
98	        expenses.add_expense(db, user, 350, "food", "2026-03-10")
99	        status = reports.budget_status(db, user, "2026-03")
100	        assert status[0]["over_budget"] is True
101	        assert status[0]["remaining"] == "-$0.50"
102	
103	    def test_budget_upsert(self, db, user):
104	        reports.set_bud
… [220 chars truncated]
```

**Assistant:**

`test_budget_status` and `test_budget_upsert` (both pre-existing, unmodified by this PR) only add expenses within the queried month, so they pass regardless of whether the query filters by month — they cannot catch the missing month-scoping bug in the new JOIN. No new test was added to cover this changed code path with a cross-month expense.

**Tool call → Grep**

```json
{"pattern": "^class TestReports|def test_", "path": "tests/test_ledgerly.py", "-n": true}
```

**Tool result:**

```
Found 1 file
tests/test_ledgerly.py
```

**Assistant:**

Confirmed no other test exercises `budget_status` with expenses outside the target month or with multiple budget months for the same user/category.

```json
{"findings": [{"file": "tests/test_ledgerly.py", "line": 96, "category": "test-adequacy", "severity": "major", "title": "No test catches missing month filter in rewritten budget_status query", "description": "The PR rewrote budget_status's SQL to LEFT JOIN expenses to budgets on user_id and category only, dropping the month filter on expenses.spent_on that the old monthly_summary()-based implementation had (via substr(spent_on,1,7) = month). This means spent is now summed across ALL months for that category, not just the requested month — a real behavior change despite the PR claiming 'no behavior change intended'. Neither test_budget_status (line 96-101) nor test_budget_upsert (line 103-107) was updated or extended to add an expense in a different month; both only add expenses within the queried month '2026-03', so they pass identically whether or not the query is month-scoped. A test that adds an expense in e.g. '2026-04' for the same category and then calls budget_status(db, user, '2026-03') would fail on this PR's code (spe
… [124 chars truncated]

---
**Final result** (7 turns, 18.0s, $0.056):

Confirmed no other test exercises `budget_status` with expenses outside the target month or with multiple budget months for the same user/category.

```json
{"findings": [{"file": "tests/test_ledgerly.py", "line": 96, "category": "test-adequacy", "severity": "major", "title": "No test catches missing month filter in rewritten budget_status query", "description": "The PR rewrote budget_status's SQL to LEFT JOIN expenses to budgets on user_id and category only, dropping the month filter on expenses.spent_on that the old monthly_summary()-based implementation had (via substr(spent_on,1,7) = month). This means spent is now summed across ALL months for that category, not just the requested month — a real behavior change despite the PR claiming 'no behavior change intended'. Neither test_budget_status (line 96-101) nor test_budget_upsert (line 103-107) was updated or extended to add an expense in a different month; both only add expenses within the queried month '2026-03', so they pass identically whether or not the query is month-scoped. A test that adds an expense in e.g. '2026-04' for the same category and then calls budget_status(db, user, '2026-03') would fail on this PR's code (spe
… [124 chars truncated]
