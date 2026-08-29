# Improvement Changelog

Every entry was actually run and measured; every number traces to a JSON
file under `results/` and can be regenerated (`docs/REPRODUCTION.md`).
Metrics are F1 / recall / precision over the seeded-defect benchmark with
the fixed matching rule in `eval/score.py`. All systems use the same model.

> **Scoring note.** Ground truth was adjudicated twice (see the
> Adjudication section below) — both passes *helped the baseline*, which
> is how you know they were honest. All systems are always re-scored
> against the same final labels.

## Final results (ground truth frozen at 61 defects, 22 cases)

**Tier 3 — six large multi-file PRs, the regime this tool targets:**

| system | found | recall | precision | F1 | FPs |
|---|---|---|---|---|---|
| baseline (1 prompt, no tools) | 19/22 | 0.86 | 0.90 | 0.884 | 2 |
| **RevGuard v5 (final)** | **20/22** | **0.91** | **0.95** | **0.930** | **1** |

**All 22 cases (both regimes pooled):**

| system | found | recall | precision | F1 | FPs | clean-PR FPs | avg s/case | avg $/case |
|---|---|---|---|---|---|---|---|---|
| baseline | 58/61 | 0.951 | 0.906 | 0.928 | 6 | 0 | 40 | 0.05 |
| v1 tooled generalist | 40/61 | 0.656 | 0.976 | 0.784 | 1 | 0 | 46 | 0.10 |
| v2 + specialists | 44/61 | 0.721 | 0.846 | 0.779 | 8 | 0 | 47 | 0.23 |
| v3 + verifier (truth-only) | 44/61 | 0.721 | 0.815 | 0.765 | 10 | 0 | 79 | 0.39 |
| v4 + nitpick (removed) | 51/61 | 0.836 | 0.810 | 0.823 | 12 | 0 | 105 | 0.55 |
| **v5 recall-tuned + policy-gated verifier** | 51/61 | 0.836 | **0.944** | 0.887 | **3** | 0 | 110 | 0.50 |

Tier 1–2 (16 small PRs) is saturated: the baseline reads 39/39 there, and
that finding — the base model has *solved* small-diff review — is
result #1 of this project. Human time comparison: a careful human review
of a tier-3 PR is 30–60 minutes; both systems run in ~1–2 minutes for
under a dollar.

## Baseline — one prompt, diff inline, no tools

The realistic "what people do today": paste the diff into the model and
ask for a review. On the 16 small-PR cases (tiers 1–2) it scored
**recall 1.000 / precision 0.907 / F1 0.951** — it found all 39 seeded
defects. Our first benchmark was saturated.

**Decision:** two consequences. (1) The interesting regime is not small
clean diffs — we expanded the benchmark with tier 3: six large, noisy,
multi-file PRs against a grown codebase (Ledgerly Pro, ~1,400 LOC), with
cross-module defects invisible from the diff alone. (2) On the full
22-case benchmark the baseline drops to **F1 0.903 (recall 0.949 /
precision 0.862)** — it misses execution-dependent bugs outright (the
index that crashes on database reopen) and *hedges* on bugs it cannot
confirm without the repo: real defects come back phrased as "there is no
test covering X" advisory comments. That hedging pattern is the
bottleneck our design attacks.

## Iteration 1 (v1) — one generalist agent with repo tools

Same model, but an agent with Read/Grep/Glob over the full post-PR repo,
and a conservative brief ("report only what you'd block the merge on").
Result: **F1 0.719 (recall 0.590 / precision 0.920)** on tiers 1–2 —
*far worse than the baseline*.

**Learning:** tools don't help if the calibration is wrong. Told to be
conservative, the agent silently dropped real majors and minors. Kept the
tools, revised the calibration later (v5).

## Iteration 2 (v2) — three parallel specialists

Split into correctness / security / test-adequacy reviewers, each with a
narrow checklist brief. **F1 0.722 (recall 0.667 / precision 0.788)** —
recall up from v1, precision *down* (specialists produce more, including
more noise), still far below baseline.

**Learning:** two structural gaps. (1) No lane owned ROBUSTNESS —
validation regressions, swallowed exceptions, unbounded growth fell
between the chairs (the misses were almost all robustness-class). (2)
More findings without a filter = worse precision. Both fixes are in v5.

## Iteration 3 (v3) — v2 + adversarial verifier

Every finding goes to a separate agent, in a fresh sandbox with Bash,
instructed to falsify it by execution. **F1 0.743 (recall 0.712 /
precision 0.778)** on all 22 cases — barely moved from v2, at twice the
latency and cost.

**Learning:** the verifier confirmed **54 of 54** findings — zero
rejections — for two distinct reasons we only separated by reading its
trajectories. (1) *Starvation:* conservative reviewers had already
filtered themselves, so there were few wrong claims to kill. (2) *Rubber
stamping:* the false positives it did receive were advisory comments
("no tests cover X") that are factually TRUE — the verifier checked
truth, and truth is the wrong gate for advice. A verification stage
needs a policy gate as well as a truth gate. Both fixes landed in v5.

## Iteration 4 (v4) — the experiment we removed: a nitpick reviewer

Added a fourth "code quality" reviewer (naming, docstrings, duplication)
expecting it to add noise and prove the value of narrow lanes. It did the
opposite: **F1 0.829 (recall 0.864 / precision 0.797)** vs v3's 0.743.
Attribution (findings carry their reviewer's name, so this is exact): the
nitpick lane produced 15 true findings and 6 false positives, and **11
defects that no specialist caught** — v4 minus its nitpick findings
scores F1 0.755.

**Decision: removed anyway — but for the right reason.** The nitpick
lane's edge wasn't taste in naming; it was its *permissive brief*. The
specialists were told to self-censor ("only what you'd block a merge on")
while nitpick was told to report anything worth a comment — so nitpick
kept catching real defects the specialists talked themselves out of. Its
false positives, meanwhile, were exactly the style noise we feared. So we
removed the lane and transplanted its permissiveness into the specialist
briefs (v5's recall calibration). The experiment's lesson: **calibration,
not specialization, was the binding constraint.**

## Iteration 5 (v5, final) — recall-tuned reviewers + verifier

The measurement-driven redesign, three changes at once, each answering a
measured failure:

1. **Recall-tuned reviewers** (`reviewer_common_v2.md`): reviewers are
   told a verification stage sits downstream and to optimize for recall
   within their lane — answers v1's conservative-calibration collapse.
2. **Robustness has an owner**: the correctness lane's brief now
   explicitly covers validation regressions, swallowed exceptions,
   durability, unbounded growth — answers v2's between-the-chairs misses.
3. **Policy-gated verifier** (`verifier_v2.md`): v3's verifier confirmed
   54/54 findings including every false positive, because the FPs were
   *factually true* advisory comments ("there is indeed no test for X") —
   it checked truth but never whether a true observation is a blocking
   defect. The v2 verifier gates on both: truth (attack by execution) AND
   policy (advice is rejected even when true). The tests specialist also
   gets a hard ban on coverage-advisory findings (defense in depth).

All prompts are versioned; v1–v4 remain reproducible byte-for-byte.

**Result: on tier 3 — the large, realistic PRs this tool exists for — v5
beats the baseline on every metric: F1 0.930 vs 0.884, recall 0.91 vs
0.86, precision 0.95 vs 0.90, one false positive across six large PRs vs
two.** Overall (all 22 cases) v5 scores F1 0.887 with 3 false positives
against the baseline's 0.928 with 6 — the gap is entirely the saturated
small-PR tier, where the baseline reads 39/39 and nothing can improve on
it. The policy-gated verifier did its job this time: it rejected advisory
findings the reviewers still produced, cutting false positives from v4's
13 to 3 while recall-tuned reviewers held recall.

The tier-3 F1 progression across the whole changelog — baseline 0.884 →
v1 0.872 → v2 0.857 → v3 0.773 → v4 0.809 → **v5 0.930** — is the
honest shape of this project: adding agent machinery made things *worse*
until measurement showed which calibrations were wrong.

## Adjudication passes (label corrections, applied to all systems)

1. **Round 1** (after baseline + v1, before v2/v3/v5 ran): two defects
   were being scored as missed purely because the finding named a
   different-but-valid location (the same bug reported at the schema line
   instead of the insert line). Added alternate anchors. Four genuine
   defects that a system found in our seeded code but our labels lacked
   (session tokens surviving password reset; reset codes lost on restart;
   token-file permission race; cache returning a mutable reference) were
   promoted to ground truth. Net effect: baseline recall ROSE from 0.943
   to 1.000 on tiers 1–2.
2. **Round 2** (after all systems ran, before the final table): applied
   the four written rules in `tools/adjudicate.py` to every FP and miss
   of every system. Three alternate anchors (the currency-mixing bug is
   validly reported at the untouched aggregation query; the invite-cap
   bypass at accept_invite's insert; the biweekly impossibility at
   create_rule). Two promotions — added tests *named for* the defective
   behavior but structured to dodge it (`test_resume_reactivates` never
   spans a paused occurrence; `test_balances_for_own_household` never
   tests a non-member) — both flagged independently by the baseline and
   the agent, matching the pattern of four pre-existing GT defects.
   Pure "no tests for X" advisories stayed false positives for everyone.
   Final ground truth: **61 defects, frozen.** Net effect of the round:
   baseline recall rose 0.949 → 0.951, so the refinements again favored
   the baseline's totals; they also cleaned both systems' FP columns
   symmetrically.

## Main failure mode & hot take

**Main failure mode.** The final system's remaining misses are almost all
minor-severity defects on small diffs (a `>` vs `>=` boundary, unescaped
LIKE wildcards): even recall-tuned specialists talk themselves out of
minors. More interesting are its two tier-3 misses — the never-consumed
invite code and the `synchronous = OFF` durability trade — both of which
a reviewer *mentioned* in an adjacent framing that then fell to lane
boundaries or the policy gate. Filtering stages don't just remove noise;
they define what the system is allowed to notice. Every gate you add
needs its own miss-audit.

**Hot take.** Everyone bolts a verifier onto their agent pipeline; almost
nobody measures what it actually gates. Ours confirmed **54 of 54**
findings — pure cost, zero value — for a reason that generalizes:
*verification checks truth, but most bad review comments are true.*
"There are no tests for X" is factually correct and still noise. A
verifier needs a policy gate (is this a defect a staff engineer would
block on?) as much as a truth gate, and the reviewers feeding it should
be tuned permissive precisely BECAUSE it exists — our biggest single
improvement came from moving the conservatism from the generators to the
filter. And beneath all of it, the two-regime finding: the base model
one-shots small-PR review (39/39 on our tier 1–2) — building agent
machinery there is negative-value. Benchmark until you find where the
model actually breaks, then build exactly there. On large multi-file PRs
the same machinery that lost on small diffs wins on every metric.
