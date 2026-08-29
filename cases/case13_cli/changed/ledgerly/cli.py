"""Command-line interface for Ledgerly.

Examples:
    python -m ledgerly.cli register alice mypassword
    python -m ledgerly.cli login alice mypassword
    python -m ledgerly.cli add 12.50 food 2026-03-01 --note "lunch"
    python -m ledgerly.cli list --category food --page 1
    python -m ledgerly.cli summary 2026-03
"""

import argparse
import json
import os
import sys
from pathlib import Path

from . import auth, expenses, reports
from .db import Database
from .utils import format_money

DB_PATH = os.environ.get("LEDGERLY_DB", str(Path.home() / ".ledgerly.db"))
TOKEN_PATH = Path.home() / ".ledgerly_token"


def _load_token():
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return None


def _save_token(token):
    TOKEN_PATH.write_text(token)
    TOKEN_PATH.chmod(0o600)


def _require_user(db):
    token = _load_token()
    if token is None:
        raise auth.AuthError("not logged in; run: ledgerly login <user> <password>")
    return auth.authenticate(db, token)


def cmd_register(db, args):
    auth.register(db, args.username, args.password)
    print(f"registered {args.username}")


def cmd_login(db, args):
    token = auth.login(db, args.username, args.password)
    _save_token(token)
    print("logged in")


def cmd_add(db, args):
    user_id = _require_user(db)
    amount_cents = int(float(args.amount) * 100)
    eid = expenses.add_expense(
        db, user_id, amount_cents, args.category, args.date, args.note or ""
    )
    print(f"added expense #{eid}: {format_money(amount_cents)} {args.category}")


def cmd_list(db, args):
    user_id = _require_user(db)
    rows = expenses.list_expenses(
        db, user_id, category=args.category, page=args.page
    )
    for r in rows:
        print(f"#{r['id']:>4}  {r['spent_on']}  {r['category']:<14}"
              f"{format_money(r['amount_cents']):>10}  {r['note']}")
    if not rows:
        print("(no expenses)")


def cmd_summary(db, args):
    user_id = _require_user(db)
    summary = reports.monthly_summary(db, user_id, args.month)
    if args.json:
        print(json.dumps(summary))
        return
    for category, total in summary.items():
        print(f"{category:<14}{format_money(total):>10}")


def build_parser():
    parser = argparse.ArgumentParser(prog="ledgerly")
    sub = parser.add_subparsers(dest="command", required=True)

    add_reg = sub.add_parser("register", help="create an account")
    add_reg.add_argument("username")
    add_reg.add_argument("password")
    add_reg.set_defaults(func=cmd_register)

    add_login = sub.add_parser("login", help="log in and cache a token")
    add_login.add_argument("username")
    add_login.add_argument("password")
    add_login.set_defaults(func=cmd_login)

    add_add = sub.add_parser("add", help="record an expense")
    add_add.add_argument("amount")
    add_add.add_argument("category")
    add_add.add_argument("date")
    add_add.add_argument("--note")
    add_add.set_defaults(func=cmd_add)

    add_list = sub.add_parser("list", help="list expenses")
    add_list.add_argument("--category")
    add_list.add_argument("--page", type=int, default=1)
    add_list.set_defaults(func=cmd_list)

    add_sum = sub.add_parser("summary", help="monthly summary")
    add_sum.add_argument("month")
    add_sum.add_argument("--json", action="store_true")
    add_sum.set_defaults(func=cmd_summary)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    db = Database(DB_PATH)
    try:
        args.func(db, args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
