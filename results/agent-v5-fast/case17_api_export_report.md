# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] Missing authorization check in /household/balances endpoint

`ledgerly/api.py:156` — security

The GET /household/balances endpoint does not verify that the requesting user is a member of the household before returning financial information. The function takes household_id from request parameters and immediately calls household.balances(db, hid) without calling household.require_member(). This allows any authenticated user to view the balances of any household if they know (or guess) the household_id. Compare this to POST /household/expenses (line 177) which properly calls household.add_shared_expense(), which internally enforces membership at line 87 of household.py. The test at line 87 (test_balances_for_own_household) only tests the authorized case; there is no test verifying that non-members cannot access balances. Failure scenario: User A creates a household with ID 5. User B, completely unrelated and not a member, authenticates and calls GET /household/balances?household_id=5 to view all members' financial positions.

*Verified: Read household.py: require_member() exists and is called by add_shared_expense() (line 87) but get_household_balances() in api.py calls household.balances(db, hid) directly with no membership check. Reproduced live: created a household owned by alice with a $50 shared expense; logged in as bob, an unrelated registered user never added as a member, and called GET /household/balances?household_id=<hid> with bob's valid token -> got HTTP 200 with the full balances array (alice's net_cents exposed).*

## 2. [CRITICAL] CSV injection vulnerability in /export endpoint

`ledgerly/api.py:200` — security

The GET /export endpoint constructs CSV output by directly concatenating user data without proper escaping (line 200: `lines.append(f"{r['spent_on']},{r['category']},{amount},{r['note']}")`). This creates two vulnerabilities: (1) Formula injection - if any field starts with `=`, `+`, `@`, or `-`, spreadsheet applications (Excel, Google Sheets) interpret it as a formula and execute it, allowing code execution. (2) CSV format corruption - fields containing commas or newlines are not quoted, breaking the CSV structure. The codebase already demonstrates proper CSV handling in importers.py (line 41) using csv.reader; the export should use csv.writer to properly quote fields. The test at line 113 (test_export_csv) only tests benign input and does not verify escaping. Failure scenario: User creates an expense with note '=cmd|\'/c calc\'!A1'. When another user downloads and opens the CSV in Excel, the formula executes, launching calculator or arbitrary commands.

*Verified: Read ledgerly/api.py get_export (lines ~186-201): CSV rows are built via f-string concatenation with no escaping/quoting. Reproduced via direct script calling api.handle(): (1) posted an expense with note '=cmd|'/c calc'!A1' and confirmed the export body contains the raw unescaped formula string starting with '=', which Excel/Sheets would execute as a formula; (2) posted an expense with note containing a comma and newline ('line1\nline2,extra,fields') and confirmed that parsing the exported body with Python's standard csv.reader splits it into two malformed rows (['2026-03-02','food','5.00','line1'] and ['line2','extra','fields']), proving CSV structural corruption.*

## 3. [MAJOR] Floating-point precision loss in household expense amount conversion

`ledgerly/api.py:176` — correctness

Line 176 uses `int(float(request.body["amount"]) * 100)` to convert currency strings to cents, which loses precision due to floating-point arithmetic. For example, float("10.99") * 100 = 1098.9999..., truncating to 1098 cents instead of the correct 1099. This creates incorrect expense amounts and balance calculations. The regular /expenses endpoint correctly uses parse_money() on line 101. Failure scenario: User posts household expense with amount "10.99" (or other problematic values like "1.29"), resulting in a 1-cent discrepancy in household balances and settlement calculations.

*Verified: Reproduced end-to-end: posted a household expense with amount '19.99' via POST /household/expenses, then queried GET /household/balances. The stored amount_cents came back as 1998 instead of 1999 (net_cents 999/-999), confirming `int(float(request.body["amount"]) * 100)` at ledgerly/api.py:176 truncates due to float imprecision (`float('19.99')*100 == 1998.9999999999998`), directly corrupting household ledger balances. Confirmed the sibling /expenses endpoint (api.py:101) instead uses `parse_money()` which parses the decimal string exactly via regex/int arithmetic, avoiding this class of bug entirely (ledgerly/utils.py:13-28).*

## 4. [MAJOR] Test name promises membership check not verified

`tests/test_api.py:87` — test-adequacy

The test is named 'test_balances_for_own_household' which promises the endpoint restricts access to the user's own household. However, the test only verifies the happy path where the user IS a member of the household. It does not test that accessing a household the user is not a member of fails or is denied. Examining get_household_balances (api.py:156-169), there is NO membership verification in the endpoint—it accepts any household_id without checking if request.user_id is a member. The test would pass even if this authorization were completely missing. Failure scenario: a non-member requesting GET /household/balances?household_id=<other_hid> would return balances, but this test cannot detect it.

*Verified: Read household.py: require_member() exists and is called by add_shared_expense/add_member/remove_member, but get_household_balances in api.py:156-169 calls household.balances(db, hid) directly with no require_member/membership check. Reproduced with a live script: registered alice/bob/carol, created a household with alice+bob, added a shared expense, then logged in as carol (never added as a member) and called GET /household/balances?household_id=<hid> with her own valid token — got HTTP 200 with the full balances of alice and bob, confirming any authenticated user can read any household's financial data by guessing/enumerating household_id.*
