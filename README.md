# RunLab

**Named Benchlab until 0.10.** The package a project imports is `runlab`. Until 1.0 two things
keep the old name, so that a project written for Benchlab needs no change: the name it is
installed by (`benchlab`, in a project's `dependencies` and its `uv` source), and `benchlab`
itself, which still imports and hands over to `runlab` (`from benchlab import Settings`,
`benchlab.cli:main`, `benchlab.lab:main`, `benchlab.testing`), as does a declaration made in the
entry-point group `benchlab`.

The bench every project shares. A project brings its pieces: for each one its settings, its
`run(settings) -> record`, and what the record keeps and can draw. RunLab brings the rest:

| package | holds |
|---|---|
| `runlab/record/` | the settings layer (`Settings` on `param`: every setting with a group, refused in words when wrong, `needs` for a setting that applies only while another holds a named value, `None` for the code's own default, `record_of` for a setting naming another piece's saved run) and the run file (`Record`, saved as one JSON and loaded back bit for bit; `Series` and `Number`, the charts and numbers a record declares; `Figure`, a plotly figure the record draws itself from its own fields, for what lines against an axis cannot say; `Provenance`, what produced it) |
| `runlab/figure/` | one panel spec built from what the records declare, drawn two ways: a PNG still with a JSON sidecar, and the Lab's live chart; asked, the numbers on it as a CSV beside the still. Runs overlaid, a row each, or pooled by their mean or RMS; a summary number against a setting. A figure a piece draws itself is passed through to the page as the piece drew it, on the card's paper |
| `runlab/runner.py` | one run of a piece: its Config (the one given, else the defaults) with the settings given, run, named and saved; what a sweep makes. The side door and the Lab both run it, so the same settings make the same file |
| `runlab/cli/` | the project's command, the side door: `<command> run <piece>` (settings from a file, `--set`, `--sweep`; one record per run) and `<command> draw <record>…` (the panels as stills, or `--number N --vs SETTING`), and `<command> settings <piece>` (every setting under its group: its variable, its name, unit, default, choices and description) |
| `runlab/lab/` | the Lab: one local page on Panel over the records -- the runs to tick, filter and compare, their charts as cards, the form that starts runs. A card's Save writes its picture as the card shows it, in a folder beside the runs named after them, and the folders it wrote are listed under the compare table. Each run is its own process (`python -m runlab.runner`), never more at once than the machine has cores, shown in the runs in progress along the bottom with a Stop each; the Lab never goes through the command line and computes nothing itself |
| `runlab/project.py` | the one door to the project: the declaration below, found once and checked |
| `runlab/testing.py` | the check a project calls from one test of its own: that what it declares is what RunLab reads |

It began as DeePC's bench, moved here unchanged but for what tied it to DeePC (v0.1.0); the
page its developer designed is being built on it, a branch at a time (runs in progress first,
v0.2.0; no hovers, v0.3.0; words as slots, v0.4.0). From 2026-11-15 it is being rebuilt to be
used the way numpy is (what a project may use, named and promised, v0.5.0; the page's words
held here, v0.6.0; a piece's own figures, v0.7.0).

## How a project declares itself

In the module that holds the project's registry (DeePC's `devkit/harness/__init__.py`), beside
`NAMES` (its pieces, in the order every surface shows them) and `get_component(name)` (a piece's
module, holding `Config`, `run` and `Record`):

```python
COMMAND = "deepc"                                       # the command its pyproject.toml installs
TITLE = "DeePC Lab"                                     # the Lab's title
ROOT = Path(__file__).resolve().parent.parent.parent    # the repository whose commit stamps a record
LIBRARIES = ("numpy", "scipy", "cvxpy", "osqp", "scs")  # the libraries whose versions a record keeps
WORDS = Path(__file__).with_name("words.toml")          # only if it changes a word of the Lab's page
```

and in its `pyproject.toml`, RunLab by a range, the two commands, and the entry point that
names that module:

```toml
[project]
dependencies = ["benchlab>=0.5,<1", ...]      # the install name, until 1.0

[project.scripts]
deepc = "runlab.cli:main"
lab = "runlab.lab:main"

[project.entry-points.runlab]
project = "harness"

[tool.uv.sources]
benchlab = { git = "https://github.com/dim-sous/BenchLab", branch = "main" }
```

then `uv sync`. The project's `uv.lock` holds the exact commit, and `uv lock --upgrade-package
benchlab` raises it, as for any other library. The range is the promise of "What a project may
use", written down: uv 0.10.10 does not hold a git source to it (measured 2026-11-16: a commit at
version 0.4.0 resolved under `>=0.5,<1`), so the lock file does the pinning. RunLab refuses, in words, an environment where no project
declares itself, where two do, or where the module lacks one of these names (`WORDS` it may
leave out). A record's provenance keeps the commit of `ROOT`, the versions of `LIBRARIES`, then
RunLab's own version.

RunLab holds every word its page writes itself (`runlab/lab/words.toml`, a word for each slot
`runlab/lab/words.py` names). A project that wants a word different lists it, and only it, in a
words file of its own and names that file as `WORDS`: TOML, one table per part of the page,
`[strip] cap = "up to {n} side by side"`; a word that counts has a `.one` and a `.many`. Every
slot it leaves out keeps RunLab's word, and a project with no words file gets them all.
Nothing in that file stops the Lab: an entry RunLab cannot use (it names no slot, or writes a
field its slot does not offer) is left out, the page keeps RunLab's word, and the Lab says so
once in its terminal.

While RunLab and a project are worked on together on one computer, the project points at the
local copy instead, `runlab = { path = "../BenchLab", editable = true }`, and that line is never
committed. `uv` writes the path into the project's `uv.lock` as well: after switching back to the
git source, run `uv lock` before committing, and `git diff uv.lock` holds no `../BenchLab`.

## What a project may use

A project uses RunLab the way it uses numpy: it touches what is listed here and nothing deeper.
**From 0.5 until 1.0 nothing on this list is removed, renamed or changed in meaning; things may be
added.** Everything else in RunLab is its own and may change in any version.
`tests/test_shore.py` holds the list, and the made-up project the suite runs on uses nothing else.

| | what a project may use |
|---|---|
| the names `runlab` holds | `Settings`, `with_overrides`, `Record`, `Series`, `Quantity`, `Figure`, `Number`, `Provenance`, `stamp`, `bound_refs`, as `from runlab import Settings, Record` |
| a setting | a `param` parameter on a `Settings`, of any kind `param` offers: a whole number, a number, yes/no, text, a choice and a list are read and written by RunLab; any other (a matrix, a date, a pair, a table) is typed as the text `param` reads (`[[1, 2], [3, 4]]`, `2026-02-03`), saved as `param` writes it and loaded as the real thing (from 0.9). A list of rows, a table, is a `param.List` whose `item_type` is a `Settings` of its own (from 0.13): each row its own settings, shown as a table on the form, saved as a list of rows, and one cell of one row set from the command line by its path (`--set segments.1.power_kw=20`, the rows numbered from 0). Its `metadata` carries `group` (required) and any of `unit`, `lines`, `needs`, `replicate`, `draws`, `record_of`, `folded`, `rows` (`runlab/record/config.py` says what each is) |
| a piece | a module holding `Config` (a `Settings`), `run` (`run(config) -> record`) and `Record` (a frozen dataclass on RunLab's `Record`, its `component` the piece's registered name). The record declares what it can draw: `series()`, its charts, lines against an axis; and `figures()`, the plotly figures it draws itself, each a `Figure`. A chart whose traces are each a mean of several independent draws (a statistic averaged over a run's seeds) may say how many, `averaged`, and give the band of a mean of `n` draws, `mean_band(n) -> (label, lo, hi)` (from 0.14): runs that differ in their seed alone, pooled by their mean, are then weighted by their draws and drawn inside the band of all of them. The band's formula is the piece's own. A chart may name the `Quantity` it draws (`quantity`), the one along its bottom axis (`x_quantity`), and a line may be one (from 0.22): a quantity is named once, `Quantity(key, name, symbol, unit)`, and the chart's title, axes and legend are then made from it, by name or by symbol as the page's Names / Symbols switch says; an axis reads "word [unit]", "word [-]" with no unit. A chart that names a quantity for an axis writes no label for it; a title written in full stays |
| the declaration | the entry point in the group `runlab`, and the module it names, holding `NAMES`, `get_component`, `COMMAND`, `TITLE`, `ROOT` and `LIBRARIES`, and `WORDS` if it changes a word |
| the words | a words file naming the words of the page the project changes, by the slots of `runlab/lab/words.toml`. A slot's name is not promised: an entry RunLab cannot use is left out and said, never refused |
| the two commands | `runlab.cli:main` and `runlab.lab:main`, as the project's `pyproject.toml` names them; its tests may call `main` of either |
| the run file | a run saved by an earlier version, or before its piece's `Record` changed, is still listed, compared and drawn (from 0.11; "When a piece's `Record` changes", below) |
| a run's files, **not yet promised** | from 0.8, and still open to change until a project has used them: inside `run`, `run_files()` gives the folder of the run in progress, where the piece writes what it likes (a trained network, a checkpoint), kept as `<name>.files/` beside the run file, which lists each file's name and size; `files_of(path)` gives the folder of a saved run, for a later run that a setting (`record_of`) points at it |
| the check | `runlab.testing`, holding `check_project` |

A project checks that it plugs in from one test of its own, on runs it made through its own
command (RunLab runs no piece itself: only the project knows settings that run quickly):

```python
from runlab.cli import main
from runlab.testing import check_project

def test_the_pieces_plug_into_the_bench(tmp_path):
    main(["run", "wave", "--name", "one", "--out-dir", str(tmp_path)])
    check_project(runs=[tmp_path / "wave" / "one.json"])
```

`check_project` refuses, naming the piece or the file and the cause: an incomplete declaration; a
piece that does not hold `Config`, `run` and `Record`, or whose defaults do not build; settings
that do not build the Lab's form; a run that
does not load, declares a chart that does not draw, or a figure of its own plotly does not take,
or lists a file its run wrote that is not in its folder at the size listed;
and a Python file of the project that
imports more of RunLab than this list.

### When a piece's `Record` changes

Runs saved before the change stay listed, compared and drawn; under each, the list says how its
file differs.

- A field the piece stops reading stays in the file. The run is shown whole.
- A field added later is given a default in the `Record` (`limits: np.ndarray | None = None`),
  and `series()` says what it draws without it. The older runs then draw everything else, and a
  chart they do not declare names them as left out.
- With no default, the field is no value for an older run: the first chart that reads it
  stops, and the page leaves that run out of the piece's charts, naming the field. No run is
  made again: add the default and the older runs draw.
- A setting added later is read as its default for an older run, and the list says so.

`tests/runs/` holds a run of the made-up project from every release, made by that release's own
code, and `tests/test_old_runs.py` lists, reads and draws each.

## Working on RunLab

```
uv sync
uv run playwright install chromium     # once per computer, for the browser test
uv run pytest                          # the suite, on a made-up project of three pieces (tests/toy/)
uv run ruff check .
```

The suite builds the Lab's page and drives it without a browser (`tests/test_lab.py`,
`tests/test_lab_view.py`) and in one (`tests/test_lab_browser.py`), on the made-up project, which
uses of RunLab only what a project may. A project's own suite checks one thing, that its
pieces plug in (`runlab.testing`, above), and reads nothing deeper.

## Licence

MIT (`LICENSE`), as DeePC-Sandbox, whose bench this was.
