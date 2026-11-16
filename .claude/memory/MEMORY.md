# Benchlab: where the work stands

Start here in a new session. Updated 2026-11-16: **branch R1 is built and checked, and not yet
committed**, in BenchLab and in DeePC; `docs/plan-branch-R1.md`, "As built", holds the whole
state. The direction changed on 2026-11-15 (`docs/design.md` §10): Benchlab, to be renamed RunLab,
is to be used like numpy. 2d and 2e are on hold; 2c is the last branch merged (`v0.4.0`). VS Code
on the developer's computer, WSL2, 12 CPUs.

## R1, built 2026-11-16, awaiting the git steps

- **The developer chose R1 first** and approved its plan (`docs/plan-branch-R1.md`). Built: the
  names a project may use (`from benchlab import ...`), the promise they stay until 1.0
  (`README.md`, `tests/test_shore.py`), the one check a project calls
  (`benchlab.testing.check_project`), DeePC's five test files that read Benchlab's insides gone
  (79 of their 85 tests now here, on the made-up project, which has a second piece, `lag`), DeePC
  on the range `benchlab>=0.5,<1`. Version `0.5.0`.
- **Checked:** Benchlab 306 passed in 72 s (198 in 35 s before), ruff clean. DeePC 131 tests in
  114 s (246 in about 200 s before); one failed, `CLAUDE.md` a line over its budget, fixed and
  its file re-run, the whole suite not run again after that. DeePC's runs and stills as before
  but provenance and wall-clock fields. DeePC's Lab driven once in headless Chromium.
- **Nothing is committed.** Both repositories are on `main` and `master`; the session's permission
  tool refused `git switch -c r1-shore`. **DeePC's `pyproject.toml` and `uv.lock` point at the
  local Benchlab copy: never committed that way.** The git steps, in order, are at the end of the
  plan's "As built"; each needs the developer's word in that turn.
- **uv does not hold a git source to a version range** (measured, uv 0.10.10): the range is the
  written promise, `uv.lock` does the pinning.
- **For the developer's review:** `docs/for-review.md`, "R1", eight choices.
- **The session was cut once**: the developer's laptop went down while DeePC's pieces ran on
  several cores (cause theirs; they later said "the problem is fixed"). The scratch folder is
  cleared by a restart: a baseline worth keeping does not belong there.
- **Usage:** the developer asked for it lean on 2026-11-16: no parallel reviewers, no agent
  fan-out, "a few bugs here and there are fine, we will iron them out later".
- **Next after the git steps:** R2, the words: the first branch that should need no DeePC change.

## Where it stands

- **Design approved** and pushed: `docs/design.md`. It holds every decision, each marked by who
  made it: the developer (what the page shows, decided after driving it) or Claude (how it is
  built, with the reason). §8 now says branch 1 is the move and the page and runner are branch 2;
  §4 records the entry-point declaration.
- **Mockup** the developer drove (two rounds, real DeePC and Hydrofoil runs):
  https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb (private to the developer).
- **Branch 1 merged** (2026-11-14), as `docs/plan-branch-1.md` says: BenchLab #1 (merge `9976b82`,
  tagged `v0.1.0`) and DeePC-Sandbox #17 (merge `8578bc1`), which installs Benchlab pinned at
  `v0.1.0`. Here: `benchlab/{record,figure,cli,lab}` moved from DeePC `c7f0d7d`,
  `benchlab/project.py`, the tests on a made-up project (`tests/toy/`), the packaging and the
  rules. In DeePC (`~/code/personal/deepc`): the four layers deleted, the declaration in
  `devkit/harness/__init__.py` and `pyproject.toml`. To work on both together on one computer,
  DeePC points at this working copy through a path source, never committed (`README.md`).
- **Checked:** every DeePC piece run and drawn on `master` twice and on the branch: records and
  stills identical but for provenance (`benchlab` version added, `git_dirty`) and the wall-clock
  fields the two `master` runs already differ in (solve and step times, the solve-time still).
  Benchlab's suite 116 passed, ruff clean under RCWS's rule set (`pyproject.toml`). DeePC's
  suite 268 passed in 197 s, browser test included (`master`: 278; 33 tests moved here, 23 added
  there that read the installed Benchlab for DeePC's piece names); `uv run lab --no-open` serves
  the page. DeePC's ruff: no new finding (13 on `master`, 7 on the branch, all its own).
  Reviewed by four parallel reviewers, each finding put to a second agent (the developer chose
  this): 30 findings, 12 fixed, the rest refuted or stated in the PRs.
- **Licence: MIT**, as DeePC (the developer's choice, 2026-11-14: Benchlab is public and holds code
  DeePC publishes under MIT; the plan named none).
- **Git, 2026-11-14,** each step on the developer's word: both PRs opened (DeePC pinned to
  Benchlab's branch, its suite rerun on it), then #1 merged and tagged `v0.1.0`, DeePC re-pinned to
  the tag with its whole suite again (268 passed, records as before), #17 merged, both branches
  deleted, both local copies back on `main` and `master`.
- **Branch 2 is five branches** (the developer, 2026-11-14), each driven in DeePC's Lab before the
  next: 2a runs in progress, 2b no hovers, 2c words as slots, 2d the tree, 2e the cards' full
  controls (`docs/design.md` §8; the old 2b split in two the same day).
- **Branch 2a merged** (2026-11-14, `docs/plan-branch-2a.md` with its "As built" part): BenchLab
  #2 (merge `4bcd510`, tagged `v0.2.0`) and DeePC-Sandbox #18 (merge `6049a60`), which pins
  `v0.2.0`. Each run its own process (`python -m benchlab.runner`), up to the cores side by side,
  the rest queued, the strip along the bottom in place of the terminal; the side door and the Lab
  share `benchlab.runner`. Checked: Benchlab 165 passed; DeePC's whole suite 244 passed on the
  local copy, on Benchlab's pushed branch and on the tag (268 before: 26 tests of the old terminal
  left, 2 checks added); its records through the side door as before the move but provenance and
  wall-clock fields, each time; a closed loop from the Lab's queue and from the side door differ
  only in name, solve times and provenance. Reviewed by four parallel reviewers (the developer's
  choice): 37 findings, 35 confirmed, all fixed or written in the plan's "As built"; DeePC's whole
  suite then found two more, fixed. Handed off in DeePC's Lab as a walkthrough Claude drove first;
  the developer approved it ("Looks good, proceed"). Git, each step on their word: both PRs, then
  #2 merged and tagged, DeePC re-pinned to the tag with its checks again, #18 merged, both
  branches deleted, both copies back on `main` and `master`.

## Next

1. **2b no hovers merged** (2026-11-14, `docs/plan-branch-2b.md` with its "As built"):
   BenchLab #3 (merge `b629c25`, tagged `v0.3.0`) and DeePC-Sandbox #19 (merge `eafdf77`),
   pinned at `v0.3.0`. No hover on a setting, a chart, a number or a plain button; a greyed
   setting's reason under it; a value outside its range, or unreadable, refused at Run under
   its setting (`jobs.refusals`, held to param's verdict); DeePC's System and Open loop
   without help lines, `x0` now `x_0`. Driven by the developer; reviewed by four parallel
   reviewers (34 findings, 31 confirmed, all fixed or written in "As built"). Checked:
   Benchlab 185 passed; DeePC 244 on the tag, its side door as before but those pieces'
   descriptions. A slip closing it, recovered: `docs/project/failures.md` [L1].
2. **2c words as slots merged** (2026-11-14): BenchLab #4 (merge `5f6431a`, tagged `v0.4.0`)
   and DeePC-Sandbox #20 (merge `e3b1f06`), pinned at `v0.4.0`, its suite 246 passed. 136 slots
   (`benchlab/lab/words.py`), `WORDS` declared; both pages' words identical to v0.3.0's in
   every toured state. No review (the developer's usage).
3. **On hold since 2026-11-15: 2d the tree and 2e the cards' full controls.** The developer set
   a new direction (`docs/design.md` §10; the incident, `docs/project/failures.md` [L2]): a change
   in a project never needs a change in RunLab, and the other way round, as with numpy. They
   accept a large rewrite ("thats okay") and asked for it to be planned later, not now (their
   usage). Nothing is built for it; Benchlab stays at `v0.4.0` and DeePC on it.
4. **The route is written, not decided** (2026-11-15, `docs/design.md` §10, "The route"): R1
   the shore named and promised, R2 words, R3 a piece's own plotly figures, R4 files a run
   writes, R5 new setting kinds, R6 the rename to RunLab as 1.0 (the rename's place is the
   developer's; the rest is Claude's proposal). §10 also holds "The image": Gibson's static
   islands, dynamic sea, read from his write-up.
5. **R1 first, the developer's choice (2026-11-16)**: see "R1 in progress" above. Waiting for a
   later branch, as before:
   progress percentages, when a piece reports one; DeePC still pins panel itself and lists
   matplotlib, which only Benchlab uses now.

## How the developer works

- **Claude is the engineer who plans and builds** (the developer, 2026-11-15): explanations of
  what was done and why are a side. No quizzes or teaching unless asked.
- **Every question goes through AskUserQuestion**, with the context inside the question, never as
  text at the end of a message (2026-11-13: "WHEN I ASK QUESTION TO WHICH I EXPECT ANSWERS,
  ALWAYS USE THE ASKTHEUSER TOOL"). On 2026-11-14 they had it added to `~/.claude/CLAUDE.md` on
  this computer.
- **Not a software engineer**: "take every last one of my answer with a grain of salt". What the
  page shows is theirs, settled only after driving it. How it is built is Claude's, said with
  its reason. Push back when an answer costs more than it looks, and write the cost beside the
  decision (`docs/design.md` §3, decision 5, is the example).
- **Plain words, no software language** (2026-11-15: "plain it bro, i dont understand software
  language, i am not a software engineer"): say it with what they know, such as instruments,
  plants and controllers, never in software terms.
- The siblings' rules hold here too: propose, then plan mode, then build. Ask before any
  multi-agent fan-out, every time. Hand off in the Lab, or say plainly there is nothing to drive.
  No git write without their word.
- **But 2b to 2e, straight through** (the developer, 2026-11-14: "I would rather have you
  complete all the steps, drive it through all repos, then I will drive through all repos and
  then i will tell if there is smth i dont like ... make one long list once at the end"). Their
  standing word, for these four branches only, in BenchLab and DeePC only: every git step
  (commit, push, PR, merge, tag, DeePC re-pinned, branches deleted) without asking, and parallel
  reviewers on each branch before it merges. Each branch planned in `docs/plan-branch-2X.md`,
  built, tested, reviewed, driven by Claude; every choice the design and mockup leave open made
  and written with its reason in `docs/for-review.md`. Stop only for a change to the run file,
  anything outside these two repositories, or a failure not fixable inside the branch. At the
  end: one walkthrough of everything, and that list.
  From 2c on, no parallel reviewers (the developer, 2026-11-14, at 93% of their weekly
  usage: "skip the reviwers ... Mistakes and bugs are fine for now. We will fix everything
  at the delivery"): tests, Claude's own drive, then the git steps; lean on tokens.
  **Ended 2026-11-15**, with 2d and 2e on hold: every git write again needs the developer's word
  in that turn, and the rewrite gets its own.
- **A hand-off is a walkthrough**: what to click, what to type, what the page should then show,
  each step driven by Claude first, never squeezed into a question's dialog (2026-11-14: a list
  of steps without them was "not clear as to what to run/drive and what to observe").

## Measured

- 2026-11-13 (cloud machine, 4 CPUs, defaults): lines in the four shared layers per project:
  DeePC 4,486, Hydrofoil 1,798, BESS 5,312, RCWS 10,294. DeePC `closed_loop` 77 s wall per
  default run; its λ_g sweep (1, 10, 100) 160 s for 3 runs one after another. Hydrofoil takeoff
  0.7 to 1.2 s per run. `uv run hydrofoil settings flight` 0.56 to 0.59 s warm, 2.2 s cold.
  Labels that are code names: 64 of Hydrofoil's 70 settings, 8 of DeePC `open_loop`'s 13. Each
  is renamed when its project moves (`docs/design.md` decision 5).
- 2026-11-14, branch 2a: a λ_g sweep (1, 10, 100) of closed loops at `sim_duration=10`, two
  rounds: one after another (master's `deepc run --sweep`, as the Lab ran it before 2a) 43.7 s
  and 43.8 s; side by side (the queue) 32.1 s and 31.7 s, the λ_g = 10 run (about 30 s) setting
  it. One `system` run the Lab's way, process start to record saved: 1.6 to 2.0 s.
- 2026-11-14 (the developer's computer): DeePC `master`'s suite 278 passed in 219 s.
  `uv run deepc run system`: 7 runs on `master`, then 7 on the branch, read median 1.90 s and
  3.13 s, but VS Code had started on the machine in between (its processes the busiest, load
  average 2.0). 12 runs each, alternating `master` (a clone) and the branch so that a load falls
  on both alike: median 2.25 s and 2.34 s, minimum 1.89 s and 1.98 s. In one process the
  branch's only new work is finding the project, 3 to 10 ms; importing the command line and a
  piece took 172 to 228 ms on both sides.
