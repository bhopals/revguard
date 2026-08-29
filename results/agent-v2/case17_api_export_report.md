# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Missing membership check allows any authenticated user to read any household's balances

`ledgerly/api.py:162` — security

get_household_balances (GET /household/balances) authenticates the caller but never verifies the caller is a member of the requested household_id before calling household.balances(db, hid). household.balances() itself performs no authorization check either (it just looks up all members and computes net positions). Any authenticated user can pass an arbitrary household_id query parameter and retrieve the full list of member user_ids and their net financial balances for a household they do not belong to (IDOR/broken access control). Compare to household.add_shared_expense, which correctly calls require_member(db, household_id, paid_by) before writing — the read path was not given the same treatment. The endpoint should call household.require_member(db, hid, request.user_id) (or equivalent) before computing balances.

## 2. [MAJOR] Household expense amount parsed with float arithmetic instead of parse_money

`ledgerly/api.py:176` — correctness

post_household_expense computes `cents = int(float(request.body["amount"]) * 100)` instead of using `parse_money(str(...))` like post_expense (line 101) and post_budget do. Binary floating point cannot represent many decimal amounts exactly: for amount "19.99", float("19.99") * 100 evaluates to 1998.9999999999998, and int() truncates toward zero, storing 1998 cents ($19.98) instead of 1999 ($19.99) — silently losing a cent on money the household ledger is supposed to track exactly. It also accepts inputs parse_money would reject (e.g. "1_000" -> 1000.0, "12.999" silently truncated instead of raising, "inf"/"nan" -> int(float('inf')*100) raises an uncaught OverflowError that isn't caught by handle()'s except clauses, crashing the request instead of returning a 400). This is inconsistent with every other money-handling endpoint in the same file and introduces real accounting drift for shared household expenses.

## 3. [MAJOR] CSV export does not escape commas or newlines in note/category fields

`ledgerly/api.py:200` — correctness

get_export builds each CSV row with plain f-string concatenation: `f"{r['spent_on']},{r['category']},{amount},{r['note']}"`. The `note` field is free text up to 500 characters (expenses.MAX_NOTE_LEN) with no character restrictions, so a note containing a comma (e.g. "lunch, with client") produces a row with five comma-separated values instead of four, shifting/duplicating the note into an extra column for any consumer that parses the CSV positionally. A note containing a newline is even worse: it splits into extra lines that don't match the 4-column header, corrupting the exported file's row structure entirely (the endpoint's own line-based construction via `"\n".join(lines)` guarantees such embedded newlines become spurious rows). Since notes are stored and returned unvalidated for character content, any user-entered note with a comma or newline yields a malformed CSV export.
