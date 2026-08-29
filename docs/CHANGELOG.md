# Improvement Changelog

Every entry was actually run and measured; every number traces to a JSON
file under `results/` and can be regenerated (`docs/REPRODUCTION.md`).
Metrics are F1 / recall / precision over the seeded-defect benchmark with
the fixed matching rule in `eval/score.py`. All systems use the same model.

> **Scoring note.** Ground truth was adjudicated twice (see the
> Adjudication section below) — both passes *helped the baseline*, which
> is how you know they were honest. All systems are always re-scored
> against the same final labels.

<!-- FINAL_TABLE -->

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
<!-- V5_RESULT -->

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
2. **Round 2** (after all systems ran): <!-- ADJUDICATION_2 -->

## Main failure mode & hot take

<!-- HOT_TAKE -->
