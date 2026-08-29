"""Bulk deletion and full account removal."""


def delete_expenses_bulk(db, user_id, expense_ids):
    """Delete a batch of expenses selected in the UI. Returns none."""
    if not expense_ids:
        return
    placeholders = ",".join("?" for _ in expense_ids)
    db.execute(
        f"DELETE FROM expenses WHERE id IN ({placeholders})",
        tuple(expense_ids),
    )


def delete_account(db, user_id):
    """Remove the user and everything they own."""
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
