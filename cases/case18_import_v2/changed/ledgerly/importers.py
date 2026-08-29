"""Bank statement import.

Supports simple CSV exports: a header row naming date, amount, and
description columns (several common spellings accepted), then data rows.
Amounts in statements are negative for spend; we import spend as positive
cents and skip credits.

v2 additions:
- category mapping: case-insensitive prefix rules applied to the
  description, e.g. {"COFFEE": "food", "STREAM": "entertainment"}.
- atomic batches: a statement imports all-or-nothing, so a malformed row
  no longer leaves a half-imported statement behind.
- faster duplicate detection keyed on (date, amount).
"""

import csv
import io

from .expenses import VALID_CATEGORIES, add_expense
from .utils import parse_iso_date, parse_money, utcnow_iso

DATE_HEADERS = {"date", "posted", "transaction date"}
AMOUNT_HEADERS = {"amount", "value", "debit"}
DESC_HEADERS = {"description", "memo", "payee", "details"}

DEFAULT_CATEGORY = "other"


class ImportError_(Exception):
    pass


def _find_column(headers, names):
    for i, h in enumerate(headers):
        if h.strip().lower() in names:
            return i
    return None


def parse_statement(text):
    """Parse CSV text into (spent_on_iso, amount_cents, description) rows.

    Raises ImportError_ with a row number on malformed data. Credit rows
    (positive statement amounts) are skipped.
    """
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration:
        raise ImportError_("empty file")
    di = _find_column(headers, DATE_HEADERS)
    ai = _find_column(headers, AMOUNT_HEADERS)
    ci = _find_column(headers, DESC_HEADERS)
    if di is None or ai is None:
        raise ImportError_("could not find date/amount columns in header")
    rows = []
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        try:
            d = parse_iso_date(row[di])
        except (ValueError, IndexError):
            raise ImportError_(f"row {lineno}: bad date {row[di]!r}")
        raw_amount = row[ai].strip()
        negative = raw_amount.startswith("-")
        try:
            cents = parse_money(raw_amount.lstrip("-"))
        except (ValueError, IndexError):
            raise ImportError_(f"row {lineno}: bad amount {raw_amount!r}")
        if not negative:
            continue  # credit / refund: not a spend
        desc = row[ci].strip() if ci is not None and ci < len(row) else ""
        rows.append((d.isoformat(), cents, desc))
    return rows


def category_for(desc, category_map):
    """Resolve a description to a category via case-insensitive prefix
    rules; falls back to DEFAULT_CATEGORY."""
    if category_map:
        for prefix, category in category_map.items():
            if desc.upper().startswith(prefix):
                if category not in VALID_CATEGORIES:
                    raise ImportError_(f"mapping targets unknown category:"
                                       f" {category}")
                return category
    return DEFAULT_CATEGORY


def _is_duplicate(db, user_id, spent_on, amount_cents):
    row = db.query_one(
        "SELECT id FROM expenses WHERE user_id = ? AND spent_on = ?"
        " AND amount_cents = ?",
        (user_id, spent_on, amount_cents),
    )
    return row is not None


def import_statement(db, user_id, text, source="csv", category_map=None):
    """Import a statement atomically. Returns (imported, skipped_duplicates).

    The whole batch succeeds or fails together: if any row cannot be
    imported, no expense from this statement is recorded.
    """
    rows = parse_statement(text)
    imported = skipped = 0
    with db.transaction():
        for spent_on, cents, desc in rows:
            if _is_duplicate(db, user_id, spent_on, cents):
                skipped += 1
                continue
            add_expense(db, user_id, cents, category_for(desc, category_map),
                        spent_on, desc)
            imported += 1
        db.conn.execute(
            "INSERT INTO import_batches (user_id, source, row_count,"
            " imported_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, source, len(rows), imported, utcnow_iso()),
        )
    return imported, skipped
