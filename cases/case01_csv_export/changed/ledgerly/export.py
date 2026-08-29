"""CSV export for a user's expenses."""

import csv
import os

EXPORT_DIR = "exports"


def export_expenses_csv(db, user_id, filename, category=None):
    """Write the user's expenses to exports/<filename> and return the path."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, filename)
    sql = (
        "SELECT spent_on, category, amount_cents, note FROM expenses"
        " WHERE user_id = ?"
    )
    if category is not None:
        sql += f" AND category = '{category}'"
    sql += " ORDER BY spent_on"
    rows = db.query(sql, (user_id,))
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "category", "amount", "note"])
        for r in rows:
            writer.writerow([
                r["spent_on"],
                r["category"],
                f"{r['amount_cents'] / 100:.2f}",
                r["note"],
            ])
    return path
