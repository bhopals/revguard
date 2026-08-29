# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/agent-v4/case10_note_search/reviewer_correctness.jsonl`

**Session init** — model `claude-sonnet-5`, tools: Glob, Grep, Read

**Tool call → Read**

```json
{"file_path": "/private/var/folders/16/68bllkdn5n75d9gn5qj1thtw0000gp/T/revguard-work-agent-v4/case10_note_search/ledgerly/expenses.py"}
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

**Tool call → Grep**

```json
{"pattern": "search_expenses", "output_mode": "files_with_matches"}
```

**Tool result:**

```
Found 1 file
ledgerly/expenses.py
```

**Assistant:**

{"findings": [{"file": "ledgerly/expenses.py", "line": 65, "category": "correctness", "severity": "major", "title": "LIKE wildcard characters in `text` are not escaped", "description": "`pattern = f\"%{text}%\"` embeds the raw search text between SQL LIKE wildcards without escaping any `%` or `_` characters the user's search text itself contains. Since SQLite LIKE treats `%` as 'any sequence' and `_` as 'any single character', a search for a note that literally contains one of these characters behaves incorrectly: e.g. searching for \"100%\" (meant to find notes containing the literal substring \"100%\", such as \"gave 100% discount\") will instead match any note starting with \"100\" followed by any characters (e.g. \"1000 dollars\"), and searching for \"5_00\" will match \"5100\", \"5900\", etc. This contradicts the function's own docstring, 'Search the user's expenses whose note contains `text`', which implies a literal substring match."}]}

---
**Final result** (3 turns, 26.3s, $0.050):

{"findings": [{"file": "ledgerly/expenses.py", "line": 65, "category": "correctness", "severity": "major", "title": "LIKE wildcard characters in `text` are not escaped", "description": "`pattern = f\"%{text}%\"` embeds the raw search text between SQL LIKE wildcards without escaping any `%` or `_` characters the user's search text itself contains. Since SQLite LIKE treats `%` as 'any sequence' and `_` as 'any single character', a search for a note that literally contains one of these characters behaves incorrectly: e.g. searching for \"100%\" (meant to find notes containing the literal substring \"100%\", such as \"gave 100% discount\") will instead match any note starting with \"100\" followed by any characters (e.g. \"1000 dollars\"), and searching for \"5_00\" will match \"5100\", \"5900\", etc. This contradicts the function's own docstring, 'Search the user's expenses whose note contains `text`', which implies a literal substring match."}]}
