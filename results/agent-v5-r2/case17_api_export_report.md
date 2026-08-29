# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Household balances endpoint missing membership authorization check

`ledgerly/api.py:156` — security

get_household_balances (ledgerly/api.py:156-169) takes a household_id from query params and calls household.balances(db, hid) directly without ever verifying that request.user_id is a member of that household (contrast with post_household_expense at line 172, which correctly calls household.add_shared_expense -> require_member). Any authenticated user can supply an arbitrary/guessed household_id (small sequential integers) and read the full list of member user_ids and their net financial balances for a household they do not belong to, leaking other users' financial data. This is an IDOR / broken object-level authorization vulnerability introduced by this PR.

*Verified: Read ledgerly/api.py:156-169 (get_household_balances) and ledgerly/household.py — neither calls require_member; household.balances() only checks members_of() to build the response, never checks the requesting user. Grepped for require_member usage across ledgerly/*.py: only used in remove_member and add_shared_expense, never in the balances path. Reproduced live: created household with alice (owner) and bob, added a $10 shared expense, then logged in as carol (a registered user with no membership in that household) and called GET /household/balances?household_id=<hid> with carol's own valid bearer token.*

## 2. [MAJOR] Household expense amount parsed with float arithmetic instead of parse_money, causing off-by-one-cent errors

`ledgerly/api.py:176` — correctness

post_household_expense converts the amount with `int(float(request.body["amount"]) * 100)` instead of using the existing `parse_money` helper (used by post_expense and post_budget). Binary floating point cannot represent many decimal fractions exactly, so e.g. `float("9.99") * 100` evaluates to 998.9999999999999, and `int()` truncates it to 998 cents ($9.98) instead of 999 ($9.99). Money for shared/household expenses is silently short-changed by a cent for many common inputs (9.99, 19.99, 29.99, etc.), which then corrupts `household.balances()` totals and settlement calculations that assume exact integer cents.

*Verified: Read ledgerly/api.py:176, confirmed it uses `int(float(request.body["amount"]) * 100)` instead of the `parse_money` helper used elsewhere. Verified via Python execution: while the reviewer's specific cited example (float('9.99')*100 == 999.0, rounds correctly) was slightly inaccurate, a sweep of all cent values from 0.00 to 199.99 showed 1145/20000 values truncate incorrectly by exactly one cent (e.g. '0.29'->28, '19.99'->1998, '2.01'->200), whereas ledgerly.utils.parse_money correctly returns 29, 1999, 201 for the same inputs.*

## 3. [MAJOR] CSV export does not escape/quote fields, corrupting rows when note contains a comma or newline

`ledgerly/api.py:200` — correctness

get_export builds each CSV line via plain string interpolation `f"{r['spent_on']},{r['category']},{amount},{r['note']}"` with no quoting or escaping. `note` is free-form user text up to 500 characters (see expenses.add_expense/MAX_NOTE_LEN) with no character restrictions. If a note contains a comma (e.g. "coffee, lunch"), the resulting line has five comma-separated fields instead of four, shifting/breaking any downstream CSV parser's column alignment. If a note contains a newline, the note content is split across CSV lines, producing a bogus extra row that doesn't match the declared `spent_on,category,amount,note` header schema. This breaks the endpoint's documented purpose of producing valid CSV output for arbitrary user expenses.

*Verified: Read ledgerly/api.py:187-202 (get_export) and ledgerly/expenses.py (add_expense/MAX_NOTE_LEN=500, no character restriction). Reproduced with executable script: registered a user, added an expense with note='coffee, lunch', called GET /export, and parsed the resulting body with Python's csv module — header row has 4 fields but the data row parses into 5 fields (['2026-03-01','food','12.50','coffee',' lunch']), confirming column misalignment. Also added an expense with note='line1\nline2' and confirmed the exported body splits into 3 lines instead of 2 (a bogus extra row).*

## 4. [MINOR] Household-expense test uses only a round dollar amount, hiding the float-conversion bug in the new handler

`tests/test_api.py:93` — test-adequacy

post_household_expense (ledgerly/api.py:176) converts the amount with `int(float(request.body["amount"]) * 100)` instead of the existing `parse_money` helper used elsewhere. This raw float multiplication is prone to precision loss for many two-decimal amounts (e.g. `float("19.99") * 100 == 1998.9999999999998`, so `int(...)` truncates to 1998 instead of 1999). test_balances_for_own_household only ever exercises amount "10.00", a value with an exact binary float representation, so the resulting net_cents (500/-500) can never reveal the truncation bug. A test using a value like "19.99" or "0.29" would fail against the current implementation, but the chosen input silently passes regardless of whether the conversion is correct.

*Verified: Reproduced directly: python3 -c confirms float('19.99')*100 == 1998.9999999999998, so int(...) truncates to 1998 instead of 1999 cents, while float('10.00')*100 == 1000.0 exactly. Confirmed ledgerly/utils.py's parse_money uses correct string-based parsing (splits on decimal, no float multiplication) and is used everywhere else (post_expense, post_budget), but post_household_expense in api.py:176 bypasses it with raw `int(float(request.body["amount"]) * 100)`.*
