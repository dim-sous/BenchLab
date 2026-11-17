# Benchlab: the bench every project shares

One package, installed in each project the way numpy is, holding what every project's bench
needs: the settings and run files, the charts, the command line and the Lab's page. What it is
and how a project declares itself: `README.md`. What it is to become, and every decision made so
far: `docs/design.md`. This file holds the working rules.

**Only advisory rules live here**, the ones no test can catch. A checked rule lives in the test
that checks it. Each rule points at what holds it: an incident in `docs/project/failures.md`,
a sibling's incident (DeePC `[D…]`, BESS `[B…]`, RCWS `[A…]`), or a test. A
new session starts from `.claude/memory/MEMORY.md`: keep it current and commit it with each branch.

## Commands

- Python through uv only, 3.13 as pinned: `uv sync`, `uv run pytest`, `uv run ruff check .`.
  The suite runs on a made-up project of three pieces (`tests/toy/`); `tests/conftest.py` declares
  it for every test.
- Benchlab is tested here, on the made-up project, which uses of Benchlab only what a project
  may (`README.md`, "What a project may use"; `tests/test_shore.py` holds the list). A project's
  own suite checks that its pieces plug in, with the check Benchlab ships
  (`benchlab.testing.check_project`), and reads nothing deeper. A change to what a project may
  use is not done until the project it was made for passes its whole suite on it, through a
  local editable install that is never committed (`README.md`).

## Workflow (the siblings', unchanged)

- Propose, then plan mode, then build. One gap per branch; the smallest change that closes it,
  its cost in lines and compute time named; no abstraction for a future no branch needs yet.
- What the page shows is the developer's, decided only after driving it. How it is built is
  Claude's, said with its reason; push back when an answer costs more than it looks, and write
  the cost beside the decision (`docs/design.md` §3, decision 5).
- No git write without the developer's word, in that turn, each time. Ask before ANY multi-agent
  fan-out, every time (RCWS `[A12]`). Every question to the developer goes through
  AskUserQuestion, with its context inside the question.
- A refactor proves itself by NOT changing the numbers: a project's runs and stills before and
  after it differ only where two runs of the unchanged code already differ from each other
  (provenance, wall-clock times) (BESS `[B4]`).
- After any move, search code, docs and settings for the old names (RCWS #159).

## Rules no test can catch

- **RunLab is used like numpy** (the developer, 2026-11-15; RunLab is Benchlab's coming name).
  A change in a project never needs a change here, and a new version here never needs a change
  in a project that does not want what is new. Branch R1 (`v0.5.0`) named what a project may use
  and promised it until 1.0; R2 to R6 follow, and 2d and 2e wait for them (`docs/design.md` §10).
  R2 (`v0.6.0`) put the page's words here; R3 (`v0.7.0`) lets a piece hand the page a figure
  it draws itself; R4 (`v0.8.0`) gives each run a folder for the files it writes, built on
  the made-up project alone and so not yet promised. A setting beyond the six kinds still
  needs a change here.
  ([L2]; RCWS `[A9]`)
- **Benchlab names no project.** Its code and the words its page shows reach a project only
  through the project's declaration (`benchlab/project.py`); what a test can hold of this,
  `tests/test_layers.py` holds. Benchlab holds the page's own words (`benchlab/lab/words.toml`),
  none of them a project's: a word only one project needs is written in that project's words
  file, over the slot Benchlab names for it (`docs/design.md` §10, R2).
- **The run file is a contract with every project.** A change to what a record saves, or how it
  loads, is a new Benchlab version, and every project takes it by raising its lock
  (`uv lock --upgrade-package benchlab`) and running its own suite. A run saved before the
  change is still listed and drawn (`docs/design.md` §4).
- **Evidence over judgement.** A claim about the code, in a comment, a README or a PR, is checked
  against the code the day it is written; never assert why a number moved, measure it.
- **The comment rule**, four kinds and nothing else: (1) a function, parameter or return doc;
  (2) a citation, source and page; (3) a `# MISMATCH` where the code knowingly departs from its
  source, saying what it does instead; (4) a decision with its observed consequence. State what
  was observed, never what it means. (DeePC `[D6]`)
- **Fail loud.** No swallowed exception, no stand-in answer for one the code failed to compute,
  no guard that hides a failure. Every `except Exception` carries `# noqa: BLE001` beside the
  reason it is there; ruff's blind-except rule finds a new one (`pyproject.toml`). (DeePC
  `[D2, D3]`)
- **Figures describe, they never conclude:** no title, axis labels that name the quantity, a
  legend only when there is more than one label, a bound named by the quantity it bounds (DeePC
  `[D7]`). The checklist is DeePC's skill `figure-conventions` (its `.claude/skills/`); it holds
  for `benchlab/figure/` and `benchlab/lab/`, and DeePC's `tests/test_figure.py` checks part of it.
- The repository is public: no papers, no private data, no credentials.
