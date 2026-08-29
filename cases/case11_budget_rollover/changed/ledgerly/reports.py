"""Monthly summaries and budget tracking."""

from .utils import format_money, next_month


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

def rollover_budgets(db, user_id, from_month):
    """Carry each category's unspent budget from from_month into the next month.

    The new limit is the original limit plus whatever was left unspent
    (never less than the original limit).
    """
    target = next_month(from_month)
    spend = monthly_summary(db, user_id, from_month)
    budgets = db.query(
        "SELECT category, limit_cents FROM budgets"
        " WHERE user_id = ? AND month = ?",
        (user_id, from_month),
    )
    for b in budgets:
        spent = spend.get(b["category"], 0)
        carry = max(b["limit_cents"] - spent, 0)
        new_limit = b["limit_cents"] + carry
        set_budget(db, user_id, b["category"], target, new_limit)
    return target
