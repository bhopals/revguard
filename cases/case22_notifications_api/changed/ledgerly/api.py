"""HTTP-style API layer.

A minimal, transport-agnostic router: handlers receive a Request and
return (status, body_dict). A real deployment mounts handle() behind any
HTTP server; tests call handle() directly. Authentication is a bearer
token resolved by the auth middleware; handlers marked @route(...,
auth=True) receive the resolved user id.
"""

from . import auth, expenses, household, notify, reports
from .utils import parse_money, utcnow_iso

_ROUTES = {}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Request:
    def __init__(self, method, path, body=None, headers=None, params=None):
        self.method = method.upper()
        self.path = path
        self.body = body or {}
        self.headers = headers or {}
        self.params = params or {}
        self.user_id = None


def route(method, path, auth_required=True):
    def register(fn):
        _ROUTES[(method.upper(), path)] = (fn, auth_required)
        return fn
    return register


def _authenticate(db, request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "missing bearer token")
    token = header[len("Bearer "):]
    try:
        return auth.authenticate(db, token)
    except auth.AuthError as e:
        raise ApiError(401, str(e))


def handle(db, request):
    """Dispatch one request. Returns (status, body_dict)."""
    entry = _ROUTES.get((request.method, request.path))
    if entry is None:
        return 404, {"error": "not found"}
    fn, auth_required = entry
    try:
        if auth_required:
            request.user_id = _authenticate(db, request)
        return fn(db, request)
    except ApiError as e:
        return e.status, {"error": e.message}
    except (expenses.ExpenseError, household.HouseholdError,
            reports.BudgetError, ValueError) as e:
        return 400, {"error": str(e)}
    except auth.AuthError as e:
        return 401, {"error": str(e)}


def _require(body, *fields):
    missing = [f for f in fields if f not in body]
    if missing:
        raise ApiError(400, f"missing fields: {', '.join(missing)}")


@route("POST", "/register", auth_required=False)
def post_register(db, request):
    _require(request.body, "username", "password")
    user_id = auth.register(db, request.body["username"],
                            request.body["password"])
    return 201, {"user_id": user_id}


@route("POST", "/login", auth_required=False)
def post_login(db, request):
    _require(request.body, "username", "password")
    token = auth.login(db, request.body["username"], request.body["password"])
    return 200, {"token": token}


@route("POST", "/expenses")
def post_expense(db, request):
    _require(request.body, "amount", "category", "spent_on")
    cents = parse_money(str(request.body["amount"]))
    eid = expenses.add_expense(
        db, request.user_id, cents, request.body["category"],
        request.body["spent_on"], request.body.get("note", ""),
    )
    return 201, {"expense_id": eid}


@route("GET", "/expenses")
def get_expenses(db, request):
    page = int(request.params.get("page", 1))
    category = request.params.get("category")
    rows = expenses.list_expenses(db, request.user_id,
                                  category=category, page=page)
    return 200, {"expenses": rows, "page": page}


@route("DELETE", "/expenses")
def delete_expense(db, request):
    _require(request.body, "expense_id")
    expenses.delete_expense(db, request.user_id,
                            int(request.body["expense_id"]))
    return 200, {"deleted": True}


@route("GET", "/summary")
def get_summary(db, request):
    month = request.params.get("month")
    if not month:
        raise ApiError(400, "month parameter required")
    return 200, {"summary": reports.monthly_summary(db, request.user_id, month)}


@route("GET", "/budgets")
def get_budgets(db, request):
    month = request.params.get("month")
    if not month:
        raise ApiError(400, "month parameter required")
    return 200, {"budgets": reports.budget_status(db, request.user_id, month)}


@route("POST", "/budgets")
def post_budget(db, request):
    _require(request.body, "category", "month", "limit")
    reports.set_budget(
        db, request.user_id, request.body["category"], request.body["month"],
        parse_money(str(request.body["limit"])),
    )
    return 201, {"ok": True}

@route("GET", "/notifications")
def get_notifications(db, request):
    uid = int(request.params.get("user_id", request.user_id))
    return 200, {"notifications": notify.unread(db, uid)}


@route("POST", "/notifications/read")
def post_notification_read(db, request):
    _require(request.body, "notification_id")
    db.execute(
        "UPDATE notifications SET read_at = ? WHERE id = ?",
        (utcnow_iso(), int(request.body["notification_id"])),
    )
    return 200, {"ok": True}
