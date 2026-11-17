# Branch R5: settings beyond the six kinds

## Context

A setting is one of six kinds: whole number, number, yes/no, text, choice, list
(`benchlab/record/config.py`, `_type_text`, `coerce_value`). `docs/design.md` §10 names anything
else, "a matrix or a date", as a change Benchlab still needs, which breaks the rule "a change in
a project never needs a change in RunLab".

Measured on `v0.8.0`, 2026-11-17, with four other kinds of the settings library (`param`):

| Kind | Typed (command line, form) | Saved in a run file and read back |
|---|---|---|
| a matrix (`param.Array`) | refused | saves, does not load |
| a date (`param.Date`) | refused, as "not a list of numbers" | does not save |
| a pair (`param.Tuple`) | refused | saves, does not load |
| a table (`param.Dict`) | refused | works |

`param` itself writes each of the four as plain text and reads it back (`serialize`,
`deserialize`; tried on all four, each came back equal).

R5 hands every setting that is not one of the six to `param`'s own writing and reading. One
opening for whatever `param` offers, as R3 was for whatever plotly draws; Benchlab keeps no list
of kinds to extend.

In instrument terms: the rack has six sockets. R5 adds one universal socket that takes the plug
the transmitter's own maker defined.

**The developer's choice (2026-11-17):** built on the made-up project, as R4 was: no project
needs such a setting today (DeePC's are lists, numbers and text). **Its cost, written beside
it:** against decision 8's rule; the shape is Claude's guess until a project uses it. R5 adds no
new name for a project, so nothing new is promised or held back.

## What R5 delivers

1. **Typed as text.** On the command line (`--set`, a settings file) and in the form's box, a
   setting of another kind is the text `param` reads: a matrix `[[1, 2], [3, 4]]`, a calendar
   date `2026-02-03`. Text it cannot read is refused naming the setting, with `param`'s reason;
   in the Lab, under the setting when Run is pressed (decision 5).
2. **Saved and read back.** The run file keeps the value as `param` writes it (a matrix as nested
   lists, a date as text); loading gives the piece the real thing (an array, a date).
3. **Shown as that text**: the form's placeholder for the default, the compare table's cell, the
   line the Lab prints beside a run.
4. **Not swept.** Such a setting is left out of the sweep row, as a list of numbers is today: its
   text may hold commas, which the sweep splits on.
5. **The six kinds are untouched**: their values, their refusals and their run files.
6. Version `0.9.0`.

## Decided by Claude, with the reason

- **`param`'s own writing and reading, not kinds added one by one.** Adding "matrix" and "date"
  would close two cases and leave the rule broken for the third.
- **A plain text box**, no grid for a matrix and no calendar for a date: the smallest thing that
  works. What the page shows is the developer's, after seeing it (`docs/for-review.md`).
- **Which settings count as "another kind"** is settled while building and held by a test: the
  six, declared as today, must save byte for byte what they save now. (A date is built on
  `param`'s number, which is why it is refused today as a list of numbers.)
- **The made-up `fit` gets two such settings**: `scale`, a 2 by 2 matrix applied to each step
  (the identity by default, so its numbers at the defaults do not move), and `day`, a calendar
  date, only saved. No new piece.
- **One new word** of Benchlab's own (`benchlab/lab/words.toml`), for the refusal under the
  setting.

## Files

- `benchlab/record/config.py`: `coerce_value` (text or a saved value through `param`'s reading),
  `to_dict`'s saved form, `fields_of` (the default as text, a mark for such a setting),
  `gated` (a matrix compared with its default without an error).
- `benchlab/record/__init__.py`: `_jsonable` writes a Config's settings in their saved form.
- `benchlab/lab/form.py` (`as_text` for a table, `axes`), `benchlab/lab/jobs.py` (`_refusal`),
  `benchlab/lab/view.py` (`compare_rows`: the cell as the text typed), `words.toml`, `words.py`.
- Tests: `tests/toy/fit.py`; `tests/test_record.py`, `tests/test_lab_form.py`,
  `tests/test_runner.py`, `tests/test_cli.py`, `tests/test_lab_browser.py`,
  `tests/test_shore.py` (a setting of any kind `param` offers).
- Docs: `README.md` ("a setting"), `docs/design.md` §10, `CLAUDE.md` (the line "A setting beyond
  the six kinds still needs a change here"), `docs/for-review.md` ("R5"),
  `docs/plan-branch-R5.md`, `.claude/memory/MEMORY.md`, version in `pyproject.toml`, `uv.lock`.

## Cost, named

- About +70 lines of code in six files, about +120 of tests. (R4's estimate ran 40% under.)
- Compute: the suite timed before and after (344 passed in 99.5 s on this cloud machine).
- Usage: smaller than R4. No reviewers, no agent fan-out.

## Verification

- `uv run pytest`, `uv run ruff check .`, before and after.
- **Runs of the six kinds are unchanged:** the made-up `wave` and `lag` runs saved before and
  after, compared field by field (R4's method).
- **DeePC needs no change:** its `master` (read-only clone), this working copy installed into
  its environment: its whole suite's failures listed before and after (seven fail on this cloud
  machine on any Benchlab), and one System run compared field by field.
- **The Lab driven by Claude** in headless Chromium on the made-up `fit`: type a matrix, run,
  see it in the compare table against a default run; type one that cannot be read, see it
  refused under the setting; load a run's settings back into the form. Screenshots sent.

## Git

Nothing is written to git on this plan's approval. The session's branch is
`ccr-ea61ca3b-35fv7x`; commit, push, a PR and the merge are each asked for when reached. **The
tag `v0.9.0` is the developer's to make** (GitHub's release page): this session cannot push a
tag. A git step is written into the notes only after it is done.

## Not in R5

A grid of boxes for a matrix, a calendar for a date; sweeping such a setting; a project
bringing its own box for the form; R6 (the rename); 2d and 2e.

---

## As built (2026-11-17; merged)

Built in a cloud session and committed on the branch `ccr-ea61ca3b-35fv7x`, on the
developer's word ("All the way: merge") after they saw the screenshots: BenchLab #12 merged
(`0b679e4`). The tag `v0.9.0` the developer made themselves, from GitHub's release page, on `c010581`
(that merge and a notes-only one, #13).

### What was built

- `benchlab/record/config.py`: `other_kind(p)`, whether a setting is of another kind than the
  six; `coerce_value` hands such a setting to `_read` (its text as JSON when it is JSON, then
  `param`'s `deserialize`; a value already of its own type passes through); `saved(cfg)`, the
  settings as a run file holds them (`param`'s `serialize`); `fields_of` gives such a
  setting's default as that text, marks it `other`, and leaves its bounds to `param`; `gated`
  compares a setting with its default as written. `benchlab/record/__init__.py` saves a Config
  through `saved`.
- `benchlab/lab/form.py`: a table as JSON text; such a setting left out of the sweep row.
  `benchlab/lab/jobs.py`: its refusal under the setting. `benchlab/lab/view.py`: its cell in
  the compare table as the text typed. One word slot (`refuse.unread`).
- The made-up `fit`: `scale` (a matrix) and `day` (a calendar date).
  `tests/test_other_kinds.py` (10 tests); one browser test.

### Which settings count as another kind

One not built on any of the six (`param.Array`, `Tuple`, `Dict`), or built on one and bringing
its own writing or reading (`param.Date` and `CalendarDate`, built on `param`'s number).
Looked up in `param` 2.4.2: none of the six, nor `Magnitude`, defines `serialize` or
`deserialize` of its own; `Date`, `CalendarDate`, `Array`, `Tuple` and `DataFrame` do.

### Departures from the plan

1. **R5's tests sit in one new file**, `tests/test_other_kinds.py`, with the browser test in
   `tests/test_lab_browser.py`; the plan named five existing files and `tests/test_shore.py`.
2. **The Lab checks only that such a value can be read.** A value that reads and is then not
   taken (a pair of three numbers, a date outside its bounds) is refused by the run, in the
   strip. `fields_of` leaves such a setting's bounds out, since they are dates, not numbers.
3. **A text that is not a matrix is taken by `param` as the name of a file holding one**, so
   the command line's reason for `[[1, 0], [0` reads "does not exist or is not a file".

### Measured (this cloud machine, 4 CPUs)

- **Lines.** Benchlab's code: +78, −14 in seven files (the plan said about +70 in six). Tests:
  +211, −2 (the plan said about +120).
- **Benchlab's suite:** 344 passed in 99.5 s before; 355 passed in 112.4 s after. Ruff clean.
- **Runs of the six kinds are unchanged.** Two `wave` runs and a `lag` run saved on `v0.8.0`
  and on this branch: the same keys in the same order, every field equal but `provenance`
  (`git_dirty`, `date`, `duration_s`) and the `lag`'s `wave_run`, the folder each was run in.
  The `fit` run at its defaults: its numbers and its loss equal; its `config` gains `scale`
  and `day`.
- **DeePC** (`c7f4569`, a read-only clone, this working copy installed into its environment,
  nothing of it changed): 125 passed and 7 failed in 115.8 s, the same seven as on Benchlab
  0.7.0 on this machine (the frozen arrays of its `coupled_masses` cases). One System run on
  0.7.0 and on this branch: every field equal but `provenance` (`date`, `duration_s`, the
  `benchlab` version).
- **The Lab, driven in headless Chromium** on the made-up `fit`: a default run; `[[1, 0], [0`
  and `tomorrow` typed, each refused under its setting at Run, nothing queued;
  `[[1, 0], [0, 0.5]]` and `2026-02-03` typed and run, the run file holding the matrix and the
  date; both runs ticked, Settings on Differing: Day and Scale shown, the matrix as its text;
  the second run's settings loaded back into the form (Use), both boxes holding that text. The
  page raised no error after the switch of piece. Screenshots looked at.

### Still to do

- The developer's judgement of `docs/for-review.md`, "R5".
- A project with a matrix or a date among its settings, to try it.
