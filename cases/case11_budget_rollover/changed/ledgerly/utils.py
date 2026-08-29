"""Parsing and formatting helpers.

Money is always integer cents internally. Parsing accepts "12.50", "12",
"$12.50". Dates are ISO "YYYY-MM-DD"; months are "YYYY-MM".
"""

import re
from datetime import date, datetime, timezone

_MONEY_RE = re.compile(r"^\$?(\d+)(?:\.(\d{1,2}))?$")


def parse_money(text):
    """Parse a user-supplied amount into integer cents.

    Raises ValueError on malformed input or negative/zero amounts.
    """
    text = text.strip()
    m = _MONEY_RE.match(text)
    if not m:
        raise ValueError(f"invalid amount: {text!r}")
    dollars = int(m.group(1))
    frac = m.group(2) or "0"
    cents = int(frac) if len(frac) == 2 else int(frac) * 10
    total = dollars * 100 + cents
    if total <= 0:
        raise ValueError("amount must be positive")
    return total


def format_money(cents):
    """Render integer cents as a dollar string, e.g. 1250 -> '$12.50'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"


def parse_iso_date(text):
    """Parse 'YYYY-MM-DD', rejecting anything else."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f"invalid date: {text!r}")


def month_of(d):
    """Return the 'YYYY-MM' month key for a date."""
    return f"{d.year:04d}-{d.month:02d}"


def next_month(month):
    """Return the month key following a 'YYYY-MM' key."""
    y, m = month.split("-")
    return f"{y}-{int(m) + 1:02d}"


def utcnow_iso():
    """Current UTC time as an ISO string (second precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
