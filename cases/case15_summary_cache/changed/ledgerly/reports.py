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


_summary_cache = {}


def monthly_summary(db, user_id, month):
    """Total spend per category for a 'YYYY-MM' month.

    Results are cached per (user, month): the dashboard calls this on
    every page load and the numbers rarely change within a session.
    """
    key = (user_id, month)
    if key in _summary_cache:
        return _summary_cache[key]
    rows = db.query(
        "SELECT category, SUM(amount_cents) AS total"
        " FROM expenses"
        " WHERE user_id = ? AND substr(spent_on, 1, 7) = ?"
        " GROUP BY category ORDER BY total DESC",
        (user_id, month),
    )
    totals = {r["category"]: r["total"] for r in rows}
    _summary_cache[key] = totals
    return totals


def budget_status(db, user_id, month):
    """Compare spend against each budget set for the month.

    Returns a list of dicts with category, limit, spent, remaining and
    an over-budget flag. Categories without a budget are omitted.
    """
    spend = monthly_summary(db, user_id, month)
    budgets = db.query(
        "SELECT category, limit_cents FROM budgets"
        " WHERE user_id = ? AND month = ?",
        (user_id, month),
    )
    out = []
    for b in budgets:
        spent = spend.get(b["category"], 0)
        remaining = b["limit_cents"] - spent
        out.append({
            "category": b["category"],
            "limit": format_money(b["limit_cents"]),
            "spent": format_money(spent),
            "remaining": format_money(remaining),
            "over_budget": spent > b["limit_cents"],
        })
    return out
