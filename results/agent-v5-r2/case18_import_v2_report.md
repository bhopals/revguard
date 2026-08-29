# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 5 blocking finding(s), 3 critical.

## 1. [CRITICAL] Atomic batch guarantee is broken: each add_expense call commits independently

`ledgerly/importers.py:112` — correctness

import_statement wraps the row loop in `with db.transaction():` (line 107) to make the batch all-or-nothing, per its own docstring: 'if any row cannot be imported, no expense from this statement is recorded.' But add_expense() (ledgerly/expenses.py:24) calls db.execute(), and Database.execute() (ledgerly/db.py:126-129) itself wraps the insert in `with self.transaction():`, which calls self.conn.commit() immediately after each successful insert (db.py:113). Since Database uses a single sqlite3 connection with no savepoints, this inner commit commits the *entire* connection state, including all previously-inserted rows from earlier iterations of the same batch. Concrete failure: import a statement where row 1 maps to a valid category (committed and durable) and row 3's category_for() raises ImportError_ (e.g. category_map={'GROCER': 'yachts'} against the STATEMENT fixture, where 'COFFEE CO' is inserted/committed first and then 'GROCER LTD' triggers the exception). import_statement raises, the outer `with db.transaction()` rolls back, but the row-1 expense was already committed by the earlier nested transaction and remains permanently in the database — producing exactly the half-imported statement the PR claims to prevent. The existing test (test_mapping_to_unknown_category) does not catch this because its category_map matches on the very first data row, so no prior row is ever committed.

*Verified: Read db.py: Database.transaction() (lines 109-116) commits self.conn unconditionally on success, and Database.execute() (126-129) wraps every single insert in its own nested `with self.transaction()`. add_expense() (expenses.py:24) calls db.execute(). Since sqlite3 has one connection and no savepoints are used, each add_expense call inside import_statement's outer `with db.transaction():` loop commits the entire connection state immediately. Reproduced directly: called import_statement(db, user, STATEMENT, category_map={'GROCER': 'yachts'}) which raises ImportError_ on the 2nd data row (GROCER LTD) after the 1st row (COFFEE CO) was already inserted.*

## 2. [CRITICAL] TestAtomicity never exercises a failing/partial batch

`tests/test_importers.py:68` — test-adequacy

The PR's core promise, stated in the description and the import_statement docstring, is that 'a malformed row no longer leaves a half-imported statement behind' and the batch is 'all-or-nothing'. TestAtomicity.test_atomic_batch (lines 68-74) only imports a fully valid STATEMENT and asserts (imported, skipped) == (3, 0) and imported_count == 3 — this is a duplicate of the pre-existing TestImport.test_batch_recorded happy-path check and contains no scenario where a row fails partway through the batch. It never constructs a statement where an earlier row succeeds and a later row fails (e.g. via a bad category mapping matching a later description, or any other mid-batch failure), so it can never detect a broken rollback where some expenses from the batch get persisted while others don't. The test class/method name promises atomicity coverage it does not provide.

*Verified: Read tests/test_importers.py: TestAtomicity.test_atomic_batch (lines 68-74) only imports a fully-valid STATEMENT and duplicates TestImport.test_batch_recorded; it never triggers a mid-batch failure. I then built the exact scenario the finding describes (a category_map where an early row succeeds and a later row targets an unknown category) and ran it against the real repo: import_statement raised ImportError_ as expected, but 2 of 3 expenses were left committed in the database (expenses before=0, after=2), and a second run confirmed COFFEE/GROCER rows persisted while STREAM's mapping failed.*

## 3. [CRITICAL] test_mapping_to_unknown_category checks only that an exception is raised, not that the batch rolled back

`tests/test_importers.py:62` — test-adequacy

This test uses category_map={"COFFEE": "yachts"} against STATEMENT, where 'COFFEE CO' is the very first row processed, so category_for raises ImportError_ before any prior row in this batch could have been committed — the test can pass even if rollback is completely broken. Additionally, after catching the raised ImportError_, the test never queries the database to confirm that no expenses were inserted and no import_batches row was created (e.g. via db.query("SELECT * FROM expenses...") or db.query_one("SELECT * FROM import_batches...")). Given a statement where an earlier valid row (e.g. GROCER LTD) is processed and added successfully before a later row triggers the ImportError_ (e.g. a mapping targeting a later description), this test would still pass even if the earlier expense was left committed in the database, because it asserts only that the exception is raised and never inspects post-failure DB state.

*Verified: Read tests/test_importers.py: test_mapping_to_unknown_category only asserts pytest.raises(ImportError_) and never queries the DB afterward; STATEMENT's first row is 'COFFEE CO' so the {"COFFEE":"yachts"} mapping fails on row 1, before any row could be committed, so the test can't detect a broken rollback.*

## 4. [MAJOR] Duplicate detection dropped by description silently discards distinct same-day/same-amount expenses

`ledgerly/importers.py:91` — robustness

_is_duplicate now matches on (user_id, spent_on, amount_cents) only, having dropped the `note` column from the old query. This means import_statement will silently skip a genuinely new transaction if the user already has *any* expense (manually entered, from a prior unrelated import, or a coincidental match) on the same date with the same amount, regardless of description. Example: user manually logs a $12.50 expense on 2026-03-01 for 'PARKING'; later they import a statement containing an unrelated $12.50 charge on 2026-03-01 for 'COFFEE CO'. The import will treat it as a duplicate, increment `skipped`, and never insert the coffee expense — silently losing a legitimate transaction with no error or warning to the user, contradicting the old guarantee that only rows matching date+amount+description were treated as duplicates.

*Verified: Read ledgerly/importers.py post-PR: _is_duplicate (line 90-96) now queries only on (user_id, spent_on, amount_cents), dropping the `note`/description column from the WHERE clause that the old version had. Wrote a reproduction script instantiating a Database, manually adding an expense (PARKING, $12.50, 2026-03-01), then calling import_statement with a statement containing an unrelated COFFEE CO row for the same date/amount. Result: imported=0, skipped=1, and only the PARKING row exists in the DB afterward — the distinct COFFEE CO transaction was silently discarded with no error, exactly as the reviewer described.*

## 5. [MAJOR] category_for is only case-insensitive on the description, not on the mapping prefix

`ledgerly/importers.py:82` — correctness

The module docstring (lines 8-10) and category_for's own docstring (lines 78-79) promise 'case-insensitive prefix rules' for category mapping. The implementation only calls .upper() on `desc`, not on `prefix`: `if desc.upper().startswith(prefix):`. If a caller supplies a category_map with a lowercase or mixed-case key, e.g. {'coffee': 'food'}, it will never match an uppercase description like 'COFFEE CO' since 'COFFEE CO'.upper() == 'COFFEE CO' does not start with the literal string 'coffee'. Every mapped transaction silently falls through to DEFAULT_CATEGORY ('other') instead of raising or matching, contradicting the documented case-insensitive behavior. The tests only exercise uppercase prefixes ('COFFEE', 'STREAM'), so this gap is not caught.

*Verified: Read ledgerly/importers.py lines 77-87: category_for only calls .upper() on desc, never on prefix, so `if desc.upper().startswith(prefix)` compares an uppercased description against the literal (unmodified) mapping key. Ran `category_for('COFFEE CO', {'coffee': 'food'})` directly, which returned 'other' instead of 'food', while `category_for('COFFEE CO', {'COFFEE': 'food'})` correctly returned 'food'. This directly contradicts the module docstring (lines 8-10) and function docstring (lines 78-79), both of which promise case-insensitive prefix rules. Grepped for any normalization of `prefix`/category_map keys elsewhere (e.g. in expenses.py) and found none.*
