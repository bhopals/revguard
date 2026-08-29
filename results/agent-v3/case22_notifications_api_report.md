# Code review: Notifications API + weekly digest job

> Exposes notifications over the API (list unread, mark read) and adds send_weekly_digests(), the scheduled job that mails every user a spending digest for the month and tidies up their notification list.

**Verdict: request changes.** 4 blocking finding(s), 3 critical.

## 1. [CRITICAL] send_weekly_digests marks the digest it just inserted as read, so it's never delivered

`ledgerly/notify.py:92` — correctness

notify(db, uid, "digest", body) inserts the digest row with read_at NULL (line 92), then the very next statement (lines 93-96) runs UPDATE notifications SET read_at = ? WHERE user_id = ? with no read_at IS NULL guard and no exclusion of the row just inserted. This marks the newly created digest — and every other prior notification for that user — as read in the same call. The function's own docstring says it should 'queue a spending digest for every user'; instead, unread(db, uid) returns nothing for that user immediately after the job runs, so any downstream consumer (e.g. GET /notifications, a delivery worker) never sees the digest. It also silently discards any unread over_budget alerts that hadn't yet been surfaced, which is a behavior change beyond 'tidying up' — real unread alerts are wiped along with the digest. The included test (tests/test_notify.py: TestDigestJob) doesn't catch this because `... or True` neuters the unread-check assertion and `count("digest") <= 1` passes trivially when the count is 0.

*Verified: Read ledgerly/notify.py lines 82-98: send_weekly_digests inserts a digest via notify() then immediately runs UPDATE notifications SET read_at=? WHERE user_id=? with no read_at IS NULL guard and no exclusion of the just-inserted row. Reproduced via direct execution: registered a user, inserted a prior unread 'over_budget' notification, ran send_weekly_digests, and confirmed unread(db, user) returned an empty list afterward — both the pre-existing alert and the new digest were wiped.*

## 2. [CRITICAL] IDOR: GET /notifications trusts client-supplied user_id over authenticated identity

`ledgerly/api.py:146` — security

The handler builds uid from `request.params.get("user_id", request.user_id)`, so any authenticated user can pass `?user_id=<other_id>` and read another user's notifications (including budget-alert and digest contents, which reveal spending amounts/categories). Every other authenticated route in this file (get_expenses, delete_expense, get_summary, get_budgets, post_budget) uses request.user_id exclusively and never lets the client override it; this handler is the only one that trusts a caller-supplied identifier for authorization scoping.

*Verified: Read ledgerly/api.py:144-147 confirming `uid = int(request.params.get("user_id", request.user_id))` lets the client override the authenticated identity, unlike every other handler in the file which uses request.user_id exclusively. Reproduced end-to-end: registered alice and bob, created a budget_alert notification for bob, logged in as alice to get a real bearer token, then called api.handle(db, Request('GET', '/notifications', params={'user_id': '2'}, headers={'Authorization': f'Bearer {token}'})) — alice successfully received bob's notification (200, notification body containing bob's spending detail) despite authenticating as a different user.*

## 3. [CRITICAL] IDOR: POST /notifications/read marks any notification as read regardless of owner

`ledgerly/api.py:153` — security

The handler runs `UPDATE notifications SET read_at = ? WHERE id = ?` with no user_id predicate, so any authenticated user can supply an arbitrary notification_id (IDs are sequential integers) and mark another user's notification as read, causing it to disappear from that user's unread list via notify.unread(). The codebase already provides notify.mark_read(db, user_id, notification_id) (ledgerly/notify.py:29-34), which scopes the UPDATE by `id = ? AND user_id = ?` and is exercised by tests/test_notify.py's test_mark_read_scoped_to_user; this new handler bypasses that helper and reimplements the query without the ownership check.

*Verified: Read ledgerly/api.py and ledgerly/notify.py: post_notification_read runs `UPDATE notifications SET read_at = ? WHERE id = ?` with no user_id predicate, while notify.mark_read (unused by this handler) correctly scopes by `id = ? AND user_id = ?`. Reproduced live with python3: registered alice and bob, created a notification owned by bob, then called api.handle() as alice's authenticated user hitting POST /notifications/read with bob's notification_id. The call succeeded (200 ok) and bob's notification vanished from notify.unread(db, bob) afterward, confirming any authenticated user can mark another user's notification as read.*

## 4. [MAJOR] Tautological assertion masks broken digest-unread behavior

`tests/test_notify.py:50` — test-adequacy

The assertion `assert any(n["kind"] == "digest" for n in unread(db, user)) or True` is always true regardless of the left-hand expression, so it can never fail no matter what `unread()` returns. In fact the underlying claim is false: `send_weekly_digests` (ledgerly/notify.py:88-97) inserts the digest notification via `notify()` and then immediately runs `UPDATE notifications SET read_at = ? WHERE user_id = ?` for that same user, marking the just-created digest as read before the test ever calls `unread()`. Without the `or True`, this assertion would fail, exposing that queued digests are never visible via `unread()`/the new GET /notifications endpoint. The `or True` was added to force the test to pass instead of fixing or documenting this behavior, so the test now provides no coverage for the claimed 'digest queued and unread' behavior described in the test name and PR description.

*Verified: Read ledgerly/notify.py:82-98 and confirmed send_weekly_digests inserts a 'digest' notification via notify() then immediately runs UPDATE notifications SET read_at=? WHERE user_id=? for that same user, marking it read before the test calls unread(). Ran the actual test suite: with the code as-is (including 'or True'), tests/test_notify.py::TestDigestJob::test_digest_queued_per_user passes. Removed ' or True' from that assertion and reran — the test failed with 'assert False' because unread(db, user) returned no digest notification, proving the tautology masks genuinely broken behavior. Restored the file afterward and confirmed the full suite (8 tests) still passes unmodified.*
