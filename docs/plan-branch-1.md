# Branch 1 (plan, approved 2026-11-13): Benchlab's core, and DeePC moved onto it, nothing changed that you can see

## Context

The design (`dim-sous/benchlab`, `docs/design.md`, approved 2026-11-13) makes one shared package
of the Lab, the run files, the charts and the command line, which each project today carries a
copy of. Branch 1 is the first step: Benchlab comes into being, and DeePC uses it instead of its
own copy.

**One change to the design's §8 order, and why.** The design said branch 1 would be "the core,
without the page". I read the code and propose instead **moving all of DeePC's shared layers,
its page included, into Benchlab unchanged**. Then the page as you designed it (the tree, runs in
their own processes, words as cells, no hovers) comes in branch 2, on top of a move already
proven. Two reasons:
- Without its page in Benchlab, DeePC would lose its Lab between the two branches, or have to
  keep a half-copy that reaches into Benchlab.
- Your rules: "match before extending", and "a refactor proves itself by NOT changing the
  numbers". A pure move is checkable bit for bit. A move plus a redesign is not.

The runner (each run its own process) moves to branch 2 as well, where its first user, the page,
arrives (your rule: nothing built before something uses it). §8 of `design.md` is updated to say
so.

**What you will see after branch 1:** DeePC's Lab, exactly as today. The proof is in files and
tests, not in the page: there is nothing new to drive, and I'll say so at hand-off.

## What I found (read-only, 2026-11-13)

- **DeePC is between branches.** PRs #14–#16 are merged (System, Open loop, System analysis S1).
  Nothing is in flight, and the next items in its queue (S2, S3, the closed loop) haven't
  started. It's a clean moment to move.
- **DeePC's shared layers**, `devkit/{record,figure,terminal,lab}`: 4,486 lines. The pieces
  (`devkit/harness/<piece>/`) import only `record` (Settings, Record, Series, Number, Provenance,
  stamp, bound_refs). The command line and the Lab reach the project only through its registry
  (`harness.NAMES`, `get_component`).
- **Exactly four things tie those layers to DeePC**, and they are what this branch cuts:
  1. the command name `deepc`, in `terminal/__init__.py` (prog, errors), `lab/jobs.py:103`
     (`["uv","run","deepc","run",piece]`) and `lab/cli.py` (help text);
  2. the title `"DeePC Lab"` in `lab/app.py:1374,1433`;
  3. the registry imported by its flat name `harness`, in `terminal` and `lab`;
  4. the provenance: `record/__init__.py:36` finds the repo for the git commit from its own
     file location (`REPO_ROOT = Path(__file__)…parent.parent.parent`), and `:44` names DeePC's
     libraries (`_LIBRARIES = ("numpy","scipy","cvxpy","osqp","scs")`). Moved as they are, a
     record would be stamped with the wrong repo's commit.

## The approach

### How a project declares itself to Benchlab
One small block in the project's registry, `devkit/harness/__init__.py`, beside `NAMES` and
`get_component`:
`COMMAND = "deepc"`, `TITLE = "DeePC Lab"`, `ROOT` (the repo, from that file's location), and
`LIBRARIES` (the libraries its runs stamp). Its `pyproject.toml` points Benchlab at it with one
entry point (`[project.entry-points.benchlab] project = "harness"`), the standard Python plugin
mechanism. Benchlab's `benchlab/project.py` finds the one declared project and refuses loudly,
naming the cause, when there is none, more than one, or one missing a name.

### PR A: `dim-sous/benchlab`, branch `core-from-deepc`
- `benchlab/record`, `benchlab/figure`, `benchlab/cli` (today's `terminal`), `benchlab/lab`: DeePC's
  files moved with their history described in the PR, and imports rewritten to `benchlab.*`.
  The only code changes are the four ties above, each now read from the project declaration.
  Provenance adds Benchlab's own version to `versions`, so a record says which Benchlab made it.
  This is a declared difference, and the only one in a record.
- `benchlab/project.py` (new, about 60 lines).
- `pyproject.toml`: Python 3.13; dependencies taken from DeePC's (numpy, matplotlib, param>=2.4.2,
  panel>=1.9.4,<1.10, plotly>=6.6.0); dev: pytest, ruff. Plus `.python-version`, `.gitignore`,
  `uv.lock`.
- Rules and records, as in the siblings: `CLAUDE.md` (advisory rules only: Benchlab names no
  project; a run-file format change is a new version that every project takes; evidence over
  judgement, the comment rule, fail loud), `README.md` (what it is, how a project declares
  itself, how it installs), `docs/project/failures.md` (empty, pointing at the siblings'
  incidents), `.claude/memory/MEMORY.md`.
- Tests: `test_record.py` moved from DeePC (it names no piece). New: a small made-up project
  under `tests/` (one piece) to drive the command line (run, draw) and to build the Lab's page
  without a browser. New: Benchlab never imports a project except through `project.py`, and its
  layers import in one direction (`record ← figure ← cli ← lab`). The Lab's import-allowlist
  half of DeePC's `test_lab.py` moves here, because it reads the Lab's own files.
- `docs/design.md` §8 updated (branch 1 = this move; the page and the runner = branch 2).

### PR B: `dim-sous/DeePC-Sandbox`, a new branch off `master` (e.g. `benchlab-move`)
- Delete `devkit/{record,figure,terminal,lab}`.
- `pyproject.toml`: Benchlab pinned at tag `v0.1.0` (`[tool.uv.sources]` git + tag); scripts
  `deepc = "benchlab.cli:main"` and `lab = "benchlab.lab:main"`; the entry point.
- `devkit/harness/__init__.py`: the declaration block.
- Pieces and tests: `record`/`figure`/`terminal`/`lab` imports become `benchlab.*` (mechanical,
  about 10 piece files and 10 test files). The Lab, chart and form tests that drive DeePC's real
  pieces (`test_lab*.py`, `test_figure.py`, about 2,000 lines) stay here, so DeePC's suite keeps
  testing the Lab through its own pieces.
- `test_devkit_layers.py`: keeps the half about DeePC's pieces. Its generic-layer half now
  lives in Benchlab.
- `test_roots.py`: `benchlab` is added to what `src/` and `tools/` may not import (the bench never
  reaches the controller or the world).
- Words, docs, notes: `CLAUDE.md` (within its heft budget), `README.md`, `devkit/README.md`,
  `docs/project/lab-words.md`, the skills, `.claude/memory/`. Old names searched for (RCWS #159),
  and `test_conventions.py` checks every backticked path still exists.

**Known debt, said plainly:** until branch 2, Benchlab's page and charts are tested mainly through
DeePC's suite. Branch 2 gives Benchlab its own test project large enough to carry them.
DeePC's page words (`"DeePC Lab"` apart) stay written inside Benchlab's Lab until the words-as-
cells branch.

## Order of git writes (each only on your word at hand-off)
1. Push Benchlab `core-from-deepc`, open PR A. 2. Push DeePC branch, open PR B (pinned to the
branch while open). 3. On your word: merge A, tag `v0.1.0`, re-pin B to the tag, run DeePC's
suite again, merge B.

## Verification
1. **Before**, on DeePC `master`, into a scratch folder: `deepc run` for every piece. That's
   `system`, `open_loop` and `dataset` at defaults, plus `closed_loop` at the 1 s settings
   `tests/lab_runs.py` uses, because 77 s per default run is not needed for a bit-for-bit check.
   Then `deepc draw` for each record.
2. **After**, on the branch, the same commands. Every record must be identical except
   provenance (date, duration, commit, the added `benchlab` version). Every PNG must be identical
   byte for byte, or else pixel for pixel. A difference stops the branch.
3. DeePC's whole suite, locally (`uv run pytest`, browser test included), green. The safety net
   (`tests/reference/`) bit for bit, as it covers `src/` and `tools/`, which this branch does not
   touch. Ruff clean.
4. Benchlab's suite green, ruff clean.
5. `uv run lab --no-open` in DeePC serves the same page; the browser test drives it.
6. `/code-review` on both diffs; said in both PRs.
7. Cost, measured and stated: wall time of `uv run deepc run system` before and after, and each
   suite's time.

**Cost:** Benchlab gains about 4,500 lines moved plus about 400 new (project finder, packaging,
rules, tests). DeePC loses about 4,486 lines and changes about 40. Run time: none added, beyond
what is measured in step 7.
