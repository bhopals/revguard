# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v2/case10_note_search/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-v2/case10_note_search/ledgerly/expenses.py"}
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
… [1603 chars truncated]
```

**Assistant:**

{"findings": [{"file": "ledgerly/expenses.py", "line": 65, "category": "correctness", "title": "LIKE special characters in `text` are not escaped, breaking the documented \"contains\" search", "severity": "major", "description": "search_expenses builds the LIKE pattern as f\"%{text}%\" without escaping SQL LIKE wildcard characters (`%` and `_`) that may appear in `text`. Since expense notes are free text (e.g. \"lunch 50% off\", \"under_budget\"), a user searching for a note containing a literal `%` or `_` gets a pattern where that character is treated as a wildcard instead of a literal, so the query silently matches unrelated rows (or fails to isolate the intended note) instead of performing the substring match the docstring promises (\"whose note contains `text`\"). This is a new function introduced by this PR, so the mismatch between documented behavior and actual SQL semantics is a regression relative to no prior guarantee having been made."}]}

---
**Final result** (2 turns, 17.4s, $0.035):

{"findings": [{"file": "ledgerly/expenses.py", "line": 65, "category": "correctness", "title": "LIKE special characters in `text` are not escaped, breaking the documented \"contains\" search", "severity": "major", "description": "search_expenses builds the LIKE pattern as f\"%{text}%\" without escaping SQL LIKE wildcard characters (`%` and `_`) that may appear in `text`. Since expense notes are free text (e.g. \"lunch 50% off\", \"under_budget\"), a user searching for a note containing a literal `%` or `_` gets a pattern where that character is treated as a wildcard instead of a literal, so the query silently matches unrelated rows (or fails to isolate the intended note) instead of performing the substring match the docstring promises (\"whose note contains `text`\"). This is a new function introduced by this PR, so the mismatch between documented behavior and actual SQL semantics is a regression relative to no prior guarantee having been made."}]}
