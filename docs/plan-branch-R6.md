# Branch R6: the rename to RunLab (version 0.10.0)

## Context

The developer chose the name RunLab on 2026-11-15 (`docs/design.md` §3, decision 1); the route
(§10) puts the rename last, "as 1.0", "once the shore is proven". On 2026-11-17 they gave the
go for it.

Measured that day: the name appears about 740 times in 61 files here (123 mentions in code, 178
in tests, the rest in documents and notes). DeePC (`c7f4569`) holds 46 mentions: about 26 lines
`from benchlab import ...`, its two commands (`benchlab.cli:main`, `benchlab.lab:main`), its
declaration (`[project.entry-points.benchlab]`), and two install lines (`benchlab>=0.7,<1` and
the git source named `benchlab`). Its `<1` shuts out a version 1.0 until DeePC is edited.

**The developer's three choices (2026-11-17):**
1. **Version `0.10.0` now, 1.0 later**, in a branch of its own, once a toy project has used R4's
   run folder and R5's settings: nothing is frozen that has not been tried.
2. **The old name keeps working**: DeePC needs no change, now or later.
3. **The name a project installs stays `benchlab` until 1.0**, when DeePC's two install lines
   are edited anyway. Saved run files do not change at all.

In instrument terms: the rack and every drawing of it are relabelled, and the old tag stays
riveted on so that nobody's wiring diagram goes wrong.

## What R6 delivers

1. **The package is `runlab`**: its folder (`benchlab/` becomes `runlab/`), every import in the
   code and the tests, the Lab's runs (`python -m runlab.runner`).
2. **`benchlab` stays, as a stand-in** of four small files that hand over to `runlab`: the
   names a project may use (`from benchlab import Settings, Record, ...`), `benchlab.cli`
   (`main`), `benchlab.lab` (`main`) and `benchlab.testing` (`check_project`). Nothing deeper:
   Benchlab's insides were never a project's to use (R1).
3. **A project is found under either name**: it declares itself in the entry-point group
   `runlab`, or `benchlab` as DeePC does. Declared in both by one project is one project; two
   projects are still refused.
4. **The install name and the version stamp stay `benchlab`** (`pyproject.toml`, `name`; the
   run file's `provenance.versions`). So a run file saved after R6 holds exactly what it holds
   today, and DeePC raises its lock to `0.10.0` without an edit.
5. **The live documents say RunLab**: `README.md`, `CLAUDE.md`, the docstrings and comments of
   the code and the tests, `runlab/lab/words.toml`'s own comments. `README.md` says how the two
   names stand until 1.0.
6. **Records of the past keep the old name**: `docs/plan-branch-*.md` up to R5,
   `docs/project/failures.md`, the dated parts of `docs/design.md` and of the notes. `docs/design.md`
   §10 gains R6 "Built".
7. Version `0.10.0`.

## What waits for 1.0 (not in R6)

The install name `runlab`, the stamp's key, DeePC's install lines and its `<1`; whether
`benchlab` the stand-in is then dropped; R4's two names promised; the repository's own name on
GitHub (the developer's, in the repository's settings on the website; GitHub forwards the old
address).

## Decided by Claude, with the reason

- **Four plain stand-in files, not an import hook**: what they hand over is read in the file,
  and a project reaching past them fails at once with Python's own "no module named".
- **The made-up project uses the new name** (`from runlab import ...`), and one test runs a
  piece and the check through the old name, as DeePC does.
- **The swap is mechanical** (`benchlab` to `runlab`, `Benchlab` to `RunLab`) over `runlab/`,
  `tests/`, `README.md`, `CLAUDE.md`, then read by hand where the old name must stay: the
  install name, the stamp, the second entry-point group, the GitHub address, DeePC's history.

## Files

- `benchlab/` moved to `runlab/` (`git mv`); new `benchlab/__init__.py`, `cli.py`, `lab.py`,
  `testing.py` (about 25 lines together).
- `runlab/project.py`: the two groups (`GROUPS`), the refusals' words. `runlab/record/__init__.py`,
  `stamp`: the version read from the install name. `runlab/testing.py`: the list of what a
  project may import, under both names.
- `pyproject.toml`: both packages found and installed, the words file's new path; version.
- `tests/`: every import; `tests/test_layers.py`, `tests/test_lab.py` (their tables of who may
  import whom), `tests/test_packaging.py` (the built package holds both names),
  `tests/test_shore.py` and one new test for the old name.
- Docs: `README.md`, `CLAUDE.md`, `docs/design.md` §10, `docs/plan-branch-R6.md`,
  `docs/for-review.md` ("R6"), `.claude/memory/MEMORY.md`.

## Cost, named

- About 400 lines touched in code and tests, nearly all a one-word swap; about 40 new lines
  (the stand-in, the second group, tests).
- Compute: the suite before and after (355 passed in 112.4 s on this cloud machine).
- Usage: about R4's. No reviewers, no agent fan-out.

## Verification (a refactor: the numbers must not move)

- `uv run pytest`, `uv run ruff check .`: the same tests pass, plus the new ones.
- **Every made-up piece's run** (`wave`, `lag`, `fit` with its files) saved before and after:
  equal field by field but provenance's date, duration and commit; the `benchlab` version
  stamp present in both.
- **DeePC, unedited**, on this working copy: its whole suite's failures the same seven as
  before; one System run equal but provenance; **its Lab started through its own command**
  (`uv run lab --no-open`, which names `benchlab.lab:main`) and its page loaded in headless
  Chromium, a screenshot looked at.
- **The old names searched for** after the move (`CLAUDE.md`, "After any move"): every
  remaining `benchlab` in code, tests and live documents listed and accounted for in the plan's
  "As built".

## Git

Nothing is written to git on this plan's approval. The session's branch is
`ccr-ea61ca3b-35fv7x`; commit, push, a PR and the merge are each asked for when reached. The tag
`v0.10.0` is the developer's to make (GitHub's release page). A git step is written into the
notes only after it is done.

---

## As built (2026-11-17; merged)

Built in a cloud session and committed on the branch `ccr-ea61ca3b-35fv7x`, on the
developer's word ("All the way: merge"): BenchLab #15 merged (`a133ef2`). The tag `v0.10.0`
the developer made themselves, from GitHub's release page, on `e161b94` (that merge and a
notes-only one, #16).

### What was built

- `benchlab/` moved to `runlab/`, and the name swapped (`benchlab` to `runlab`, `Benchlab` to
  `RunLab`) across `runlab/`, `tests/`, `README.md`, `CLAUDE.md` and `pyproject.toml`: 358
  mentions.
- The stand-in `benchlab/`: `__init__.py` (every name `runlab` holds for a project), `cli.py`
  and `lab.py` (`main`), `testing.py` (`check_project`); 20 lines.
- `runlab/project.py`: `GROUPS`, the entry-point groups `runlab` and `benchlab`; a project
  declared in both is counted once (`_once`: one module, one distribution).
- `runlab/record/__init__.py`: `INSTALLED = "benchlab"`, the name the version stamp is read
  from and saved under. `pyproject.toml`: `name = "benchlab"`, both packages installed, version
  `0.10.0`.
- `runlab/testing.py`: a project file's imports are held to the same list under both names.
- `tests/test_old_name.py` (8 tests); `tests/test_project.py` and `tests/test_packaging.py`
  hold the two groups, the stamp's key and the built package's two names.

### Where the old name is left, each accounted for (searched after the move)

- **Code:** `runlab/project.py` (the second group), `runlab/record/__init__.py` (the install
  name), `runlab/testing.py` (the second import name), the stand-in `benchlab/`.
- **Packaging:** `pyproject.toml` (the install name, the stand-in's folder), `uv.lock`.
- **Tests:** `tests/test_old_name.py`, `tests/test_project.py` (the stamp),
  `tests/test_packaging.py`.
- **Live documents:** `README.md` (its first paragraph, the install lines of a project),
  `CLAUDE.md` (the lock command).
- **Records of the past, untouched:** `docs/plan-branch-*.md` up to R5,
  `docs/project/failures.md`, `docs/design.md` and `docs/for-review.md` but for their R6
  parts, `.claude/memory/MEMORY.md` but for its top and its R6 part.

### Departures from the plan

1. **`benchlab.record`, a path a project used before 0.5, no longer imports** (the plan:
   "nothing deeper"). `tests/test_shore.py` holds those paths under `runlab`.
2. **More lines than named**: code, tests and packaging, +569 and −445 in 57 files, 28 of
   them moved (the plan said about 400 touched and 40 new).

### Measured (this cloud machine, 4 CPUs)

- **RunLab's suite:** 355 passed in 112.4 s before; 363 passed in 110.7 s after. Ruff clean.
- **The numbers did not move.** Every made-up piece run and drawn (`wave` twice, `lag`, `fit`
  twice with its files; 19 files) twice on the code of `3da96cd` and once after: the stills
  and the files the fit wrote equal byte for byte; the run files and the stills' notes equal
  but for what the two runs of the old code already differ in (date, duration, the command's
  folder) and `git_dirty` and the `benchlab` version (`0.9.0` to `0.10.0`), still under the
  key `benchlab`.
- **DeePC, unedited** (`c7f4569`, a read-only clone, this working copy installed into its
  environment): `benchlab` and `runlab` both import from this copy; 125 passed and 7 failed in
  117.9 s, the same seven as on Benchlab 0.7.0 on this machine; one System run on 0.9.0 and
  on this branch equal but `provenance` (`date`, `duration_s`, the `benchlab` version).
- **DeePC's Lab through its own command** (`uv run lab`, which names `benchlab.lab:main`, its
  declaration in the group `benchlab`): served; the page loaded in headless Chromium shows
  "DeePC Lab", its four pieces and the form's settings, and raised no error. Screenshot
  looked at.

### Still to do

- 1.0, a branch of its own ("What waits for 1.0").
