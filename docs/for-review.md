# For your review: Benchlab's branches 2b to 2e

You asked, on 2026-11-14, for branches 2b to 2e built straight through, each planned, tested,
reviewed and driven by Claude, then one walkthrough of everything and one list from you. This file
is the list's other half: every choice your design (`docs/design.md`) and your mockup left open,
made by Claude, with its reason. Each is easy to change; say which.

**2026-11-15: the list closes at 2c.** 2d and 2e are on hold for a new direction
(`docs/design.md` §10), which may make some of what is below moot; 2c's strict check of the
words file (its item 5) goes with decision 4.

## 2b: no hovers (BenchLab #3, DeePC-Sandbox #19)

1. **The refusal words**, taken from the mockup: `<setting> must be at least | above | at most |
   below <bound>, got <text>` and `<setting> takes a number | a whole number | a list of numbers,
   got <text>`, in red under the setting; a sweep value's under the sweep row. A swept pick or
   yes/no reads `<setting> takes one of <its choices> | true or false, got <text>`.
2. **Text that is not a number is refused at Run too**, like a value outside its range: the same
   box, the same moment, and the run would refuse it anyway, in the strip.
3. **A greyed setting's reason is a dim line under it** (the mockup's line under the box), wrapping
   inside the box's column, so that row grows taller.
4. **A gate only some sweep values open says nothing under the setting** (its hover said "only some
   sweep values of … open it"); the note under the bar warns when such a setting is set, as before.
5. **Kept: the charts' own hovers**, as in the mockup: a point's run and value on mouse-over, and
   the chart toolbar's button names (Zoom, Pan, Zoom in, Zoom out, Reset axes), plotly's own.
6. **Hovers also gone from plain controls**, as in the mockup: Use and ✕ in the run list, All and
   None, Show all and Hide all, a card's ✕, and the divider between the panes ("drag to resize ·
   double-click to reset").
7. **Yours, recorded here:** `x0` is now `x_0` (your "standard math" answer: beside the states' x1,
   x2, …, `x0` read as a component numbered 0); every other label kept; `∠G` and the phase margin
   keep no unit (your no-units rule; a Bode phase is in degrees by convention).
8. **Yours, recorded here:** a bug older than Benchlab fixed in 2b: picking another piece now starts
   its form empty (its name and sweep boxes kept the last piece's words).
9. **A refusal in a folded group opens the group**, so its words show (the review found Run
   otherwise changed nothing on screen).

## Found on the way, not fixed (each its own branch, if you want it)

- **A browser error from plotly, now and then** ("Cannot read properties of undefined (reading
  '_guiEditing')"), in 3 of 5 tours of DeePC's page on v0.3.0: after ticking runs, opening a
  number card from the compare table and filtering the list to nothing and back, opening the runs
  in progress raised it. Nothing visible broke. Seven plain opens and closes of the form and the
  strip with two charts open raised none, so it needs that history; the 2b review met it once in a
  browser test, which passed again.

## 2c: words as slots

1. **One file of the page's own words per project**: DeePC's `devkit/harness/words.toml`, TOML,
   one table per part of the page, holding today's words; change a word there. A piece's words stay
   in its folder.
2. **The title stays where it was** (`TITLE` in `devkit/harness/__init__.py`), not in the words
   file: one change less to what a project declares.
3. **Marks are not words**: the ✕ buttons are slots, but the ▸ and ▾ arrows and the ` · ` between
   counts stay Benchlab's.
4. **A word that counts is two slots**, `.one` and `.many` (`{n} record` and `{n} records`), so
   English's plural is written by the project.
5. **The file is checked strictly**: a missing or unknown slot, a field the slot does not offer, or
   a stray brace stops `uv run lab`, naming each; a word may leave a field out ("Running" without
   its count).
6. **Not slots**: words the page shows but does not write: the figure layer's (legends, a card's
   refusal), a record's, param's and the runner's refusals. They stay those layers' own; moving
   them would be a later branch.

## R1: what a project may use (2026-11-16, not yet merged)

Built from `docs/plan-branch-R1.md`, which you approved. Nothing on the page changed. What the
plan left open, or what changed on the way, each easy to change; say which.

1. **One planned check was left out.** `check_project` does not check that Benchlab's code spells
   none of a project's piece names. Shipped to every project, it would let a piece named `label`
   or `figure` fail the project's own suite: the opposite of the rule. Benchlab's own suite keeps
   the check, on the made-up project.
2. **The range is a written promise, not an enforced one.** uv 0.10.10 does not hold a GitHub
   source to a version range: a commit at 0.4.0 resolved under `>=0.5,<1`. DeePC's `uv.lock` does
   the pinning. The range becomes enforced the day RunLab is on PyPI.
3. **The promise covers nine setting keys**, two of which no project uses yet (`lines`, `draws`).
   They were already documented for projects, so they are promised with the rest.
4. **`with_overrides` is on the list for one user**, a test of DeePC's System piece.
5. **The made-up project has a second piece, `lag`** (a first-order lag driven by a saved wave
   run), added for what the moved tests need: a setting naming another piece's run, defaults the
   code resolves, lists with a row each, a unit, constants, bounds, log axes.
6. **DeePC keeps playwright** in its development group: its hand-off skill drives the Lab in
   Chromium. It dropped panel and matplotlib, which only Benchlab imports.
7. **DeePC's `devkit/README.md` still describes Benchlab's insides** in a table (which inner
   module draws what). It will go stale when Benchlab is rebuilt inside. Claude's advice: cut it to
   a pointer at Benchlab's README, in DeePC's next branch of its own.
8. **One `except Exception` in `benchlab/testing.py` carries no `# noqa: BLE001`**: it raises
   again, naming the run and the chart, so ruff does not count it blind and refuses the marker as
   unused. `CLAUDE.md`'s "Fail loud" words say every one carries it.
