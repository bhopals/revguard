# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] send_weekly_digests marks the digest it just created as read, so it is never delivered

`ledgerly/notify.py:92` — correctness

In send_weekly_digests, for each user the code calls notify(db, uid, "digest", body) (line 92) which inserts a new notification row with read_at = NULL, and then immediately runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` (lines 93-96) with no read_at IS NULL guard and no exclusion of the row just inserted. This UPDATE marks every notification for that user — including the digest inserted one line above — as read in the same transaction/call. Since notify.unread() (used by both the GET /notifications API and, per the module docstring, the delivery worker that emails/pushes notifications) only returns rows where read_at IS NULL, the digest is immediately invisible to unread() and will never be surfaced via the API or emailed by a delivery worker. This defeats the entire purpose of the job: 'the scheduled job that mails every user a spending digest' never actually results in a deliverable/visible digest. The bug is masked in tests/test_notify.py because the assertion `any(n["kind"] == "digest" for n in unread(db, user)) or True` is vacuously true and `bodies.count("digest") <= 1` also passes when the count is 0.

## 2. [CRITICAL] IDOR: any authenticated user can read another user's notifications

`ledgerly/api.py:146` — security

get_notifications lets the caller override the authenticated user id via the `user_id` query param (`request.params.get("user_id", request.user_id)`), instead of always using `request.user_id` like every other handler in this file (get_expenses, get_summary, get_budgets, delete_expense all use request.user_id unconditionally with no override). Any authenticated user can call GET /notifications?user_id=<other_uid> and read another user's full notification list, including over_budget alerts and weekly spending digests, which leak that user's spending categories and totals. This is a broken access control / IDOR vulnerability exposing sensitive financial data across accounts.

## 3. [MAJOR] POST /notifications/read drops the ownership guarantee enforced by notify.mark_read

`ledgerly/api.py:154` — correctness

The existing notify.mark_read(db, user_id, notification_id) helper updates with `WHERE id = ? AND user_id = ? AND read_at IS NULL`, guaranteeing a caller can only mark their own, currently-unread notifications as read. The new post_notification_read handler bypasses this helper and issues its own UPDATE with only `WHERE id = ?` (line 154), dropping both the user_id and read_at IS NULL filters. Any authenticated caller supplying an arbitrary notification_id can mark any other user's notification as read (or re-stamp an already-read one), silently making that notification disappear from the victim's GET /notifications (unread) results. This is a regression versus the guarantee the pre-existing mark_read function enforced for exactly this operation.

## 4. [MAJOR] Tautological assertion masks digest-marked-as-read bug

`tests/test_notify.py:50` — test-adequacy

Line 50 `assert any(n["kind"] == "digest" for n in unread(db, user)) or True` is unconditionally true because of the trailing `or True`, so it can never fail regardless of what `unread()` returns. This directly hides a real defect in `send_weekly_digests` (ledgerly/notify.py:92-96): the function inserts the digest notification via `notify()` and then immediately runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` for that same user with no `read_at IS NULL` guard, which marks the just-created digest notification as read in the same call. Without the `or True`, this assertion — the only place in the new test that checks whether a digest actually appears as unread — would fail, since `unread(db, user)` returns an empty list after `send_weekly_digests` runs. The remaining assertion (line 51-52, `bodies.count("digest") <= 1`) is trivially satisfied by an empty list and doesn't verify the digest was ever delivered/unread, so the test suite gives no coverage that the digest job actually leaves a readable notification for the user, despite that being the entire purpose of the feature.
