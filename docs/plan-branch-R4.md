# Branch R4: files a run writes

## Context

Today a run leaves one thing behind: its run file, holding the numbers and the series
(`benchlab/record/__init__.py`, `Record.save`). A piece that also writes a trained network or a
checkpoint has nowhere to put it that the Lab knows of: deleting the run would leave the file
behind, and a later run could not be pointed at it. `docs/design.md` §10 names this as a change
Benchlab still needs (`CLAUDE.md`: "A file a run writes ... still need a change here").

In instrument terms: the logbook has one sheet per run. R4 gives each run a drawer under its
sheet, and the sheet lists what is in the drawer.

**The developer's choice (2026-11-16, this session):** R4 is built against Benchlab's own made-up
project, since no real project writes files yet (DeePC `c7f4569`: none of its four pieces does;
the toy projects are not started). **Its cost, written beside it:** this departs from decision
8's rule ("arrives with its first user"), so the shape is Claude's guess until a toy project
tries it. The two new names are therefore listed as **not yet promised**.

## What R4 delivers

1. **A folder per run**, beside its run file: `results/<piece>/<name>.files/`. While it runs, the
   piece calls `benchlab.run_files()` and gets that folder; it writes there whatever it likes, in
   any format. Benchlab never opens these files.
2. **The run file lists the folder's content**: one new entry, `files`, each file's name and its
   size in bytes. Written only when the run wrote a file, so **a run that writes none saves
   exactly the file it saves today**, and a run saved before R4 loads as before.
3. **A later run reads an earlier run's files**: a setting already can pick a saved run
   (`record_of`, as DeePC's closed loop picks its dataset run); `benchlab.files_of(that path)`
   gives its folder.
4. **The run file and its folder stay together.** The piece writes into a waiting folder
   (`<name>.files.partial/`); only when the run ends well does it take the place of the old
   folder, just before the run file is written. A run that fails or is stopped leaves the earlier
   run of that name whole and no waiting folder. Deleting a run in the Lab deletes its folder.
5. **On the page**, the compare table gains a heading "Files" after the run cost: one row per
   file name, each shown run's cell its size, or a word when the run file lists a file that is no
   longer there. Where it sits is the developer's to judge after seeing it
   (`docs/for-review.md`).
6. **The side door** (`<command> run`) prints the folder after the run file's path when the run
   wrote files.
7. **The check a project calls** (`check_project`) refuses a run whose listed file is missing or
   of another size.
8. Version `0.8.0`.

## Decided by Claude, with the reason

- **The piece asks for its folder; `run(config)` keeps its shape.** Changing what `run` takes
  would touch every piece of every project. Called outside a run started by the command or the
  Lab, `run_files()` refuses in words (fail loud), so a test of a file-writing piece runs it
  through `main(["run", ...])`.
- **`<name>.files/`, not `<name>/`:** the results folder is one people keep things in
  (`benchlab/lab/state.py`); the ending keeps the Lab from ever deleting a folder a person made.
- **One made-up piece, not two:** `fit`, which fits a line to noisy points in a few steps, writes
  its weights (`weights.npy`), and has a setting `start_from` naming an earlier fit run whose
  weights it starts from. It covers writing and reading in one piece (the question said two;
  one is fewer lines and the existing 34 mentions of `lag` in the tests stay untouched).
- **No copy, no hash of the files:** sizes only. A trained network can be large; hashing it on
  every listing costs time nobody asked for.
- **New words are Benchlab's own** (`benchlab/lab/words.toml`), no project touched.

## Files

- `benchlab/record/files.py` (new, about 50 lines): `run_files()`, `files_of(path)`, the folder
  names, the swap from waiting folder to kept folder, the listing (name, bytes).
- `benchlab/record/__init__.py`: `FILES_KEY` joins `HEADER_KEYS`; `save` writes the list when the
  folder holds a file. `benchlab/__init__.py`: the two names.
- `benchlab/runner.py`, `run_once`: opens the waiting folder before `component.run`, swaps it in
  before `save`, removes it when the run raises.
- `benchlab/lab/jobs.py`: `delete` takes the folder with the run file; a run that ends failed or
  stopped (`terminate`, lines 295-378) has its waiting folder removed.
- `benchlab/lab/state.py`: a listed row carries `files`. `benchlab/lab/view.py`,
  `compare_rows`: the "Files" rows. `benchlab/lab/words.toml`, `words.py`: about three slots.
- `benchlab/cli/__init__.py`: the folder line. `benchlab/testing.py`, `_check_run`: the check.
- Tests: `tests/toy/fit.py` (new, about 70 lines), `tests/toy/__init__.py` (`NAMES`);
  `tests/test_record.py`, `test_runner.py`, `test_lab.py`, `test_lab_view.py`,
  `test_lab_browser.py`, `test_cli.py`, `test_testing.py`, `test_shore.py` (a second list,
  "held, not yet promised"), `test_layers.py`.
- Docs: `README.md` (the two names, marked not yet promised), `docs/design.md` §10, `CLAUDE.md`
  (the line above), `docs/for-review.md` ("R4"), `docs/plan-branch-R4.md` (this plan, then "As
  built"), `.claude/memory/MEMORY.md`, version in `pyproject.toml` and `uv.lock`.

## Cost, named

- Benchlab: about +150 lines of code in nine files, about +200 of tests with the new piece.
- Compute: the suite timed before and after (328 passed in 80 s on the laptop; this cloud
  machine is timed fresh, before any change).
- Usage: moderate, about R3's size. No reviewers, no agent fan-out.

## Verification

- `uv run pytest`, `uv run ruff check .`, before and after.
- **A run that writes no file is unchanged:** every made-up `wave` and `lag` run saved before and
  after, compared byte for byte apart from provenance and wall-clock fields.
- **DeePC needs no change** (R2's method): its `master`, cloned read-only in this session,
  pointed at this working copy (never committed, and this session cannot push there); its whole
  suite (132 passed on 0.7.0), and one System run before and after compared field by field.
- **The Lab driven by Claude** in headless Chromium on the made-up project: run `fit`, see its
  file in the compare table; run a second `fit` starting from the first; tick both; stop a run
  half-way and see no folder left; delete a run and see its folder gone. Screenshots sent to the
  developer, since the made-up project is not on their computer.

## Git

Nothing is written to git on this plan's approval. This session works on the branch
`ccr-ea61ca3b-35fv7x`; the commit, the push, a PR, the merge and the tag `v0.8.0` are each asked
for when reached.

## Not in R4

Opening or previewing a file on the page; downloading; resuming a half-finished run; cleaning
old files by age or size; files shared between runs (a dataset); progress; R5; R6; 2d and 2e.

---

## As built (2026-11-17; merged)

Built in a cloud session and, on the developer's word ("Commit and push"), committed and
pushed on the branch `ccr-ea61ca3b-35fv7x`. After they saw the screenshots ("Figs look good,
proceed"; "All the way: merge and tag"): BenchLab #9 merged (`464a6bb`). The tag
`v0.8.0` is not made: the cloud session could not push one, and the developer makes it.

### What was built

- `benchlab/record/files.py` (new, 102 lines): `run_files()`, `files_of(path)`, the two folder
  names, `writing` and `keep` (the swap), `discard`, `listed`.
- `benchlab/record/__init__.py`: `FILES_KEY` in `HEADER_KEYS`; `save` writes the list when the
  folder beside the run file holds a file. `benchlab/__init__.py`: the two names.
- `benchlab/runner.py`: `run_once` runs the piece inside `writing`, then `keep`, then `save`.
- `benchlab/lab/jobs.py`: `delete` takes the folder and names it among what went; a run that
  ends failed or stopped has its waiting folder removed. `benchlab/lab/state.py`: a listed row
  carries `files`, each with `there`, read at every listing. `benchlab/lab/view.py`: the "Files"
  rows, last in the compare table, and `size`. `benchlab/lab/app.py`: the delete question.
  Four word slots (`compare.files`, `compare.file_gone`, `messages.delete_ask_files.one`,
  `.many`).
- `benchlab/cli/__init__.py`: the folder line. `benchlab/testing.py`: the check.
- The made-up `fit` (`tests/toy/fit.py`, 94 lines); `tests/test_files.py` (11 tests); one
  browser test; `tests/test_shore.py` holds the two names as held, not yet promised.

### Departures from the plan

1. **The delete question names the folder** when the run wrote files ("Delete <run file> and
   <folder>, the 2 files its run wrote?"). Found by driving: the question named the run file
   alone while the folder went with it.
2. **The Lab says what went**, the folder after the run file, in the terminal and in its note.
3. **More lines than named**: see "Measured".
4. **DeePC's suite was run before departure 1** was written, which changes the Lab's question
   alone; it was not run again after.

### Measured (this cloud machine, 4 CPUs)

- **Lines.** Benchlab's code: +214, −33 in twelve files, one new (the plan said about +150 in
  nine). Tests: +316, −9, with the new piece (the plan said about +200).
- **Benchlab's suite:** 328 passed in 90.9 s before (the first edits were made while it was
  still running); 344 passed in 99.5 s after. Ruff clean.
- **A run that writes no file is unchanged.** Two `wave` runs and a `lag` run, saved by the
  code of `861a066` and by this branch: the same keys in the same order, every field equal but
  `provenance` (`git_sha`, `git_dirty`, `duration_s`) and the `lag`'s `wave_run`, which holds
  the folder each was run in. No `files` entry and no folder.
- **DeePC** (`c7f4569`, a read-only clone, this working copy installed into its environment and
  nothing of it changed): 125 passed and 7 failed in 114.4 s; on the Benchlab it is locked to
  (`0.7.0`), 125 passed and the same 7 failed in 112.9 s. The seven are the frozen arrays of
  its `coupled_masses` cases (`tests/test_reference.py`, five; `tests/test_harness.py`, two).
  The notes record 132 passed on the developer's computer. One System run before and after:
  every field equal but `provenance` (`date`, `duration_s`, the `benchlab` version).
- **The Lab, driven in headless Chromium** on the made-up project: Fit opened; a run started
  from the form, its two files listed under "Files" at 144 B each; a second run started from
  the first through the form's "Start from" (saved as `results/fit/fit-1.json`), its loss
  starting under 0.01; both ticked, each file's size under each run; a 60 s run stopped from
  its row, its waiting folder there while it ran and gone after; the first run deleted, its
  run file and folder gone, the second's kept. Screenshots looked at. The one browser error
  raised came on switching piece, before any of this; the R3 browser test sets the same aside.

### Still to do

- The developer's judgement of `docs/for-review.md`, "R4".
- A toy project that writes files, to try the two names before they are promised.
