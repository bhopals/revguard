# RevGuard — full demo script (word-for-word)

Your 11 steps, each with **what to run**, **what's happening behind the scenes**,
and **what to say** — written to sound like a person talking, not a slide deck.
Speak in your own rhythm; these are the words, not a cage.

**Before you record**
- Terminal in `revguard/`, font ~18–20pt, window ~100 columns.
- A browser with three tabs ready: the dashboard
  (`…/revguard/docs/dashboard.html`), the report
  (`…/revguard/results/demo/case21_perf_reports_report.html`), and the PR
  (`https://github.com/bhopals/revguard/pull/1`).
- The slow commands now print **live progress**, so you can run them on camera
  and narrate over the scrolling output. Nothing is faked and nothing stalls
  silently.

Legend: **RUN** = type this · **SAY** = your narration · **SHOW** = point at this.

---

## 00 · Opening (about 45 seconds)

**SAY:**
> "Hi — I want to show you RevGuard. Here's the problem it solves. On every team
> I've worked on, the senior engineers are the bottleneck for code review. Your
> tests catch what they cover — but the bugs that actually hurt are the ones the
> tests *don't* cover, and a human has to catch those by reading carefully. It's
> slow, and it doesn't scale.
>
> People reach for AI review bots, and they all hit the same wall: the bot posts
> a wall of plausible-sounding comments, most of them wrong, and within a week
> everyone learns to ignore it. So the bar I set wasn't 'find more issues.' It
> was: *only tell me things that are true, and prove each one.*
>
> That one idea drives the whole design. RevGuard has a rule: no finding ever
> reaches you unless a second, independent agent has tried to prove it wrong —
> by actually running the code — and failed. Let me show you the whole thing
> working, end to end, on a real bug."

*(Pitch hook — say it with a little weight: "A reviewer you don't learn to
ignore.")*

---

## 01 · `make validate` — prove the benchmark is honest (~25 seconds)

**RUN:**
```bash
make validate
```

**SAY (while the green `ok` lines scroll):**
> "First, the foundation. You can't claim a reviewer is good without something
> to measure it against — so we built a benchmark: a small but real
> application, and twenty-two pull requests against it that carry sixty-one bugs
> we planted and labeled by hand. SQL injection, money math that loses a cent,
> tests literally written to sneak a bug past CI.
>
> What's scrolling by right now is every one of those twenty-two pull requests
> having its full test suite run. And here's the trick that makes the whole
> project fair — watch — every suite *passes*. The bugs are real, but they're
> invisible to the tests. So the benchmark measures exactly the thing that
> matters: what your CI would wave straight through. That last line —
> **'All cases valid'** — means every planted bug is accounted for and hidden.
> No API calls here, this is just proof the yardstick is honest."

**SHOW (optional):** open the dashboard tab for two seconds — "and all of that
rolls up into this scoreboard, which I'll come back to at the end."

---

## 01b · `make map` — a quick tour of the codebase (~25 seconds)

**RUN:**
```bash
make map
```

**SAY (over the printed tree):**
> "Before I run it, half a minute on what's actually in here — because this is a
> real, navigable project, not a one-off script. Everything hangs off two things.
> The first is the *benchmark*: a real application under review, and the
> twenty-two pull requests with the sixty-one bugs we just validated. The second
> is the *pipeline* — that's the `agent` folder: the parallel reviewers, the
> adversarial verifier, and each agent's actual instructions in `prompts`.
> Everything else supports those two: a fair `baseline` to measure against, an
> `eval` folder that does the scoring, a command-line tool to run it on real
> repositories, and `results` and `trajectories`, where every run and every
> agent's full transcript is written down as evidence. The Makefile ties it into
> single commands — validate, baseline, agent, eval, test. It's all public and it
> all reproduces from a clean checkout. Now let's watch it work."

---

## 02 · `make test` — the harness tests itself (~2 seconds)

**RUN:**
```bash
make test
```

**SAY:**
> "Quick one. It's fair to ask: how do I know the *scoring* itself isn't fudged?
> So the scoring engine has its own unit tests — seventeen of them — covering how
> a finding is matched to a known bug, how duplicates are handled, how a wrong
> line becomes a miss. Green across the board. The grader is graded. Now let's
> actually review some code."

---

## 03 · Run a real review — watch the pipeline work (~80 seconds)

**RUN:**
```bash
python3 agent/run.py --config v5 --case case21_perf_reports --run-name live --force
```

**SAY (narrate over the live output as it appears):**
> "This is a real review, happening right now — and you can watch it think.
>
> The pull request I picked looks completely innocent: it's a *performance
> refactor*, the kind a reviewer approves on autopilot, and its tests pass. See
> the first line — three specialist reviewers just launched *in parallel*: one
> for correctness, one for security, one for test quality. And this is
> important — each of them gets tools to read the *whole repository*, not just
> the diff. A lot of bugs only exist because of code the diff doesn't touch, and
> a reviewer staring at the diff alone will never see them.
>
> There — the reviewers are coming back with what they found. Now the step that
> makes RevGuard different kicks in: **stage two, the adversarial verifier.**
> Every finding gets handed to a fresh agent, in its own clean sandbox copy of
> the repo, with a shell — and one instruction: *prove this wrong.* Watch the
> confirmations land one by one. Anything it can't disprove survives; anything
> that turns out to be noise gets thrown out right here, before it ever reaches
> a human.
>
> And that's the run — two findings, both survived verification. Under a minute
> and a half, well under a dollar. A careful human on this PR is thirty to sixty
> minutes. Let's read what it found."

*(Note: you're running into `--run-name live` so this on-camera run can't
disturb the polished report you'll open next.)*

---

## 04 · Open the report (~40 seconds)

**SHOW:** open `results/demo/case21_perf_reports_report.html` in the browser.

**SAY:**
> "This is the finished review — the thing a teammate would actually read. Notice
> the verdict up top: *request changes*, two critical findings. And each finding
> isn't just an opinion — read the italic line under it, that's the verifier's
> evidence.
>
> First bug: the refactor rewrote a database query, and in doing so it quietly
> dropped the filter that limits a budget to one month. So now every budget adds
> up spending across *all time*. A user who's been on the app a year is suddenly
> reported as wildly over budget. The tests never caught it because the test data
> never spans two months.
>
> Second bug — and this one's my favorite — the PR added a new database index,
> but left off two words: 'if not exists.' Which means the app runs fine the
> first time, and then **crashes every time the database is opened again.** In
> production that's an outage on the second deploy. The tests never see it
> because they use a fresh in-memory database that never gets reopened. This is
> exactly the class of bug that sails through CI and pages you at 2am."

---

## 05 · The verifier's evidence — the money shot (~35 seconds)

**RUN:**
```bash
python3 tools/render_trajectory.py trajectories/demo/case21_perf_reports/verifier_01.jsonl | less
```
*(press `q` to exit `less` when done)*

**SAY:**
> "I want to prove to you that RevGuard isn't just pattern-matching and guessing.
> This is the actual, unedited transcript of the verifier working on that
> reopen-crash bug.
>
> Look what it did. It didn't *argue* the crash was likely. It wrote a tiny
> script, created a real database file, opened it, closed it, and opened it a
> second time — and it captured the actual error the database threw:
> *index already exists.* Then it went and grepped the test suite to confirm
> why CI never catches this — because the tests only ever use in-memory
> databases. And only then does it stamp the verdict: **confirmed.**
>
> That's the whole philosophy in one screen. Every finding you saw survived
> something like this. That's why you can trust the report instead of skimming
> it and moving on."

---

## 06 · The fair baseline — same PR, one prompt (~45 seconds)

**RUN:**
```bash
python3 baseline/run.py --case case21_perf_reports --out results/demo-baseline --force
```

**SAY (over the live line):**
> "Now, the honest question a good engineer asks: is all this machinery actually
> better than just pasting the diff into the model and asking? So here's the
> fair comparison — the *baseline*. Same pull request, same model, but one prompt
> and no tools and no verifier. This is what most people actually do today.
>
> It's faster and it's cheaper, no argument. But it's reading the diff as *text*.
> It can't open the database to catch the reopen crash, and it can't go read the
> untouched module the broken query depends on. So on the hard PRs it misses the
> bugs that need investigation — and worse, when it's unsure, it hedges: you get
> vague 'you might want to add a test here' comments instead of a confirmed bug.
> That gap — investigation and proof versus a text skim — is the entire reason
> RevGuard exists."

---

## 07 · `eval/compare.py` — score them side by side (~30 seconds)

**RUN:**
```bash
python3 eval/compare.py results/demo-baseline results/demo
```

**SAY:**
> "And I don't want you to take my word for any of this — every number is
> computed, not claimed. This scores both runs against the known bugs with one
> fixed rule: did you name the right file and the right line. Same rule for both,
> decided before either ran. You're looking at the two systems on the same case —
> what each found, what it missed, how long it took, what it cost. Every cell
> traces back to a file on disk. Which brings me to the full picture."

---

## 08 · The dashboard — the whole story (~60 seconds) — **spend time here**

**SHOW:** open `docs/dashboard.html`.

**SAY:**
> "This is the scoreboard for the entire project, and it's where the real story
> is. Three things I want you to see.
>
> **One — and I'll be completely straight with you** — look at the small pull
> requests. The plain baseline gets a perfect score on those. On small diffs, the
> model alone has already solved code review, and our pipeline adds nothing. We
> put that front and center instead of hiding it, because it tells you *where* to
> spend engineering effort — and it isn't on the easy cases.
>
> **Two — now look at the large, multi-file pull requests**, the realistic ones
> with cross-module bugs. That's where RevGuard pulls ahead on *every* measure:
> it finds more of the real bugs, it raises fewer false alarms, and its F-1 score
> is point-nine-three against the baseline's point-eight-eight. This is the regime
> that actually eats your senior engineers' time, and it's exactly where the tool
> earns its keep.
>
> **Three — the one I'd tattoo on the wall.** We ran both systems twice, start to
> finish. RevGuard gave the *identical* result both times — three false positives,
> then three again. The baseline's false positives *tripled* between runs, six to
> eighteen. That instability *is* the 'boy who cried wolf' problem, measured in a
> number. A reviewer that's noisy and different every time is one you stop
> trusting. RevGuard is boring and repeatable — and for a reviewer, boring is
> exactly what you want."

---

## 09 · Real code — it reviews a live GitHub PR, including its own (~45 seconds)

**RUN (optional live — or just show the result, it's already posted):**
```bash
python3 revguard.py --pr bhopals/revguard#1
```

**SHOW:** switch to the browser tab at
`https://github.com/bhopals/revguard/pull/1` and scroll the two RevGuard
comments.

**SAY:**
> "Last thing — and this is where it stops being a benchmark and starts being a
> tool you'd actually wire into your team. This same command reviews *any* GitHub
> pull request and can post the review right on it.
>
> Here's the proof it's real. I opened an actual pull request on this project,
> and I ran RevGuard on it. It found the bug I'd planted for the demo — but it
> also found *two real security holes I had accidentally written into the tool
> itself*: a command-injection through a git branch name, which its verifier
> reproduced with a working exploit, and a prompt-injection through the PR text.
> I fixed both — and the second comment here is RevGuard re-reviewing and
> confirming they're gone. The tool made its own next version safer. That's the
> workflow, running for real, on real code, catching real bugs."

---

## 10 · Closing pitch (about 75 seconds) — **the most important 75 seconds**

**SAY:**
> "So let me pull it together, and be direct about why this one deserves a serious
> look.
>
> **What we built** is a code reviewer you don't learn to ignore — because it
> proves every single thing it tells you by running the code, and it throws away
> everything it can't prove. That's not a demo trick; it's measured. On the hard,
> real-world pull requests it beats the honest baseline on every metric, and it's
> stable run to run where the baseline is noise.
>
> **How you'd use it:** point it at a pull request, and before a human ever opens
> that PR, they get a short list of confirmed, evidence-backed findings instead of
> a wall of maybes. Your senior engineers stop spending their afternoons hunting
> for the needle, and start their review already knowing where the real problems
> are. It runs in about a minute, for well under a dollar, against thirty to sixty
> minutes of expert time. That math is the whole pitch.
>
> **And on the criteria you set** — I built this to hit them squarely. *Problem
> and user value:* a real bottleneck for a clearly-defined user, senior reviewers,
> quantified. *Agent engineering:* purposeful multi-agent design — parallel
> specialists, an adversarial verifier, isolation, a policy gate — every choice
> made because a measurement told me to, and I kept the receipts in the changelog.
> *End-to-end quality:* a finished tool that reviews real GitHub PRs and reports
> like a senior engineer would. *Measured improvement:* a fair baseline, one fixed
> rule, every number reproducible from a clean checkout. *Reproducibility:* it's
> all public — `make validate`, `make baseline`, `make agent`, `make eval`, and
> you get these results. And the *hot take:* everyone bolts a verifier onto their
> agent; almost nobody checks what it actually gates. Ours rubber-stamped
> fifty-four out of fifty-four findings until we realized verification checks
> *truth*, but most bad review comments are *true* — 'there's no test for this' is
> correct and still useless. A verifier needs a *policy* gate, not just a truth
> gate. That single insight was our biggest jump in quality, and it's the kind of
> lesson that transfers to any agent you build.
>
> That's RevGuard. It's honest about where it helps, it's measured everywhere it
> matters, and it already found real security bugs in the wild — including its own.
> Thank you — everything's public at github dot com slash bhopals slash revguard."

---

## Fallback timings
Full run ≈ 8–9 minutes with narration. To fit a 5-minute cap, keep 00, 03, 04,
05, 08, 10 and cut 02, 06, 07, 09 (mention them in one breath in step 08). The
irreplaceable beats are **03 (watch it work)**, **05 (the evidence)**,
**08 (the numbers)**, and **10 (the pitch)**.
