# Branch R2: RunLab holds its own words

## Context

Today Benchlab names 136 slots for the words its page writes ("Refresh", "New run", "Runs in
progress") and holds none of the words. Every project must hand over a file filling all 136, or
the Lab will not start. Two consequences, measured:

- DeePC's words file (`devkit/harness/words.toml`, 158 lines) is the made-up project's, word for
  word. It exists only because the Lab refuses to start without it.
- Every new word on the page would be an edit in every project (DeePC's PR #20 was exactly that).

That breaks the rule "a new RunLab never needs a change in a project" (`docs/design.md` §10).
R2 closes it: Benchlab holds the words itself, and a project's file lists only the words it
wants different. A project with no words file gets the page in Benchlab's own words.

In instrument terms: the panel ships with its labels printed. A plant may relabel a button; it
no longer has to supply every label before the panel powers on.

This is the first branch that should need **no change in DeePC**. That is the test of R1.

## What R2 delivers

1. **Benchlab's own words**, `benchlab/lab/words.toml`: today's 136 words, the made-up project's
   file moved here unchanged (`git mv tests/toy/words.toml`).
2. **A project's file lists only what it changes.** `benchlab/lab/words.py`, `load`: Benchlab's own
   words first, the project's laid over them. Still refused, naming each, exactly as today: a slot
   Benchlab does not name (a typo would otherwise do nothing, silently), a word that is not text,
   a field its slot does not offer, a stray brace. No longer refused: a slot left out.
3. **`WORDS` becomes optional in the declaration.** `benchlab/project.py`: `DECLARED` drops it;
   `words_path()` returns nothing when the project names no file.
4. **The slot names join the promise.** A project's file names slots, so a slot renamed here would
   break that project. From this version until 1.0 no slot is removed or renamed and none offers
   fewer fields. Held by `tests/test_shore.py` against a list written once
   (`tests/slots_promised.txt`, 136 lines) and never regenerated from the code.
5. **The check a project calls** (`benchlab/testing.py`) reads the words the same way: no file is
   fine; a file with a bad entry is refused.
6. Version `0.6.0`.

## Decided by Claude, with the reason

- **The words stay a TOML file, inside the package**, not a table in Python code. It is the file
  that already exists, moved; it is in the same form a project writes, so a project copies a line
  from it to change a word. Cost: it is the package's first file that is not Python, and such a
  file is left out of an installed copy unless the packaging says to include it (two lines in
  `pyproject.toml`). Benchlab's own suite would not notice it missing, since it runs from the
  source folder; every project's Lab would fail to start. So a test builds the package and looks
  inside (`tests/test_packaging.py`, a few seconds). If that test proves slow or needs the
  network, it is cut to a check of the two lines, and said so.
- **The slot names are promised now**, rather than left free. Cost, to know before 2d and 2e
  redesign the page: a word that is renamed or dropped later keeps its old name accepted in a
  project's file (it simply shows nowhere). That is one line per retired name, added the day the
  first one is retired; nothing is built for it now.
- **The made-up project declares no words file.** It is the common case, and it puts the whole
  suite on Benchlab's own words. The tests of changing a word write their own small files.
- **DeePC is not touched.** Its full file keeps working: all 136 entries equal Benchlab's own.
  Deleting that file is DeePC's to do whenever it wants, in a branch of its own.

## Files

- `benchlab/lab/words.toml` (moved), `benchlab/lab/words.py` (`load`, its docstring),
  `benchlab/project.py` (`DECLARED`, `words_path`), `benchlab/testing.py` (one call),
  `pyproject.toml` (package data, version).
- `tests/toy/__init__.py` (no `WORDS`), `tests/test_words.py` (rewritten: own words fill every
  slot; a file of one word changes that word and no other; no file at all; the four refusals; the
  Lab starts on a short file and not on one naming an unknown slot; one test that a changed word
  reaches the built page), `tests/test_shore.py` + `tests/slots_promised.txt`,
  `tests/test_packaging.py` (new), `tests/test_project.py` and `tests/test_testing.py` (the
  required names, a bad words file).
- Docs: `README.md` (the words paragraph, the declaration example, "What a project may use"),
  `docs/design.md` (decision 4 replaced; §10, R2 built), `CLAUDE.md` (the words sentence of
  "Benchlab names no project"), `docs/for-review.md`, `.claude/memory/MEMORY.md`,
  `docs/plan-branch-R2.md` (this plan and its "As built").

## Cost, named

- Benchlab's code: about 40 lines changed across four files; the words file moves, 0 net.
- Tests: about +100 lines, and the 136-line list.
- Compute: the suite's 72 s plus the packaging test, measured at build.
- DeePC: 0 lines.
- Usage: small. No parallel reviewers, no agent fan-out.

## Verification

- Benchlab: `uv run pytest` and `uv run ruff check .`, whole suite (306 passed before).
- **DeePC, unchanged, on the new Benchlab.** In a scratch clone of DeePC's `master`, with only the
  clone's source line pointed at this branch, installed the way a project installs it (not as an
  editable copy, so the packaging is exercised): its whole suite (131 passed before), and
  `uv run lab --no-open` serves the page. Nothing in DeePC's own repository is edited.
- **The page's words do not move:** every one of the 136 words read through DeePC's file on
  `v0.5.0` and on this branch, compared.
- Hand-off: nothing new to drive. The page reads as before; what is new is that a project may
  leave the file out.

## Git

BenchLab only. Approving this plan is the developer's word for one git step: creating the branch
`r2-words` (the notes of R1's merge, uncommitted on `main`, ride onto it). Commit, push, PR,
merge and the tag `v0.6.0` are each asked for when reached. DeePC gets no branch and no PR.

## Not in R2

Deleting DeePC's words file; a piece's own figures (R3); files a run writes (R4); new setting
kinds (R5); the rename (R6); 2d and 2e.

---

## As built (2026-11-16; merged)

Merged on the developer's word: BenchLab #6 (merge `521948e`, tagged `v0.6.0`). DeePC's
repository is untouched: no branch, no PR, its lock still on Benchlab `v0.5.0`.

### One departure, the developer's

**Nothing in a project's words file stops the Lab.** The plan above kept the refusal at start
(a slot Benchlab does not name, a field a slot does not offer) and, because of it, promised the
slot names. While updating `docs/design.md`, Claude read the developer's decision of 2026-11-15
there (decision 4, "Replaced"): "nothing is checked at start. If a word is missing or wrong i
will see it in the lab and make the change. No reason for anything more complex than that." The
plan had been written without it. Asked on 2026-11-16, with the plan already built, the developer
chose: **always start, and say what was left out.** So:

- An entry Benchlab cannot use (it names no slot, is not text, writes a field its slot does not
  offer, holds a stray brace) is left out; the page keeps Benchlab's own word; the Lab prints one
  line in its terminal naming each (`benchlab.lab.words.left_out`, `benchlab/lab/cli.py`). A
  words file that cannot be read at all is left out whole, and said the same way.
- **The slot names are not promised**, and `tests/slots_promised.txt` and its test are gone: a
  slot renamed later leaves a project's entry out, said, and breaks nothing. 2d and 2e owe no
  retired names.
- `check_project` warns of what is left out and does not refuse: a slot renamed in a later
  Benchlab must not fail a project's suite.
- Only Benchlab's own file is still held strictly (every slot filled, every entry usable): a
  mistake there is Benchlab's, and its suite holds it.

### What was built

- `benchlab/lab/words.toml`: the made-up project's file, moved; its head comment says how a
  project changes a word.
- `benchlab/lab/words.py`: `load` (Benchlab's own words, a project's over them), `read` (a
  project's file: what can be used, what is left out and why), `left_out` (the one line).
- `benchlab/project.py`: `WORDS` is no longer required; `words_path()` may be `None`.
- `benchlab/lab/cli.py` prints the line; `benchlab/testing.py` warns with it.
- `pyproject.toml`: the words file named as package data; version `0.6.0`.
- The made-up project names no words file.
- Tests: `tests/test_words.py` rewritten (own words fill every slot; no file; a file of two
  words changes those two; each kind of unusable entry left out and said, the usable one beside
  it used; an unreadable or absent file; the Lab starts and says; a changed word on the built
  page), `tests/test_packaging.py` (new), and lines in `tests/test_shore.py`,
  `tests/test_testing.py`, `tests/test_project.py`.

### Measured

- **Lines.** Code: about +110, −50 in five files (`words.py`, `project.py`, `testing.py`,
  `lab/cli.py`, `pyproject.toml`); the words file moved, four comment lines changed. Tests: about
  +140, −40, one file new. DeePC: 0.
- **Benchlab's suite:** 306 passed in 72.2 s before; 315 passed in 73.0 s after. Ruff clean.
- **The packaging test** builds the package in about 1 s and finds the words file inside. Built
  once without the two packaging lines, the file was absent (0 found): the test can fail.
- **DeePC, unchanged, on this Benchlab.** A clone of DeePC's `master` (`3cf9542`) in a scratch
  folder, only the clone's source line pointed at this working tree, installed as a built
  package (in `site-packages`, not an editable copy): the words file is inside the installed
  copy; all 136 words read through DeePC's file equal those read on `v0.5.0`; nothing is left
  out; its whole suite, 131 passed in 122 s; its Lab driven once in headless Chromium (title,
  four pieces, two charts, the System form's rows, a System run from the form ending Done, no
  error on the page or in its console).

### Still to do

- The git steps are done. DeePC takes `0.6.0` whenever it wants, by
  `uv lock --upgrade-package benchlab` and its suite.
- DeePC's `devkit/harness/words.toml` (158 lines, every word Benchlab's own) and its `WORDS` line
  can go, in a branch of DeePC's own, when the developer wants.
- Then R3, a piece's own plotly figures (`docs/design.md` §10).
