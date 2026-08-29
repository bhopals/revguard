# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 3 blocking finding(s), 1 critical.

## 1. [CRITICAL] Weekly digest is marked read immediately after creation, so it never appears as unread

`ledgerly/notify.py:92` — correctness

In send_weekly_digests, notify(db, uid, "digest", body) inserts a new unread notification (line 92), and the very next statement (lines 93-96) runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` with no created_at/id filter, so it also marks the row just inserted as read. Since db.execute commits immediately (ledgerly/db.py:126-129), every digest notification is read_at-stamped before the function returns. Consequently notify.unread(db, uid) and the new GET /notifications endpoint never surface the digest to the user, and any delivery worker that (per the module docstring) 'reads unread rows' will never see it either — the digest is silently discarded even though send_weekly_digests reports it as 'sent'. The test added for this (tests/test_notify.py:47-52) is written so it cannot catch the bug: line 50 ends with `or True`, making that assertion always pass, and line 52's `<= 1` check passes whether 0 or 1 digests are unread.

## 2. [MAJOR] GET /notifications allows reading any user's notifications via user_id parameter

`ledgerly/api.py:146` — security

get_notifications takes uid from `request.params.get("user_id", request.user_id)` instead of using the authenticated request.user_id directly. Any authenticated caller can pass `?user_id=<other_id>` to read another user's notification list (including budget-alert and digest bodies, which can reveal spending details). Every other authenticated GET handler in this file (get_expenses, get_summary, get_budgets) uses request.user_id exclusively with no client-supplied override; this handler is the only one that trusts a client-supplied user id for authorization, and there is no ownership/household check performed before returning the data.

## 3. [MAJOR] POST /notifications/read marks any notification as read without checking ownership

`ledgerly/api.py:153` — security

post_notification_read runs `UPDATE notifications SET read_at = ? WHERE id = ?` using only the client-supplied notification_id, with no `user_id = request.user_id` constraint. Any authenticated user can mark any other user's notification (e.g. an over-budget alert or digest) as read by guessing/enumerating small integer ids, causing that notification to disappear from the victim's unread list. The codebase already has a correctly scoped helper, notify.mark_read(db, user_id, notification_id) (ledgerly/notify.py:29-34), which filters by `id = ? AND user_id = ?` and is covered by tests/test_notify.py:14-17 (test_mark_read_scoped_to_user); this new API handler bypasses that helper and reimplements the update without the ownership check.
