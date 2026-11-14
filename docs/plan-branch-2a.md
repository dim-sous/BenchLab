# Branch 2a (plan, approved 2026-11-14): runs in progress, each run its own process, in place of the terminal

## Context

Branch 2 builds the page the developer designed (mockup https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb,
`docs/design.md` §3–§5). On 2026-11-14 they chose to build it as four small branches, each driven in
DeePC's Lab before the next: **2a runs in progress** (this plan), 2b words as slots and no hovers,
2c the tree, 2d the cards' full controls. Old runs and Re-fly stay branch 6, run cost branch 4.

Today a run goes through the command line: the Lab types `uv run deepc run …` into one subprocess,
one command per Lab (`benchlab/lab/jobs.py`: `_LAUNCHED`, "a command is already in progress"), and
shows its printed output in a terminal drawer. A sweep's runs go one after another. Design decision 3
(the developer's): "Start run launches each run as its own program, started by the Lab and talking to
it directly. Today's hidden terminal and its output drawer go. The command line stays as a side door
for Claude and the tests. The Lab never goes through it." And §4 (Claude's): never more at once than
the machine has cores, the rest queued; Stop ends that process and nothing else; a crash takes down
only itself; the Lab and the side door give identical files for the same settings, held by a test.

## What the developer will see (and drive at hand-off)

- **Runs in progress**, a strip along the bottom in place of the terminal drawer (as the mockup):
  each run with its name and piece, its state — Queued, Running (with elapsed time), Done, Failed
  (with its error), Stopped — Stop on a queued or running one, ✕ to clear a finished one; the
  head says how many run, wait and finished, and "up to 12 side by side" (this machine's cores).
- **Run** never greys while something runs: it queues. A sweep's runs go side by side.
- A finished run's record appears in the list, ticked, as today.
- Gone: the terminal drawer, the header's Idle/Running tag and its Stop, and the drawer's line
  "lab: uv run deepc run …" (it would describe a command the Lab no longer types; the mockup has
  none). A refusal (a value the settings refuse) shows as that run Failed with the settings' own
  words. Showing it next to the setting comes with 2b (decision 5).
- Proposed, to be judged when driving: runs belong to the Lab, not to a browser tab. A closed tab
  no longer stops its run; every tab shows the same strip; stopping the Lab (ctrl-c) stops them all.
- Progress shows as elapsed time: no piece reports a fraction yet (decision: "A run that never calls
  it shows its elapsed time"). Passing `progress` to a piece comes with the first piece that reports.

## Approach

### Benchlab (branch `runs-in-progress`, PR, tag v0.2.0)

1. **One way to run a piece once** — new `benchlab/runner.py`, below `cli` and `lab` in the layers
   (`project ← record ← runner ← cli, lab`):
   - `planned(name, overrides, sweeps) -> [(record name, [(setting, text)])]`: the sweep
     expansion and its refusals, moved verbatim out of `cli.run_command` (`benchlab/cli/__init__.py:82-117`).
     They become `ValueError`s, so the command line now prefixes them `deepc:` like every other refusal.
   - `run_once(piece, pairs, name, out_dir) -> Path`: `Config()` + `with_overrides` once, `run`,
     rename, `save` — the loop body of `run_command`, unchanged.
   - `python -m benchlab.runner <piece> <name> <out_dir> <pairs as JSON>`: the program one run
     is. It keeps its own copy of stdout as the channel to the Lab (one JSON line: the path it
     saved) and points fd 1 at stderr, so whatever a piece prints cannot be read as the answer.
     A refusal (`ValueError`, `KeyError`, `FileNotFoundError`, as the command line converts) exits
     non-zero with its words on stderr; anything else ends in its own traceback. No catch-all.
   - `cli.run_command` keeps its flags and output, now `planned` + `run_once`.
2. **The queue** — `benchlab/lab/jobs.py` reworked: a `Run` (piece, name, pairs, state, started,
   ended, error, saved path, its process), states `queued → running → done | failed | stopped` and
   `queued → stopped`. One queue per Lab process (every tab sees it), guarded by one lock. `submit`
   queues the runs `planned` makes and starts as many as `os.cpu_count()` allows; each running
   run has a watcher thread that reads its channel and stderr and, when the process ends, records
   how and starts the next queued run. Each run starts as `[sys.executable, "-m",
   "benchlab.runner", …]` in the project root: the Lab's own interpreter (the project's
   environment), no `uv run`, no command line. `stop` terminates that one process (a stopped run
   saves nothing: `Record.save` writes `.partial`, then renames). An `atexit` hook terminates what
   still runs when the Lab stops. `run_argv` and `line_of` stay for the line the Lab prints to its
   own console per run (`lab: uv run deepc run …`, the side-door command that would make the same
   record); `delete` stays; `launch`, `Job`, `_LAUNCHED` and `state.wrote` go.
3. **The page** — `benchlab/lab/app.py`: the terminal drawer, console, history, `job_tag`, the
   header's Stop and `command_line` go; `_run` submits (`launch=` stays injectable for tests, now a
   submit); `_poll` (every 700 ms while runs exist) redraws the strip and, when runs finished since,
   reloads the list and ticks what they saved. The strip is one HTML pane plus a Stop/✕ per row
   (Panel buttons), styled in `benchlab/lab/skin.py` beside the drawer's styles; its words are
   written in Benchlab until 2b turns them into slots.
4. **Tests** (Benchlab's suite, on the made-up project, which gains two test-only settings: a
   delay before it computes, and a switch that makes its run raise):
   - the side door and the runner write identical files for the same settings, provenance aside (§4);
   - never more than N at once (N set small in the test), the rest queued in order; Stop ends one
     run and nothing else; a stopped queued run never starts; a refusal and a crash each end as
     Failed with their words; a piece that prints does not confuse the channel;
   - the page: Run queues and the strip shows each state; the tripwire (the Lab never runs a piece
     nor builds its Config) adapted to submitted runs;
   - the run and terminal tests DeePC holds today that test Benchlab's mechanics, not DeePC's pieces
     (in `tests/test_lab_view.py`, from `test_run_launches_the_form_as_the_command…` on; in
     `tests/test_lab.py`, the job and argv tests), rewritten here for the runner;
   - a browser test of the strip (Benchlab gains `playwright` as a dev dependency, as DeePC pins
     it): a sweep of three delayed toy runs shows Running and Queued, then Done, and the list
     shows their records.
5. Layers test: `runner` added to the table; the Lab's allowlist gains `planned` from the runner.

### DeePC (branch, PR, pinned to Benchlab's branch, then to v0.2.0)

- `pyproject.toml`: Benchlab's pin raised (branch while open, then `v0.2.0`), lock redone.
- Tests: the run/terminal tests that moved to Benchlab deleted; kept and rewritten through the
  runner: the end-to-end real run from the page (`test_a_real_run_from_the_page_writes_a_record_the_list_shows`,
  closed loop at 1 s), the tripwire, and the browser test's form check, which now presses Run and
  reads the settings the saved record holds, not a command line.
- Words and docs: `docs/project/lab-words.md` (the strip's words in place of the terminal's; the
  line Run would type gone), `devkit/README.md` (the Lab row), `.claude/memory/`. No piece changes.

## Files

On approval this plan is saved as Benchlab's `docs/plan-branch-2a.md`, and `docs/design.md` §8
records the split of branch 2 into 2a–2d (the developer's choice, 2026-11-14).

Benchlab: `benchlab/runner.py` (new), `benchlab/cli/__init__.py`, `benchlab/lab/jobs.py`,
`benchlab/lab/app.py`, `benchlab/lab/state.py` (`wrote` goes), `benchlab/lab/skin.py`,
`tests/toy/wave.py`, `tests/test_runner.py` (new), `tests/test_lab.py`, `tests/test_lab_browser.py`
(new), `tests/test_layers.py`, `pyproject.toml` (version 0.2.0, playwright), `uv.lock`, README,
`.claude/memory/MEMORY.md`. DeePC: `pyproject.toml`, `uv.lock`, `tests/test_lab.py`,
`tests/test_lab_view.py`, `tests/test_lab_browser.py`, `docs/project/lab-words.md`,
`devkit/README.md`, `.claude/memory/`.

## Verification

1. Benchlab: `uv run pytest` (browser test included), `uv run ruff check .`; the residual of
   `run_command` → `planned` + `run_once` read line by line.
2. DeePC on the branch: every piece run and drawn through the side door, compared with v0.1.0's
   (the bit-for-bit pass of branch 1): identical but provenance and wall-clock fields.
3. DeePC: one closed loop run from the page and from the side door with the same settings: identical
   files, provenance aside. Whole suite green, browser test included.
4. Measured and stated, with conditions: a λ_g sweep (1, 10, 100) of closed loops at
   `sim_duration=10`, from the Lab, on v0.1.0 (one after another) and on this branch (side by side),
   wall time; and the start of one run (process start to record saved) for `system`.
5. Review: `/code-review` on both diffs (parallel reviewers only on the developer's word, asked then).
6. Hand-off in DeePC's Lab: start that sweep, watch three run side by side, stop one, run a refused
   value, close and reopen the tab.

## Order of git writes (each on the developer's word, as branch 1)

Push Benchlab's branch, PR; DeePC's branch pinned to it, its suite, PR; hand-off; then merge, tag
`v0.2.0`, re-pin DeePC to the tag, its suite again, merge, branches deleted.

## Cost (estimated, measured at hand-off)

Benchlab about +700 / −350 lines (most of it tests moved from DeePC and the runner's), DeePC about
+150 / −450. Run time: each run pays its own Python start and its piece's imports, as each
`uv run deepc run` does today, but not `uv run`'s environment check; measured per verification 4.

## As built (2026-11-14), where it differs from the plan above

- **The strip is one component** (`benchlab/lab/strip.py`, rows as data, Stop and ✕ sending
  messages, as the run list does), not an HTML pane with a Panel button per row: clicking a Panel
  button added after the page loaded drew a Bokeh "reference already known" warning at every
  click. Its words sit in that component until 2b makes them slots.
- **The Lab takes a queue** (`Lab(queue=…)`), not a `launch=` turned into a submit, and polls every
  700 ms from the moment its page is built, not only while its own runs exist: every tab shows the
  same runs, so a tab must see runs another tab started.
- **`run_once(piece, pairs, name, out_dir, config=None)` returns the path and the record**: the
  command line passes the Config a config file gives, and prints the record's numbers.
- **From the review** (four reviewers, each finding put to a second agent; the developer chose
  this): a record name a queued or running run writes is refused, and the name the form offers
  skips it (two runs of one record at once lost one, or left it unreadable); the form's drawer ends
  where the strip begins, so a run can be stopped while the next is set up; SIGTERM ends the Lab
  as ctrl-c does, stopping its runs; a run ended by a signal says so; a refusal is kept whole on
  one line; a piece's prints come before the error that ends its run; a run that saved its record
  reads Done even when Stop reached it after; the strip's clock never steps back
  (`time.monotonic`); the strip counts running, queued, done, failed, stopped, the mockup's order.
- **Tests**: DeePC's three tests of the printed side-door line moved here too, as the plan said
  of its argv tests; the browser test runs a sweep of three, two at once, and stops a run while
  the form is open.
- **From DeePC's whole suite** (after the review): a run whose end could not be read raised a
  `TypeError` in its watcher, left the run Failed without words and the next one queued for ever;
  now it fails with "its end could not be read: …", its process is ended, the next starts, and the
  reason is raised on. The suites' stand-in processes returned, after 20 s (here) or 60 s (DeePC),
  with no exit code, which a real process never does; they now wait until ended. DeePC's chart
  test, which read the charts 1.5 s after the network went idle and found none twice in its whole
  suite, waits until they are drawn: the page took as long to draw them on v0.1.0 as on this
  branch (network idle after 2.6 to 3.1 s and 2.7 to 3.0 s, the charts drawn 0.01 to 0.02 s
  after that, fifteen loads each, alternated).
