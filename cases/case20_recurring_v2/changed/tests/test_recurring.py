from datetime import date

import pytest

from ledgerly import expenses, recurring


class TestRules:
    def test_create_monthly(self, db, user):
        rid = recurring.create_rule(
            db, user, 120000, "housing", "monthly", day_of_month=1, note="rent")
        assert rid > 0

    def test_validation(self, db, user):
        with pytest.raises(recurring.RecurringError):
            recurring.create_rule(db, user, 500, "food", "daily")
        with pytest.raises(recurring.RecurringError):
            recurring.create_rule(db, user, 500, "food", "monthly")
        with pytest.raises(recurring.RecurringError):
            recurring.create_rule(db, user, 500, "food", "weekly", weekday=9)


class TestOccurrences:
    def test_monthly_clamps_short_months(self):
        rule = {"cadence": "monthly", "day_of_month": 31}
        occs = recurring.occurrences_between(
            rule, date(2026, 1, 31), date(2026, 4, 30))
        assert occs == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]

    def test_monthly_year_rollover(self):
        rule = {"cadence": "monthly", "day_of_month": 15}
        occs = recurring.occurrences_between(
            rule, date(2026, 11, 15), date(2027, 1, 31))
        assert occs == [date(2026, 12, 15), date(2027, 1, 15)]

    def test_weekly(self):
        rule = {"cadence": "weekly", "weekday": 0}  # Mondays
        occs = recurring.occurrences_between(
            rule, date(2026, 3, 2), date(2026, 3, 16))
        assert occs == [date(2026, 3, 9), date(2026, 3, 16)]


class TestMaterialize:
    def test_creates_and_is_idempotent(self, db, user):
        recurring.create_rule(
            db, user, 120000, "housing", "monthly", day_of_month=1)
        n = recurring.materialize_due(db, user, today=date(2026, 3, 3))
        assert n == 1
        again = recurring.materialize_due(db, user, today=date(2026, 3, 3))
        assert again == 0
        rows = expenses.list_expenses(db, user)
        assert len(rows) == 1
        assert rows[0]["spent_on"] == "2026-03-01"

    def test_catches_up_multiple_months(self, db, user):
        recurring.create_rule(
            db, user, 5000, "entertainment", "monthly", day_of_month=10)
        recurring.materialize_due(db, user, today=date(2026, 1, 15))
        n = recurring.materialize_due(db, user, today=date(2026, 3, 15))
        assert n == 2  # Feb 10 and Mar 10

    def test_inactive_rules_skipped(self, db, user):
        rid = recurring.create_rule(
            db, user, 5000, "food", "monthly", day_of_month=5)
        recurring.deactivate_rule(db, user, rid)
        assert recurring.materialize_due(db, user, today=date(2026, 3, 6)) == 0

class TestBiweekly:
    def test_biweekly_occurrence(self):
        rule = {"cadence": "biweekly", "weekday": 0}  # Mondays
        occs = recurring.occurrences_between(
            rule, date(2026, 3, 2), date(2026, 3, 10))
        assert occs == [date(2026, 3, 9)]

    def test_biweekly_validation(self, db, user):
        with pytest.raises(recurring.RecurringError):
            recurring.create_rule(db, user, 500, "food", "biweekly")


class TestPauseResume:
    def test_pause_stops_materialization(self, db, user):
        rid = recurring.create_rule(
            db, user, 5000, "food", "monthly", day_of_month=5)
        recurring.pause_rule(db, user, rid)
        assert recurring.materialize_due(db, user, today=date(2026, 3, 6)) == 0

    def test_resume_reactivates(self, db, user):
        rid = recurring.create_rule(
            db, user, 5000, "food", "monthly", day_of_month=5)
        recurring.pause_rule(db, user, rid)
        recurring.resume_rule(db, user, rid)
        n = recurring.materialize_due(db, user, today=date(2026, 3, 6))
        assert n == 1
