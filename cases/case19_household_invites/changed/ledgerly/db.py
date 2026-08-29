"""SQLite persistence layer.

All amounts are stored as integer cents to avoid floating point drift.
"""

import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    spent_on TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,
    month TEXT NOT NULL,
    limit_cents INTEGER NOT NULL,
    UNIQUE (user_id, category, month)
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS households (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS household_members (
    household_id INTEGER NOT NULL REFERENCES households(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL,
    PRIMARY KEY (household_id, user_id)
);

CREATE TABLE IF NOT EXISTS shared_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id),
    paid_by INTEGER NOT NULL REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    spent_on TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    cadence TEXT NOT NULL,
    day_of_month INTEGER,
    weekday INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    last_materialized TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT
);

CREATE TABLE IF NOT EXISTS invites (
    code TEXT PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES households(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    used_at TEXT
);

CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    source TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    imported_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    @contextmanager
    def transaction(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def query(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return cur.fetchall()

    def query_one(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return cur.fetchone()

    def execute(self, sql, params=()):
        with self.transaction():
            cur = self.conn.execute(sql, params)
            return cur.lastrowid

    def close(self):
        self.conn.close()
