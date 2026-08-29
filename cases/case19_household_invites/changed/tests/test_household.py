import pytest

from ledgerly import household


@pytest.fixture()
def home(db, user, bob):
    hid = household.create_household(db, user, "Flat 4B")
    household.add_member(db, hid, user, bob)
    return hid


class TestMembership:
    def test_owner_is_member(self, db, user):
        hid = household.create_household(db, user, "Home")
        assert household.require_member(db, hid, user) == "owner"

    def test_only_owner_adds(self, db, home, user, bob, carol):
        with pytest.raises(household.HouseholdError):
            household.add_member(db, home, bob, carol)
        household.add_member(db, home, user, carol)
        assert len(household.members_of(db, home)) == 3

    def test_member_can_leave(self, db, home, bob):
        household.remove_member(db, home, bob, bob)
        assert household._member_role(db, home, bob) is None

    def test_member_cannot_remove_other(self, db, home, user, bob, carol):
        household.add_member(db, home, user, carol)
        with pytest.raises(household.HouseholdError):
            household.remove_member(db, home, bob, carol)

    def test_owner_cannot_be_removed(self, db, home, user, bob):
        with pytest.raises(household.HouseholdError):
            household.remove_member(db, home, bob, user)
        with pytest.raises(household.HouseholdError):
            household.remove_member(db, home, user, user)


class TestBalances:
    def test_even_split(self, db, home, user, bob):
        household.add_shared_expense(db, home, user, 1000, "food", "2026-03-01")
        net = household.balances(db, home)
        assert net[user] == 500
        assert net[bob] == -500
        assert sum(net.values()) == 0

    def test_remainder_goes_to_payer(self, db, home, user, bob, carol):
        household.add_member(db, home, user, carol)
        household.add_shared_expense(db, home, user, 1000, "food", "2026-03-01")
        net = household.balances(db, home)
        # 1000 / 3 = 333 each, payer absorbs the extra cent.
        assert net[user] == 1000 - 333 - 1
        assert net[bob] == -333
        assert net[carol] == -333
        assert sum(net.values()) == 0

    def test_non_member_cannot_pay(self, db, home, carol):
        with pytest.raises(household.HouseholdError):
            household.add_shared_expense(
                db, home, carol, 500, "food", "2026-03-01")

    def test_settlement_plan_clears_debts(self, db, home, user, bob):
        household.add_shared_expense(db, home, user, 1000, "food", "2026-03-01")
        household.add_shared_expense(db, home, bob, 400, "transport", "2026-03-02")
        plan = household.settlement_plan(db, home)
        net = household.balances(db, home)
        for debtor, creditor, cents in plan:
            net[debtor] += cents
            net[creditor] -= cents
        assert all(v == 0 for v in net.values())

class TestInvites:
    def test_invite_flow(self, db, user, carol):
        hid = household.create_household(db, user, "Flat")
        code = household.create_invite(db, hid, user)
        assert household.accept_invite(db, code, carol) == hid
        assert household.require_member(db, hid, carol) == "member"

    def test_only_owner_invites(self, db, home, bob):
        with pytest.raises(household.HouseholdError):
            household.create_invite(db, home, bob)

    def test_bad_code(self, db, carol):
        with pytest.raises(household.HouseholdError):
            household.accept_invite(db, "zzzzzz", carol)

    def test_member_cannot_accept_twice(self, db, user, carol):
        hid = household.create_household(db, user, "Flat")
        code = household.create_invite(db, hid, user)
        household.accept_invite(db, code, carol)
        with pytest.raises(household.HouseholdError):
            household.accept_invite(db, code, carol)
