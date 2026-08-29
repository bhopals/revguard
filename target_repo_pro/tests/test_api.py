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
