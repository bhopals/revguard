# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] Atomic batch promise broken: add_expense commits each row individually inside the outer transaction

`ledgerly/importers.py:112` — correctness

import_statement wraps the row loop in `with db.transaction():` to fulfil its docstring promise that "the whole batch succeeds or fails together". However, each row is inserted via add_expense (ledgerly/expenses.py:24), which calls `db.execute(...)` (ledgerly/db.py:126). db.execute itself opens its own `with self.transaction():` block and calls `self.conn.commit()` immediately after the INSERT succeeds (ledgerly/db.py:109-116). Because sqlite3's implicit transaction is connection-wide (not a real nested/savepoint transaction), this inner commit() commits everything pending on the connection right after each expense insert, not at the end of the outer `with db.transaction():` block. Concrete failure: import_statement(db, user, STATEMENT, category_map={"COFFEE": "food", "GROCER": "badcat"}) processes COFFEE CO first -> add_expense succeeds and is committed immediately by the inner transaction. On the next row, category_for raises ImportError_ because "badcat" is not in VALID_CATEGORIES. The exception propagates to the outer `with db.transaction()`, which calls self.conn.rollback() -- but there is nothing left to roll back for the COFFEE CO row since it was already committed. The result is a half-imported statement (one expense persisted, no import_batches row created, exception raised to the caller), exactly the scenario the docstring and PR description claim is now prevented.

*Verified: Read ledgerly/db.py: Database.execute() wraps its INSERT in its own `with self.transaction()` block which calls self.conn.commit() unconditionally on success (lines 109-129). add_expense (expenses.py:24) calls db.execute for the INSERT. import_statement (importers.py:99-120) wraps the row loop in an outer `with db.transaction():` but each add_expense call triggers its own inner commit via db.execute, since sqlite3 transactions are connection-wide there's no real nesting/savepoint. Reproduced directly: ran import_statement with STATEMENT containing COFFEE CO (valid mapping) then GROCER LTD (mapped to invalid category 'badcat').*

## 2. [CRITICAL] TestAtomicity.test_atomic_batch never exercises a failure/rollback path

`tests/test_importers.py:68` — test-adequacy

This test only runs import_statement with a fully valid statement and asserts the same happy-path outcome already covered by TestImport.test_import_and_reimport / test_batch_recorded (lines 38-50). It contains no row that fails partway through the batch, so it cannot detect whether the new `with db.transaction()` wrapper actually rolls back previously-inserted rows on a later failure. In fact, db.execute() (used inside add_expense, ledgerly/db.py:126-129) opens and commits its own nested transaction for every row, so each row is committed to disk as soon as it's inserted regardless of the outer transaction in import_statement — the 'atomic batch' feature the PR advertises does not actually prevent partial imports. Because this test never introduces a mid-batch failure (e.g. a row with an invalid category via category_map, or a bad note length) and then checks that expenses/import_batches have zero rows, it would pass identically whether atomicity is implemented correctly, implemented incorrectly, or not implemented at all — it cannot fail for the very behavior it is named after.

*Verified: Read ledgerly/db.py: db.execute() wraps each call in its own `with db.transaction()`, which calls self.conn.commit() on success. Since sqlite3 has one real connection-level transaction (no savepoints/nesting used here), this inner commit inside add_expense (called per-row from import_statement) permanently commits to disk regardless of the outer `with db.transaction()` in import_statement. Reproduced directly: ran import_statement with a category_map that fails on the 4th/last row (STREAM->'yachts', an invalid category) after 2 rows (COFFEE, GROCER) were already processed.*

## 3. [MAJOR] Duplicate key (date, amount) causes false-positive duplicate detection, silently dropping legitimate rows

`ledgerly/importers.py:90` — correctness

_is_duplicate now matches solely on (user_id, spent_on, amount_cents), dropping the previous description/note comparison. Within a single statement (or across statements), two distinct, legitimate transactions that happen to share the same date and amount but have different descriptions (e.g. two unrelated $9.99 charges on the same day to different merchants) will be treated as duplicates: the second is silently counted as `skipped` and never inserted, even though it is not actually a duplicate of the first. This is a real data-loss regression versus the old (date, amount, note) key, and the existing test fixture (STATEMENT) has no two rows sharing date+amount, so this false-positive skip path is not exercised by the test suite.

*Verified: Read ledgerly/importers.py: _is_duplicate (line 90-96) now queries only on (user_id, spent_on, amount_cents), dropping the prior note/description comparison. Reproduced with the real Database/auth/importers modules: importing a CSV with two distinct legitimate transactions sharing date+amount but different descriptions ('Merchant A' and 'Merchant B', both -9.99 on 2026-03-01) yields imported=1, skipped=1, and only 'Merchant A' ends up in the expenses table — 'Merchant B' is silently dropped as a false-positive duplicate. Confirmed the existing STATEMENT fixture in tests/test_importers.py has no two rows sharing date+amount, so this path is untested.*

## 4. [MAJOR] category_for is not actually case-insensitive with respect to the mapping keys

`ledgerly/importers.py:82` — correctness

The module docstring and category_for's own docstring both promise 'case-insensitive prefix rules', but the implementation only upper-cases the description (`desc.upper().startswith(prefix)`) and never normalizes `prefix`. If a caller supplies a category_map with a lower- or mixed-case key, e.g. {"coffee": "food"}, and a description "COFFEE CO", then "COFFEE CO".startswith("coffee") is False (case mismatch), so the row silently falls through to DEFAULT_CATEGORY ("other") instead of being categorized as "food". This contradicts the documented case-insensitive behavior and will silently miscategorize transactions whenever a caller's mapping keys are not already all-uppercase.

*Verified: Read ledgerly/importers.py:82-90 category_for(); confirmed via python3 -c that 'COFFEE CO'.upper().startswith('coffee') is False while startswith('coffee'.upper()) is True. Only `desc` is uppercased, `prefix` (the mapping key) never is, so a mixed/lower-case category_map key fails to match an all-caps description and silently falls through to DEFAULT_CATEGORY ('other'). This directly contradicts the module docstring ('category mapping: case-insensitive prefix rules') and category_for's own docstring.*
