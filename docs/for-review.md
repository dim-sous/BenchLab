# For your review: Benchlab's branches 2b to 2e

You asked, on 2026-11-14, for branches 2b to 2e built straight through, each planned, tested,
reviewed and driven by Claude, then one walkthrough of everything and one list from you. This file
is the list's other half: every choice your design (`docs/design.md`) and your mockup left open,
made by Claude, with its reason. Each is easy to change; say which.

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
