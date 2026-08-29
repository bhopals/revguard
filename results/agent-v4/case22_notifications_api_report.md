# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 5 blocking finding(s), 3 critical.

## 1. [CRITICAL] send_weekly_digests marks the digest it just inserted (and all other unread notifications) as read

`ledgerly/notify.py:93` — correctness

In send_weekly_digests, notify(db, uid, "digest", body) inserts the digest with read_at NULL (line 92), but the very next statement runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` with no read_at IS NULL filter and no kind filter (lines 93-96). This updates every notification row for that user, including the digest row just inserted in the same iteration. As a result the digest is immediately marked read and never appears in unread(db, uid) — the module's own docstring states 'a delivery worker reads unread rows' (notify.py:3-4), so the delivery worker will never see any digest, defeating the entire feature the PR claims to add ('mails every user a spending digest'). The same UPDATE also silently marks any other outstanding unread notifications for that user (e.g. unread over_budget alerts from run_budget_alerts) as read, even though the user never acted on them, which contradicts the guarantee provided by mark_read (which only marks read on explicit user action, scoped by id/user). The bundled test (tests/test_notify.py:50) masks this because it asserts `... or True`, so it always passes regardless of whether any digest is actually left unread.

*Verified: Read ledgerly/notify.py:82-98, matching the diff exactly. Ran a direct reproduction: after send_weekly_digests(db, '2026-03'), notify.unread(db, alice) returns [] even though sent==2 and a digest row was inserted; querying the notifications table directly shows the digest row has read_at set immediately. Also confirmed a pre-existing unread over_budget notification for the user is wiped (marked read) by the same job, despite the user never acting on it. Ran the bundled test suite (pytest tests/test_notify.py) — all 8 tests pass despite the bug, confirming the added test's `... or True` clause masks the defect.*

## 2. [CRITICAL] IDOR: GET /notifications lets any authenticated user read another user's notifications

`ledgerly/api.py:146` — security

get_notifications() takes uid from request.params.get("user_id", request.user_id) instead of always using the authenticated request.user_id. Any logged-in user can pass ?user_id=<other_id> to read another user's notifications, which include over-budget alert bodies containing spend/category/limit details. There is no admin/role check anywhere in auth.py to justify trusting a client-supplied user_id. This directly contradicts the pattern used everywhere else in api.py (expenses, summary, budgets all scope strictly by request.user_id).

*Verified: Read ledgerly/api.py:144-147: get_notifications() sets uid = int(request.params.get("user_id", request.user_id)) with no ownership/role check afterward, unlike every other handler (expenses, summary, budgets) which use request.user_id exclusively. Grepped for 'role'/'admin' across ledgerly/ and found household.py's role concept is scoped to household membership (owner/member) only, never checked in api.py's notifications route.*

## 3. [CRITICAL] Tautological assertion (`or True`) makes the check unable to fail

`tests/test_notify.py:50` — test-adequacy

Line 50 is `assert any(n["kind"] == "digest" for n in unread(db, user)) or True`. Because of the trailing `or True`, this assertion is always true no matter what `unread(db, user)` returns — even if no digest notification was ever created for the user, or if `unread()` raises no error but returns an empty list. This test therefore cannot catch the real bug in `send_weekly_digests` (ledgerly/notify.py:93-96), which marks every notification for the user as read (including the digest just inserted) immediately after creating it, so `unread(db, user)` will actually be empty. The test passes despite the digest never showing up as unread, which is the exact behavior the test name ('queued_per_user') claims to verify.

*Verified: Read ledgerly/notify.py:82-98: send_weekly_digests inserts a digest notification via notify() then immediately runs UPDATE notifications SET read_at=... WHERE user_id=uid, marking the just-inserted digest as read. Read tests/test_notify.py:46-52: the assertion at line 50 is `assert any(...) or True`, which is a tautology (always True) regardless of the generator's result. Ran the actual test file with pytest: it passes as-is. Then temporarily removed the `or True` and reran: the test failed with `assert False`, proving unread(db, user) is genuinely empty after send_weekly_digests runs — confirming the real bug is masked by the tautological assertion.*

## 4. [MAJOR] IDOR: POST /notifications/read marks any user's notification as read without ownership check

`ledgerly/api.py:153` — security

post_notification_read() runs `UPDATE notifications SET read_at = ? WHERE id = ?` using only the caller-supplied notification_id, with no user_id filter. Any authenticated user can enumerate/guess notification_id values and mark other users' notifications as read, silently clearing their unread over-budget alerts and digests without their knowledge. The existing helper notify.mark_read(db, user_id, notification_id) already implements the correct ownership-scoped query (WHERE id = ? AND user_id = ? AND read_at IS NULL) but this new handler bypasses it and reimplements the UPDATE unsafely.

*Verified: Read ledgerly/api.py:150-157: post_notification_read runs `UPDATE notifications SET read_at = ? WHERE id = ?` with only notification_id, no user_id filter, unlike ledgerly/notify.py:29-34 mark_read() which scopes by `WHERE id = ? AND user_id = ? AND read_at IS NULL`. Reproduced live via python3: registered alice and bob, created a notification for bob, authenticated as alice, called api.handle() with POST /notifications/read and bob's notification_id — got 200 {'ok': True}, and notify.unread(db, bob) went from containing the notification to empty, proving alice (an unrelated authenticated user) cleared bob's unread notification.*

## 5. [MINOR] send_weekly_digests silently clears all unread notifications, not just digests, contrary to its docstring's implication

`ledgerly/notify.py:82` — correctness

The docstring says the job will "clear their read pile" as part of sending a digest, but the implementation (lines 93-96) marks every unread notification row for the user as read regardless of `kind` — including unrelated `over_budget` alerts the user has never seen. A user who has an unread budget-alert notification will have it marked read the moment the weekly digest job runs, even though they never opened it. The docstring should call out this destructive side effect explicitly (e.g. "marks all prior unread notifications, of any kind, as read") so callers/maintainers don't assume it only touches old digests.

*Verified: Read ledgerly/notify.py:82-98 — send_weekly_digests runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` with no `kind` filter. Reproduced with a live script: created an unread over_budget alert via run_budget_alerts, confirmed unread() showed ['over_budget'], then called send_weekly_digests, and unread() became [] — even the newly-inserted digest itself was marked read immediately, alongside the unrelated budget alert. Existing test suite (8 tests) passes since no test exercises a pre-existing unread notification of another kind before calling send_weekly_digests.*
