# Branch 2b: no hovers

## Context

Branch 2 builds the page the developer designed (mockup https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb,
`docs/design.md`). 2a (runs in progress) is merged and tagged `v0.2.0`. On 2026-11-14 the developer split
the old 2b in two: **2b no hovers** (this plan), then **2c words as slots**; the tree and the cards
become 2d and 2e. Decision 5 (theirs): "No hovers on settings, charts or numbers ... Greyed buttons keep
their reason on hover ... A setting's allowed range is not shown. A value outside it is refused when the
run starts, next to the setting", and labels whose meaning only the hover showed are renamed to standard
terms, the developer choosing every word, their descriptions deleted.

The developer's answers, 2026-11-14: a refused value is shown **under its setting only** (the form stays
open, nothing queued, nothing in the strip, as a taken name is refused today); the naming pass covers
**System and Open loop only** (the old Dataset and Closed loop go with DeePC's own rewrite branch 3); the
help lines are **deleted, as decided**, knowing they also document the code and fill each saved
picture's JSON note. Read with the first answer: deleted in System and Open loop, with their naming
pass; the old two pieces are left whole until the rewrite deletes them (deleting theirs now would remove
the only place W, k_max and c are explained, in pieces about to go).

## What the developer will see (and drive at hand-off)

- No hover on a setting, a chart, a number, the run list's Use and ✕, All / None, Show all / Hide all, or
  a card's ✕ (the mockup's round 2). Kept: a greyed card control's reason on its hover, and a chart's own
  data hover (a point's run and value).
- A greyed setting (behind a gate, or the sweep axis) says why in a line under it, as the mockup did,
  instead of on its hover.
- A setting's range is not shown. Run with a value outside it, or text that is not a number: the words
  in red under that setting ("T_s must be above 0, got 0"), the form stays open, nothing is queued.
  A refused sweep value: the words under the sweep row. Editing the setting clears its words.
- Gone with the hovers: the range interval, the line beside a pick (a choice's help, a saved run's path),
  "Click to plot it against a setting", and "only some sweep values open it" (the form's note keeps its
  warning when such a setting is set).
- In DeePC's System and Open loop: the labels the developer renames (from the file they edit), and no
  help lines.

## Approach

### Benchlab (branch `no-hovers`, version 0.3.0; no change to the run file)

1. **Hovers out.** `lab/form.py`: `hover()` goes; `Form.state_of` returns `(off, reason)`, the reason only
   when greyed. `lab/app.py`: setting labels and row-field labels without `title`; the pick's
   `TooltipIcon` and `_tips` go (the third grid cell is the unit or the spacer it already falls back
   to); no `description=` on All, None, Show all, Hide all, a card's ✕; `_frame` without the title's
   `doc` hover and without the foot's `title` (it repeated its visible words). `lab/view.py` and
   `lab/compare.py`: compare rows carry no `hover`, the term cell no `title`. `lab/runlist.py`: Use and ✕
   without `title`. Untouched: greyed card controls (`_toolbar`, `title=capital(why)`), the strip's
   `aria-label`s (names for the buttons, not hovers), plotly's data hover. `Series.doc`, `Number.doc` and
   `fields_of`'s `doc` stay: saved pictures' notes and every record's header still carry them (a
   project that keeps its help lines keeps them there), so the run file does not change.
2. **Reasons and refusals under the setting.** Each field's box cell becomes the box and a note under
   it: the refusal in red, else the greyed reason, else hidden. The sweep row gets the same note.
3. **Refused at Run.** New `jobs.refusals(piece, typed, swept, rungs)`: each typed value, and each sweep
   rung of the swept setting, read as the run will read it (`record.config.coerce_value`, on the
   declared `Config.param[name]`; no Config built), then held to the bounds `fields_of` reads, with
   param's own rule (param 2.4.2 `Number._validate_bounds`: inclusive unless declared otherwise).
   Words, from the mockup: `<label> takes a number | a whole number | a list of numbers, got <text>`;
   `<label> must be at least | above <low>, got <text>`; `must be at most | below <high>`. `_run` checks
   first: any refusal, its words under its setting (or the sweep row), the form stays open, nothing
   queued. A setting's words clear when it is edited, all of them on Clear, Use, another piece, or a
   Run that queues. The Lab's import allowlist gains `coerce_value`, with that reason.
4. **The toy piece** gains `duty`, a square wave's duty cycle in (0, 1), both ends excluded, open only
   while Shape is square: a gate and an exclusive bound for the tests to drive.
5. **Tests.** Page (no browser): no setting, compare row, card title, list button or card ✕ carries a
   hover, a greyed card control still does; a gated setting and the sweep axis show their reason under
   them; A = -1, N = 2.5, duty = 1, a sweep with one rung below its bound: each refused under its place,
   nothing queued, the form open; edited, the words go. The restated bounds rule held to param's own
   verdict (the test builds Configs, which the Lab never does): for values at, just inside and just
   outside each bound of every toy setting and of inclusive and exclusive bounds, the Lab refuses
   exactly when param refuses. Browser: with a run shown, a chart card and a number card open, the form
   open with a greyed setting and a run in the strip, every element carrying a `title` (through the
   shadow roots) is a greyed card control; the A = -1 refusal shown and nothing queued.
6. **Words and docs**: `docs/plan-branch-2b.md` (this plan), `docs/design.md` (decision 5: the answers
   above and the help lines' other readers, the cost accepted; §8: 2b no hovers, 2c words as slots, 2d
   the tree, 2e the cards), `.claude/memory/MEMORY.md`.

### DeePC (branch `no-hovers`, pinned to Benchlab's branch, then `v0.3.0`)

1. **The naming pass, first, so the developer edits while Benchlab is built.** A file,
   `docs/project/labels.md`: every label of System and Open loop (settings, charts' titles, axes and
   traces, numbers), what its hover says today, and a suggested word where the label is a code name or
   a bare symbol (x0, u_min, u_max, u_exc_min, u_exc_max, rtol, atol, x*, u*, n, m, p, q, r, ∠G, whose
   degrees only its hover gives, ...); the developer writes their word or leaves it. Applied in
   `devkit/harness/system/` and `devkit/harness/open_loop/` (`config.py`, `record.py`); the file then
   deleted, its table kept in the PR.
2. **Help lines deleted** in System and Open loop: settings' `doc`, charts' and numbers' `doc`, choices'
   `lines`. Dataset and Closed loop untouched.
3. **Tests**: `test_lab_form.py`'s hover tests go (the bounds interval, the compare rows' `hover`);
   `test_lab_view.py`'s card-title hover becomes "no hover"; tests that read a renamed label follow it.
4. **Words**: `docs/project/lab-words.md` (no hovers; the reasons under greyed settings; the refusal
   words; System's and Open loop's new labels, their help-line column gone), `CLAUDE.md` (its words
   rule lists "labels, hovers, chart names, legends": the hovers go from it), `.claude/memory/`.

## Files

Benchlab: `benchlab/lab/{form,app,view,compare,runlist,jobs}.py`, `tests/toy/wave.py`,
`tests/test_lab.py`, `tests/test_lab_browser.py`, a new test of the bounds rule (`tests/test_runner.py`
beside `checked`'s), `pyproject.toml` (0.3.0), `uv.lock`, `docs/design.md`, `docs/plan-branch-2b.md`,
`.claude/memory/MEMORY.md`. DeePC: `devkit/harness/{system,open_loop}/{config,record}.py`,
`docs/project/labels.md` (while the pass lasts), `docs/project/lab-words.md`, `CLAUDE.md`,
`tests/test_lab_form.py`, `tests/test_lab_view.py`, `pyproject.toml`, `uv.lock`, `.claude/memory/`.

## Verification

1. Benchlab: `uv run pytest` (browser test included), `uv run ruff check .`.
2. DeePC, its path source on this copy (never committed): whole suite, browser tests included.
3. DeePC's side door, every piece run and drawn against the runs before (`c7f0d7d`, as 2a): numbers,
   series and every array identical; differences only in System's and Open loop's renamed words and
   deleted help lines (record headers' number labels and docs, stills' titles, axes and notes), each
   listed.
4. Review: `/code-review` on both diffs (parallel reviewers only on the developer's word, asked then).
5. Hand-off in DeePC's Lab, a walkthrough driven first by Claude: what to click, type and see (no hover
   on a setting, a chart, a number; T_s = 0 refused under T_s; λ_g swept and its reason under it).

## Order of git writes (each on the developer's word, as 2a)

Benchlab's branch, PR; DeePC's branch pinned to it, its suite, PR; hand-off; merge, tag `v0.3.0`, DeePC
re-pinned to the tag, its suite and side door again, merge, branches deleted, copies back on `main` and
`master`.

## Cost (estimated)

Benchlab about +350 / −120 lines (tests most of it), DeePC about +80 / −150 and the developer's words for
about 20 labels. Compute: one parse and comparison per typed value at Run, nothing measurable.

## As built (2026-11-14), where it differs from the plan above

- **One more hover, found by the browser test**: the divider between the panes said "drag to resize ·
  double-click to reset" on its hover. It is gone; the divider is a separator, as the mockup's was
  (`role="separator"`, `aria-orientation="vertical"`).
- **The run list's ✕ was named only by its hover**; it keeps a name for a screen reader and the tests
  in an `aria-label` ("Delete <run>"), which no pointer shows, as the strip's Stop and ✕ have.
- **A pick's options no longer carry a line** (a choice's help, or a saved run's path): only the
  removed help icon showed it (`Form.options` returns `{value, words}`).
- **DeePC's naming pass, as the developer settled it** (2026-11-14): "all of these configs are
  standard math stuff. Use common/standard/mathy terminology, symbols and acronyms". Every label of
  System and Open loop is kept but `x0`, now `x_0`: beside the states' components x1, x2, …, `x0`
  read as a component numbered 0. `∠G` keeps no unit (their no-units rule; a Bode phase is in
  degrees by convention). The file the pass was to be written in, `docs/project/labels.md`, is
  deleted unused.
- **A bug from before Benchlab, found driving the hand-off, fixed here on the developer's word**
  (2026-11-14): picking another piece left the form's name and sweep boxes, and its "From <run>"
  head, holding the last form's words, which the next Run no longer used. A piece now starts its
  form as Clear leaves one (`Lab._on_piece` calls `_clear`); a test holds it.
