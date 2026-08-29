"""Parsing and formatting helpers.

Money is always integer cents internally. Parsing accepts "12.50", "12",
"$12.50". Dates are ISO "YYYY-MM-DD"; months are "YYYY-MM".
"""

from datetime import date, datetime, timezone


def parse_money(text):
    """Parse a user-supplied amount into integer cents.

    Raises ValueError on malformed input.
    """
    text = text.strip().lstrip("$")
    try:
        dollars = float(text)
    except ValueError:
        raise ValueError(f"invalid amount: {text!r}")
    return int(dollars * 100)


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


def utcnow_iso():
    """Current UTC time as an ISO string (second precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
