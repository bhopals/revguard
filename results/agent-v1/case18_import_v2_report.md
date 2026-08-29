# Code review: Importer v2: category mapping and atomic batches

> Statement import learns two things users kept asking for: map merchant descriptions to categories (case-insensitive prefix rules, e.g. 'COFFEE' -> food), and all-or-nothing batches so a bad row no longer leaves a half-imported statement. Duplicate detection was also simplified and sped up by keying on (date, amount).

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] "Atomic" batch import is not atomic: rows are committed individually via nested transactions

`ledgerly/importers.py:112` — correctness

import_statement wraps the row loop in `with db.transaction():` (line 107) to make the batch all-or-nothing, but add_expense() calls db.execute() (expenses.py:24, db.py:126-129), which opens its own `with db.transaction():` and calls self.conn.commit() immediately after each insert. sqlite3's connection has no real nested-transaction/savepoint support here, so each per-row commit() commits the whole current transaction, including all expenses added earlier in the same import loop. If a later row fails category_for()'s unknown-category check (line 83-85) and raises ImportError_, the outer transaction's except-block calls self.conn.rollback(), but the earlier rows are already permanently committed and there is nothing left to roll back. Concretely: import a 4-row statement with category_map={"STREAM": "yachts"} where STREAM is the last matching row — the first three expenses get inserted and committed, the import_batches row never gets written (its insert never runs), and the function raises instead of returning (imported, skipped). This directly contradicts the documented and tested guarantee ('if any row cannot be imported, no expense from this statement is recorded') and leaves the database in a half-imported state with no audit record, which the PR explicitly claims to prevent. The existing test (test_mapping_to_unknown_category) doesn't catch this because it maps the very first row's prefix, so no prior row is ever committed before the failure.

## 2. [MAJOR] category_for is not actually case-insensitive for the mapping keys

`ledgerly/importers.py:82` — correctness

The docstring and PR description promise 'case-insensitive prefix rules', but category_for() only upper-cases the description (`desc.upper()`) and compares it against `prefix` as-is, without upper-casing the prefix. A category_map with a lower- or mixed-case key, e.g. {"Coffee": "food"} or {"stream": "entertainment"} — a very natural way to write these rules since the target category values themselves are lowercase — will never match any description, silently falling back to DEFAULT_CATEGORY ('other') for every transaction that should have been categorized. The only test (test_prefix_mapping) happens to use all-uppercase keys, so this regression is not caught.

## 3. [MAJOR] Duplicate detection keyed only on (date, amount) causes silent data loss for distinct same-day, same-amount transactions

`ledgerly/importers.py:92` — correctness

_is_duplicate() was changed to match only on (user_id, spent_on, amount_cents), dropping the description/note that was previously part of the key. Two genuinely distinct transactions that happen to share the same date and amount — e.g. two separate $9.99 charges on the same day from different merchants, or two identical-price coffee purchases in one day — will now cause the second one to be treated as a duplicate and silently skipped, even within a single statement import (each add_expense call commits immediately per the nested-transaction bug, so the row is visible to the very next _is_duplicate() check in the same loop). This is a real regression from the prior behavior (which also compared note/description) and results in legitimate expenses being dropped without any error or warning — they're just counted as 'skipped duplicates' — which is a meaningful correctness/data-loss issue for a financial ledger.
