"""User notifications: over-budget alerts and weekly digests.

Notifications are rows in the notifications table; delivery (email, push)
is out of scope — a delivery worker reads unread rows. run_budget_alerts
is designed to be called after any expense write; it only notifies once
per (category, month) so users are not spammed.
"""

from .reports import budget_status, monthly_summary
from .utils import format_money, utcnow_iso


def notify(db, user_id, kind, body):
    return db.execute(
        "INSERT INTO notifications (user_id, kind, body, created_at)"
        " VALUES (?, ?, ?, ?)",
        (user_id, kind, body, utcnow_iso()),
    )


def unread(db, user_id):
    return [dict(r) for r in db.query(
        "SELECT * FROM notifications"
        " WHERE user_id = ? AND read_at IS NULL ORDER BY id",
        (user_id,),
    )]


def mark_read(db, user_id, notification_id):
    db.execute(
        "UPDATE notifications SET read_at = ?"
        " WHERE id = ? AND user_id = ? AND read_at IS NULL",
        (utcnow_iso(), notification_id, user_id),
    )


def _already_alerted(db, user_id, category, month):
    marker = f"[{category}/{month}]"
    row = db.query_one(
        "SELECT id FROM notifications"
        " WHERE user_id = ? AND kind = 'over_budget' AND body LIKE ?",
        (user_id, f"%{marker}%"),
    )
    return row is not None


def run_budget_alerts(db, user_id, month):
    """Create an over-budget notification per newly exceeded category.

    Returns the number of notifications created. Alerts fire once per
    (category, month).
    """
    created = 0
    for status in budget_status(db, user_id, month):
        if not status["over_budget"]:
            continue
        if _already_alerted(db, user_id, status["category"], month):
            continue
        body = (
            f"[{status['category']}/{month}] Over budget: spent"
            f" {status['spent']} of {status['limit']}"
            f" ({status['remaining']} remaining)."
        )
        notify(db, user_id, "over_budget", body)
        created += 1
    return created


def weekly_digest_body(db, user_id, month, spend_by_category):
    """Render the digest text for a month's spend dict (category -> cents)."""
    if not spend_by_category:
        return f"No spending recorded yet for {month}."
    lines = [f"Your spending for {month}:"]
    total = 0
    for category, cents in sorted(
            spend_by_category.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {category:<14}{format_money(cents):>10}")
        total += cents
    lines.append(f"  {'total':<14}{format_money(total):>10}")
    return "\n".join(lines)

def send_weekly_digests(db, month):
    """Queue a spending digest for every user and clear their read pile.

    Run by the weekly scheduler. Returns the number of digests queued.
    """
    sent = 0
    for row in db.query("SELECT id FROM users"):
        uid = row["id"]
        body = weekly_digest_body(
            db, uid, month, monthly_summary(db, uid, month))
        notify(db, uid, "digest", body)
        db.execute(
            "UPDATE notifications SET read_at = ? WHERE user_id = ?",
            (utcnow_iso(), uid),
        )
        sent += 1
    return sent
