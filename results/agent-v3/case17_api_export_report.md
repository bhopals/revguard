# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] IDOR: any authenticated user can read any household's balances

`ledgerly/api.py:157` — security

get_household_balances (ledgerly/api.py:157-166) takes household_id straight from the query string and calls household.balances(db, hid) without verifying that request.user_id is a member of that household. household.balances() (ledgerly/household.py:111) itself performs no membership check either — it just looks up members_of(household_id) and sums shared_expenses for that id. Contrast this with post_household_expense, which relies on household.add_shared_expense calling household.require_member(db, household_id, paid_by) before inserting, and with expenses.py where every query is scoped by user_id. Any authenticated user can enumerate household_id values (sequential integer primary key) and call GET /household/balances?household_id=<id> to read the full member list and every member's net balance in cents for a household they do not belong to, leaking other users' financial data and household membership (user_ids) they have no relationship to.

*Verified: Read ledgerly/household.py: require_member() is defined but only called from add_shared_expense and remove_member (confirmed via grep), never from balances() or any code path reached by get_household_balances in api.py:157-166. Wrote and ran a direct reproduction: registered alice, bob (household members) and carol (not a member); called api.handle() as carol against GET /household/balances?househ*

## 2. [CRITICAL] No test that a non-member is denied access to a household's balances

`tests/test_api.py:96` — test-adequacy

get_household_balances (ledgerly/api.py:162) calls household.balances(db, hid) directly with no household.require_member(db, hid, request.user_id) check, so any authenticated user can read any household's balances by guessing/enumerating household_id. TestHouseholdEndpoints.test_balances_for_own_household only exercises the case where the requesting user (alice) is a member of the household being queried, so it can't fail even if the (missing) access check were never added. The conftest already provides a `carol` fixture (a user not in the household) that could have been used to assert `GET /household/balances?household_id=<hid>` returns 403/401 for a non-member; no such test exists, so this access-control gap in a newly-added endpoint ships with zero test coverage.

*Verified: Read household.py and api.py: get_household_balances calls household.balances(db, hid) directly with no require_member check anywhere on that path (grep confirms 'require_member' never appears in api.py). Wrote a live repro registering alice/bob/carol, creating a household with alice+bob as members, then logging in as carol (never added) and calling GET /household/balances with the household_id — *

## 3. [MAJOR] Household expense amount computed with float arithmetic instead of parse_money, causing cent-level rounding errors

`ledgerly/api.py:176` — correctness

post_household_expense computes cents as `int(float(request.body["amount"]) * 100)` instead of using `parse_money(str(...))` like post_expense and post_budget do. Binary floating point cannot exactly represent many decimal amounts (e.g. 19.99, 2.31), so `float(amount) * 100` frequently yields values like 1998.9999999999998 instead of 1999.0; `int()` truncates toward zero, silently storing one cent less than the user entered. Because add_shared_expense's balances feed directly into household.balances() (ledgerly/household.py:111-139), this off-by-one-cent error corrupts who-owes-whom calculations for real dollar amounts, and unlike parse_money it also has no format validation (accepts scientific notation, `inf`, `nan`, arbitrary precision) making the conversion unpredictable versus the documented cents-parsing contract in ledgerly/utils.py.

*Verified: Read ledgerly/api.py:176 confirming `cents = int(float(request.body["amount"]) * 100)` in post_household_expense, vs. parse_money used elsewhere. Executed `int(float(x)*100)` for common amounts: '19.99' -> 1998 (should be 1999), '0.29' -> 28 (should be 29), confirming silent truncation of a cent. Read household.py:85-99 add_shared_expense which stores amount_cents as-is, and balances() (line 111+)*

## 4. [MAJOR] CSV export does not escape fields, corrupting rows whose note contains a comma or newline

`ledgerly/api.py:200` — correctness

get_export builds each CSV row via a raw f-string `f"{r['spent_on']},{r['category']},{amount},{r['note']}"` with no quoting/escaping. Notes are free-form text up to 500 characters (ledgerly/expenses.py MAX_NOTE_LEN) with no restriction on commas or newlines, so an expense created with e.g. note="lunch, with team" produces a 5-field CSV line where any consumer parsing the file with a standard CSV reader will misalign the `amount` and `note` columns (or, if the note contains a newline, will split into an extra malformed row). This silently produces incorrect exported data for a very common real-world input, defeating the purpose of the new /export endpoint.

*Verified: Read ledgerly/api.py get_export (line ~200): builds CSV rows via raw f-string `f"{r['spent_on']},{r['category']},{amount},{r['note']}"` with no quoting. Confirmed expenses.py has MAX_NOTE_LEN=500 but no restriction on commas/newlines in notes. Reproduced via script: created an expense with note="lunch, with team", called GET /export, then parsed the resulting body with Python's standard csv.reader*
