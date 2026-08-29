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
