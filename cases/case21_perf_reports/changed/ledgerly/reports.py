"""Monthly summaries and budget tracking."""

from .utils import format_money


class BudgetError(Exception):
    pass


def set_budget(db, user_id, category, month, limit_cents):
    if limit_cents <= 0:
        raise BudgetError("budget limit must be positive")
    db.execute(
        "INSERT INTO budgets (user_id, category, month, limit_cents)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT (user_id, category, month)"
        " DO UPDATE SET limit_cents = excluded.limit_cents",
        (user_id, category, month, limit_cents),
    )


def monthly_summary(db, user_id, month):
    """Total spend per category for a 'YYYY-MM' month."""
    rows = db.query(
        "SELECT category, SUM(amount_cents) AS total"
        " FROM expenses"
        " WHERE user_id = ? AND substr(spent_on, 1, 7) = ?"
        " GROUP BY category ORDER BY total DESC",
        (user_id, month),
    )
    return {r["category"]: r["total"] for r in rows}


def budget_status(db, user_id, month):
    """Compare spend against each budget set for the month.

    Returns a list of dicts with category, limit, spent, remaining and
    an over-budget flag. Categories without a budget are omitted.
    """
    rows = db.query(
        "SELECT b.category, b.limit_cents,"
        " COALESCE(SUM(e.amount_cents), 0) AS spent"
        " FROM budgets b"
        " LEFT JOIN expenses e ON e.user_id = b.user_id"
        "   AND e.category = b.category"
        " WHERE b.user_id = ? AND b.month = ?"
        " GROUP BY b.category, b.limit_cents",
        (user_id, month),
    )
    out = []
    for b in rows:
        remaining = b["limit_cents"] - b["spent"]
        out.append({
            "category": b["category"],
            "limit": format_money(b["limit_cents"]),
            "spent": format_money(b["spent"]),
            "remaining": format_money(remaining),
            "over_budget": b["spent"] > b["limit_cents"],
        })
    return out
