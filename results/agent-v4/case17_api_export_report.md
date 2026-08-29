# Code review: CSV export endpoint + household API

> Adds GET /export (download expenses as CSV), and first household endpoints: GET /household/balances and POST /household/expenses. Also tidies the handler layer: field validation renamed to _require_fields and route registrations grouped by resource.

**Verdict: request changes.** 3 blocking finding(s), 0 critical.

## 1. [MAJOR] Household expense amount parsed with float arithmetic instead of parse_money, causing cent-level rounding errors

`ledgerly/api.py:176` — correctness

post_household_expense computes cents as int(float(request.body["amount"]) * 100) instead of using the existing parse_money() helper (used by post_expense and post_budget). Standard binary-float rounding means many valid two-decimal amounts truncate to the wrong number of cents, e.g. float("19.99")*100 == 1998.9999999999998, and int() truncates (not rounds) to 1998 instead of 1999; float("0.1")*100 == 9.999999999999998 -> 9 cents instead of 10. Every shared expense recorded with such an amount silently undercharges the payer by 1 cent, corrupting household.balances() ledger totals. It also bypasses parse_money's format validation (e.g. "1e2" or 3+ decimal digits are silently accepted/mis-truncated instead of rejected), diverging from the money-handling contract enforced everywhere else in the codebase.

*Verified: Read ledgerly/api.py:176 confirming `cents = int(float(request.body["amount"]) * 100)` is used in post_household_expense, unlike post_expense/post_budget which use parse_money(). Reproduced end-to-end: registered users, created a household, and POSTed a shared expense with amount '19.99' via api.handle(). The stored ledger (via GET /household/balances) showed net_cents of ±999 (i.e. $9.99 each / $19.98 total) instead of the correct $19.99, confirming the 1-cent truncation from float("19.99")*100 == 1998.9999999999998 -> int() == 1998. Also confirmed parse_money's format validation is bypassed (float('1e2') parses to 100 without error, whereas parse_money's regex would reject '1e2').*

## 2. [MAJOR] CSV export does not escape fields, producing malformed CSV when note contains a comma or newline

`ledgerly/api.py:200` — correctness

get_export builds each CSV row via an unescaped f-string: f"{r['spent_on']},{r['category']},{amount},{r['note']}". The note field (expenses.add_expense allows up to 500 arbitrary characters, no comma/newline restriction) is not quoted or escaped. Any expense whose note contains a comma (e.g. note="lunch, with friends") produces a row with an extra unquoted field, shifting/breaking column alignment for any CSV consumer; a note containing a newline splits into multiple malformed lines. Since this endpoint's entire purpose is to produce a valid CSV file for download, this is a correctness defect in the export's core contract, not a hypothetical edge case.

*Verified: Read ledgerly/api.py get_export (line ~200): rows are built via unescaped f-string `f"{r['spent_on']},{r['category']},{amount},{r['note']}"`. Confirmed expenses.add_expense only restricts note length (MAX_NOTE_LEN), not content. Reproduced via direct execution: added an expense with note='lunch, with friends', then called GET /export and parsed the resulting body with Python's csv module — header row parsed to 4 fields but the data row parsed to 5 fields (['2026-03-01','food','12.50','lunch',' with friends']), confirming misaligned/malformed CSV.*

## 3. [MAJOR] Missing membership check on GET /household/balances (IDOR)

`ledgerly/api.py:162` — security

get_household_balances (ledgerly/api.py:156-169) takes household_id from the query string and passes it straight to household.balances(db, hid) without ever verifying that request.user_id is a member of that household (household.require_member, used by add_shared_expense at ledgerly/household.py:87, is never invoked here). Any authenticated user can call GET /household/balances?household_id=<N> for an arbitrary household id and receive the net balance, user_id list, and financial position of every member of a household they do not belong to, simply by enumerating small integer ids. This is an authorization bypass (IDOR) exposing other users' financial data, inconsistent with the ownership scoping used everywhere else in the codebase (e.g. expenses.list_expenses/get_expense/delete_expense all filter by user_id, and add_shared_expense enforces require_member).

*Verified: Read ledgerly/api.py get_household_balances (line ~156-169): it parses household_id from query params and calls household.balances(db, hid) directly, with no call to household.require_member or any check that request.user_id belongs to that household. Confirmed household.require_member exists (household.py:42) and is used by add_shared_expense/remove_member but grep shows it is never invoked in api.py. Wrote and ran a live exploit: registered alice/bob/mallory, created a household with alice+bob and a shared expense, then called api.handle with mallory's (non-member) auth token against GET /household/balances?household_id=<hid>.*
