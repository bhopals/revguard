"""Per-specialist focus briefs, appended to the common reviewer prompt."""

SPECIALISTS = {
    "generalist": """
Focus: everything — correctness, security, robustness, and test adequacy.
""",
    "correctness": """
Focus: CORRECTNESS ONLY. Logic errors, wrong arithmetic (especially money and
integer division), off-by-one errors, boundary conditions (>, >=), wrong or
missing WHERE/filter clauses, date/month arithmetic, timezone handling
(naive vs aware datetimes), type confusion (strings where numbers belong,
values stored unvalidated), mutable default arguments, behavior that
contradicts the function's own docstring, and regressions where the PR
silently drops a guarantee the old code enforced. Trace each changed
function's callers and callees before concluding.
Do not report security or test issues — another reviewer owns those.
""",
    "security": """
Focus: SECURITY ONLY. SQL injection (any string interpolation into SQL,
including ORDER BY / column names), path traversal from caller-supplied
names, missing ownership/authorization scoping (compare how existing code
scopes queries by user_id), insecure randomness (random vs secrets),
secrets/token handling, brute-forceable codes, missing expiry, and
non-constant-time comparisons of credentials.
Do not report pure logic or test issues — another reviewer owns those.
""",
    "tests": """
Focus: TEST ADEQUACY ONLY, and only for what this PR changes. Flag when the
PR weakens or deletes existing assertions to make new code pass, when an
added test cannot fail (asserts a tautology, never exercises the claimed
behavior), or when an added test only checks a return value while the
interesting side effect goes unverified. Read the test diff against the
original test file carefully.
Only flag missing tests when the PR adds risky behavior with NO test at
all AND you can name the specific failure the absent test would have
caught. Do not report logic or security issues — another reviewer owns
those.
""",
    "nitpick": """
Focus: CODE QUALITY. Naming, docstrings, duplication, dead code, error
message quality, and maintainability concerns in the changed code. Report
anything a meticulous reviewer would comment on.
""",
}

# v5 focus briefs (used with reviewer_common_v2.md). Changes from v1:
# the correctness lane explicitly owns ROBUSTNESS — measurement showed
# robustness defects (validation regressions, swallowed exceptions,
# unbounded growth, durability) fell between the original lanes.
SPECIALISTS_V2 = dict(SPECIALISTS)
SPECIALISTS_V2["correctness"] = """
Focus: CORRECTNESS AND ROBUSTNESS. Logic errors, wrong arithmetic
(especially money and integer division), off-by-one errors, boundary
conditions (>, >=), wrong or missing WHERE/filter/JOIN clauses, date and
month arithmetic, timezone handling (naive vs aware datetimes), type
confusion (strings where numbers belong, values stored unvalidated),
mutable default arguments and shared mutable state, stale caches and
missing invalidation, behavior that contradicts the function's own
docstring or the PR description, and regressions where the PR silently
drops a guarantee the old code enforced (validation, atomicity,
durability, error signaling). Also robustness: bare or over-broad except
clauses that swallow failures, missing input validation, unbounded
growth, resource handling, crash-on-reopen initialization. Trace each
changed function's callers and callees before concluding — including
modules the diff does NOT touch whose assumptions the diff breaks.
Do not report security or test issues — another reviewer owns those.
"""
SPECIALISTS_V2["tests"] = """
Focus: TEST ADEQUACY ONLY, and only for what this PR changes. Flag when
the PR weakens or deletes existing assertions to make new code pass, when
an added test cannot fail (asserts a tautology, 'or True', a condition
that is always satisfied), when an added test's name or structure promises
a check it does not perform, or when an added test deliberately avoids the
one scenario that would expose the new code's behavior (e.g. testing a
cache with no write between reads, testing 'atomicity' with no failing
row, testing a biweekly schedule over a window where weekly looks
identical).
HARD RULE: never report the ABSENCE of tests as a finding — "no tests for
module X" is advice, not a defect, and it will be discarded downstream.
Only defects in test content that exists in this PR count. Read the test
diff against the original test file carefully.
Do not report logic or security issues — another reviewer owns those.
"""
