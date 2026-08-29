# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 5 blocking finding(s), 1 critical.

## 1. [CRITICAL] Missing authorization check on GET /household/balances (IDOR)

`ledgerly/api.py:156` — security

get_household_balances takes household_id from the query params and calls household.balances(db, hid) directly, without verifying that request.user_id is a member of that household (unlike post_household_expense, which internally hits household.require_member via add_shared_expense, and unlike expenses.list_expenses which scopes by user_id). Any authenticated user can enumerate arbitrary household_id values and read the net balances (user_id -> cents owed) of households they do not belong to, leaking other users' financial data. Fix by calling household.require_member(db, hid, request.user_id) before computing balances.

*Verified: Read ledgerly/household.py: balances(db, household_id) (line 111) has no membership check, only add_shared_expense calls require_member (line 87). Read ledgerly/api.py get_household_balances (diff lines ~156-169): it takes household_id straight from query params and calls household.balances(db, hid) with no require_member call and no comparison to request.user_id. Wrote and ran a live exploit: registered alice/bob/carol, created a household with alice+bob only, added a shared expense, then logged in as carol (not a member) and called GET /household/balances?household_id=<hid> with her own valid token.*

## 2. [MAJOR] Household expense amount parsed with float arithmetic, causing off-by-one-cent truncation

`ledgerly/api.py:176` — correctness

post_household_expense computes cents as int(float(request.body["amount"]) * 100) instead of reusing parse_money (as post_expense and post_budget do). Binary floating point cannot exactly represent many two-decimal amounts, and int() truncates toward zero: e.g. float("19.99") * 100 evaluates to 1998.9999999999998 in Python, so int(...) yields 1998 cents instead of 1999. A user submitting amount="19.99" for a shared household expense will have $0.01 silently shaved off the stored amount, corrupting household balances/settlement math. This is a regression relative to the established parse_money-based parsing used everywhere else in this file, which parses the decimal string directly and avoids float rounding.

*Verified: Read ledgerly/api.py:176 and confirmed post_household_expense computes `cents = int(float(request.body["amount"]) * 100)` while sibling handlers post_expense/post_budget use parse_money (utils.py), which parses the decimal string directly without float conversion. Verified household.add_shared_expense stores amount_cents as-is with no re-parsing/validation that would fix truncation. Executed a full end-to-end repro through api.handle(POST /household/expenses, amount='19.99') and inspected the DB row directly: stored amount_cents == 1998 instead of the correct 1999 (parse_money('19.99') == 1999, confirmed separately). Also confirmed other amounts like '0.29' truncate to 28 cents.*

## 3. [MAJOR] CSV export does not escape or quote fields, corrupting rows with commas/newlines in notes

`ledgerly/api.py:198` — robustness

get_export builds CSV lines by naive string interpolation: f"{r['spent_on']},{r['category']},{amount},{r['note']}" (line 200), with no quoting/escaping of the note field. expenses.add_expense only bounds note length (MAX_NOTE_LEN) and does not forbid commas or newlines, so a legitimately created expense such as note="lunch, with team" produces a CSV line with 5 comma-separated fields instead of 4, shifting/breaking column alignment for any consumer parsing the export. Likewise a note containing a newline (e.g. "line1\nline2") splits into an extra bogus row when the body is split/read line-by-line, since lines are joined solely with '\n' (line 202) with no CSV quoting. This breaks the endpoint's own docstring promise of well-formed 'CSV text' for any expense whose note isn't comma/newline-free.

*Verified: Read ledgerly/expenses.py: add_expense only checks len(note) > MAX_NOTE_LEN, no restriction on commas/newlines. Read ledgerly/api.py get_export: builds lines via f"{r['spent_on']},{r['category']},{amount},{r['note']}" with no CSV quoting, joined with '\n'. Reproduced via python3 script calling api.handle directly: (1) note='lunch, with team' produces exported line 'lunch, with team' -> splitting on ',' yields 5 fields instead of 4 ['2026-03-01','food','12.50','lunch',' with team']; (2) note='line1\nline2' produces body with an extra bogus line when using splitlines() (3 lines total instead of 2: header + 1 data row becomes header + 2 lines).*

## 4. [MAJOR] Household expense test only uses a round dollar amount, hiding the new float-based cents bug

`tests/test_api.py:93` — test-adequacy

post_household_expense (ledgerly/api.py:176) parses the amount with `int(float(request.body["amount"]) * 100)` instead of the codebase's precision-safe `parse_money` used by every other money-accepting endpoint. The only test exercising this endpoint, test_balances_for_own_household, submits amount="10.00", which happens to convert to exactly 1000.0 in IEEE-754 float and truncates cleanly to 1000 cents. Values that don't round-trip exactly in binary floating point (e.g. "19.99" -> 1998.9999999999998 -> int() truncates to 1998, one cent short) would silently record the wrong amount and produce an off-by-one-cent balance, but the test never exercises such a value, so it cannot catch this class of bug despite being the sole coverage for the new endpoint's amount handling.

*Verified: Read ledgerly/api.py:176 (post_household_expense uses `int(float(amount)*100)`) vs ledgerly/utils.py parse_money (string-based, precision-safe, used by every other money endpoint). Reproduced the bug end-to-end: called the real POST /household/expenses handler with amount='19.99' and queried the raw sqlite row afterward — amount_cents was stored as 1998 instead of the correct 1999, silently losing one cent. Confirmed the sole existing test (test_balances_for_own_household) only uses amount='10.00', which happens to convert exactly (1000.0) in IEEE-754 and thus never exercises the truncation path; ran it and it passes despite the underlying data-corruption bug.*

## 5. [MAJOR] Test name promises household-scoped access but only exercises the happy path

`tests/test_api.py:87` — test-adequacy

test_balances_for_own_household is named to suggest it verifies balances are scoped to a household the caller belongs to, but it never checks the negative case (a user with no membership in the household requesting GET /household/balances for that household_id). get_household_balances (ledgerly/api.py:157-169) never calls household.require_member or otherwise checks that request.user_id belongs to the household before returning balances, so any authenticated user can view any household's balances by guessing/knowing its id. The test's name implies membership scoping is being validated, but its structure (single user who is in fact a member) cannot fail even if that scoping is completely absent.

*Verified: Read ledgerly/api.py:157-169 and ledgerly/household.py: get_household_balances never calls household.require_member (or any membership/ownership check) before returning balances, and household.balances() itself performs no caller check either — require_member is only used inside add_shared_expense/remove_member. Executed a live reproduction: registered alice, bob, and mallory; created a household with alice+bob as the only members; added a shared expense; then had mallory (never added as a member) call GET /household/balances with that household_id — result was HTTP 200 with full balance data for alice and bob.*
