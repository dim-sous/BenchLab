# Benchlab: where the work stands

Start here in a new session. Updated 2026-11-14, after building branch 1 in VS Code on the
developer's computer (WSL2, 12 CPUs).

## Where it stands

- **Design approved** and pushed: `docs/design.md`. It holds every decision, each marked by who
  made it: the developer (what the page shows, decided after driving it) or Claude (how it is
  built, with the reason). §8 now says branch 1 is the move and the page and runner are branch 2;
  §4 records the entry-point declaration.
- **Mockup** the developer drove (two rounds, real DeePC and Hydrofoil runs):
  https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb (private to the developer).
- **Branch 1 built, reviewed, not committed** (2026-11-14), as `docs/plan-branch-1.md` says.
  Here, on `main`'s working tree (to become `core-from-deepc`): `benchlab/{record,figure,cli,lab}`
  moved from DeePC `c7f0d7d`, `benchlab/project.py`, the tests on a made-up project
  (`tests/toy/`), the packaging and the rules. In DeePC (`~/code/personal/deepc`), on `master`'s
  working tree (to become `benchlab-move`): the four layers deleted, the declaration in
  `devkit/harness/__init__.py` and `pyproject.toml`. DeePC points at this working copy through a
  path source in its `pyproject.toml` (and so in its `uv.lock`) that is never committed; at
  hand-off it becomes a git pin, the branch while PR A is open, tag `v0.1.0` after, re-locked
  each time (`README.md`).
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
- **Git, 2026-11-14:** the developer gave the word for the plan's steps 1 and 2 (Benchlab's branch
  and PR A; DeePC's branch, pinned to Benchlab's pushed branch, and PR B). Step 3 (merge A, tag
  `v0.1.0`, re-pin B to the tag, DeePC's suite again, merge B) waits for their word.

## Next

1. Step 3 of branch 1's git writes, on the developer's word: merge PR A, tag `v0.1.0`, re-pin
   DeePC's PR B to the tag (`uv lock`, no `../BenchLab` left in its lock), its suite, merge B.
2. Branch 2: the page as designed (tree, runs in their own processes, words as cells, no hovers),
   with Benchlab's own test project. Then Hydrofoil moves (with its naming pass), the shared
   calculations, BESS, old runs and Re-fly (`docs/design.md` §8). Left for branch 2 on purpose:
   "the terminal" in the Lab's prose still means the command line (now `benchlab/cli`), and the
   Lab's terminal drawer goes with the runner. DeePC still pins panel itself and lists matplotlib,
   which only Benchlab uses now.

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
- 2026-11-14 (the developer's computer): DeePC `master`'s suite 278 passed in 219 s.
  `uv run deepc run system`: 7 runs on `master`, then 7 on the branch, read median 1.90 s and
  3.13 s, but VS Code had started on the machine in between (its processes the busiest, load
  average 2.0). 12 runs each, alternating `master` (a clone) and the branch so that a load falls
  on both alike: median 2.25 s and 2.34 s, minimum 1.89 s and 1.98 s. In one process the
  branch's only new work is finding the project, 3 to 10 ms; importing the command line and a
  piece took 172 to 228 ms on both sides.
