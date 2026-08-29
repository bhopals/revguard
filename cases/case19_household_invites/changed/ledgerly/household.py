"""Shared households: several users pooling expenses.

A household has one owner and any number of members. Shared expenses are
paid by one member and split equally; settlement computes who owes whom.
All amounts are integer cents.
"""

import random

from .expenses import VALID_CATEGORIES, ExpenseError
from .utils import parse_iso_date, utcnow_iso

MAX_MEMBERS = 12


class HouseholdError(Exception):
    pass


def create_household(db, owner_id, name):
    if not name.strip():
        raise HouseholdError("household name must not be empty")
    hid = db.execute(
        "INSERT INTO households (name, owner_id, created_at) VALUES (?, ?, ?)",
        (name.strip(), owner_id, utcnow_iso()),
    )
    db.execute(
        "INSERT INTO household_members (household_id, user_id, role, joined_at)"
        " VALUES (?, ?, 'owner', ?)",
        (hid, owner_id, utcnow_iso()),
    )
    return hid


def _member_role(db, household_id, user_id):
    row = db.query_one(
        "SELECT role FROM household_members"
        " WHERE household_id = ? AND user_id = ?",
        (household_id, user_id),
    )
    return row["role"] if row else None


def require_member(db, household_id, user_id):
    role = _member_role(db, household_id, user_id)
    if role is None:
        raise HouseholdError("not a member of this household")
    return role


def add_member(db, household_id, acting_user, new_user_id):
    """Only the owner may add members."""
    if _member_role(db, household_id, acting_user) != "owner":
        raise HouseholdError("only the owner can add members")
    count = db.query_one(
        "SELECT COUNT(*) AS n FROM household_members WHERE household_id = ?",
        (household_id,),
    )["n"]
    if count >= MAX_MEMBERS:
        raise HouseholdError("household is full")
    if _member_role(db, household_id, new_user_id) is not None:
        raise HouseholdError("already a member")
    db.execute(
        "INSERT INTO household_members (household_id, user_id, role, joined_at)"
        " VALUES (?, ?, 'member', ?)",
        (household_id, new_user_id, utcnow_iso()),
    )


def remove_member(db, household_id, acting_user, target_user_id):
    """The owner may remove anyone but themselves; members may leave."""
    acting_role = require_member(db, household_id, acting_user)
    target_role = _member_role(db, household_id, target_user_id)
    if target_role is None:
        raise HouseholdError("no such member")
    if target_role == "owner":
        raise HouseholdError("the owner cannot be removed")
    if acting_user != target_user_id and acting_role != "owner":
        raise HouseholdError("only the owner can remove other members")
    db.execute(
        "DELETE FROM household_members"
        " WHERE household_id = ? AND user_id = ?",
        (household_id, target_user_id),
    )


def create_invite(db, household_id, acting_user):
    """Issue a shareable invite code. Owner only."""
    if _member_role(db, household_id, acting_user) != "owner":
        raise HouseholdError("only the owner can create invites")
    code = "%06x" % random.randrange(16 ** 6)
    db.execute(
        "INSERT INTO invites (code, household_id, created_by, created_at)"
        " VALUES (?, ?, ?, ?)",
        (code, household_id, acting_user, utcnow_iso()),
    )
    return code


def accept_invite(db, code, user_id):
    """Join the household an invite code belongs to. Returns household id."""
    row = db.query_one(
        "SELECT household_id FROM invites WHERE code = ?", (code,)
    )
    if row is None:
        raise HouseholdError("invalid invite code")
    hid = row["household_id"]
    if _member_role(db, hid, user_id) is not None:
        raise HouseholdError("already a member")
    db.execute(
        "INSERT INTO household_members (household_id, user_id, role, joined_at)"
        " VALUES (?, ?, 'member', ?)",
        (hid, user_id, utcnow_iso()),
    )
    return hid


def add_shared_expense(db, household_id, paid_by, amount_cents, category,
                       spent_on, note=""):
    require_member(db, household_id, paid_by)
    if category not in VALID_CATEGORIES:
        raise ExpenseError(f"unknown category: {category}")
    if amount_cents <= 0:
        raise ExpenseError("amount must be positive")
    d = parse_iso_date(spent_on)
    return db.execute(
        "INSERT INTO shared_expenses (household_id, paid_by, amount_cents,"
        " category, note, spent_on, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (household_id, paid_by, amount_cents, category, note,
         d.isoformat(), utcnow_iso()),
    )


def members_of(db, household_id):
    rows = db.query(
        "SELECT user_id, role FROM household_members"
        " WHERE household_id = ? ORDER BY joined_at",
        (household_id,),
    )
    return [dict(r) for r in rows]


def balances(db, household_id):
    """Net position per member in cents: positive means the household owes
    them, negative means they owe the household.

    Each shared expense is split equally among ALL current members; the
    payer is credited the full amount and every member (payer included)
    is debited their equal share. Remainder cents from uneven splits are
    debited to the payer, so the total always sums to zero.
    """
    member_ids = [m["user_id"] for m in members_of(db, household_id)]
    if not member_ids:
        return {}
    net = {uid: 0 for uid in member_ids}
    rows = db.query(
        "SELECT paid_by, amount_cents FROM shared_expenses"
        " WHERE household_id = ?",
        (household_id,),
    )
    n = len(member_ids)
    for r in rows:
        share = r["amount_cents"] // n
        remainder = r["amount_cents"] - share * n
        if r["paid_by"] in net:
            net[r["paid_by"]] += r["amount_cents"]
        for uid in member_ids:
            net[uid] -= share
        if r["paid_by"] in net:
            net[r["paid_by"]] -= remainder
    return net


def settlement_plan(db, household_id):
    """Greedy list of (debtor, creditor, cents) transfers settling all
    balances."""
    net = balances(db, household_id)
    debtors = sorted((uid, -amt) for uid, amt in net.items() if amt < 0)
    creditors = sorted((uid, amt) for uid, amt in net.items() if amt > 0)
    plan = []
    di = ci = 0
    while di < len(debtors) and ci < len(creditors):
        d_uid, owes = debtors[di]
        c_uid, due = creditors[ci]
        pay = min(owes, due)
        plan.append((d_uid, c_uid, pay))
        owes -= pay
        due -= pay
        debtors[di] = (d_uid, owes)
        creditors[ci] = (c_uid, due)
        if owes == 0:
            di += 1
        if due == 0:
            ci += 1
    return plan
