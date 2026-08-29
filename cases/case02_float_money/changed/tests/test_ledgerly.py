import pytest

from ledgerly.db import Database
from ledgerly import auth, expenses, reports
from ledgerly.utils import parse_money, format_money, month_of, parse_iso_date


@pytest.fixture()
def db():
    d = Database()
    yield d
    d.close()


@pytest.fixture()
def user(db):
    return auth.register(db, "alice", "s3cretpass")


class TestUtils:
    def test_parse_money(self):
        assert parse_money("12.50") == 1250
        assert parse_money("$12.50") == 1250
        assert parse_money("12") == 1200
        assert parse_money("0.5") == 50

    def test_parse_money_rejects_garbage(self):
        for bad in ["", "abc", "1,000"]:
            with pytest.raises(ValueError):
                parse_money(bad)

    def test_format_money(self):
        assert format_money(1250) == "$12.50"
        assert format_money(5) == "$0.05"
        assert format_money(-1250) == "-$12.50"

    def test_month_of(self):
        assert month_of(parse_iso_date("2026-03-07")) == "2026-03"


class TestAuth:
    def test_register_and_login(self, db, user):
        token = auth.login(db, "alice", "s3cretpass")
        assert auth.authenticate(db, token) == user

    def test_wrong_password(self, db, user):
        with pytest.raises(auth.AuthError):
            auth.login(db, "alice", "wrongpass1")

    def test_bad_token(self, db):
        with pytest.raises(auth.AuthError):
            auth.authenticate(db, "not-a-token")

    def test_duplicate_username(self, db, user):
        with pytest.raises(auth.AuthError):
            auth.register(db, "alice", "anotherpass")


class TestExpenses:
    def test_add_and_get(self, db, user):
        eid = expenses.add_expense(db, user, 1250, "food", "2026-03-01", "lunch")
        row = expenses.get_expense(db, user, eid)
        assert row["amount_cents"] == 1250
        assert row["category"] == "food"

    def test_ownership_enforced(self, db, user):
        other = auth.register(db, "bob", "bobspassword")
        eid = expenses.add_expense(db, user, 500, "food", "2026-03-01")
        with pytest.raises(expenses.ExpenseError):
            expenses.get_expense(db, other, eid)

    def test_delete(self, db, user):
        eid = expenses.add_expense(db, user, 500, "food", "2026-03-01")
        expenses.delete_expense(db, user, eid)
        with pytest.raises(expenses.ExpenseError):
            expenses.get_expense(db, user, eid)

    def test_bad_category(self, db, user):
        with pytest.raises(expenses.ExpenseError):
            expenses.add_expense(db, user, 500, "yachts", "2026-03-01")

    def test_list_filters_by_category(self, db, user):
        expenses.add_expense(db, user, 100, "food", "2026-03-01")
        expenses.add_expense(db, user, 200, "transport", "2026-03-02")
        rows = expenses.list_expenses(db, user, category="food")
        assert [r["amount_cents"] for r in rows] == [100]


class TestReports:
    def test_monthly_summary(self, db, user):
        expenses.add_expense(db, user, 100, "food", "2026-03-01")
        expenses.add_expense(db, user, 250, "food", "2026-03-15")
        expenses.add_expense(db, user, 400, "transport", "2026-04-01")
        assert reports.monthly_summary(db, user, "2026-03") == {"food": 350}

    def test_budget_status(self, db, user):
        reports.set_budget(db, user, "food", "2026-03", 300)
        expenses.add_expense(db, user, 350, "food", "2026-03-10")
        status = reports.budget_status(db, user, "2026-03")
        assert status[0]["over_budget"] is True
        assert status[0]["remaining"] == "-$0.50"

    def test_budget_upsert(self, db, user):
        reports.set_budget(db, user, "food", "2026-03", 300)
        reports.set_budget(db, user, "food", "2026-03", 500)
        status = reports.budget_status(db, user, "2026-03")
        assert status[0]["limit"] == "$5.00"
