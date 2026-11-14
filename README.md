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

It began as DeePC's bench, moved here unchanged but for what tied it to DeePC
(`docs/plan-branch-1.md`, v0.1.0); the page its developer designed is being built on it, a branch at a time
(`docs/design.md` §8: runs in progress first, `docs/plan-branch-2a.md`, v0.2.0).

## How a project declares itself

In the module that holds the project's registry (DeePC's `devkit/harness/__init__.py`), beside
`NAMES` (its pieces, in the order every surface shows them) and `get_component(name)` (a piece's
module, holding `Config`, `run` and `Record`):

```python
COMMAND = "deepc"                                       # the command its pyproject.toml installs
TITLE = "DeePC Lab"                                     # the Lab's title
ROOT = Path(__file__).resolve().parent.parent.parent    # the repository whose commit stamps a record
LIBRARIES = ("numpy", "scipy", "cvxpy", "osqp", "scs")  # the libraries whose versions a record keeps
```

and in its `pyproject.toml`, Benchlab pinned at a tag, the two commands, and the entry point that
names that module:

```toml
[project]
dependencies = ["benchlab", ...]

[project.scripts]
deepc = "benchlab.cli:main"
lab = "benchlab.lab:main"

[project.entry-points.benchlab]
project = "harness"

[tool.uv.sources]
benchlab = { git = "https://github.com/dim-sous/BenchLab", tag = "v0.1.0" }
```

then `uv sync`. Benchlab refuses, in words, an environment where no project declares itself, where
two do, or where the module lacks one of these names. A record's provenance keeps the commit of
`ROOT`, the versions of `LIBRARIES`, then Benchlab's own version.

While Benchlab and a project are worked on together on one computer, the project points at the
local copy instead, `benchlab = { path = "../BenchLab", editable = true }`, and that line is never
committed. `uv` writes the path into the project's `uv.lock` as well: after switching back to the
git pin, run `uv lock` before committing, and `git diff uv.lock` holds no `../BenchLab`.

## Working on Benchlab

```
uv sync
uv run playwright install chromium     # once per computer, for the browser test
uv run pytest                          # the suite, on a made-up project of one piece (tests/toy/)
uv run ruff check .
```

The suite builds the Lab's page without a browser, and drives its runs in progress in one
(`tests/test_lab_browser.py`); the rest of the page in a browser is tested by the projects that
use it (DeePC's `tests/test_lab_browser.py`) until Benchlab's own test project is large enough to
carry it.

## Licence

MIT (`LICENSE`), as DeePC-Sandbox, whose bench this was.
