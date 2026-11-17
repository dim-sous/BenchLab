# Benchlab: where the work stands

Start here in a new session. Updated 2026-11-17: **R1 to R5 are merged** (`v0.5.0`, `v0.6.0`,
`v0.7.0`, `v0.8.0`, `v0.9.0`); each
`docs/plan-branch-R*.md`, "As built", holds what was built and measured. **Next: R6, the
rename to RunLab as 1.0**, on the developer's go; neither R4's two names nor R5 has had a real
user yet, and the developer placed R6 "once the shore is proven". The direction since 2026-11-15
(`docs/design.md` §10): Benchlab, to be renamed RunLab, is used like numpy. 2d and 2e are on
hold. VS Code on the developer's computer, WSL2, 12 CPUs.

## R5, merged 2026-11-17 (built in the same cloud session)

- **The developer's choices (2026-11-17):** "Propose R5", then "Made-up project now": no
  project has a matrix or a date among its settings (DeePC's are lists, numbers and text), so
  R5 has no first user either. They approved the plan (`docs/plan-branch-R5.md`, "As built").
- **Built:** a setting may be of any kind `param` offers. The six are read and written as
  before; any other (a matrix, a date, a pair, a table) is typed as the text `param` reads,
  saved as `param` writes it, loaded as the real thing, and shown as that text in a plain box
  (`benchlab/record/config.py`, `other_kind`). No new name for a project. The made-up `fit`
  has a matrix (`scale`) and a calendar date (`day`). Version `0.9.0`.
- **Checked (cloud machine):** Benchlab 355 passed in 112.4 s (344 in 99.5 s before), ruff
  clean. Runs of the six kinds save what they saved. DeePC on this working copy: the same seven
  failures as on 0.7.0, its System run unchanged. The Lab driven in headless Chromium,
  screenshots looked at.
- **For the developer:** `docs/for-review.md`, "R5", seven points.
- **Git:** the developer saw the screenshots and chose "All the way: merge" (2026-11-17).
  One commit (`3129983`) on `ccr-ea61ca3b-35fv7x`, BenchLab #12 merged (`0b679e4`). **The tag
  `v0.9.0` was made by the developer** (2026-11-17, GitHub's release page), on `c010581`:
  `main`'s head then, R5's merge plus a notes-only merge (#13). A plain tag, as `v0.8.0`. A
  cloud session cannot push a tag: the developer makes it from
  `github.com/dim-sous/BenchLab/releases/new` in a phone's browser (the phone app has no such
  page), and the session then checks it with `git ls-remote --tags origin`.
  DeePC is untouched and stays on Benchlab `5023526` (`v0.7.0`) in its lock.
- **After it:** R6, the rename to RunLab as 1.0 (`docs/design.md` §10), which the developer
  placed last, "once the shore is proven"; R4's two names and R5 have no real user yet. Then
  2d and 2e.

## R4, merged 2026-11-17 (built in a cloud session)

- **The developer's choices (2026-11-16, from a phone):** "Propose R4", then "Made-up project
  now" over waiting for a toy project: no project writes files yet (DeePC `c7f4569`: none of its
  four pieces does), so R4 has no first user, against decision 8's rule. They approved the plan
  (`docs/plan-branch-R4.md`, with its "As built").
- **Built:** a folder per run beside its run file (`<name>.files/`); the piece asks for it while
  it runs (`benchlab.run_files()`); the run file lists each file's name and size (`files`, left
  out when the run wrote none); a later run reads an earlier run's folder
  (`benchlab.files_of(path)`); a failed or stopped run leaves the earlier run whole; deleting a
  run takes its folder; the compare table's "Files" rows. The made-up project has a third
  piece, `fit`. Version `0.8.0`. **The two names are held, not yet promised**
  (`tests/test_shore.py`, `README.md`) until a project has used them.
- **Checked (cloud machine, 4 CPUs):** Benchlab 344 passed in 99.5 s (328 in 90.9 s before),
  ruff clean. A run that writes no file saves the same file as before. DeePC on this working
  copy: 125 passed, 7 failed, and the same 7 fail there on Benchlab 0.7.0: the frozen arrays of
  its `coupled_masses` cases, on that machine (132 pass on the developer's computer). The Lab
  driven in headless Chromium on the made-up project, screenshots looked at.
- **For the developer:** `docs/for-review.md`, "R4", eight points.
- **The developer looked at the screenshots and said "Figs look good, proceed"**, then "All
  the way: merge and tag" (2026-11-17). Git, on those words: one commit (`0d80852`) and one
  for the notes on `ccr-ea61ca3b-35fv7x`, BenchLab #9 merged (`464a6bb`).
- **The tag `v0.8.0` was made by the developer** (2026-11-17, from GitHub's release page on a
  phone), on `af76991`: `main`'s head then, R4's merge (`464a6bb`) plus a notes-only merge
  (#10). It is a plain tag, where `v0.7.0` carries a message. The cloud session could not make
  it: it may push to its own branch only, and the tag's push was cut off three times.
  **Claude's slip, recorded:** the notes merged with #9 said "tagged" before the tag existed;
  #10 corrected them. Write a git step into the notes only after it is done.
- **Still to do:** a toy project that writes files, to try the two names before they are
  promised; the eight points of `docs/for-review.md`, "R4", are the developer's to judge.
- **After it:** R5 (above).

## For a session that starts from GitHub alone (2026-11-17)

The developer said they would continue in a new cloud session, from a phone. Such a session has
this repository and nothing of the laptop the work was done on:

- **DeePC is another repository**, `dim-sous/DeePC-Sandbox` (default branch `master`). A change
  here that a project is to use is checked against it: clone it beside this one and point it at
  this working copy (`README.md`, "How a project declares itself"; that line is never committed).
  Its whole suite takes about two minutes; R2 showed a change may need none of it. In a cloud
  session it is cloned read-only (`add_repo`, then `uv pip install -e` of this copy into its
  environment, `uv sync` to put its own back); seven of its frozen-array tests fail on the
  cloud machine on any Benchlab (measured 2026-11-17), so compare failures before and after.
- **The scripts used to check that DeePC's numbers do not move are not kept.** The method is
  written out: `docs/plan-branch-1.md`, "Verification" (which piece is run with which settings,
  then drawn), and `docs/plan-branch-R1.md` and `docs/plan-branch-R3.md`, "Measured" (what two
  runs of one code already differ in): every piece run and drawn into a folder before and after,
  records compared field by field and stills byte for byte.
- **The developer's toy projects** (P1 to P9, `docs/design.md` §10) are a private file on their
  computer, all not started on 2026-11-17. Ask them; none of it belongs in this repository.
- **How the developer works** is below, and holds in any session: every question through the
  question tool with its context inside, plain words, no git write without their word in that
  turn, lean usage.

## R3, merged 2026-11-17

- **A piece may hand the page a plotly figure it draws itself**: `benchlab.Figure`,
  `Record.figures()`, drawn when shown from the record's own fields (the run file keeps the
  numbers; its `panels` and `panel_groups` gain the figures' names). Version `0.7.0`.
- **The developer's four choices (2026-11-17):** first user DeePC's pole map on System; several
  runs, one figure per run, stacked; a short read of MLflow's and TensorBoard's docs; no saved
  picture yet (`draw` names what it left out).
- **DeePC**: the pole map, one test, `benchlab>=0.7,<1`, its lock at Benchlab `5023526`.
- **Checked:** Benchlab 328 passed in 80 s (315 before), ruff clean. DeePC 132 passed in 114 s.
  DeePC's runs as before but provenance, wall-clock fields and the System file's two lists
  gaining `pole-map`. A System run saved on 0.5.0 draws its pole map. DeePC's Lab driven in
  headless Chromium, screenshots looked at.
- **Found by driving:** under plotly's stock template the grid and zero lines did not show on
  the card's paper; the card's look is now laid under a piece's figure as a plotly template.
- **For the developer after driving:** `docs/for-review.md`, "R3", six points; the first is the
  colour of a stacked figure (the piece's own, not the run's).
- **The developer drove it and said "Looks right: all the way"** (2026-11-17). Git, on that
  word: BenchLab #7 merged (`5023526`), tagged `v0.7.0`; DeePC's whole suite on Benchlab's
  pushed branch as an installed package (132 passed in 111 s), then its source line to `main`,
  its lock at `5023526` (same tree as the branch head; the bench, System and document checks
  re-run, 51 passed), DeePC-Sandbox #22 merged (`c7f4569`); each merge's state read before its
  branch went; both branches deleted, both copies on `main` and `master`, clean but for this
  edit of the notes and the plan's. BenchLab #7's merge subject lacks its number (written
  before the PR had one).
- **Open after R3** (`docs/for-review.md`, "R3"): the colour of a stacked figure (the piece's
  own, not the run's); figures built on opening, when a piece has heavy ones; saved pictures.
- **After it:** R4, files a run writes (above).

## R2, merged 2026-11-16

- **Benchlab holds the page's 136 words** (`benchlab/lab/words.toml`); a project's file lists only
  those it changes and `WORDS` is optional. Version `0.6.0`. BenchLab only: **DeePC needed no
  change**, checked on a scratch clone of its `master` (131 passed, all 136 words as on `v0.5.0`,
  its Lab driven). Benchlab: 315 passed in 73 s, ruff clean.
- **Nothing in a project's words file stops the Lab** (the developer, 2026-11-15, and again
  2026-11-16): an entry it cannot use is left out and named once in the terminal. So no slot
  name is promised. **Claude's slip, recorded:** the R2 plan was written without reading decision
  4's "Replaced" note and kept the refusal; found while editing `docs/design.md`, put to the
  developer, reworked. Read the numbered decisions of `docs/design.md` §3 before planning what
  they touch.
- **Git, on the developer's word** (2026-11-16: "All the way: merge and tag"): BenchLab #6 merged
  (`521948e`), tagged `v0.6.0`, its state read before the branch went, the branch deleted, the
  copy back on `main`, clean but for this edit of the notes and the plan's, which ride with the
  next branch. DeePC stays on Benchlab `0c99bf1` (`v0.5.0`) in its lock until it wants more.
- **After it:** R3, a piece's own plotly figures. DeePC's words file can be deleted in a branch
  of its own when the developer wants.

## R1, merged 2026-11-16

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
- **Git, each step on the developer's word** (2026-11-16: "Commit and open both PRs", then "merge
  both PRs and finish the git steps"): BenchLab #5 merged (`0c99bf1`) and tagged `v0.5.0`; DeePC's
  source line moved to Benchlab's `main`, its lock at `0c99bf1`, its whole suite again (131
  passed in 118 s), DeePC-Sandbox #21 merged (`3cf9542`); each merge's state read before its
  branch went ([L1]); both branches deleted, both copies back on `main` and `master`, clean but
  for this edit of the notes and the plan's, which ride with the next branch. DeePC's remote
  address still carries the repository's old name; GitHub sends it on to
  `dim-sous/DeePC-Sandbox`, where a merged PR's branch is deleted by GitHub itself.
- **uv does not hold a git source to a version range** (measured, uv 0.10.10): the range is the
  written promise, `uv.lock` does the pinning.
- **For the developer's review:** `docs/for-review.md`, "R1", eight choices.
- **The session was cut once**: the developer's laptop went down while DeePC's pieces ran on
  several cores (cause theirs; they later said "the problem is fixed"). The scratch folder is
  cleared by a restart: a baseline worth keeping does not belong there.
- **Usage:** the developer asked for it lean on 2026-11-16: no parallel reviewers, no agent
  fan-out, "a few bugs here and there are fine, we will iron them out later".
- **Next:** R2, the words: the first branch that should need no DeePC change. DeePC takes a
  later Benchlab only when it wants it, by `uv lock --upgrade-package benchlab` and its suite.

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
