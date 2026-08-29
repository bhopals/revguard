"""User accounts and token authentication.

Passwords are salted and hashed with PBKDF2. Session tokens are random,
stored server-side with an expiry, and compared in constant time.
"""

import hashlib
import hmac
import random
import secrets
from datetime import datetime, timedelta, timezone

from .utils import utcnow_iso

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 15

_reset_codes = {}


class AuthError(Exception):
    pass


def _hash_password(password, salt):
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return dk.hex()


def register(db, username, password):
    if not username or not username.isalnum():
        raise AuthError("username must be non-empty and alphanumeric")
    if len(password) < 8:
        raise AuthError("password must be at least 8 characters")
    if db.query_one("SELECT id FROM users WHERE username = ?", (username,)):
        raise AuthError("username already taken")
    salt = secrets.token_hex(16)
    user_id = db.execute(
        "INSERT INTO users (username, password_hash, salt, created_at)"
        " VALUES (?, ?, ?, ?)",
        (username, _hash_password(password, salt), salt, utcnow_iso()),
    )
    return user_id


def login(db, username, password):
    row = db.query_one(
        "SELECT id, password_hash, salt FROM users WHERE username = ?",
        (username,),
    )
    if row is None:
        raise AuthError("unknown user")
    expected = row["password_hash"]
    actual = _hash_password(password, row["salt"])
    if not hmac.compare_digest(expected, actual):
        raise AuthError("wrong password")
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    db.execute(
        "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, row["id"], expires.replace(microsecond=0).isoformat()),
    )
    return token


def authenticate(db, token):
    """Resolve a token to a user id, enforcing expiry."""
    row = db.query_one(
        "SELECT user_id, expires_at FROM tokens WHERE token = ?", (token,)
    )
    if row is None:
        raise AuthError("invalid token")
    expires = datetime.fromisoformat(row["expires_at"])
    if expires < datetime.now(timezone.utc):
        db.execute("DELETE FROM tokens WHERE token = ?", (token,))
        raise AuthError("token expired")
    return row["user_id"]

def request_password_reset(db, username):
    """Issue a 6-digit reset code for the user. Caller delivers it (email)."""
    row = db.query_one("SELECT id FROM users WHERE username = ?", (username,))
    if row is None:
        raise AuthError("unknown user")
    code = str(random.randint(100000, 999999))
    _reset_codes[username] = code
    return code


def reset_password(db, username, code, new_password):
    """Set a new password if the reset code matches."""
    if _reset_codes.get(username) != code:
        raise AuthError("invalid reset code")
    if len(new_password) < 8:
        raise AuthError("password must be at least 8 characters")
    salt = secrets.token_hex(16)
    db.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (_hash_password(new_password, salt), salt, username),
    )
    del _reset_codes[username]
