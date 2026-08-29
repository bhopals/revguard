# RevGuard — the 5-minute cut (and a 4-minute variant)

A tight, self-contained script. Follow it top to bottom — the narration is
already condensed to fit the clock while keeping the pitch. The full 8–9 min
version with every step is in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## What's kept vs cut

| # | Step | Full | **5-min** | **4-min** |
|---|---|---|---|---|
| 00 | Opening + the problem | ✓ | **keep (0:35)** | keep (0:35) |
| 01 | `make validate` | ✓ | **keep (0:20)** | ✂ fold one line into 00 |
| 01b | `make map` — codebase tour | ✓ | **keep (0:25)** | ✂ cut |
| 02 | `make test` | ✓ | ✂ cut | ✂ cut |
| 03 | Live review — watch it work | ✓ | **keep (1:10)** | keep (1:05) |
| 04 | Open the report | ✓ | **keep (0:25)** | keep (0:22) |
| 05 | Verifier evidence — the wow | ✓ | **keep (0:30)** | keep (0:28) |
| 06 | Baseline run | ✓ | ✂ cut (name it in 08) | ✂ cut |
| 07 | `eval/compare` | ✓ | ✂ cut (it's in 08) | ✂ cut |
| 08 | Dashboard — the numbers | ✓ | **keep (0:55)** | keep (0:48) |
| 09 | Real PR / dogfood | ✓ | **keep (0:30)** | ✂ fold one line into 10 |
| 10 | Closing pitch | ✓ | **keep (0:55)** | keep (0:52) |

The four beats that must never be cut: **03** (proof it works), **05** (proof
it's trustworthy), **08** (proof it's better), **10** (why you should care).

### Timing reality — read this
The one expensive thing is step 03's live run: it takes ~80 seconds no matter
what. So:
- **For a ~5:00 cut:** record step 03 live, then in your editor **speed the
  waiting part up 2–3×** — keep real time only for the launch and the
  confirmation lines landing. Everything else is talk-time. That lands ~5:00–5:30.
- **For a hard 4:00 cut:** don't run 03 live at all. Show the pre-baked log and
  talk over a quick scroll (command below), and drop steps 01 and 09. That lands
  ~4:00.
  ```bash
  # a ready-made run log to scroll instead of waiting live:
  REVGUARD_QUIET= python3 - <<'PY'
  print(open('results/demo/case21_perf_reports_report.md').read())
  PY
  ```
  (Or just narrate the pipeline over the report itself — the point of 03 in the
  4-min cut is the *idea*, not the wait.)

Pure narration time: ~5:35 with the codebase tour (01b), ~5:10 without it, at a
brisk pace; step 03's run time overlaps your narration, so it doesn't simply add
on top. **For a hard 5:00 with the tour, drop step 01** (`make validate`) — the
tour already tells the viewer the benchmark exists, and step 08 re-earns the
"it's honest" point. The tour is the first thing to cut if you're long.

**Before recording:** terminal in `revguard/` (font ~18pt); three browser tabs
open — dashboard (`docs/dashboard.html`), report
(`results/demo/case21_perf_reports_report.html`), PR
(`https://github.com/bhopals/revguard/pull/1`).

Legend: **RUN** = type this · **SHOW** = point at this · **SAY** = say this.

---

## 00 · Opening — the problem (0:35)

**SAY:**
> "This is RevGuard. The problem it solves: on every team, senior engineers are
> the bottleneck for code review — because the bugs that hurt are exactly the
> ones your tests *don't* catch, and a human has to read carefully to find them.
> AI review bots were supposed to help, but they cry wolf: a wall of plausible,
> mostly-wrong comments, and people learn to ignore them. So I set a different
> bar — not 'find more issues,' but *only tell me things that are true, and
> prove each one.* RevGuard's rule: no finding reaches you unless a second agent
> has tried to prove it wrong, by running the code, and failed. Let me show you."

---

## 01 · `make validate` — the benchmark is honest (0:20)  *(4-min: skip; add the italic line to step 00)*

**RUN:**
```bash
make validate
```
**SAY (over the scrolling `ok` lines):**
> "First, the foundation. We built a benchmark — 22 pull requests with 61 bugs we
> planted by hand. This runs all 22 test suites, and here's the key: *every one
> passes.* The bugs are real but invisible to the tests — so we're measuring
> exactly what CI waves through. 'All cases valid' — the yardstick is honest."

---

## 01b · 25-second codebase tour (0:25)  *(optional; drop first if over time)*

**RUN:**
```bash
make map
```
**SAY (over the printed tree):**
> "Thirty seconds on what's actually here, because it's a real project, not a
> notebook. Two things drive everything. The *benchmark* — a real app under
> review, and twenty-two pull requests with sixty-one hand-labeled bugs. And the
> *pipeline* — that's `agent/`: the reviewers, the verifier, and each agent's
> instructions. Around them: a fair baseline to compare against, an `eval` folder
> that scores everything, a CLI to run it on real repos, and `results` and
> `trajectories` where every run and every agent transcript is saved as evidence.
> A Makefile ties it together — validate, baseline, agent, eval. All public, all
> reproducible. Okay — let's watch it review real code."

---

## 03 · Live review — watch the pipeline work (1:10)

**RUN:**
```bash
python3 agent/run.py --config v5 --case case21_perf_reports --run-name live --force
```
**SAY (narrate over the live output as each line appears):**
> "Here's a real review, live — you can watch it think. This pull request looks
> harmless: a performance refactor, tests passing, the kind you approve on
> autopilot.
>
> First line — three specialist reviewers launched in parallel: correctness,
> security, tests. And each one reads the *whole repo*, not just the diff,
> because the worst bugs hide in code the diff doesn't touch.
>
> Now they report back — and here's what makes RevGuard different. Stage two: the
> adversarial verifier. Every finding goes to a fresh agent, in its own sandbox,
> with a shell, told to *prove it wrong.* Watch the confirmations land — whatever
> it can't disprove survives, the noise gets thrown out right here.
>
> Done. Two findings, both survived. Under 90 seconds, under a dollar — against
> half an hour for a human. Let's read them."

---

## 04 · The report (0:25)

**SHOW:** open `results/demo/case21_perf_reports_report.html`.
**SAY:**
> "The finished review — two critical findings, each with the verifier's evidence
> under it. First, the refactor dropped a filter, so every budget now sums
> spending across *all time*. Second, my favorite — a new index is missing two
> words, 'if not exists,' so the app runs once and then *crashes every time the
> database reopens.* An outage on your second deploy — and the tests never see it,
> because they use a fresh in-memory database."

---

## 05 · The verifier's evidence — the wow (0:30)

**RUN:**
```bash
python3 tools/render_trajectory.py trajectories/demo/case21_perf_reports/verifier_01.jsonl | less
```
*(press `q` to exit when done)*
**SAY:**
> "And this is why you can trust it. This is the verifier's actual transcript for
> that crash. It didn't guess — it wrote a script, created a real database,
> opened it twice, and caught the actual error: *index already exists.* Then it
> grepped the tests to prove why CI misses it. Only then: verdict, confirmed.
> Every finding you saw survived something like this."

---

## 08 · The dashboard — the numbers (0:55)  *(spend your time here)*

**SHOW:** open `docs/dashboard.html`.
**SAY:**
> "The whole project scored — three things, and I'll be straight on all three.
>
> One: on *small* PRs, the plain baseline already scores perfectly. The model
> alone has solved easy review — our pipeline adds nothing there, and we say so
> instead of hiding it.
>
> Two: on the *large, real-world* PRs — the ones that eat senior-engineer time —
> RevGuard wins on every metric: more real bugs, fewer false alarms, F-1 of
> point-nine-three versus point-eight-eight.
>
> Three, the one that matters most: we ran both twice. RevGuard was identical
> both times — three false positives, then three. The baseline's *tripled*, six
> to eighteen. That instability *is* the cry-wolf problem, in a number. A noisy
> reviewer is one you stop trusting — RevGuard is boring and repeatable, and for
> a reviewer, boring is the whole point."

---

## 09 · Real code — it reviews its own PR (0:30)  *(4-min: skip; add the italic line to step 10)*

**SHOW:** browser tab at `https://github.com/bhopals/revguard/pull/1` — scroll the
two RevGuard comments.
**SAY:**
> "And it's not a toy — this same tool reviews any GitHub pull request and posts
> the review on it. Proof: I ran it on a real PR on this project. It caught the
> bug I planted — *and two real security holes I'd accidentally written into the
> tool myself*, one of which its verifier reproduced with a working exploit. I
> fixed them; the second comment is RevGuard confirming they're gone. It made its
> own next version safer."

---

## 10 · Closing pitch (0:55) — **land this**

**SAY:**
> "So — why this one. We built a reviewer you don't learn to ignore: it proves
> everything it tells you and discards what it can't. On the hard PRs it beats the
> honest baseline on every metric, and it's stable where the baseline is noise.
> Point it at a pull request, and before a human opens it they get a short list of
> confirmed, evidence-backed findings instead of a wall of maybes — in a minute,
> for under a dollar, against an hour of expert time.
>
> *(4-min only: add — 'And it works on real code — we ran it on its own pull
> request and it caught two real security bugs it had just introduced, then
> confirmed the fixes.')*
>
> It hits your criteria squarely: a real bottleneck for a clear user; a
> purposeful multi-agent design where every choice came from a measurement; a
> finished tool, not a draft; and one fixed rule so every number reproduces from a
> clean checkout. And a lesson that transfers to any agent: everyone adds a
> verifier, nobody checks what it gates — ours rubber-stamped 54 of 54 findings,
> because verification checks *truth*, and most bad review comments are *true.*
> 'There's no test for this' is correct and useless. A verifier needs a *policy*
> gate, not just a truth gate — that one fix was our biggest jump in quality.
>
> That's RevGuard: honest about where it helps, measured where it matters, and
> already catching real security bugs in the wild — including its own. It's all
> public at github dot com slash bhopals slash revguard. Thank you."

---

### Recording tips
- Rehearse step 03 once so you know when the reviewer/verifier lines land, and
  time your words to them — that's what makes it feel live, not read.
- If a live command runs long, you have `Space`-free filler: keep talking about
  the architecture; the script's 03/06 narration is written to cover the wait.
- If you fluff a line, pause and repeat the sentence — you'll cut it later. Don't
  restart the whole take.
