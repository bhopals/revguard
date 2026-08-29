# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Atomic-batch guarantee is broken: add_expense commits each row individually

`ledgerly/importers.py:107` — correctness

import_statement wraps the loop in `with db.transaction():` to make the batch all-or-nothing, but each row is inserted via add_expense (ledgerly/expenses.py:24), which itself calls db.execute -> `with self.transaction(): ... self.conn.commit()` (ledgerly/db.py:126-129, 109-116). sqlite3's Python transaction model has no real nesting/savepoints here, so that inner commit() commits the connection's entire pending transaction, including any earlier rows added in the same outer `with db.transaction():` block. Concretely: import a 3-row statement where row 3 triggers a failure after rows 1-2 succeeded (e.g. category_for raises ImportError_ for row 3's mapped category, or add_expense raises ExpenseError for a too-long note on row 3). Rows 1 and 2 are already durably committed by the time row 3's exception propagates to the outer `with db.transaction()` handler, which then rolls back a connection that has nothing left to undo. The statement ends up half-imported and no import_batches row is written for it, directly contradicting the PR's stated guarantee ('a bad row no longer leaves a half-imported statement') and the function's own docstring ('The whole batch succeeds or fails together'). The existing tests never hit this because the only failure-path test (test_mapping_to_unknown_category) fails on the very first row (COFFEE CO), so there are no prior successful inserts to observe as leaked.

## 2. [MAJOR] Duplicate key dropped description, causing false positives within/across a single statement

`ledgerly/importers.py:90` — correctness

_is_duplicate now matches solely on (user_id, spent_on, amount_cents), no longer on note/description. Two distinct real transactions on the same date for the same amount but different merchants (e.g. a $12.50 coffee and a $12.50 taxi fare on the same day) will now cause the second to be silently skipped as a 'duplicate', including within a single import batch: add_expense's insert (via db.execute) is committed to the same connection before the next row's _is_duplicate check runs, so an earlier legitimate row in the same statement can shadow a later legitimate row. The previous code (keyed on date+amount+note) did not have this false-positive risk. This silently drops real spend data with no error surfaced to the caller (it just increments skipped_duplicates).

## 3. [MAJOR] category_for is not actually case-insensitive on the mapping keys, contradicting its own docstring

`ledgerly/importers.py:82` — correctness

category_for's docstring promises 'case-insensitive prefix rules', but the implementation only uppercases the description (`desc.upper()`) and compares it against `prefix` as-supplied. If a caller supplies a category_map with a lower- or mixed-case prefix (e.g. {"coffee": "food"}), `desc.upper().startswith(prefix)` compares an all-uppercase string against a lowercase prefix and never matches, so every matching description silently falls back to DEFAULT_CATEGORY instead of being mapped. This only appears to work in the tests/docstring example because both use all-uppercase prefixes ("COFFEE", "STREAM"); any caller relying on the stated case-insensitive contract with non-uppercase prefixes gets silently wrong categorization with no error raised.

## 4. [?] TestAtomicity never exercises a failing batch, so rollback logic is unverified

`tests/test_importers.py:68` — test-adequacy

test_atomic_batch (tests/test_importers.py:69-74) just re-runs the plain happy-path import already covered by TestImport.test_import_and_reimport — it imports a clean statement and checks imported/skipped counts and the batch row, with no failure injected. The PR's core new claim is that 'a malformed row no longer leaves a half-imported statement behind' via db.transaction() wrapping the loop (ledgerly/importers.py:107-119), but no test ever causes a row after a successful add_expense to fail (e.g. a later description mapping to an invalid category, or a duplicate-check hitting an error) and then asserts that the expenses table and import_batches table contain zero rows for that statement. If the rollback wiring were broken (e.g. db.conn.execute at line 115 bypassing the transaction, or an exception swallowed before propagating), this test suite would not catch it — the only failure test (test_mapping_to_unknown_category) fails on the very first row of STATEMENT, so it can't distinguish 'nothing was ever inserted' from 'inserted rows were rolled back'.
