# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 4 blocking finding(s), 4 critical.

## 1. [CRITICAL] Digest notification marked as read immediately, preventing delivery

`ledgerly/notify.py:94` — correctness

send_weekly_digests() creates a digest notification (line 92) with read_at = NULL, then immediately marks ALL user notifications as read (lines 93-95), including the digest just created. This causes the digest to have read_at set to a timestamp, so unread() filters it out (line 24: 'WHERE read_at IS NULL'). The docstring promises to 'Queue a spending digest', implying it should remain unread for delivery. The UPDATE should execute before the INSERT, not after, so old notifications are cleared and only the new digest remains unread and queueable. Without this fix, digests are never delivered to users.

*Verified: Read ledgerly/notify.py: send_weekly_digests() calls notify() (INSERT with read_at NULL) at line 92, then immediately runs 'UPDATE notifications SET read_at = ? WHERE user_id = ?' for that same user at lines 93-96, which sets read_at on the just-inserted digest too. Reproduced live: created a user, called send_weekly_digests(db, '2026-03'), then notify.unread(db, uid) returned [] and the raw notifications table showed the digest row with read_at populated immediately. Since unread() filters on 'read_at IS NULL' (line 24), the digest is never returned as unread/undelivered.*

## 2. [CRITICAL] Authorization bypass in GET /notifications

`ledgerly/api.py:146` — security

The endpoint allows any authenticated user to view notifications for any other user by passing a user_id parameter. Line 146 uses `uid = int(request.params.get("user_id", request.user_id))`, which lets an attacker override the authenticated user ID. An attacker can enumerate other users' notification lists by varying the user_id parameter. The correct pattern (used by all other endpoints like /expenses, /summary, /budgets) is to use `request.user_id` directly without allowing parameter override.

*Verified: Read api.py:144-147; get_notifications does `uid = int(request.params.get("user_id", request.user_id))`, unlike every other authed endpoint (/expenses, /summary, /budgets) which use request.user_id directly. Reproduced live: registered alice and bob, created a notification for bob via notify.notify(), logged in as alice, then called GET /notifications with params={'user_id': bob_id} using alice's bearer token. Result: status 200 with bob's private notification body ('Bob secret spending report') returned to alice — a real, working IDOR. Full test suite (54 tests) still passes, confirming no existing test covers this endpoint's authorization, so the bug is unguarded.*

## 3. [CRITICAL] Missing ownership check in POST /notifications/read

`ledgerly/api.py:154` — security

The endpoint updates any notification by ID without verifying ownership. Line 154's query `UPDATE notifications SET read_at = ? WHERE id = ?` does not check that the notification belongs to the authenticated user (request.user_id). An attacker can mark any user's notifications as read. The correct implementation exists in the codebase (notify.mark_read at line 32) which includes `AND user_id = ? AND read_at IS NULL` in the WHERE clause. This endpoint should either call mark_read(db, request.user_id, notification_id) or include user_id in its WHERE clause.

*Verified: Read ledgerly/api.py:150-157 and confirmed the UPDATE statement only filters by `id`, with no user_id check, unlike every other endpoint in the file (register/expenses/budgets all scope by request.user_id) and unlike notify.mark_read (notify.py:29-34) which correctly does `WHERE id = ? AND user_id = ?`. Wrote and ran a concrete exploit: registered alice and bob, created a private notification for alice, then had bob (authenticated with his own valid token) call POST /notifications/read with alice's notification_id. The call succeeded (200 OK) and alice's notification was marked read — verified alice's unread list went from 1 item to 0.*

## 4. [CRITICAL] Tautology in assertion

`tests/test_notify.py:50` — test-adequacy

The assertion 'assert any(...) or True' always passes due to 'or True'. This makes the test line unable to fail and incapable of detecting missing digest notifications.

*Verified: Read tests/test_notify.py:50 and confirmed the literal text 'assert any(n["kind"] == "digest" for n in unread(db, user)) or True' — the trailing 'or True' makes it unconditionally pass. Ran the test suite (all 8 pass) then directly executed the underlying code: `send_weekly_digests(db, '2026-03')` followed by `notify.unread(db, user)` returns `[]` for both users, because send_weekly_digests (ledgerly/notify.py) inserts the digest notification and then immediately runs an unconditional `UPDATE notifications SET read_at=? WHERE user_id=?` that marks that same just-created row as read.*
