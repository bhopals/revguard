# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 4 blocking finding(s), 1 critical.

## 1. [CRITICAL] Atomic-batch guarantee is not actually atomic: add_expense commits each row individually

`ledgerly/importers.py:112` — correctness

import_statement wraps the row loop in `with db.transaction():` (importers.py:107) and its own docstring (lines 100-103) promises 'if any row cannot be imported, no expense from this statement is recorded.' But add_expense (expenses.py:24) inserts via db.execute, and Database.execute (db.py:126-129) itself opens `with self.transaction():` and calls self.conn.commit() immediately after each insert. Because Database.transaction() has no nesting/reference-count guard, every row's insert is committed to the connection the instant add_expense returns, regardless of the outer `with db.transaction():` in import_statement. Concretely: with STATEMENT rows COFFEE CO, GROCER LTD, ... and category_map={'GROCER': 'invalidcat'}, row 1 (COFFEE CO) is added_expense'd and committed to the DB immediately; row 2's category_for('GROCER LTD', ...) then raises ImportError_ (line 84) before add_expense is even called for that row. The exception propagates out of the for-loop and out of `with db.transaction()`, which calls conn.rollback() — but there is nothing left uncommitted to roll back, since row 1's insert was already committed by the nested db.execute call. The import_batches audit row is never written (its insert is after the loop), yet the COFFEE CO expense is now permanently persisted despite the whole statement having 'failed'. This directly contradicts the PR's core feature and its own docstring, and TestAtomicity/test_mapping_to_unknown_category in tests/test_importers.py does not catch it because the invalid-category row happens to be the very first row parsed, so no prior row is ever committed in that test.

*Verified: Read db.py: Database.execute() (line 126-129) wraps each call in its own `with self.transaction()` which commits self.conn immediately, with no nesting/refcount guard against the outer `with db.transaction()` in import_statement. add_expense (expenses.py:24) calls db.execute for every row insert. Reproduced with a live sqlite3-backed Database: imported a 2-row statement where row 1 (COFFEE CO) is *

## 2. [MAJOR] Duplicate check dropped description, silently discarding legitimate same-day/same-amount expenses

`ledgerly/importers.py:90` — correctness

_is_duplicate (importers.py:90-96) now matches on (user_id, spent_on, amount_cents) only, having dropped the `note` column entirely from the WHERE clause. Any two distinct real transactions that share the same date and amount — e.g. two separate $9.99 purchases on the same day at different merchants, or a coffee and an unrelated $12.50 purchase on the same date — will cause the second to be treated as a duplicate of the first and silently skipped (imported count under-reports, skipped count over-reports, and the second real expense is never recorded). Because add_expense's inserts are committed immediately (see the atomicity finding), this also applies within a single statement: two data rows in the same import with matching date+amount but different descriptions will have the second one skipped as a 'duplicate' even though it is a genuine separate transaction. This silently drops the discrimination the old code guaranteed (matching on date, amount, AND description) without any corresponding safeguard, and is a real data-loss regression, not merely a performance simplification.

*Verified: Read ledgerly/importers.py: _is_duplicate's SQL query only checks user_id, spent_on, amount_cents (note/desc removed from WHERE clause per diff). Reproduced live: imported a 2-row statement with same date/amount but different descriptions ('Coffee Shop A' vs 'Random Store B'); result was imported=1, skipped=1, and only the first expense was actually persisted in the DB — the second real transactio*

## 3. [MAJOR] TestAtomicity test never exercises a failing/rolled-back import

`tests/test_importers.py:68` — test-adequacy

test_atomic_batch (lines 68-74) imports the fully-valid STATEMENT and just re-asserts the normal-success counts and batch row already covered by TestImport.test_import_and_reimport/test_batch_recorded. It never triggers a mid-batch failure (e.g. a row with an unknown-category mapping, or a bad row appended after valid rows), so it cannot detect a regression where the new `with db.transaction():` wrapping is broken or removed and a bad row leaves a half-imported statement — exactly the bug this PR claims to fix. As written, this test would pass even if atomicity were never implemented.

*Verified: Read tests/test_importers.py: TestAtomicity.test_atomic_batch only imports the fully-valid STATEMENT and asserts (3,0) plus imported_count==3 — identical assertions to TestImport.test_import_and_reimport/test_batch_recorded. No failing/mid-batch-invalid row is ever exercised, and TestCategoryMapping.test_mapping_to_unknown_category (the only test that triggers an ImportError_) never inspects the e*

## 4. [MAJOR] Unknown-category test doesn't verify rollback of already-inserted rows

`tests/test_importers.py:62` — test-adequacy

test_mapping_to_unknown_category only asserts that ImportError_ is raised; it never checks that expenses/import_batches remain empty afterward. Additionally, the failing mapping targets 'COFFEE', which matches the very first data row in STATEMENT, so category_for() raises before any add_expense() call has succeeded — the test can't exercise or catch a rollback failure for rows that were already committed earlier in the same batch (e.g. if GROCER's expense had already been inserted before STREAM's category failed). A broken rollback (e.g. transaction() catching but not re-raising, or add_expense committing per-row) would still pass this test.

*Verified: Read tests/test_importers.py: test_mapping_to_unknown_category only asserts pytest.raises(ImportError_), no assertion on expenses/import_batches tables. Confirmed via execution that category_for('COFFEE CO', ...) raises on the very first STATEMENT row, before any add_expense call, so the test can never observe a rollback failure. To prove the gap is real (not just hypothetical), I ran import_state*
