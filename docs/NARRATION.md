# RevGuard — word-for-word narration track (target 4:30)

Read this over the self-playing screencast (`docs/screencast.html`, also
published as an Artifact — open it fullscreen and it auto-plays through all ten
scenes in 4:30). Each scene below matches one scene of the screencast; the
timings are cumulative. `[SCREEN]` notes what's visible so you can pace your
voice. Speak at ~140 words/min; the whole script is ~630 words.

## How to record the video
1. Open `docs/screencast.html` (or the Artifact link) in a browser, press **F**
   for fullscreen. **Slides do NOT auto-advance** — you drive the pace.
2. Screen-record it (macOS: **Cmd-Shift-5**; or QuickTime → New Screen
   Recording). Press **Home** to be sure you're on scene 1, then start recording.
3. Controls: **→ / Space / click** = next slide, **←** = back, **Home** =
   first, **End** = last, **F** = fullscreen. Advance each slide when you finish
   its narration line below — no timer to race.
4. Read the script below as you go — either live while recording, or over the
   silent capture in any editor. The on-screen captions carry the gist, so the
   video works even before voiceover.
5. Upload (YouTube/Loom/Drive) and paste the link into the submission form.

The timings below are just a *pacing guide* now — advance manually when each
line is done. Total is still ~4:30 at a natural pace.

---

### Scene 1 — Title (0:00–0:12)
`[SCREEN: title card — "RevGuard: code review that proves every finding"]`

> "This is RevGuard — a code-review agent with one rule: no finding reaches a
> human unless a second agent has tried to disprove it, by actually running the
> code, and failed."

### Scene 2 — The problem (0:12–0:40)
`[SCREEN: the "cry wolf" problem statement]`

> "Senior reviewers are the bottleneck on every team. CI catches what tests
> cover; humans catch what tests miss. AI review bots exist, but they cry
> wolf — they spray plausible comments that are mostly wrong, so people learn
> to ignore them. The problem worth solving isn't finding more issues. It's:
> only tell me things that are true, with evidence."

### Scene 3 — The benchmark (0:40–1:05)
`[SCREEN: benchmark card — 22 PRs, 61 bugs, 2 clean, tests pass]`

> "To measure that, we built a benchmark: a working app, and twenty-two pull
> requests carrying sixty-one planted, labeled bugs — SQL injection, money
> corruption, tests written to dodge the very bug they're named after. Two PRs
> are completely clean, to catch bots that invent problems. And every single
> case's test suite passes — so the benchmark measures exactly what CI misses."

### Scene 4 — Validate (1:05–1:20)
`[SCREEN: terminal running `make validate` → "All cases valid."]`

> "One command proves it. `make validate` runs all twenty-two test suites —
> they're green — and confirms every bug is really hidden. No API calls, just
> proof the benchmark is honest."

### Scene 5 — The pipeline (1:20–1:55)
`[SCREEN: animated pipeline diagram — 3 reviewers → merge → verifier → report]`

> "Here's the pipeline. Three specialist reviewers — correctness, security,
> tests — read the PR in parallel, each with tools to grep the whole
> repository, not just the diff, because some bugs only exist relative to code
> the diff doesn't touch. Their findings are merged. Then the key step: every
> finding goes to an adversarial verifier — a fresh sandbox, a shell, and one
> instruction: prove this wrong. Only findings it can't disprove survive."

### Scene 6 — Live review (1:55–2:35)
`[SCREEN: terminal — `agent/run.py --config v5 --case case21` → 2 findings]`

> "Let's run it on a hard one. This PR is a performance refactor — it looks
> clean and its tests pass. RevGuard finds two critical bugs. First: the
> refactor's new database JOIN silently lost its month filter, so every budget
> now sums spending across all time. Second: a new index definition crashes the
> app the second time the database is opened. Tests never catch it because they
> use in-memory databases that never reopen."

### Scene 7 — The verifier's evidence (2:35–3:05)
`[SCREEN: verifier trajectory — opens DB twice → OperationalError]`

> "And here's what makes it trustworthy. The verifier didn't guess that second
> bug was likely. It created a real database file, opened it twice, and
> captured the actual crash — then grepped the tests to explain why CI stayed
> green. That's the difference between an opinion and evidence."

### Scene 8 — Results (3:05–3:45)
`[SCREEN: results table — tier-3 v5 0.930 vs baseline 0.884; stability row]`

> "Now the numbers, same cases, same model, one scoring rule. Finding one: on
> small PRs the base model is already perfect — thirty-nine out of thirty-nine.
> We report that instead of hiding it. Finding two: on large, realistic PRs the
> pipeline wins on every metric — F-one of point-nine-three versus point-eight-
> eight. Finding three, the one I love: we ran both twice. RevGuard was
> identical — three false positives both times. The baseline's false positives
> tripled. That instability *is* the cry-wolf failure mode, measured."

### Scene 9 — The changelog honesty (3:45–4:05)
`[SCREEN: tier-3 F1 progression bars — v1 worse than baseline → v5 best]`

> "And it wasn't a straight line. Version one — tools plus a cautious prompt —
> was worse than the baseline. Our verifier once confirmed fifty-four out of
> fifty-four findings — a rubber stamp — because verification checks truth, but
> most bad review comments are true. Fixing that, giving the verifier a policy
> gate, was the biggest single gain."

### Scene 10 — Dogfood + close (4:05–4:30)
`[SCREEN: PR #1 — found seeded bug + 2 real security bugs → close card]`

> "Finally — it works on real code. We ran it on its own pull request, and it
> found a bug we planted plus two real security holes we'd accidentally written
> into the tool itself, one of which its verifier reproduced with a live
> exploit. We fixed them. The tool made its own next version safer. That's
> RevGuard: not a reviewer that finds more — a reviewer you don't learn to
> ignore. Everything's reproducible at github dot com slash bhopals slash
> revguard."

---

## Pacing notes
- Total ≈ 630 words ≈ 4:30 at a natural pace. If you run long, Scene 9 is the
  safe cut (drop to one sentence).
- The screencast is **manual** — finish a scene's line, then press **→** (or
  Space, or click) to advance. Take all the time you need on any scene; nothing
  moves until you say so. **←** steps back if you need a retake.
