# Branch 2c: words as slots

## Context

Decision 4 (the developer's, `docs/design.md` §3): "Words are empty cells. Benchlab names every slot
for its own buttons and labels and holds no word. Each project's words file fills every slot. A
missing word stops the Lab from starting and names the slot." On 2026-11-14 the developer split
the old 2b in two; this is the second half, and it changes nothing the page shows: it proves
itself by every word staying the same, word for word, in every state of the page (`CLAUDE.md`:
a refactor proves itself by not changing what it carries). The developer asked for 2b to 2e built
straight through: this plan is written, not presented; its open choices are listed in
`docs/for-review.md`.

## What the developer will see

Nothing new on the page. In DeePC, one file, `devkit/harness/words.toml`, holds every word the
page writes itself (its buttons, headings, counts, states, notes and refusals), grouped by where
it shows: changing a word is editing that file. A word missing, a slot named that Benchlab does
not have, or a word using a field its slot does not offer stops `uv run lab` before it serves,
naming each.

## Approach

### Benchlab (branch `words-as-slots`, version 0.4.0; the run file unchanged)

1. **The slots**: `benchlab/lab/words.py` names every slot, with the fields its word may use
   (`strip.count.running: n`), grouped by where the page shows it. A word that counts has two
   slots, `.one` and `.many`, and Benchlab picks one by the count: English's plural is the
   project's to write, not Benchlab's.
2. **The words file**: TOML (`tomllib`, the standard library), one table per group. The project
   declares it: `WORDS` joins `benchlab/project.py`'s declared names, a path to the file.
   `words.load(path)` refuses, naming each: a slot left empty, a slot Benchlab does not name, a
   word using a field its slot does not offer, a brace that is no field. The Lab loads it before
   it serves (`benchlab.lab.cli`), so a refusal stops `uv run lab` with those words.
3. **Every word the page shows** comes from `say(slot, **fields)`: `lab/app.py`, `form.py`,
   `view.py`, `shaping.py`, `state.py`, `jobs.py` (the words the page can show: the name refusals,
   the refusals at Run, a run's failure words), and the strip, run list and compare table, whose
   script code takes its words as a parameter. Not slots: words the page does not write itself
   (a record's, a setting's label, param's, the runner's and the figure layer's refusals, shown
   as the words of what refused) and words no person using the page can reach (an unknown piece,
   an argument that is not `SETTING=VALUE`: a programming mistake's).
4. **The toy's words file**, `tests/toy/words.toml`: today's words.
5. **Tests**: the toy fills every slot; each refusal of a words file, by name; the Lab refuses to
   start on one; every slot is said somewhere in `benchlab/lab` and every slot said is named (read
   off the sources); a count picks `.one` or `.many`.

### DeePC (branch `words-as-slots`, pinned to Benchlab's branch, then `v0.4.0`)

`devkit/harness/words.toml` with today's words, declared as `WORDS` in `devkit/harness/__init__.py`;
a test that it fills every slot; `docs/project/lab-words.md` points at it for the page's own words
and keeps the pieces' words; `CLAUDE.md`'s words rule names it.

## Verification

1. The page's words, unchanged: a tour of the page's states (the page; runs ticked; settings all,
   differing; a number card; a filter that lists none; a delete asked; the form; a sweep that
   repeats a value; a value refused; a name refused; the strip with runs done, failed, stopped,
   running and queued; another piece) collects every word shown, placeholder, option, label and
   hover, before any 2c code (v0.3.0) and after: the toy's and DeePC's, each identical.
2. Benchlab's suite and ruff; DeePC's whole suite, and its side door (the records cannot move:
   no piece changes).
3. Parallel review (the developer's standing word), then the git steps.

## Cost (estimated)

Benchlab about +600 / −300 (the slots and the words file hold every word once more; the code
loses its literals); DeePC about +250 (its words file). Compute: one TOML file read when the Lab
starts.

## As built (2026-11-14), where it differs from the plan above

- **136 slots** in nine tables (`header`, `runs`, `compare`, `figures`, `cards`, `form`, `refuse`,
  `strip`, `messages`). The title stays a declared name (`TITLE`), not a slot; the ✕ buttons are
  slots, the ▸ and ▾ marks and the ` · ` and `; ` that join several words stay Benchlab's. A word
  may leave out a field its slot offers; only a field the slot does not offer is refused.
- **The proof, as planned**: two tours of each page on v0.3.0 matched each other, word for word,
  before any 2c code; after it, the toy's 12 states and DeePC's 13 match them. One of DeePC's tours
  met plotly's `_guiEditing` error (`docs/for-review.md`, found on the way) and was run again.
- **Tests**: `tests/test_words.py` (the toy fills every slot; five ways a words file is refused,
  by name; the Lab will not start on one; one and many; every slot named is said and every slot
  said is named, read off the sources). `DECLARED` gains `WORDS`; the test of a module lacking
  declared names expects it.
