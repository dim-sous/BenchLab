# Benchlab: where the work stands

Start here in a new session. Updated 2026-11-14, with branch 2a built and reviewed, not yet
committed (VS Code on the developer's computer, WSL2, 12 CPUs).

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
- **Branch 2 is four branches** (the developer, 2026-11-14), each driven in DeePC's Lab before the
  next: 2a runs in progress, 2b words as slots and no hovers, 2c the tree, 2d the cards' full
  controls (`docs/design.md` §8).
- **Branch 2a built and reviewed, not committed** (2026-11-14, `docs/plan-branch-2a.md` with its
  "As built" part): each run its own process (`python -m benchlab.runner`), up to the cores side
  by side, the rest queued, the strip along the bottom in place of the terminal; the side door and
  the Lab share `benchlab.runner`; version 0.2.0. In the working trees: here on `main`, in DeePC on
  `master`, which points at this copy through its path source (never committed). Checked: Benchlab
  165 passed; DeePC's whole suite 244 passed in 187 s; its records through the side door as
  `master`'s but provenance and wall-clock fields; a closed loop from the Lab's queue and from the
  side door differ only in name, solve times and provenance. Reviewed by four parallel reviewers
  (the developer's choice): 37 findings, 35 confirmed, all fixed or written in the plan's "As
  built". DeePC's whole suite then found two more, fixed (the plan's "As built"): a run whose end
  could not be read crashed its watcher, and DeePC's chart test read the charts at a fixed time.
  Handed off in DeePC's Lab with a step-by-step walkthrough Claude drove first (the developer,
  2026-11-14: "Looks good, proceed"). On their word, steps 1 and 2: this branch,
  `runs-in-progress`, pushed with its PR; then DeePC's branch of the same name, pinned to it, its
  whole suite rerun, with its PR. Waiting: step 3 on their word (merge, tag `v0.2.0`, re-pin
  DeePC to the tag, its suite again, merge, branches deleted, both copies back on `main` and
  `master`).

## Next

1. 2a's step 3, on the developer's word (above). A hand-off is a walkthrough: what to click, what
   to type, what the page should then show, each step driven by Claude first (2026-11-14: the
   developer found a list of steps without them "not clear as to what to run/drive and what to
   observe").
2. 2b words as slots and no hovers (proposed first), 2c the tree, 2d the cards' full controls.
   Then Hydrofoil moves (with its naming pass), the shared calculations, BESS, old runs and Re-fly
   (`docs/design.md` §8). Waiting for a later branch: progress percentages, when a piece reports
   one; DeePC still pins panel itself and lists matplotlib, which only Benchlab uses now.

## How the developer works

- **Every question goes through AskUserQuestion**, with the context inside the question, never as
  text at the end of a message (2026-11-13: "WHEN I ASK QUESTION TO WHICH I EXPECT ANSWERS,
  ALWAYS USE THE ASKTHEUSER TOOL"). On 2026-11-14 they had it added to `~/.claude/CLAUDE.md` on
  this computer.
- **Not a software engineer**: "take every last one of my answer with a grain of salt". What the
  page shows is theirs, settled only after driving it. How it is built is Claude's, said with
  its reason. Push back when an answer costs more than it looks, and write the cost beside the
  decision (`docs/design.md` §3, decision 5, is the example).
- The siblings' rules hold here too: propose, then plan mode, then build. Ask before any
  multi-agent fan-out, every time. Hand off in the Lab, or say plainly there is nothing to drive.
  No git write without their word.

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
