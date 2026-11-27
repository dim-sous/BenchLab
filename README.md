# RunLab

A bench for Python projects that run experiments. A project writes its **pieces**. Each piece
has its settings, a `run(settings) -> record`, and a record that says what it can draw. RunLab
provides everything else: the settings checked and grouped, each run saved as one JSON file,
charts drawn from the runs, a command line, and **the Lab**, a local web page where runs are
started, compared and charted.

A project installs RunLab the way it installs numpy. It uses only what
[What a project may use](#what-a-project-may-use) lists, and that list holds until 2.0.

## What it does

- **Settings.** A piece's `Config` is a [`param`](https://param.holoviz.org) class. Each setting
  sits under a group, and a wrong value is refused with a message saying why. A setting can
  depend on another (it applies only while that one holds a named value), hold a table of rows,
  or hold another piece's whole settings.
- **Run files.** Each run is saved as one JSON file and loads back bit for bit. It records what
  produced it: the project's commit, the versions of the libraries the project names, and
  RunLab's own version. A run saved by an older RunLab, or saved before its piece's `Record`
  changed, still loads.
- **Charts.** What a record declares is drawn two ways: as a PNG still with a JSON sidecar, and
  as a live chart in the Lab. Several runs can be overlaid, given a row each, or pooled by their
  mean or RMS, and a summary number can be drawn against a setting. A piece can also supply a
  plotly figure it draws itself.
- **A command line.** `run`, `draw` and `settings`, under the project's own command name. It
  makes the same run files as the Lab.
- **The Lab.** One local page: tick, filter and compare the runs, see their charts as cards, and
  start new runs from a form. Each run is its own process, and no more run at once than the
  machine has cores.
- **Re-fly.** A saved run is flown again from its own settings and seed, to check that it comes
  back the same.
- **A check.** `check_project` runs as one test in the project's own suite and tells it whether
  its pieces plug in.

## Install

RunLab is installed from GitHub with [uv](https://docs.astral.sh/uv/) and needs Python 3.13.
In the project's `pyproject.toml`:

```toml
[project]
dependencies = ["runlab>=1,<2"]

[project.scripts]
demo = "runlab.cli:main"     # the project's command, any name it likes
lab = "runlab.lab:main"      # the Lab

[project.entry-points.runlab]
project = "demo"             # the module that declares the project (see Quickstart)

[tool.uv.sources]
runlab = { git = "https://github.com/dim-sous/RunLab", branch = "main" }

[build-system]               # without it uv does not install the project, and its commands do not exist
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

then `uv sync`. The project's `uv.lock` pins the exact commit, and
`uv lock --upgrade-package runlab` moves it to the latest one. uv does not hold a git source to
the version range (uv 0.11.32 locks 1.17.0 under `runlab>=2,<3`), so the range states the
promise and the lock file does the pinning.

## Quickstart

A project of one piece, `sine`, in a package `demo` under `src/`.

**The piece**, `src/demo/sine.py`: its settings, its record and its run.

```python
import dataclasses
import time

import numpy as np
import param

from runlab import TIME, Number, Provenance, Series, Settings, stamp
from runlab import Record as _Record


class Config(Settings):
    amplitude = param.Number(1.0, bounds=(0.0, None), label="A", doc="The wave's amplitude.",
                             metadata={"group": "Wave"})
    frequency = param.Number(2.0, bounds=(0.0, None), label="f", doc="Cycles per second.",
                             metadata={"group": "Wave", "unit": "Hz"})


@dataclasses.dataclass(frozen=True)
class Record(_Record):
    name: str
    config: Config
    provenance: Provenance | None
    t: np.ndarray
    y: np.ndarray
    numbers: dict

    component = "sine"                     # the piece's name in the declaration
    label = "Sine"                         # its name on the page
    produced_by = "uv run demo run sine"   # the command that makes one

    def series(self):
        return (Series(name="y", x=self.t, x_quantity=TIME, y_label="y [-]",
                       traces=(("y", self.y),)),)

    def number_specs(self):
        return (Number("rms", "RMS of y"),)


def run(cfg: Config) -> Record:
    started = time.perf_counter()
    t = np.linspace(0.0, 1.0, 200)
    y = cfg.amplitude * np.sin(2 * np.pi * cfg.frequency * t)
    return Record(name="default", config=cfg, provenance=stamp(time.perf_counter() - started),
                  t=t, y=y, numbers={"rms": float(np.sqrt(np.mean(y ** 2)))})
```

**The declaration**, `src/demo/__init__.py`, the module the entry point names:

```python
from importlib import import_module
from pathlib import Path

NAMES = ("sine",)                           # the pieces, in the order every surface shows them
COMMAND = "demo"                            # the command pyproject.toml installs
TITLE = "Demo Lab"                          # the Lab's title
ROOT = Path(__file__).resolve().parents[2]  # the repository whose commit stamps a run
LIBRARIES = ("numpy",)                      # the libraries whose versions a run keeps


def get_component(name):
    if name not in NAMES:
        raise KeyError(f"unknown piece {name!r}; registered: {list(NAMES)}")
    return import_module(f".{name}", __name__)
```

**Run it:**

```bash
uv run demo run sine                                      # writes results/sine/default.json
uv run demo run sine --sweep amplitude=1,2,4              # one run per value
uv run demo run sine --set frequency=5 --name fast        # one setting changed
uv run demo settings sine                                 # every setting: group, unit, default, bounds
uv run demo draw results/sine/*.json                      # the charts, as PNG stills
uv run demo draw results/sine/*.json --number rms --vs amplitude
uv run demo run sine --refly results/sine/default.json    # fly a saved run again; exit 3 if it differs
uv run lab                                                # the Lab, in the browser
```

**Check that it plugs in**, with one test in the project's own suite:

```python
from runlab.cli import main
from runlab.testing import check_project

def test_the_pieces_plug_into_the_bench(tmp_path):
    main(["run", "sine", "--name", "one", "--out-dir", str(tmp_path)])
    check_project(runs=[tmp_path / "sine" / "one.json"])
```

## What a project may use

A project uses what this section lists and nothing deeper. **From 1.0 until 2.0, nothing listed
here is removed, renamed or changed in meaning; things may be added.** Everything else in RunLab
may change in any version. `tests/test_shore.py` holds the list, and `check_project` refuses a
project file that imports more of RunLab than this.

### The names `runlab` holds

Imported as `from runlab import Settings, Record`:

| name | what it is |
|---|---|
| `Settings` | the base class of a piece's `Config` |
| `with_overrides` | `with_overrides(config, [(setting, value), ...])`: a new `Config` with those settings changed (a built one never changes) |
| `Record` | the base class of a piece's record, a frozen dataclass |
| `Series` | one chart a record declares: lines against an axis |
| `Figure` | a plotly figure a record draws itself |
| `Number` | the words and unit of one summary number |
| `Message` | something a run says in words about how it ended |
| `Quantity` | a quantity named once, `Quantity(key, name, symbol, unit)`, from which a chart's axes, title and legend are written |
| `TIME` | time in seconds, a `Quantity` ("Time [s]", "t [s]") |
| `Role` | what a line is: `TRUTH`, `ESTIMATE`, `MEASURED`, `ESTIMATION_ERROR`, `MEASUREMENT_ERROR`, `SETPOINT`, `APPLIED` |
| `bound_refs` | reference lines at a quantity's bounds: `bound_refs(bounds, quantity)`, or `bound_refs(bounds, words, unit)` ("Lower bound of state of charge [-]") |
| `ci` | a band named as a confidence interval: `ci(of, level=95)` ("Estimate 95% CI") |
| `Provenance`, `stamp` | what produced a run; `stamp(duration_s)` makes one |

### The declaration

An entry point in the group `runlab` names one module of the project, which holds:

| name | what it is |
|---|---|
| `NAMES` | the pieces, in the order every surface shows them |
| `get_component` | `get_component(name)`: a piece's module |
| `COMMAND` | the command the project's `pyproject.toml` installs |
| `TITLE` | the Lab's title |
| `ROOT` | the repository whose commit stamps a run |
| `LIBRARIES` | the libraries whose versions a run keeps |
| `WORDS` | optional: the project's words file, if it changes a word of the page (below) |
| `OUT_DIR` | optional: the folder under `ROOT` that runs are written to when no `--out-dir` is given; `results` if left out |

RunLab refuses, saying why, an environment where no project declares itself, where two do, or
where the module lacks one of the required names. A run's provenance keeps the commit of `ROOT`,
the versions of `LIBRARIES`, then RunLab's own version.

### A piece

A module holding three names:

- `Config`, a `Settings`: the piece's settings.
- `run`, `run(config) -> record`.
- `Record`, a frozen dataclass on RunLab's `Record`. Its fields are what a run keeps; `name`,
  `config` and `provenance` among them, and `numbers`, a dict of summary numbers, if it has any.
  Its class attributes: `component`, the piece's name in `NAMES`; `label`, its name on the page;
  `produced_by`, the command that makes one; optionally `group`, the heading the page lists the
  piece under (once one piece names one, every piece is listed under a heading); and `provides`,
  a tuple of names every run of the piece carries, which a setting's `record_of` may ask for
  instead of a piece.

A record says what it can show through four methods, each returning a tuple:

- `series()`, its charts, each a `Series` (below);
- `figures()`, its own plotly figures, each a `Figure`: drawn from the record's fields when
  shown, never kept in the run file. A figure that holds plotly frames plays, shown on its card as
  plotly's own page; `script` is JavaScript that page runs once the plot is made (`{plot_id}` in
  it is the plot's element);
- `number_specs()`, the words of each entry of `numbers`, each a `Number` (below);
- `messages()`, each a `Message(title, text)`: how the run ended, said from the record's fields
  when shown and never kept in its file. The page lists "Messages" beside the charts when a shown
  run says any. No chart or figure may be named `messages`.

### A setting

A `param` parameter on a `Settings`. RunLab reads and writes six kinds itself: a whole number, a
number, yes/no, text, a choice and a list. Three more shapes:

- **A table**: a `param.List` whose `item_type` is a `Settings` of its own. Each row has its own
  settings, the form shows a table, the run file saves a list of rows, and one cell is set from
  the command line by its path, rows numbered from 0: `--set segments.1.power_kw=20`. With
  `by_name`, a row is addressed by the value of one of its settings instead:
  `--set transition.cv.ca=0.05` sets the row called `cv`, and adds it if the list has none.
- **A part**: a `param.ClassSelector` whose `class_` is another piece's `Config`. Its settings
  become settings of this piece, by dotted name (`--set mount.gain=2`), on every surface: the
  form shows them under "<part> · <group>", a sweep and the compare table take them, and a run
  file holds the part as the dict of its settings. `composes` names the groups of it that apply;
  a value set in another of its groups is refused.
- **Any other kind `param` offers** (a matrix, a date, a pair): typed as the text `param` reads
  (`[[1, 2], [3, 4]]`, `2026-02-03`), saved as `param` writes it, and loaded as the real thing.
  **Not promised**: no project has used one yet, so it may still change.

A default of `None` stands for the code's own default: the piece resolves it when it runs. A
setting's `metadata` carries `group` (required) and any of:

| key | what it does |
|---|---|
| `group` | the heading the form puts the setting under |
| `unit` | the unit the setting is typed in |
| `lines` | each choice's own line of description, `{choice: words}` |
| `needs` | when the setting applies: `{other: {"in": [values]}}`; a value set while it does not apply is refused |
| `replicate` | `True` on a setting that only re-draws the noise (a seed) |
| `draws` | on a replicate, the setting that counts the draws a run makes from it |
| `record_of` | on a path setting, the piece whose saved run it names, or a name in `provides`: then a run of any piece that provides it |
| `folded` | the form shows the setting's group closed until it is opened |
| `rows` | on a list, the form's words for each row and for its add button |
| `composes` | on a part, the groups of it that apply |
| `by_name` | on a table, the row setting a row is called by |
| `default_from` | an empty setting is looked up off another setting's value; the form shows what it will run as. On a table called by name, the rows registered for that value |
| `stands_for` | on a choice, `{option: {setting: value}}`: an option that stands for a set of settings, which the form's Use opens |
| `replaces` | on a `record_of` setting, the field of the picked run listing the settings it sets instead; the form shows them once it is picked |
| `row_words` | on a table called by name, the words the form shows each row by |

`runlab/record/config.py` says each in full.

### A chart

A `Series(name, x, x_label, y_label, traces=((label, values), ...))` draws lines of one unit
against one axis. Beyond its traces it may declare:

| field | what it does |
|---|---|
| `refs`, `bands` | reference lines `(label, value)` and bands `(label, lo, hi)`; either may name the trace it belongs to as a last element, and wears that trace's colour |
| `quantity`, `x_quantity` | the `Quantity` along each axis, which then writes the axis label ("word [unit]") and the title; a trace's label may be a quantity too. The words follow the page's Names / Symbols switch |
| `pooled` | the statistics its traces may be pooled by across runs, `("mean", "rms")` |
| `averaged`, `mean_band` | how many independent draws each trace is a mean of, and `mean_band(n) -> (label, lo, hi)`, the band of a mean of `n` draws (or several, each naming its trace). Runs that differ only in their seed, pooled by their mean, are weighted by their draws and drawn inside the band of all of them |
| `x_log`, `y_log` | a logarithmic axis |
| `points` | each sample a dot, for samples that are events |
| `split` | a row per run, for a chart of one run |
| `stacked` | the traces are shares of one whole, drawn as stacked areas |
| `rows` | stacked axes over one abscissa, each row a `Series` of its own |
| `colours` | one `"#rrggbb"` per trace, kept on every chart, each run a shade of it |
| `cold_start_end` | where the run's cold start ends: the chart is drawn from there unless its card's Cold start switch is on |
| `equal_aspect`, `rings`, `marks` | a chart of a plane: one unit along each axis, circles about the origin `(label, radius)`, named places `(label, x, y)` |
| `trace_x` | each trace's own abscissa: a cloud of dots |
| `group`, `title`, `doc` | the heading it is listed under, its words, its description |

A line, reference line or band may be named by what it is: a `Role`, a `bound_refs`, or a `ci`.

### A number

A `Number` gives the words of one entry of `numbers`: written in full, `Number("rms", "RMS of
y")`, or made from a quantity and a statistic, `Number("soc", quantity=SOC, statistic="final")`
("Final state of charge"). The statistics are `final`, `initial`, `max`, `min`, `mean`, `std`,
`rmse` and `snr`, and the shares `share_of_steps` and `share_of_time` of a `condition` the number
names ("Share of steps clipped"). `headline=True` shows it first; `reference_of` names the number
this one is the published value of, and a sweep of that number draws this one beside it, dashed.

### The words

RunLab holds every word its page writes (`runlab/lab/words.toml`). A project that wants a word
different lists it, and only it, in a TOML file of its own named as `WORDS`: one table per part
of the page, `[strip] cap = "up to {n} side by side"`; a word that counts has a `.one` and a
`.many`. Every word it leaves out stays RunLab's. A slot's name is not promised: an entry RunLab
cannot use is left out, and the Lab says so once in its terminal; it is never refused.

### The two commands

`runlab.cli:main` and `runlab.lab:main`, as the project's `pyproject.toml` names them. The
project's tests may call `main` of either.

### The run file

A run saved by an earlier version, or before its piece's `Record` changed, is still listed,
compared and drawn (see [below](#when-a-pieces-record-changes)).

### A run's files (not yet promised)

Inside `run`, `run_files()` gives the folder of the run in progress, where the piece writes what
it likes (a trained network, a checkpoint). It is kept as `<name>.files/` beside the run file,
which lists each file's name and size. `files_of(path)` gives the folder of a saved run, for a
later run that a `record_of` setting points at it. These are not yet promised: they may change
until a project has used them.

### The check

`runlab.testing`, holding `check_project`. It refuses, naming the piece or file and the cause:

- an incomplete declaration;
- a piece without `Config`, `run` and `Record`, or whose defaults do not build;
- settings that do not build the Lab's form, a form that does not draw as the page draws it, or
  a pick of the piece that the browser would refuse;
- a run that does not load, a chart that does not draw, a figure plotly does not accept,
  messages it cannot say, or a file its run wrote that is missing or not the size listed;
- a Python file of the project that imports more of RunLab than this section lists.

RunLab runs no piece itself: only the project knows settings that run quickly, so it passes in
runs its own command made.

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

## Working on RunLab and a project together

While both are changed on one computer, the project points at the local copy instead,
`runlab = { path = "../RunLab", editable = true }`, and that line is never committed. uv writes
the path into the project's `uv.lock` too: after switching back to the git source, run `uv lock`
before committing, and check that `git diff uv.lock` holds no `../RunLab`.

## Developing RunLab

```bash
uv sync
uv run playwright install chromium     # once per computer, for the browser test
uv run pytest
uv run ruff check .
```

The suite runs on a made-up project of three pieces (`tests/toy/`) that uses only what a project
may. It builds the Lab's page and drives it both without a browser and in one.
`tests/runs/` holds a run from every release, made by that release's own code, and
`tests/test_old_runs.py` reads and draws each.

## Versions

Each release is a git tag (`v1.17.0`) with a GitHub release whose notes list the pull requests
merged since the tag before it. Until 1.0, RunLab was
installed as `benchlab`. A project on an earlier version moves by changing that name to `runlab`
in its dependency line, its imports, its two commands and its entry-point group; every run it
saved still reads.

## Licence

MIT (`LICENSE`).
