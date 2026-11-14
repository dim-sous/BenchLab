# Benchlab: design

The shared Lab for DeePC-Sandbox, Hydrofoil-Flight-Control and BESS-Optimization-Platform (RCWS
later): one package, installed in each project the way numpy is, holding everything the four
Labs share. Written 2026-11-13 from a design session in which the developer drove two rounds of
a clickable mockup over real runs (https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb).

Each decision says who made it. **The developer** decides what the page shows and how it feels
to use, and only after driving it. **Claude** decides how it is built and says why. The developer
on 2026-11-13: "i am not a software engineer, thus take every last one of my answer with a grain
of salt". So Claude pushes back when an answer costs more than it looks, and the cost found is
written beside the decision.

---

## 1. What Benchlab is

The no-code front door to a project. Every piece, setting, run, chart and number is reached by
clicking, never by typing a command (the developer: "the quintessence of it is the no-code,
no-in-terminal command calling functionality of it"). A project brings its pieces and its words.
Benchlab brings everything else: the page, the running, the run files, the charts and the
calculations every project repeats.

Today each project carries its own copy of that everything-else, in `devkit/lab`, `figure`,
`record` and `terminal`. Measured 2026-11-13: 4,486 lines in DeePC, 1,798 in Hydrofoil, 5,312 in
BESS and 10,294 in RCWS. The three copies have drifted: the same feature exists in one and was
never ported to the others.

## 2. The split

| Benchlab holds | Each project fills |
|---|---|
| The page: the tree, run list, compare table, chart and number cards, the form, runs in progress, saved pictures | Its **pieces**. For each one: its settings, its `run(settings) → record`, and what the record keeps and can draw |
| The running: start, sweep, stop, progress, each run its own process | Its **tree**: which pieces, in what order. Which piece feeds which is read off the settings that name another piece's run (`record_of`) |
| The run-file format: one JSON per run, saved atomically, loaded loudly, old runs still shown | Its **words**: one file filling every slot Benchlab names |
| The chart engine: overlay, split, mean, RMS, sweep; a still as PNG, CSV and JSON note | Its **standard labels** for settings, charts and numbers, with units. There are no descriptions |
| The shared calculations (§6) | Its own calculations, where no shared one fits |
| The side door: a command line for Claude and the tests | Its **declaration**: in its registry, its command, the Lab's title, its repository and the libraries its runs stamp; in its `pyproject.toml`, Benchlab at a pinned version, its two commands and the entry point that names the registry (`README.md`) |

Decided: the developer (the split; "maybe by decomposing stuff even further we can achieve bigger
efficiency").

## 3. The developer's decisions (2026-11-13)

1. **Name and home.** Benchlab, public, `dim-sous/benchlab`. Public because DeePC is public, and
   a public project cannot be installed by others if it depends on a private one. Each project
   keeps `uv run lab` as the command that opens it.
2. **Order.** DeePC first, then Hydrofoil, then BESS. RCWS is decided once those three work.
3. **Running.** Start run launches each run as its own program, started by the Lab and talking to
   it directly. Today's hidden terminal and its output drawer go. The command line stays as a
   side door for Claude and the tests. The Lab never goes through it.
4. **Words are empty cells.** Benchlab names every slot for its own buttons and labels and holds
   no word. Each project's words file fills every slot. A missing word stops the Lab from
   starting and names the slot.
5. **No hovers** on settings, charts or numbers. The developer's reason: "if the name is
   appropriate/standard then it should be enough to avoid confusion and/or misinterpretation".
   Greyed buttons keep their reason on hover, because those are Benchlab's own words. A
   setting's allowed range is not shown. A value outside it is refused when the run starts,
   next to the setting.
   **Its cost, accepted** ("No hovers + rename"): on 2026-11-13, 64 of Hydrofoil's 70 settings
   and 8 of DeePC `open_loop`'s 13 used their code name as their label (`KPH`, `LSDH`,
   `alpha_CRH_min`; `x0`, `u_min`), and the hover was the only place their meaning showed. When
   a project moves, each such label is renamed to its standard term, the developer choosing
   every word, and its description is deleted.
6. **The tree.** A sidebar lists the pieces. Under the open piece sit its charts and numbers by
   group, each opening its card. The developer drove three layouts (tabs, tree, chain) and chose
   this one.
7. **Every feature of the four Labs** (§5), the union rather than a cut. RCWS [A9]: "a capability
   the Lab cannot reach is, to the person at the Lab, a capability that does not exist". After
   driving round 1: "right direction".
8. **Scenes and the Messages card arrive with their first user.** At the latest that is when RCWS
   moves. The developer reversed an earlier "build them anyway" on Claude's advice. Rule: "no
   abstraction for a future no branch needs yet".
9. **Old runs** read as shown in round 2: a line per difference under the run's name, a Re-fly
   button, and a chart card that says which run it leaves out.
10. **Run cost** is recorded by Benchlab for every run and shown last in the compare table,
    under its own heading.

## 4. Claude's decisions on how it is built

- **Panel**, as the four Labs today. One language, today's code carries over, and the browser
  test keeps working. Revisited only if a round of driving asks for something Panel cannot do.
- **One process per run.** Each run starts in its own process, never more at once than the
  machine has cores; the rest wait in a queue. Stop ends that process and nothing else. A run
  that crashes or hangs takes down only itself. Progress needs the run's help: Benchlab passes
  each `run` a `progress(fraction)` it may call. A run that never calls it shows its elapsed
  time instead of a percentage. Measured 2026-11-13 on this cloud machine (4 CPUs), what a run
  costs before its own work begins: importing Hydrofoil's devkit took 0.25 s, and a whole
  `uv run hydrofoil settings flight` took 0.56 to 0.59 s warm, 2.2 s cold.
- **The "Lab computes nothing" guarantee** is held by a test, not by the terminal. The same
  settings run from the Lab and from the side door give identical files, provenance aside (its
  date and duration differ by nature).
- **A project declares itself through an entry point** (decided in plan mode, 2026-11-13,
  `docs/plan-branch-1.md`): its `pyproject.toml` names its registry module in the `benchlab`
  group, the standard Python plugin mechanism, and Benchlab finds the one declared project there
  (`benchlab/project.py`), refusing none, two, or a module missing a name. Benchlab then never
  imports a project by its name.
- **Pinned versions.** A project names a Benchlab git tag (`uv add
  git+https://github.com/dim-sous/benchlab --tag vX.Y.Z`) and moves only when the tag is raised by
  hand, then runs its own suite. While Benchlab and a project are worked on together on one
  computer, the project uses a local editable install, which is never committed. The developer
  had no preference.
- **The run-file format is Benchlab's.** One JSON per run, as today. A change to it is a new
  Benchlab version and a bump in every project. A run saved before a change is still listed and
  drawn, with its notes (RCWS [A18]).
- **The address keeps the open piece, the ticked runs and the open charts**, so a hand-off is a
  link: "the address with its runs and charts open" (each project's hand-off rule).
- **Drawing never freezes the page** (BESS does it today). The start-up cache of the run list
  (RCWS's `listing.json`) is built only once a project's start-up is measured slow.
- **Tests live with what they test.** Benchlab's own suite covers the page, the runner, the
  records, the charts and the calculations, including the browser test. Each project keeps one
  test that its pieces plug in: every piece's settings build a form, every declared chart draws
  for a saved run, and its words file fills every slot. Each project's safety net
  (`tests/reference/`) must come out bit for bit the same across its move: the move is a
  refactor, and a refactor proves itself by not changing the numbers (BESS [B4]).

## 5. The page (rounds 1 and 2)

- **Tree** on the left: the pieces, and under the open one its charts and numbers by group.
- **Runs**: tick, filter by words, All / None, Delete ticked (confirmed in a dialog), and **Use**
  to load a run's settings into the form. An old run shows a line per thing today's code reads
  differently, plus **Re-fly**.
- **Compare**: the ticked runs column by column. Their numbers sit in the groups their record
  declares, and the run cost comes last. Settings show as None / Differing / All, a value left to
  the code shown as the project's word for it (DeePC "Code default", Hydrofoil "Code's own").
  Clicking a number opens its card against the setting that varies.
- **Cards**, one per open chart, each with the same controls. Axes: X (own / sample index), Log
  x, Log y. Runs: Overlay, Split, Mean, RMS. Colour by: run or quantity. Drawing: Lines, Dots,
  Cold start. View: Chart or Table. Then **Save**. A control a card cannot use is greyed with the
  reason on hover.
- **Saved pictures**: what Save wrote (PNG, CSV, JSON note), each with a delete.
- **New run**: the form in a drawer. Settings sit in their groups, folded ones closed. A gate is
  greyed with its reason. A list setting is shown as rows with ✕ and +. A setting naming another
  piece's run is a pick of those runs. Then Name, Sweep (a setting and its values), Clear and
  the run button.
- **Runs in progress** along the bottom, in place of the terminal: Queued, Running with %, Done,
  Failed with its error, Stopped. At most as many run side by side as the machine has cores.
- A draggable divider between the runs side and the cards side.

## 6. Shared calculations

Today each project computes its summary numbers by hand inside its runs. On 2026-11-13 the four
repos, outside their tests, held about 20 hand-written RMS formulas in five variants. In
Benchlab a number is **declared** in the record ("RMS of y1 − r1") and Benchlab computes it from
the same series the chart draws, so a number and its chart cannot disagree. Each calculation is
written once and its variants are named:

| Calculation | Variants, as found 2026-11-13 |
|---|---|
| RMS | per channel (DeePC `closed_loop/run.py:76`, BESS `estimator/run.py:184`); of a vector's length (RCWS `engagement/run.py:727`); skipping missing samples (RCWS `figure/validate.py:60`); over chosen samples (RCWS `track/log.py:305`); about the mean, the standard deviation (RCWS `servo_control/log.py:91`) |
| Run cost | wall time of the run, timed by Benchlab itself; per simulated second where the record states the simulated time (Hydrofoil `wall_s_per_sim_s` today) |
| Solver outcomes | every solve counted by its outcome (DeePC, BESS by hand today) |
| Estimator checks | the χ² consistency test with its band (BESS `record/consistency.py`, RCWS's tracker); the chart of truth, estimate and measurement inside the 95 % band (BESS, as RCWS's tracker draws it) |

A project computes its own number only where no shared calculation fits, and says so where the
number is declared.

## 7. Moving a project onto Benchlab

For each project, in its own branch, judged in its Lab:

1. Benchlab added at a pinned tag. The project's copies of `devkit/lab`, `figure`, `record` and
   `terminal` are deleted, and its pieces are declared to Benchlab.
2. Its words file written, filling every slot. Its code-name labels renamed to standard terms
   (decision 5, the developer's words) and its descriptions deleted.
3. Its hand-written numbers declared as shared calculations where one fits.
4. Its safety net bit for bit the same (BESS: its estimator record, diffed); every CLAUDE.md, README
   and skill that names the old layers updated; old names searched for (RCWS #159).

**Order** (decision 2): DeePC, Hydrofoil, BESS. **Watch:** DeePC is in the middle of its own
rewrite (`docs/project/design.md`: system → open loop → closed loop, three branches). Its move
onto Benchlab is planned against where that rewrite stands, never on top of a half-built branch.

## 8. Building Benchlab: the first branches (refined in plan mode)

1. **The core: DeePC's four layers, moved unchanged** (`docs/plan-branch-1.md`). Settings and
   records, the charts, the side door and DeePC's own page, moved from DeePC with only their ties
   to DeePC cut (its command, its title, its registry, its provenance). DeePC is moved onto it with
   every record and still identical, but for provenance (Benchlab's version added) and the
   wall-clock fields two runs of the same code already differ in. Changed in plan mode from "the core, without the page": a pure
   move is checkable bit for bit, a move plus a redesign is not, and without its page DeePC would
   lose its Lab between branches 1 and 2.
2. **The page and the runner.** The tree, runs, compare, cards, form and runs in progress, from
   BESS's Lab, with the runner (each run its own process) in place of the terminal, on Benchlab's
   own test project. The runner comes here with its first user, the page. Driven in DeePC.
3. **Hydrofoil moves**, with its naming pass.
4. **Shared calculations**: the RMS family, run cost and solver outcomes. DeePC's and Hydrofoil's
   numbers are declared instead of hand-written.
5. **BESS moves**, with the estimator checks.
6. **Old runs with notes, and Re-fly.**

## 9. Risks, said plainly

- **The run-file format becomes a contract across four repositories.** Changing it costs a
  version bump everywhere. Old runs stay readable (decision 9).
- **The union of every feature is the most to build**, and RCWS [A9] records "way too many stuff…
  cognitive overload" from an earlier Lab. Each branch is driven before the next, and a feature
  that proves to be noise is cut then.
- **Progress %** needs each run to report it. Until it does, a run shows elapsed time.
- **Panel's version**: DeePC and Hydrofoil pin `panel>=1.9.4,<1.10` today. Benchlab sets one
  pin for all three.
- **The repository is public**: no papers, no private data, no credentials in it.
- **RCWS's Lab** is twice the size of the others (scenes, overlays, validation, sweeps). Whether
  Benchlab can carry it is open until the other three work.
