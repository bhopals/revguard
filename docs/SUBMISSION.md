# Submission checklist (deadline: Mon Aug 31, 18:00 UTC)

Four required items, per the challenge page:

## 1. Complete solution code + improvement changelog
- [x] Full project in this repo (agents, prompts, benchmark, eval)
- [x] README: intended user, bottleneck, why it matters
- [x] README results: tier-3 table, saturation finding, stability
      (2 runs/system), all traceable to results/
- [x] `docs/CHANGELOG.md` — every iteration measured, incl. the removed
      experiment (v4) with exact attribution and the two adjudication
      rounds
- [x] Hot take + main failure mode finalized (verifier policy-gate
      insight; 54/54 rubber-stamp evidence)
- [x] What existed before the competition: nothing — every file in this
      repo was created during the event (see git log). Tools used:
      Claude Code CLI (agent runtime), Python 3.12, pytest.

## 2. Reproduction guide
- [x] `docs/REPRODUCTION.md` — clean-environment steps, exact commands,
      versions, runtime and cost expectations, repeat-run + real-repo CLI
- [x] Commands verified on final state (make validate/test/eval; full
      sweeps ran via the same entry points)

## 3. Solution video (≤5 min)
- [x] Script: `docs/VIDEO_SCRIPT.md`
- [ ] Record (user)

## 4. Agent trajectories
- [x] Every agent invocation streams to `trajectories/<system>/<case>/`
- [x] All trajectories rendered to .md; representative set indexed in the
      README (incl. the verifier that reproduces the reopen-crash)

## Packaging notes
- HackerEarth form: repository archive or link + video. Prefer a public
  GitHub repo (single `git push`) + unlisted video link.
- Trajectories are large; keep the full set in the repo (text, compresses
  well) — judges are told which ones are representative.
- No credentials or private data anywhere in the repo (agents run with
  --restricted; nothing reads user settings).
- Coding-agent disclosure (required by rules): built with Claude Code
  (Sonnet for all measured agents; orchestration authored interactively).
