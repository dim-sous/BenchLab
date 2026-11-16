# Branch R3: a piece's own figures

## Context

Today a piece can hand the page two things only: lines drawn against an axis, and numbers
(`benchlab/record/__init__.py`, `Series` and `Number`). A histogram, a heatmap, an image, or a map
of poles each needs a change inside Benchlab (`docs/design.md` §10, measured on `v0.4.0`). That
breaks the rule "a change in a project never needs a change in RunLab".

R3 opens it: a piece may hand the page any plotly figure it drew itself. The page already draws
with plotly, so this one opening covers every kind of figure plotly can make.

In instrument terms: the rack already takes every transmitter's 4-20 mA signal and draws the
trend itself. R3 adds a slot for a transmitter that brings its own display.

**The developer's four choices (2026-11-17):**
1. First user: **DeePC's System piece gets a pole map.** It already computes and saves its poles
   (`constants["poles_re"]`, `["poles_im"]`) and shows them only as numbers.
2. Several runs ticked: **one figure per run, stacked**, each under its run's name.
3. The look at other tools: **a short read of their docs** (below).
4. Saved pictures: **the page only for now**; the `draw` command says which figures it left out.

## What the short read found

MLflow's and PyTorch's TensorBoard pages, read 2026-11-17 (the MLflow part reached me as a
summary of its page, so it is less certain than the TensorBoard part, which is verbatim):

- **MLflow** takes a matplotlib or a plotly figure from a run (`mlflow.log_figure`) and stores it
  as a file of that run; its examples keep plotly as `.html`, so it stays live, and matplotlib as
  `.png`.
- **TensorBoard** takes a matplotlib figure and "render[s it] into an image": it goes flat.
- **Neither page says** anything about merging several runs' figures into one. Both hand a run's
  own figure over whole.

What R3 takes from it: a run's own figure is shown whole, one per run (choice 2 matches both
tools), and it stays live as MLflow keeps plotly. Where R3 differs from both, on purpose: they
store the **finished picture** when the run ends; R3 stores the **numbers** in the run file, as
today, and the piece draws the figure from them when it is shown. So a figure's look can be fixed
later without running again, and a run saved before a figure existed gains it. Cost: the piece's
code must still be able to read its old runs, which is already true of its line charts.

## What R3 delivers

**In Benchlab**
1. **A new name a project may use, `Figure`**, and a new method a record may have, `figures()`,
   beside today's `series()`. A `Figure` is a name, the plotly figure, a group and a title. The
   piece builds it from the record's own saved fields.
2. **The run file lists a record's figures among its charts.** No new part of the file: the same
   two lists (`panels`, `panel_groups`) carry the figures' names and groups. A run saved before
   R3 loads and draws as before.
3. **On the page**, a figure sits in the chart list in its group, like any chart, and opens a
   card. The card shows one figure per ticked run, stacked, each under its run's name. A ticked
   run that has no such figure is named in a line on the card. The card's one control (Overlay |
   Split | Mean | RMS) is greyed with its reason, since the page cannot merge a piece's own
   figure.
4. **The `draw` command** draws the line charts as today and prints one line naming the figures
   it left out. Asked for one by name, it refuses, saying the page shows it.
5. **The check a project calls** builds every figure of every run it is given and refuses one
   plotly cannot take, naming the run and the figure.
6. Version `0.7.0`.

**In DeePC (its first user)**
7. **A pole map on the System piece**: the poles as crosses on the complex plane, real part
   across, imaginary part up, both axes on one scale, a line at zero real part. Drawn from the
   poles a System run already saves, so old System runs get it too. Axis labels `Re` and `Im`,
   no units (the developer's rule for that piece), no title, no legend (one label).
   What it looks like is the developer's, settled after driving it.

## Decided by Claude, with the reason

- **The piece draws the figure when shown; the run file keeps the numbers** (above). Cost: every
  figure of a shown run is built when the run is loaded, whether or not its card is open. A pole
  map is a handful of points. A piece with heavy figures (images) would want them built only when
  opened; that is added when such a piece exists.
- **Benchlab adds nothing to a piece's figure but its card's paper and font, where the piece set
  none**, so the figure sits on the card like the others. Titles, labels and legends are the
  piece's. `CLAUDE.md`'s figure rules cannot be held by a test for a figure Benchlab did not draw.
- **A figure's name shares one list with the chart names** (the chart list, the page's address).
  A record naming a figure as one of its charts is refused when saved, naming it.
- **Plotly's own readout of a point under the cursor stays**, as on today's charts. Decision 5
  removed descriptions on hover, not that readout.
- **The made-up project's `lag` gets one figure**, written as a plain dict; a test also hands
  over one built with plotly's own classes, so both forms are held.
- **The new words are Benchlab's** (three slots in `benchlab/lab/words.toml`). No project is
  touched for them: R2's first use.

## Files

**Benchlab**
- `benchlab/record/__init__.py`: `Figure`; `Record.figures()`; `header()` lists figures; a clash
  of names refused at `save`. `benchlab/__init__.py`: `Figure` on the list.
- `benchlab/figure/own.py` (new, about 45 lines): a record's figures as plain dicts, the card's
  paper and font laid under them. Reuses `benchlab/figure/style.py` (`SURFACE`, `FONT`, `INK`).
- `benchlab/lab/app.py`: `_record_of` and `_drawable` list figures with charts; a card for a
  figure (`_own_view`, beside `_chart_view`), built with the existing `_frame` and `_toolbar`.
  `benchlab/lab/shaping.py`: the kind `own`, its control greyed. `benchlab/lab/words.toml` and
  `words.py`: three slots.
- `benchlab/cli/__init__.py` (`draw_command`), `benchlab/testing.py` (`_check_run`).
- Tests: `tests/toy/lag.py` (one figure); `tests/test_record.py`, `tests/test_figure.py`,
  `tests/test_lab_view.py`, `tests/test_lab_browser.py`, `tests/test_cli.py`,
  `tests/test_testing.py`, `tests/test_shore.py`; the import list in `tests/test_lab.py` and the
  table in `tests/test_layers.py`.
- Docs: `README.md`, `docs/design.md` §10, `CLAUDE.md`, `docs/for-review.md`,
  `.claude/memory/MEMORY.md`, `docs/plan-branch-R3.md`.

**DeePC**
- `devkit/harness/system/record.py`: `figures()` with the pole map. `tests/test_system.py`: the
  map holds exactly the saved poles. `pyproject.toml`: `benchlab>=0.7,<1`; `uv.lock` raised.
  `devkit/README.md`: one line.

## Cost, named

- Benchlab: about +170 lines of code in seven files, about +150 of tests.
- DeePC: about +25 lines of code, +15 of tests.
- Compute: both suites timed before and after; expected a few seconds more in Benchlab.
- Usage: moderate, smaller than R1. No parallel reviewers, no agent fan-out.

## Verification

- Benchlab: `uv run pytest`, `uv run ruff check .` (315 passed before).
- DeePC on the branch, through a local install: its whole suite (131 passed before).
- **The numbers do not move** (R1's method): every DeePC piece run and drawn before and after.
  Expected differences beyond provenance and wall-clock fields, stated in advance: the System
  run file's two lists gain `pole-map`. Nothing else.
- **A System run saved on `v0.6.0`** loads and shows the pole map.
- **Hand-off: a walkthrough, driven by Claude first** in DeePC's Lab: open System, open the pole
  map, read the poles against the numbers in the compare table; make a second System run with
  another system, tick both, see two maps stacked under their names; open a line chart beside
  them; switch to the closed loop and back.

## Git

Two repositories. Approving this plan is the developer's word for one git step: creating the
branch `r3-figures` in BenchLab and in DeePC (the notes of R2's merge, uncommitted on `main`,
ride onto BenchLab's). Commit, push, PRs, merges, the tag `v0.7.0` and DeePC's lock are each
asked for when reached.

## Not in R3

Saved PNGs of a piece's own figure; several runs merged into one figure by the project; figures
built only when opened; files a run writes (R4); new setting kinds (R5); the rename (R6); 2d and
2e.

---

## As built (2026-11-17; built and checked, not yet committed)

On the branch `r3-figures` in BenchLab and in DeePC, uncommitted. DeePC points at the local
Benchlab copy (`pyproject.toml`, `uv.lock`): never committed that way.

### What was built

**Benchlab**
- `benchlab.Figure` (name, figure, group, title, doc) and `Record.figures()`; `Record.header()`
  lists the figures after the charts in `panels` and `panel_groups` and refuses a name declared
  twice, at save.
- `benchlab/figure/own.py` (new, 73 lines): `own_figure(record, name)`, the piece's figure as the
  plain dict the page's pane takes.
- `benchlab/lab/app.py`: `_declared` (charts, then figures, read once with the record) and
  `_own_view`, the card. `benchlab/lab/shaping.py`: the kind `own`. Three word slots
  (`cards.own_runs`, `cards.own_without.one`, `.many`), in Benchlab's own words file alone.
- `benchlab/cli/__init__.py`: `draw` names the figures it left out and refuses one asked for by
  name. `benchlab/testing.py`: every figure of every run given is read by plotly.
- The made-up `lag` draws its pole. Version `0.7.0`.

**DeePC**
- `devkit/harness/system/record.py`: `figures()`, the pole map, from `constants["poles_re"]` and
  `["poles_im"]`. One test in `tests/test_system.py`. `pyproject.toml`: `benchlab>=0.7,<1`.
  `devkit/README.md`: one phrase.

### Departures from the plan

1. **The card's whole look is laid under a piece's figure, as a plotly template**: the paper, the
   type, the grid and zero lines, the margins, the charts' colours in order. The plan said "its
   card's paper and font". Found by driving DeePC's pole map: under plotly's stock template,
   which plotly's classes give every figure and the page's pane gives a plain dict, the grid and
   the zero lines are white, drawn for that template's grey-blue plot, and on the card's paper
   they did not show. A template fills only what a figure leaves unset, so whatever the piece
   set is kept; a template the piece chose itself is kept too; plotly's stock one makes way.
2. **`draw` says what it left out on the error stream**, so the output stream still holds only
   the paths it wrote.
3. **Each run's figure wears the piece's own colours, not the run's.** With two runs stacked, the
   dot beside a run's name is the run's colour and the crosses under it are the first chart
   colour in both. Left for the developer to judge after driving (`docs/for-review.md`).

### Measured

- **Lines.** Benchlab: code about +190, −23 (ten files, one new); tests +242, −18. DeePC: +36,
  −5 in four files.
- **Benchlab's suite:** 315 passed in 73.0 s before; 328 passed in 79.6 s after. Ruff clean.
- **DeePC's suite**, on the local copy: 131 passed in about 115 s before; 132 passed in 114.3 s.
- **The numbers did not move.** Every DeePC piece run and drawn (70 files) on a clone of its
  `master` (`3cf9542`, Benchlab 0.5.0 from its lock) and on this branch. Beyond provenance and
  the wall-clock fields two runs of one code already differ in, exactly what the plan named: the
  System run file's `panels` and `panel_groups` gain `pole-map`. No other field of it differs.
- **A System run saved on Benchlab 0.5.0** loads and draws its pole map: four poles, the
  rightmost cross equal to its `max_pole_re`.
- **DeePC's Lab, driven in headless Chromium** over a default System run and a pendulum: the
  chart list shows Frequency, Time and Poles; the pole map opens beside the Bode magnitude; its
  crosses are (−0.1, ±0.995), its axes read Re and Im, it has no title; the compare table's
  "Max pole Re", −0.1, is its rightmost cross; the card's control is greyed; with both runs
  ticked two maps stack, one under each run's name, the second holding the default system's
  four poles; back on the closed loop the page raised no error. Screenshots looked at.

### Still to do

- The developer drives it (the walkthrough is in the hand-off message), then the git steps, each
  on their word: commits; Benchlab pushed, its PR, merged, tagged `v0.7.0`; DeePC's source line
  back to Benchlab's `main`, `uv lock`, its suite, its PR, merged; branches deleted.
- Then R4, files a run writes (`docs/design.md` §10).
