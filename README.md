# Benchlab

The bench every project shares. A project brings its pieces: for each one its settings, its
`run(settings) -> record`, and what the record keeps and can draw. Benchlab brings the rest:

| package | holds |
|---|---|
| `benchlab/record/` | the settings layer (`Settings` on `param`: every setting with a group, refused in words when wrong, `needs` for a setting that applies only while another holds a named value, `None` for the code's own default, `record_of` for a setting naming another piece's saved run) and the run file (`Record`, saved as one JSON and loaded back bit for bit; `Series` and `Number`, the charts and numbers a record declares; `Provenance`, what produced it) |
| `benchlab/figure/` | one panel spec built from what the records declare, drawn two ways: a PNG still with a JSON sidecar, and the Lab's live chart. Runs overlaid, a row each, or pooled by their mean or RMS; a summary number against a setting |
| `benchlab/runner.py` | one run of a piece: its Config (the one given, else the defaults) with the settings given, run, named and saved; what a sweep makes. The side door and the Lab both run it, so the same settings make the same file |
| `benchlab/cli/` | the project's command, the side door: `<command> run <piece>` (settings from a file, `--set`, `--sweep`; one record per run) and `<command> draw <record>…` (the panels as stills, or `--number N --vs SETTING`) |
| `benchlab/lab/` | the Lab: one local page on Panel over the records -- the runs to tick, filter and compare, their charts as cards, the form that starts runs. Each run is its own process (`python -m benchlab.runner`), never more at once than the machine has cores, shown in the runs in progress along the bottom with a Stop each; the Lab never goes through the command line and computes nothing itself |
| `benchlab/project.py` | the one door to the project: the declaration below, found once and checked |
| `benchlab/testing.py` | the check a project calls from one test of its own: that what it declares is what Benchlab reads |

It began as DeePC's bench, moved here unchanged but for what tied it to DeePC
(`docs/plan-branch-1.md`, v0.1.0); the page its developer designed is being built on it, a branch at a time
(`docs/design.md` §8: runs in progress first, `docs/plan-branch-2a.md`, v0.2.0; no hovers,
`docs/plan-branch-2b.md`, v0.3.0; words as slots, `docs/plan-branch-2c.md`, v0.4.0). From
2026-11-15 it is being rebuilt to be used the way numpy is (`docs/design.md` §10: what a project
may use, named and promised, `docs/plan-branch-R1.md`, v0.5.0).

## How a project declares itself

In the module that holds the project's registry (DeePC's `devkit/harness/__init__.py`), beside
`NAMES` (its pieces, in the order every surface shows them) and `get_component(name)` (a piece's
module, holding `Config`, `run` and `Record`):

```python
COMMAND = "deepc"                                       # the command its pyproject.toml installs
TITLE = "DeePC Lab"                                     # the Lab's title
ROOT = Path(__file__).resolve().parent.parent.parent    # the repository whose commit stamps a record
LIBRARIES = ("numpy", "scipy", "cvxpy", "osqp", "scs")  # the libraries whose versions a record keeps
WORDS = Path(__file__).with_name("words.toml")          # every word the Lab's page writes itself
```

and in its `pyproject.toml`, Benchlab by a range, the two commands, and the entry point that
names that module:

```toml
[project]
dependencies = ["benchlab>=0.5,<1", ...]

[project.scripts]
deepc = "benchlab.cli:main"
lab = "benchlab.lab:main"

[project.entry-points.benchlab]
project = "harness"

[tool.uv.sources]
benchlab = { git = "https://github.com/dim-sous/BenchLab", branch = "main" }
```

then `uv sync`. The project's `uv.lock` holds the exact commit, and `uv lock --upgrade-package
benchlab` raises it, as for any other library. The range is the promise of "What a project may
use", written down: uv 0.10.10 does not hold a git source to it (measured 2026-11-16: a commit at
version 0.4.0 resolved under `>=0.5,<1`), so the lock file does the pinning. Benchlab refuses, in words, an environment where no project declares itself, where
two do, or where the module lacks one of these names. A record's provenance keeps the commit of
`ROOT`, the versions of `LIBRARIES`, then Benchlab's own version.

The words file fills every slot Benchlab names for its page (`benchlab/lab/words.py`): TOML, one
table per part of the page, `[strip] cap = "up to {n} side by side"`; a word that counts has a
`.one` and a `.many`. The Lab will not start on a file that leaves a slot empty, names one
Benchlab does not have, or writes a field a slot does not offer, and names each. The made-up
project's, `tests/toy/words.toml`, holds every slot.

While Benchlab and a project are worked on together on one computer, the project points at the
local copy instead, `benchlab = { path = "../BenchLab", editable = true }`, and that line is never
committed. `uv` writes the path into the project's `uv.lock` as well: after switching back to the
git source, run `uv lock` before committing, and `git diff uv.lock` holds no `../BenchLab`.

## What a project may use

A project uses Benchlab the way it uses numpy: it touches what is listed here and nothing deeper.
**From 0.5 until 1.0 nothing on this list is removed, renamed or changed in meaning; things may be
added.** Everything else in Benchlab is its own and may change in any version.
`tests/test_shore.py` holds the list, and the made-up project the suite runs on uses nothing else.

| | what a project may use |
|---|---|
| the names `benchlab` holds | `Settings`, `with_overrides`, `Record`, `Series`, `Number`, `Provenance`, `stamp`, `bound_refs`, as `from benchlab import Settings, Record` |
| a setting | a `param` parameter on a `Settings`, its `metadata` carrying `group` (required) and any of `unit`, `lines`, `needs`, `replicate`, `draws`, `record_of`, `folded`, `rows` (`benchlab/record/config.py` says what each is) |
| a piece | a module holding `Config` (a `Settings`), `run` (`run(config) -> record`) and `Record` (a frozen dataclass on Benchlab's `Record`, its `component` the piece's registered name) |
| the declaration | the entry point in the group `benchlab`, and the module it names, holding `NAMES`, `get_component`, `COMMAND`, `TITLE`, `ROOT`, `LIBRARIES` and `WORDS` |
| the two commands | `benchlab.cli:main` and `benchlab.lab:main`, as the project's `pyproject.toml` names them; its tests may call `main` of either |
| the run file | a run saved by an earlier version is still listed and drawn |
| the check | `benchlab.testing`, holding `check_project` |

A project checks that it plugs in from one test of its own, on runs it made through its own
command (Benchlab runs no piece itself: only the project knows settings that run quickly):

```python
from benchlab.cli import main
from benchlab.testing import check_project

def test_the_pieces_plug_into_the_bench(tmp_path):
    main(["run", "wave", "--name", "one", "--out-dir", str(tmp_path)])
    check_project(runs=[tmp_path / "wave" / "one.json"])
```

`check_project` refuses, naming the piece or the file and the cause: an incomplete declaration; a
piece that does not hold `Config`, `run` and `Record`, or whose defaults do not build; settings
that do not build the Lab's form; a words file that does not fill the page's slots; a run that
does not load, or declares a chart that does not draw; and a Python file of the project that
imports more of Benchlab than this list.

## Working on Benchlab

```
uv sync
uv run playwright install chromium     # once per computer, for the browser test
uv run pytest                          # the suite, on a made-up project of two pieces (tests/toy/)
uv run ruff check .
```

The suite builds the Lab's page and drives it without a browser (`tests/test_lab.py`,
`tests/test_lab_view.py`) and in one (`tests/test_lab_browser.py`), on the made-up project, which
uses of Benchlab only what a project may. A project's own suite checks one thing, that its
pieces plug in (`benchlab.testing`, above), and reads nothing deeper.

## Licence

MIT (`LICENSE`), as DeePC-Sandbox, whose bench this was.
