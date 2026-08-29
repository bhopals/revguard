# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 4 blocking finding(s), 2 critical.

## 1. [CRITICAL] IDOR: GET /notifications lets any authenticated user read another user's notifications

`ledgerly/api.py:146` — security

get_notifications() computes `uid = int(request.params.get("user_id", request.user_id))`, trusting a client-supplied `user_id` query parameter over the authenticated `request.user_id`. Any logged-in user can call `GET /notifications?user_id=<victim>` to retrieve another user's full unread notification list (including over-budget alerts and digest bodies with spending details), bypassing authorization entirely. Every other authenticated handler in this file (e.g. get_expenses, get_summary, get_budgets) uses `request.user_id` directly with no client override, so this is a deviation introduced by the PR.

*Verified: Read ledgerly/api.py:144-147 and confirmed `uid = int(request.params.get("user_id", request.user_id))` trusts a client-supplied query param over the authenticated request.user_id, unlike every other authenticated handler in the file (get_expenses, get_summary, get_budgets, delete_expense all use request.user_id directly). Confirmed notify.unread(db, user_id) (ledgerly/notify.py:21-26) performs no ownership/authorization check, just a raw SELECT by user_id.*

## 2. [CRITICAL] Missing ownership check lets any user mark another user's notifications as read

`ledgerly/api.py:150` — security

post_notification_read() runs `UPDATE notifications SET read_at = ? WHERE id = ?` using only the client-supplied notification_id, with no filter on request.user_id. Any authenticated user can pass an arbitrary/guessed notification_id (ids are small sequential integers) and mark any other user's notification as read, effectively dismissing/suppressing alerts (e.g. over-budget notices) they don't own. The codebase already has notify.mark_read(db, user_id, notification_id) (ledgerly/notify.py:29-34) which correctly scopes by `WHERE id = ? AND user_id = ?`, but the new API handler does not use it and instead issues its own unscoped SQL.

*Verified: Read ledgerly/api.py: post_notification_read runs `UPDATE notifications SET read_at = ? WHERE id = ?` using only the client-supplied notification_id, with no user_id filter, while notify.mark_read(db, user_id, notification_id) in ledgerly/notify.py correctly scopes by `WHERE id = ? AND user_id = ?` but is never called from the API handler. Reproduced live via handle(): created a notification owned by alice (user 1), authenticated as bob (user 2), and POSTed /notifications/read with alice's notification_id. The request succeeded (200 {'ok': True}) and alice's unread list became empty — bob successfully suppressed alice's notification despite having no ownership of it.*

## 3. [MAJOR] send_weekly_digests marks the digest it just created as read

`ledgerly/notify.py:93` — correctness

In send_weekly_digests, notify(db, uid, "digest", body) inserts a new notification with read_at NULL (line 92), but the very next statement (lines 93-96) runs an unscoped UPDATE that sets read_at for every notification belonging to that user, with no WHERE read_at IS NULL or exclusion of the row just inserted. This means the digest notification is marked read in the same call that creates it, so it never shows up in notify.unread(db, uid) or the GET /notifications endpoint. The docstring promises to 'Queue a spending digest for every user' (implying the user can see/act on it) while also clearing old notifications, but as written the digest itself is immediately swallowed along with everything else, so users never actually see their weekly digest via the notification list. The included test masks this: `assert any(n["kind"] == "digest" for n in unread(db, user)) or True` always passes regardless of the actual (broken) behavior.

*Verified: Read ledgerly/notify.py:82-98: send_weekly_digests inserts a digest notification then runs UPDATE notifications SET read_at = ? WHERE user_id = ? with no filter on read_at IS NULL or the newly inserted id, so it marks the just-created digest (and all other notifications) as read. Reproduced live: registered two users, called send_weekly_digests(db, '2026-03'), then notify.unread(db, user) and notify.unread(db, bob) both returned [] despite sent == 2, confirming digests are immediately swallowed and never reachable via GET /notifications.*

## 4. [MAJOR] Tautological assertion via `or True` can never fail

`tests/test_notify.py:50` — test-adequacy

`assert any(n["kind"] == "digest" for n in unread(db, user)) or True` is always true regardless of the left-hand expression, because of the trailing `or True`. This makes the assertion a no-op: it can never fail no matter what `send_weekly_digests` does. In fact the real behavior it should be checking is broken — `send_weekly_digests` (ledgerly/notify.py:82-98) inserts the digest notification via `notify()` and then immediately runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` with no `read_at IS NULL` filter, which also marks the just-inserted digest as read. So `unread(db, user)` actually returns `[]` after the call, and the `any(...)` expression evaluates to `False` — a genuine regression from the docstring's promise ("Queue a spending digest for every user"). The `or True` masks this and lets the test pass despite the digest never appearing as unread.

*Verified: Read ledgerly/notify.py:82-98 and tests/test_notify.py:46-52, confirming the diff verbatim. Ran the test suite as-is (8 passed, including the tautological assertion).*
