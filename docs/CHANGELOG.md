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
instructed to falsify it by execution. <!-- V3_RESULT -->

**Learning:** the verifier confirmed 29/29 findings from the conservative
reviewers — zero rejections. A precision stage is useless when the
upstream is already starved down to only-safe findings. The layering was
backwards: reviewers were doing the verifier's job (filtering) instead of
their own (finding).

## Iteration 4 (v4) — the experiment we removed: a nitpick reviewer

Added a fourth "code quality" reviewer (naming, docstrings, duplication)
to test whether more coverage helps. <!-- V4_RESULT -->

**Decision: removed.** <!-- V4_DECISION -->

## Iteration 5 (v5, final) — recall-tuned reviewers + verifier

The measurement-driven redesign: reviewers are explicitly told a
verification stage sits downstream and to optimize for recall within
their lane (real defects only — no style, no advisory comments);
the correctness lane now owns robustness; prompts are versioned
(`reviewer_common_v2.md`) so v1–v4 remain reproducible.
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
