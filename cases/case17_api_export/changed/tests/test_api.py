import pytest

from ledgerly import api


@pytest.fixture()
def token(db, user):
    status, body = api.handle(db, api.Request(
        "POST", "/login", body={"username": "alice", "password": "s3cretpass"}))
    assert status == 200
    return body["token"]


def authed(method, path, token, **kw):
    headers = {"Authorization": f"Bearer {token}"}
    return api.Request(method, path, headers=headers, **kw)


class TestAuthFlow:
    def test_register_login(self, db):
        status, body = api.handle(db, api.Request(
            "POST", "/register",
            body={"username": "dave", "password": "davespassword"}))
        assert status == 201
        status, body = api.handle(db, api.Request(
            "POST", "/login",
            body={"username": "dave", "password": "davespassword"}))
        assert status == 200 and body["token"]

    def test_missing_token(self, db, user):
        status, body = api.handle(db, api.Request("GET", "/expenses"))
        assert status == 401

    def test_bad_token(self, db, user):
        status, _ = api.handle(db, api.Request(
            "GET", "/expenses", headers={"Authorization": "Bearer nope"}))
        assert status == 401

    def test_unknown_route(self, db):
        status, _ = api.handle(db, api.Request("GET", "/nope"))
        assert status == 404


class TestExpenseEndpoints:
    def test_create_list_delete(self, db, token):
        status, body = api.handle(db, authed(
            "POST", "/expenses", token,
            body={"amount": "12.50", "category": "food",
                  "spent_on": "2026-03-01", "note": "lunch"}))
        assert status == 201
        eid = body["expense_id"]

        status, body = api.handle(db, authed("GET", "/expenses", token))
        assert status == 200
        assert body["expenses"][0]["amount_cents"] == 1250

        status, body = api.handle(db, authed(
            "DELETE", "/expenses", token, body={"expense_id": eid}))
        assert status == 200

    def test_validation_maps_to_400(self, db, token):
        status, body = api.handle(db, authed(
            "POST", "/expenses", token,
            body={"amount": "12.50", "category": "yachts",
                  "spent_on": "2026-03-01"}))
        assert status == 400
        status, body = api.handle(db, authed(
            "POST", "/expenses", token, body={"amount": "12.50"}))
        assert status == 400

    def test_summary_and_budgets(self, db, token):
        api.handle(db, authed(
            "POST", "/expenses", token,
            body={"amount": "10.00", "category": "food",
                  "spent_on": "2026-03-01"}))
        api.handle(db, authed(
            "POST", "/budgets", token,
            body={"category": "food", "month": "2026-03", "limit": "50.00"}))
        status, body = api.handle(db, authed(
            "GET", "/summary", token, params={"month": "2026-03"}))
        assert status == 200 and body["summary"] == {"food": 1000}
        status, body = api.handle(db, authed(
            "GET", "/budgets", token, params={"month": "2026-03"}))
        assert status == 200 and body["budgets"][0]["over_budget"] is False

class TestHouseholdEndpoints:
    def test_balances_for_own_household(self, db, user, bob, token):
        from ledgerly import household
        hid = household.create_household(db, user, "Flat")
        household.add_member(db, hid, user, bob)
        status, body = api.handle(db, authed(
            "POST", "/household/expenses", token,
            body={"household_id": hid, "amount": "10.00",
                  "category": "food", "spent_on": "2026-03-01"}))
        assert status == 201
        status, body = api.handle(db, authed(
            "GET", "/household/balances", token,
            params={"household_id": str(hid)}))
        assert status == 200
        net = {b["user_id"]: b["net_cents"] for b in body["balances"]}
        assert net[user] == 500 and net[bob] == -500


class TestExport:
    def test_export_csv(self, db, token):
        api.handle(db, authed(
            "POST", "/expenses", token,
            body={"amount": "12.50", "category": "food",
                  "spent_on": "2026-03-01", "note": "lunch"}))
        status, body = api.handle(db, authed("GET", "/export", token))
        assert status == 200
        assert body["body"].splitlines()[0] == "spent_on,category,amount,note"
        assert "2026-03-01,food,12.50,lunch" in body["body"]
