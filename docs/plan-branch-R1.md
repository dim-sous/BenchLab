# Branch R1: the shore, named and promised

## Context

RunLab (today Benchlab) is to be used like numpy: a change in a project never needs a change in
RunLab, and a new RunLab never needs a change in a project (`docs/design.md` §10). Today that
fails in three places, measured 2026-11-16 on Benchlab `v0.4.0` and DeePC `e3b1f06`:

- **DeePC's tests reach inside Benchlab.** Five test files, 1,929 lines, import its insides
  (`benchlab.lab.app`, `form`, `state`, `view`, `jobs`, `skin`, `words`, `benchlab.figure.*`).
  Any rewiring inside Benchlab breaks them.
- **Nothing says what a project may touch.** DeePC's four pieces use seven names
  (`Settings`, `Record`, `Series`, `Number`, `Provenance`, `stamp`, `bound_refs`) from two inner
  modules, in 16 import lines. No list, no promise.
- **DeePC takes Benchlab at a tag raised by hand**, so every Benchlab branch needed a DeePC PR
  (#18, #19, #20).

R1 closes these three. Nothing on the page changes. After it, R2 to R5 land without a DeePC PR,
which is the first proof the rule holds.

In instrument terms: R1 fixes the terminal block. What DeePC wires to is listed and stays put;
everything behind it can be rebuilt freely.

## What R1 delivers

1. **The shore: one named place.** A project imports from `benchlab` itself and nothing deeper:
   `from benchlab import Settings, Record, Series, Number, Provenance, stamp, bound_refs`
   (plus `with_overrides`, which DeePC's own System test uses). The old inner paths keep working,
   so a project that does not want the new way changes nothing.
2. **The shore, written down** (README, "What a project may use"): those names; the two commands
   a project's `pyproject.toml` names (`benchlab.cli:main`, `benchlab.lab:main`); the declaration
   (the seven names of `benchlab/project.py:30`); what a piece holds (`Config`, `run`, `Record`)
   and the settings' metadata keys; the run file; `benchlab.testing`.
3. **The promise:** from 0.5 until 1.0 nothing on the shore is removed, renamed or changed in
   meaning; things may be added. Held by a new test, `tests/test_shore.py`: a name dropped from
   the shore fails it. The made-up project (`tests/toy/`) is rewritten to import only the shore,
   and a test holds that too, so Benchlab's whole suite runs through the shore.
4. **One check a project calls from one test**, as numpy ships `numpy.testing`:
   `benchlab.testing.check_project(runs)`. It refuses, naming the piece and the cause, when: the
   declaration is incomplete; a piece lacks `Config`, `run` or `Record`; a piece's settings do
   not build a form; the words file leaves a slot empty; a given run does not load; a chart it
   declares does not draw; a project file imports Benchlab's insides; Benchlab's code spells one
   of the project's piece names. This is the "one test per project" `docs/design.md` §4 planned.
5. **DeePC's five test files go.** Each of their about 90 tests gets one of three fates, written
   as a table in `docs/plan-branch-R1.md`:
   - Benchlab's suite already checks it on the toy: deleted.
   - It checks Benchlab and nothing here does: moved into Benchlab's suite, on the toy. The toy
     grows only where a moved test needs it (expected: a second piece that takes the first's
     saved run, and a list setting).
   - It checks DeePC's own work (a unit per plant channel, the frozen loop, its numbers): stays in
     DeePC, reading only the shore.
6. **DeePC takes Benchlab by a range**: `"benchlab>=0.5,<1"`, from GitHub's `main`. Its lock file
   holds the exact commit, and `uv lock --upgrade-package benchlab` raises it: the same command
   and the same lock file as for numpy.

## Decided by Claude, with the reason

- **A flat shore (`from benchlab import ...`) rather than a list of inner paths.** "Nothing deeper
  than `benchlab`" is one rule a test can hold; a list of allowed inner modules is not. Cost: 12
  import lines replace 16 in DeePC; `import benchlab` now loads the record layer (numpy, param),
  which every piece and the command line load anyway. Import time measured before and after.
- **GitHub's `main`, not PyPI, until R6.** PyPI names are permanent and "benchlab" is to be
  dropped at the rename; publishing is for 1.0 under the final name, if wanted. Cost: `main` must
  always be a finished state, which "one gap per branch, merged when done" already gives.
  To verify at build, not assumed: that uv 0.10.10 refuses a git commit whose version falls
  outside the range. If it does not, the range stays as the written promise and the lock file
  does the pinning alone.
- **`check_project` takes runs the project made itself**, through its own command. Benchlab cannot
  run a project's pieces at their defaults: DeePC's closed loop is 77 s, and it needs a saved
  dataset run first.
- **DeePC drops the dependencies only Benchlab uses**, each only if no DeePC file still imports it
  (panel and playwright are imported by the five test files alone; matplotlib and plotly are
  checked at build, `tune.py` uses at least one). Rides here because this is DeePC's last PR made
  for Benchlab's sake.

## Steps

One branch in each repository, built in two steps. Both suites are green after each, so the work
can pause between them at no cost.

**Step 1, additive (Benchlab, then DeePC on a local editable install):**
- `benchlab/__init__.py`: the shore's names and `__all__`. `tests/test_layers.py`: its import
  table gains this.
- `benchlab/testing.py` (new, about 120 lines), built from what exists: `project.declared`,
  `record.config.fields_of`, `lab.words.load`, `Record.load`, `figure.draw`.
- `tests/test_shore.py`, `tests/test_testing.py` (new): the promise; the check passes on the toy
  and refuses each broken stand-in by name.
- `tests/toy/wave.py`: imports from the shore.
- `README.md`: "What a project may use" and the promise; the pin paragraph becomes the range.
- DeePC: the pieces' imports (12 files under `devkit/harness/`); `tests/test_bench.py` (new, one
  test calling the check on the runs `tests/lab_runs.py` already makes).

**Step 2, the sort (the larger part):**
- The fate table, then the moved tests into `tests/test_lab.py`, `tests/test_lab_browser.py` and a
  new `tests/test_figure.py`; the toy's growth.
- DeePC: the five files deleted; `tests/test_devkit_layers.py`, `test_harness.py`,
  `test_system.py`, `lab_runs.py` read only the shore; `pyproject.toml` takes the range and drops
  the unused dependencies; `uv.lock` regenerated.
- Search both repositories' code, docs and settings for the old names and the tag pin.

**Docs, last:** `docs/plan-branch-R1.md` (this plan and its "As built"); `docs/design.md` §10 (R1
built, measured); `CLAUDE.md` ("Benchlab is tested twice" replaced by: Benchlab's suite on the
toy, and a project's one check); `.claude/memory/MEMORY.md`; `docs/for-review.md` for any choice
left open. DeePC's `devkit/README.md` and memory. Version `0.5.0`.

## Cost, named

- Benchlab: about +250 lines of code and docs in step 1; up to about +1,000 test lines in step 2
  (an upper bound: DeePC's 1,929 less what is already checked here or is DeePC's own).
- DeePC: about −1,900 test lines, +40.
- Compute: both suites timed before and after (DeePC's was 246 tests in about 200 s; it loses its
  browser test and most Lab tests).
- Usage: step 2 is the heavy part (about 1,900 lines read, about 1,000 rewritten onto the toy).
  No parallel reviewers, no agent fan-out.

## Verification

- Benchlab: `uv run pytest` and `uv run ruff check .`, whole suite (185 passed before).
- DeePC's whole suite three times, as each branch before: on the local editable install, on
  Benchlab's pushed branch, and on `main` through the range after the merge.
- **The numbers do not move** (the refactor rule): every DeePC piece run and drawn on `master`
  and on the branch, by `docs/plan-branch-1.md`'s method; records and stills differ only in
  provenance (the Benchlab version) and the wall-clock fields two `master` runs already differ in.
- The rule itself: no DeePC file imports deeper than `benchlab`, `benchlab.testing` or the two
  commands. `check_project` holds this from then on.
- Hand-off: nothing new to drive. Claude opens DeePC's Lab once, runs a piece, and confirms the
  page is as on `v0.4.0`.

## Git

Approving this plan is the developer's word for one git step only: creating the branch
`r1-shore` in BenchLab and in DeePC (the 2026-11-15 notes, uncommitted on `main`, ride onto it).
Every later step (commit, push, PR, merge, tag `v0.5.0`, DeePC's lock raised, branches deleted)
is asked for when reached.

## Not in R1

Words (R2), a piece's own figures (R3), files a run writes (R4), new setting kinds (R5), the
rename (R6), 2d and 2e, any project other than DeePC.

---

## As built (2026-11-16; merged)

Merged on the developer's word: BenchLab #5 (merge `0c99bf1`, tagged `v0.5.0`) and DeePC-Sandbox
#21 (merge `3cf9542`), which takes Benchlab from `main` at `0c99bf1`.
The session was cut once, by the developer's laptop going down mid-run (cause theirs to find; a
restart cleared the scratch folder and the first before-and-after runs with it); all checks below
were run after it.

### What was built

**Benchlab**
- `benchlab/__init__.py` holds the eight names; `benchlab/testing.py` (135 lines) holds
  `check_project(runs, sources)`. `README.md`: "What a project may use", the promise, the range.
- `tests/test_shore.py` (6 tests) holds the list; `tests/test_testing.py` (11) holds the check.
- The made-up project imports only what a project may, and has a second piece, `tests/toy/lag.py`
  (a first-order lag driven by a saved wave run), for what the moved tests need.
- DeePC's tests, on the made-up project: `tests/test_lab_form.py` (new, 33 tests),
  `tests/test_lab_view.py` (new, 33), `tests/test_figure.py` (new, 14), and six more in
  `tests/test_lab_browser.py`. `two_runs` moved to `tests/conftest.py`.
- Version `0.5.0`.

**DeePC**
- The 12 files under `devkit/harness/*/` import from `benchlab` (16 lines).
- `tests/test_bench.py` (new): the one check, on a small run of every piece, over the whole
  repository. `tests/test_units.py` (new): the two tests of `tests/test_figure.py` that are
  DeePC's own.
- Deleted: `tests/test_lab.py`, `test_lab_browser.py`, `test_lab_form.py`, `test_lab_view.py`,
  `test_figure.py`.
- `tests/test_devkit_layers.py`, `test_harness.py`, `test_system.py`, `lab_runs.py` read only
  what a project may use. Every Benchlab import left in DeePC: names of `benchlab` (18 lines),
  `main` of `benchlab.cli` (3), `check_project` (1).
- `pyproject.toml`: `benchlab>=0.5,<1`; panel and matplotlib dropped (no DeePC file imports
  them); playwright kept (its hand-off skill drives the Lab in Chromium). The source line
  points at Benchlab's branch `r1-shore` while both PRs are open, and at `main` after
  Benchlab's merge.
- Docs: `README.md`, `CLAUDE.md` (140 lines, its budget), `devkit/README.md`, the hand-off skill.

### Where each of DeePC's 85 tests went

| DeePC's file | tests | moved here | deleted | stays in DeePC |
|---|---|---|---|---|
| `tests/test_lab.py` | 12 | 9, to `tests/test_lab_form.py` | 2 with a test of the same name here; 1 (the words fill every slot) is `check_project`'s | |
| `tests/test_lab_form.py` | 23 | 23, to `tests/test_lab_form.py` | | |
| `tests/test_lab_view.py` | 34 | 33, to `tests/test_lab_view.py` | 1 (a real run from the page: `tests/test_lab.py` here runs one) | |
| `tests/test_lab_browser.py` | 5 | 5, to `tests/test_lab_browser.py` | | |
| `tests/test_figure.py` | 11 | 9, to `tests/test_figure.py` | | 2, in `tests/test_units.py` |
| all five | 85 | 79 | 4 | 2 |

Also in `tests/test_devkit_layers.py`: the test that Benchlab's code names none of DeePC's pieces
is deleted (departure 1); its two tests of gates and bounds read `param`'s own metadata in place
of `fields_of`. The made-up project's words file was already DeePC's, word for word, so every
expected wording moved unchanged. All moved tests passed on their first run here.

### Departures from the plan

1. **`check_project` does not check that Benchlab's code spells none of the project's piece
   names.** Shipped to every project, it would let a project's own piece name (`label`, `figure`)
   fail the project's own suite. Benchlab's suite keeps the check, on the made-up project
   (`tests/test_layers.py`).
2. **uv does not hold a git source to the range.** Measured with uv 0.10.10 in a throwaway
   project: `benchlab>=0.5,<1` with the source at tag `v0.4.0` (version 0.4.0) resolved, with no
   warning. The range is the written promise; the lock file does the pinning.
3. **The moved tests are about 1,800 lines here, not "up to about 1,000"**: nearly every one of
   DeePC's had no counterpart here, so they moved one for one.
4. **`limits`, the made-up lag's list of numbers, has a row each in the form**, so a number list
   with rows is driven here as DeePC's θ was; a number list in one box is no longer driven on a
   page (the form's plain-data test still holds how it is written and read).

### Measured

- **Lines.** Benchlab: code and tests +2,068, −36 (of which `benchlab/` itself +147). DeePC:
  +125, −1,999; its test lines 3,105 to 1,231.
- **Benchlab's suite:** 198 passed in 34.9 s before; 306 passed in 72.2 s after
  (`tests/test_lab_browser.py` alone, its eight tests: 53.9 s). Ruff clean.
- **DeePC's suite:** 246 passed in about 200 s on `v0.4.0` (2c's record); 248 passed in 231 s
  after step 1; after step 2, 131 tests in 114 s, of which one failed: `CLAUDE.md` was one line
  over its 140-line budget. Shortened; its file and the three others changed since passed again
  (24 passed). Then, on Benchlab's pushed branch (`25d7dde`, installed from GitHub, no local
  copy): the whole suite, 131 passed in 110.6 s; and on Benchlab's `main` after its merge
  (`0c99bf1`): 131 passed in 118.1 s.
- **The numbers did not move.** Every DeePC piece run and drawn (70 files) on a clone of
  `e3b1f06` with Benchlab 0.4.0 from the tag, and on the finished working tree with Benchlab
  0.5.0. They differ only in: provenance (`date`, `duration_s`, `git_dirty`, and `versions`,
  where Benchlab reads 0.5.0); each sidecar's `command` (the clone's path), `date` and
  `git_dirty`; and the wall-clock fields two runs of the unchanged code already differed in
  (the closed loop's `constants`, `solve_time_s`, `numbers.solve_time_*`, `solve-time.png` and
  its sidecar's `ylim`; the open loop's `numbers.step_time_*`).
- **`import benchlab`:** 0.09 to 0.10 ms before (an empty package), 147 to 198 ms after; `import
  benchlab.record` before: 187 to 408 ms. Three reads each.
- **DeePC's Lab, driven once in headless Chromium** on the finished code: title "DeePC Lab", the
  four pieces offered, two charts of a closed loop drawn, the System form's twelve labelled
  rows, a System run started from the form ending Done and saved, no error on the page or in
  its console.

### Still to do

- The git steps are done: both merged, `v0.5.0` tagged, both branches deleted, both copies on
  `main` and `master`.
- `docs/for-review.md`, "R1", holds the eight choices made on the way.
- Then R2, the words (`docs/design.md` §10): the first branch that should need no DeePC change.
