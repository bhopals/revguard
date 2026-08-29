# HackerEarth submission form — paste-ready content

The form has four required fields: **Title**, **Description**, **Video URL**,
**Source Code**. Below is exactly what to put in each.

---

## Field 1 — Title

```
RevGuard: an evidence-linked code-review agent you don't learn to ignore
```

(Alternative, shorter: `RevGuard — code review that proves every finding`)

---

## Field 2 — Description

The editor supports formatting and links. Paste the text below; apply bold to
the **bold** lines and make the GitHub URL a link. (If it only takes plain
text, paste as-is — it still reads well.)

---

**The user & bottleneck.** Senior reviewers are the bottleneck on every team.
CI catches what tests cover; humans catch what tests *miss*. Existing AI review
bots fail the same way — they spray plausible-but-wrong comments until people
learn the bot cries wolf and ignore it. The problem worth solving isn't "find
more issues," it's **"only tell me things that are true, with evidence."**

**What RevGuard is.** A multi-agent code-review pipeline whose defining rule is
that no finding reaches a human unless a second, *adversarial* agent has tried
to disprove it — by actually running the code in a sandbox — and failed. Three
specialist reviewers (correctness, security, tests) review each PR in parallel
with real repo tools; every finding then faces a verifier with a shell whose
only job is to falsify it. Only survivors are reported.

**How we proved it.** You can't measure a reviewer without ground truth, so we
built one: a working expense-tracker app and **22 pull requests carrying 61
planted, labeled bugs** (2 PRs are clean, to catch bots that invent problems).
Every case's test suite passes — the benchmark measures exactly what CI misses.
A fair baseline (one prompt, same model) is scored on the same cases with one
fixed rule.

**Results (all traceable to files in the repo):**
- **The base model has already solved small-PR review** — the one-prompt
  baseline found 39/39 bugs on small PRs. We report that instead of hiding it.
- **On large, realistic multi-file PRs the pipeline wins on every metric** —
  F1 **0.930** vs the baseline's **0.884**, better recall, better precision,
  fewer false positives.
- **The pipeline is stable; the baseline is not** — run twice end-to-end,
  RevGuard was identical (3 false positives both times); the baseline's false
  positives tripled (6 → 18). That run-to-run noise *is* the "cry wolf" failure
  mode, quantified.

**It works on real code, not just our benchmark.** `revguard.py --pr` reviews
any GitHub PR. We opened a real PR on our own repo; RevGuard found a planted
bug **and two real security vulnerabilities we'd just written into the feature
itself** (argument injection via a git ref, which its verifier reproduced by
building a malicious ref; and prompt injection via PR text). Both are now fixed.
It also flags real escaped bugs in open-source history — one that lived ~18
months in a released library.

**Hot take / main lesson.** Everyone bolts a verifier onto their agent
pipeline; almost nobody measures what it gates. Ours confirmed 54/54 findings
at one point — pure cost — because *verification checks truth, but most bad
review comments are true* ("there are no tests for X" is correct and still
noise). A verifier needs a *policy* gate as much as a truth gate, and the
reviewers feeding it should be tuned permissive *because* it exists. And: don't
build agent machinery for regimes the base model already solved — benchmark
until you find where it breaks, then build exactly there.

**Reproduce it.** Public repo (code, benchmark, all results, agent
trajectories, changelog, reproduction guide):
**https://github.com/bhopals/revguard**
From a clean checkout: `make validate` (proves the benchmark, no API calls),
then `make baseline && make agent && make eval`. Full walkthrough in
`docs/WALKTHROUGH.md`; live-demo commands in `docs/DEMO.md`; the honest
iteration story with every measured version in `docs/CHANGELOG.md`.

Built entirely during the event with the Claude Code CLI as the agent runtime
(same model for baseline and agent). Coding-agent use disclosed; full agent
trajectories included in the repo.

---

## Field 3 — Video URL

Paste your recorded demo link here (YouTube/Loom/Drive, up to 5 min). Script is
in `docs/VIDEO_SCRIPT.md`. **This is the only piece still to record.**

---

## Field 4 — Source Code (upload)

Upload `HACHATHON/revguard-submission.zip` (~13 MB, well under the 50 MB cap).
It contains the full project minus the `.git` folder — code, the 22-case
benchmark, all measured results, and every agent trajectory.

> Tip: the public GitHub repo is the richer artifact (browsable history proves
> in-event provenance and shows the tool reviewing its own PR). The zip
> satisfies the required upload; the repo link in the description gives judges
> the clean-checkout reproduction path.

---

## Final pre-submit checklist
- [ ] Title pasted
- [ ] Description pasted (GitHub URL is a clickable link)
- [ ] Video recorded and URL pasted
- [ ] `revguard-submission.zip` uploaded
- [ ] Repo is public (it is: https://github.com/bhopals/revguard)
- [ ] Submit before **Mon Aug 31, 18:00 UTC**
