"""Recurring expense rules (rent, subscriptions) and their materialization.

A rule fires monthly on day_of_month, or weekly on weekday (0 = Monday).
materialize_due() turns every due occurrence since the rule was last
materialized into a real expense row, exactly once — it is safe to call
repeatedly (idempotent) and is normally run daily by a scheduler.
"""

import calendar
from datetime import date, timedelta

from .expenses import VALID_CATEGORIES, ExpenseError, add_expense
from .utils import parse_iso_date

VALID_CADENCES = {"monthly", "weekly"}


class RecurringError(Exception):
    pass


def create_rule(db, user_id, amount_cents, category, cadence,
                day_of_month=None, weekday=None, note=""):
    if cadence not in VALID_CADENCES:
        raise RecurringError(f"unknown cadence: {cadence}")
    if category not in VALID_CATEGORIES:
        raise ExpenseError(f"unknown category: {category}")
    if amount_cents <= 0:
        raise ExpenseError("amount must be positive")
    if cadence == "monthly":
        if not (day_of_month and 1 <= day_of_month <= 31):
            raise RecurringError("monthly rules need day_of_month in 1..31")
    if cadence == "weekly":
        if weekday is None or not 0 <= weekday <= 6:
            raise RecurringError("weekly rules need weekday in 0..6")
    return db.execute(
        "INSERT INTO recurring_rules (user_id, amount_cents, category, note,"
        " cadence, day_of_month, weekday) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, amount_cents, category, note, cadence, day_of_month, weekday),
    )


def deactivate_rule(db, user_id, rule_id):
    row = db.query_one(
        "SELECT id FROM recurring_rules WHERE id = ? AND user_id = ?",
        (rule_id, user_id),
    )
    if row is None:
        raise RecurringError("rule not found")
    db.execute(
        "UPDATE recurring_rules SET active = 0 WHERE id = ?", (rule_id,)
    )


def _clamp_day(year, month, day):
    """Feb 30 -> Feb 28/29 etc.: clamp to the month's last day."""
    return min(day, calendar.monthrange(year, month)[1])


def occurrences_between(rule, start, end):
    """Every date in (start, end] on which the rule fires."""
    out = []
    if rule["cadence"] == "monthly":
        y, m = start.year, start.month
        while True:
            d = date(y, m, _clamp_day(y, m, rule["day_of_month"]))
            if d > end:
                break
            if d > start:
                out.append(d)
            m += 1
            if m == 13:
                m, y = 1, y + 1
    else:  # weekly
        d = start + timedelta(days=1)
        while d <= end:
            if d.weekday() == rule["weekday"]:
                out.append(d)
            d += timedelta(days=1)
    return out


def materialize_due(db, user_id, today=None):
    """Create expense rows for every due occurrence of the user's active
    rules. Returns the number of expenses created. Idempotent: each
    occurrence is recorded at most once via last_materialized."""
    today = today or date.today()
    created = 0
    rules = db.query(
        "SELECT * FROM recurring_rules WHERE user_id = ? AND active = 1",
        (user_id,),
    )
    for rule in rules:
        if rule["last_materialized"]:
            start = parse_iso_date(rule["last_materialized"])
        else:
            # First run: catch occurrences from the start of this month.
            start = today.replace(day=1) - timedelta(days=1)
        for occ in occurrences_between(rule, start, today):
            add_expense(
                db, user_id, rule["amount_cents"], rule["category"],
                occ.isoformat(), rule["note"],
            )
            created += 1
        db.execute(
            "UPDATE recurring_rules SET last_materialized = ? WHERE id = ?",
            (today.isoformat(), rule["id"]),
        )
    return created
