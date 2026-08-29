from ledgerly import expenses, notify, reports


class TestNotifications:
    def test_notify_and_unread(self, db, user):
        notify.notify(db, user, "info", "hello")
        assert [n["body"] for n in notify.unread(db, user)] == ["hello"]

    def test_mark_read(self, db, user):
        nid = notify.notify(db, user, "info", "hello")
        notify.mark_read(db, user, nid)
        assert notify.unread(db, user) == []

    def test_mark_read_scoped_to_user(self, db, user, bob):
        nid = notify.notify(db, user, "info", "hello")
        notify.mark_read(db, bob, nid)
        assert len(notify.unread(db, user)) == 1


class TestBudgetAlerts:
    def test_alert_fires_once(self, db, user):
        reports.set_budget(db, user, "food", "2026-03", 1000)
        expenses.add_expense(db, user, 1500, "food", "2026-03-05")
        assert notify.run_budget_alerts(db, user, "2026-03") == 1
        assert notify.run_budget_alerts(db, user, "2026-03") == 0
        assert len(notify.unread(db, user)) == 1

    def test_no_alert_under_budget(self, db, user):
        reports.set_budget(db, user, "food", "2026-03", 1000)
        expenses.add_expense(db, user, 500, "food", "2026-03-05")
        assert notify.run_budget_alerts(db, user, "2026-03") == 0


class TestDigest:
    def test_digest_renders_sorted(self, db, user):
        body = notify.weekly_digest_body(
            db, user, "2026-03", {"food": 350, "transport": 1200})
        lines = body.splitlines()
        assert "transport" in lines[1]
        assert "food" in lines[2]
        assert "$15.50" in lines[3]

    def test_digest_empty(self, db, user):
        assert "No spending" in notify.weekly_digest_body(db, user, "2026-03", {})
