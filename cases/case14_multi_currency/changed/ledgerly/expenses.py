"""Expense CRUD and listing. Every operation is scoped to the owning user."""

from .utils import parse_iso_date, utcnow_iso

VALID_CATEGORIES = {
    "food", "transport", "housing", "utilities",
    "health", "entertainment", "other",
}

MAX_NOTE_LEN = 500
PAGE_SIZE = 20


class ExpenseError(Exception):
    pass


def add_expense(db, user_id, amount_cents, category, spent_on, note="", currency="USD"):
    if category not in VALID_CATEGORIES:
        raise ExpenseError(f"unknown category: {category}")
    if len(note) > MAX_NOTE_LEN:
        raise ExpenseError("note too long")
    d = parse_iso_date(spent_on)
    return db.execute(
        "INSERT INTO expenses (user_id, amount_cents, currency, category,"
        " note, spent_on, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, amount_cents, currency, category, note,
         d.isoformat(), utcnow_iso()),
    )


def get_expense(db, user_id, expense_id):
    row = db.query_one(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    if row is None:
        raise ExpenseError("expense not found")
    return dict(row)


def delete_expense(db, user_id, expense_id):
    # Verify ownership before deleting.
    get_expense(db, user_id, expense_id)
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )


def list_expenses(db, user_id, category=None, page=1):
    """Return one page of the user's expenses, newest first."""
    if page < 1:
        raise ExpenseError("page must be >= 1")
    sql = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]
    if category is not None:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY spent_on DESC, id DESC LIMIT ? OFFSET ?"
    params += [PAGE_SIZE, (page - 1) * PAGE_SIZE]
    return [dict(r) for r in db.query(sql, tuple(params))]
