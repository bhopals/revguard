# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] Broken atomicity in import_statement: nested transactions commit independently

`ledgerly/importers.py:107` — correctness

The import_statement function claims to be atomic (lines 100-103: 'The whole batch succeeds or fails together: if any row cannot be imported, no expense from this statement is recorded'), but the implementation breaks this guarantee. The outer 'with db.transaction()' context manager (line 107) calls add_expense() (line 112), which internally calls db.execute() (expenses.py:24). This db.execute() method has its own nested transaction context manager (db.py:127) that calls commit() independently (db.py:128), immediately persisting each expense to the database. If any subsequent operation fails (e.g., an invalid category in the mapping at line 112), the exception propagates to the outer transaction handler, which calls rollback(). However, previous expenses are already committed and cannot be rolled back, leaving a half-imported statement in the database. Concrete failure: importing a 3-row statement where row 2 has an invalid category results in row 1 being committed to the database while the import_batches record is never inserted, violating the all-or-nothing contract.

*Verified: Read ledgerly/db.py: Database.transaction() is a plain contextmanager wrapping the single shared sqlite3 connection with commit()/rollback() and no savepoints; Database.execute() (used by add_expense via expenses.py:24) opens its own nested `with self.transaction()` block that calls self.conn.commit() immediately. Because there is only one underlying connection with no SAVEPOINT nesting, that inner commit() flushes ALL pending work on the connection, not just the row it inserted. Reproduced directly: ran import_statement with a 3-row statement and a category_map that fails on row 3 (or row 2) with an unknown category.*

## 2. [CRITICAL] Atomicity test does not verify rollback behavior

`tests/test_importers.py:69` — test-adequacy

test_atomic_batch imports a valid statement and verifies it succeeds. However, the PR's core feature is 'all-or-nothing batches' to prevent 'a half-imported statement' when a row fails. The test never exercises the rollback scenario: it should import a statement with an error partway through and verify that the entire batch (expenses and batch record) is rolled back. Currently it only tests the success path, leaving the atomicity guarantee untested.

*Verified: Read tests/test_importers.py in full (74 lines): TestAtomicity.test_atomic_batch only imports a valid statement and checks the success path; no test triggers a mid-batch failure to verify rollback. Executed a manual repro: import_statement(db, user, STATEMENT, category_map={'STREAM': 'yachts'}) raises ImportError_ on the 4th row as expected, but afterward `expenses` table has 2 rows (COFFEE CO, GROCER LTD) persisted while `import_batches` has 0 rows -- i.e. the batch is NOT rolled back atomically. Root cause: ledgerly/db.py Database.execute() wraps each call in its own `with self.transaction(): ...*

## 3. [MAJOR] Duplicate detection overly broad: removed description from uniqueness check

`ledgerly/importers.py:90` — correctness

The _is_duplicate function was changed from checking (user_id, spent_on, amount_cents, note) to checking only (user_id, spent_on, amount_cents). This causes legitimate different transactions on the same date with the same amount but different descriptions to be incorrectly marked as duplicates. Concrete failure scenario: A statement contains two separate transactions on 2026-03-05: '-50.00, COFFEE SHOP' and '-50.00, DONUT PLACE'. Both are real expenses from different vendors. With the new code, the second row would be skipped as a duplicate, losing data that should be imported. The PR description mentions this was 'simplified and sped up', but the trade-off introduces a correctness defect where real transactions are silently discarded.

*Verified: Read ledgerly/importers.py:90-96 confirming _is_duplicate now queries only (user_id, spent_on, amount_cents), having dropped the `note` column from the old query (visible in diff). Reproduced the exact scenario from the finding via python3 -c: imported a statement with two 2026-03-05 rows of -50.00 each, 'COFFEE SHOP' and 'DONUT PLACE'. Result: imported=1, skipped=1, and monthly_summary shows only 5000 cents total instead of 10000 — the second legitimate transaction was silently discarded as a false-positive duplicate.*

## 4. [MAJOR] Category mapping requires uppercase keys but doesn't validate or document this

`ledgerly/importers.py:82` — correctness

The category_for() function's docstring (line 78) promises 'case-insensitive prefix rules', but the implementation is not fully case-insensitive. Line 82 checks 'if desc.upper().startswith(prefix)' where the description is uppercased but the prefix (from category_map keys) is not. This means a category_map like {'coffee': 'food'} will not match descriptions like 'COFFEE CO' because 'COFFEE CO'.startswith('coffee') is False. The mapping silently fails and falls back to DEFAULT_CATEGORY, contradicting the docstring's promise and violating the principle of least surprise. There is no validation or error message to alert users that their lowercase keys will not work as expected. Concrete failure: A user creates category_map={'coffee': 'food'} and imports a statement with 'COFFEE CO'. The expense is categorized as 'other' instead of 'food', silently contradicting the function's documented behavior.

*Verified: Read ledgerly/importers.py:77-87 and reproduced with `python3 -c`: category_for('COFFEE CO', {'coffee': 'food'})` returns 'other' while `category_for('COFFEE CO', {'COFFEE': 'food'})` returns 'food'. Line 82 does `desc.upper().startswith(prefix)` — only the description is uppercased, not the map key/prefix — so lowercase or mixed-case category_map keys silently never match and fall back to DEFAULT_CATEGORY, with no validation or error raised. This directly contradicts the function's own docstring ('case-insensitive prefix rules') and the module docstring's promise. The existing test suite only exercises uppercase keys ({'COFFEE': ..., 'STREAM': ...}), masking the bug.*
