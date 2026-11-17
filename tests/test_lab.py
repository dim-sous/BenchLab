"""The Lab: its constraints, read off its own files (DeePC's ``tests/test_lab.py``, the half that
reads them, moved here with the Lab), and its page built over the made-up project's runs without a
browser.

The Lab holds no logic of its own but one rule it restates, held to param by ``tests/test_runner.py``:
it imports only what lets it read declarations and files and queue runs, reaches no third-party package but Panel, and never calls anything that could compute
on what it reads.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import shlex
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from runlab import project, record
from runlab.lab import jobs, state
from runlab.lab.app import Lab
from runlab.runner import planned
from tests.stand_ins import Process, settled

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "runlab" / "lab"
SOURCES = sorted(p for p in LAB.glob("*.py"))
#: Exactly what the Lab may take from the rest of RunLab, by module and name.
_ALLOWED = {# the declared project: its pieces, and its command and title -- words, never the
            # project's module, which holds every piece (before the move: NAMES, get_component)
            "runlab.project": {"piece_names", "get_component", "command", "title",
                                 # and the file of the page's own words (lab.words)
                                 "words_path"},
            # a record's header keys, and how every word the page shows begins (the developer's
            # rule, 2026-10-27)
            "runlab.record": {"read_header", "FILES_KEY", "COMPONENT_KEY", "PANELS_KEY", "NUMBER_SPECS_KEY",
                                "PANEL_GROUPS_KEY", "HEADER_KEYS", "capital"},
            # the settings' declarations; and a typed value read as the run will read it, so
            # Run refuses what the run would refuse before queueing it (decision 5)
            "runlab.record.config": {"fields_of", "coerce_value"},
            "runlab.record.files": {"kept", "discard"},
            # the one constant saying where records live
            "runlab.cli": {"DEFAULT_OUT_DIR"},
            # how a record name and the form's words become runs, the command line's own rule
            "runlab.runner": {"planned"},
            # what a card draws is the figure layer's own: the panel built from what the records
            # declare and the card's controls hold, the refusal a control is greyed with, and the
            # twin of it the page shows; the colour a run wears is the figure layer's slot, so
            # its dot in the list matches its lines; the page's paper, inks, rules and type are
            # the figure layer's, so a chart sits on its card's paper
            "runlab.figure.chart": {"chart_of", "sweep_of", "pool_refusal", "distinct"},
            "runlab.figure.twin": {"figure_of"},
            # a figure the piece draws itself, as the page's pane takes it: passed through
            "runlab.figure.own": {"own_figure"},
            "runlab.figure.style": {"series_color", "FONT", "MONO", "SURFACE", "INK",
                                      "INK_SECONDARY", "GRID"}}
_THIRD_PARTY = {"panel", "param"}
_OWN = {"runlab"}
#: The Lab's own package: what a Lab file takes from another Lab file is not checked here.
_LAB = "runlab.lab"
#: Call names that would make the Lab compute instead of read. Cheap to check and easy to
#: dodge by renaming, which is why the capability itself is held by the tripwire test below.
#: Loading a record through its class is READING (every rule of it the class's own), so
#: ``load`` is not here; building a trace is not reading, which the chart test holds.
_COMPUTES = {"run", "Config", "run_command", "draw_command"}


def _top(name: str) -> str:
    return name.split(".")[0]


def _module(node: ast.ImportFrom) -> str:
    """The module a ``from ... import`` names, absolute: a relative one resolved against the Lab's
    package, where ``from ..figure.render import render`` reaches past the allowlist."""
    if not node.level:
        return node.module
    base = _LAB.split(".")[:len(_LAB.split(".")) - node.level + 1]
    return ".".join(base + ([node.module] if node.module else []))


@pytest.mark.parametrize("path", SOURCES, ids=[p.name for p in SOURCES])
def test_the_lab_imports_only_its_allowlist_and_no_third_party_but_panel(path: Path) -> None:
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _top(alias.name)
                assert top in sys.stdlib_module_names or top in _THIRD_PARTY, \
                    f"{path.name} imports {alias.name}"
                assert top not in _OWN, f"{path.name}: `import {alias.name}` — only `from X import` of the allowlist"
        elif isinstance(node, ast.ImportFrom):
            module = _module(node)
            top = _top(module)
            if top in sys.stdlib_module_names or top in _THIRD_PARTY:
                continue
            if module == _LAB or module.startswith(_LAB + "."):
                continue
            taken = {a.name for a in node.names}
            allowed = _ALLOWED.get(module, set())
            assert taken <= allowed, (f"{path.name} takes {sorted(taken - allowed)} from "
                                      f"{module}; allowed: {sorted(allowed)}")


def test_the_header_keys_the_lab_reads_are_the_records_own() -> None:
    """``state`` names the header keys one by one; if the record layer gains another, this fails
    instead of every rail row turning red with a false 'holds gone field'."""
    assert state._HEADER == record.HEADER_KEYS


def test_the_lab_never_calls_what_could_compute_on_what_it_reads() -> None:
    hits = []
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in _COMPUTES:
                hits.append(f"{path.name}:{node.lineno} {func.id}(")
            elif isinstance(func, ast.Attribute) and func.attr in _COMPUTES:
                owner = func.value.id if isinstance(func.value, ast.Name) else ""
                if owner not in {"json", "subprocess"}:
                    hits.append(f"{path.name}:{node.lineno} .{func.attr}(")
    assert not hits, hits


# --- the page, over the made-up project's runs ---------------------------------------------

def _tripwire(real: types.ModuleType) -> types.SimpleNamespace:
    """The piece with everything the Lab may READ -- its declarations, and its records through
    ``Record.load``, which is reading -- and a raise on everything that would COMPUTE: running
    it, building its Config."""

    def boom(*_a, **_k):
        raise AssertionError("the Lab computed instead of reading")

    class Config(real.Config):
        def __init__(self, *_a, **_k):
            boom()

    return types.SimpleNamespace(Record=real.Record, Config=Config, run=boom)


def test_driving_the_lab_never_runs_the_piece_nor_builds_its_config(monkeypatch, two_runs) -> None:
    """The page is driven through every handler a person reaches, against a piece that raises if
    it is run: the Lab may read a piece's declarations and must never exercise it. Its runs are
    queued, never started here: their processes are stand-ins."""
    stand_in = _tripwire(project.get_component("wave"))
    for module in (state, jobs):
        monkeypatch.setattr(module, "get_component", lambda _n, s=stand_in: s)
    root, out_dir = two_runs
    started: list[jobs.Run] = []
    queue = jobs.Queue(at_once=1, start=lambda run: started.append(run) or Process())
    lab = Lab(root, out_dir, queue=queue, every=lambda cb, ms: None, toast=lambda _w: None)
    lab.page()
    lab._on_type("amplitude", "3")
    lab._on_pick("shape", "square")
    lab._on_sweep(field="frequency", values="1,3")
    lab._on_name("probe")
    lab._on_sweep(values="1,-3")                # refused at Run: read against the declaration
    lab._run()
    assert queue.runs() == [] and lab.sweep_note.visible
    lab._use("second")
    lab._run()
    lab._poll()
    lab.reload()
    lab.run_list.shown = ["second", "first"]
    lab._on_chart("y", True)
    lab.open_number("rms_y")
    for card in lab.cards:
        card.runs = "mean" if card.kind == "chart" else "each"
    lab._draw_cards()
    lab._on_settings("all")
    # Use loaded the second run's settings, and with them took back the name and sweep typed
    assert [(r.piece, r.name, r.pairs) for r in queue.runs()] == [
        ("wave", "wave-1", [("amplitude", "2")])]
    assert [r.name for r in started] == ["wave-1"]
    assert not lab.banner.visible, lab.banner.object
    for run in queue.runs():
        queue.stop(run.id)
    assert dataclasses.fields(stand_in.Record)      # the declarations WERE readable


def test_every_chart_on_the_page_is_the_figure_layers(monkeypatch, two_runs) -> None:
    """The page draws nothing of its own: with the figure layer's twin stubbed, every chart on
    the page is exactly what the stub returned, of exactly the panel the figure layer built for
    the shown runs' records in the order they were ticked."""
    import panel as pn

    import runlab.lab.app as app_module
    built: list[tuple[str, list[str]]] = []
    real_chart = app_module.chart_of

    def spy(pairs, name, **keywords):
        built.append((name, [run for run, _record in pairs]))
        return real_chart(pairs, name, **keywords)

    def stub(panel, legend=True):
        return {"data": [], "layout": {"height": 100, "meta": {"doc": f"stub {panel.name}",
                                                                "panel": panel.name}}}

    monkeypatch.setattr(app_module, "chart_of", spy)
    monkeypatch.setattr(app_module, "figure_of", stub)
    root, out_dir = two_runs
    lab = Lab(root, out_dir, every=lambda cb, ms: None, toast=lambda _w: None)
    lab.page()
    lab.run_list.shown = ["second", "first"]
    lab._on_chart("y", True)
    assert set(lab.open_charts) == {"u", "y"}
    drawn = {}
    for card in lab.cards_box.objects:                 # each card's chart, by its title's panel
        chart = re.search(r"data-panel='([^']+)'", card.objects[0].objects[0].object).group(1)
        drawn[chart] = next(o for o in card.objects if isinstance(o, pn.pane.Plotly)).object
    assert set(drawn) == {"u", "y"}
    for chart, fig in drawn.items():
        assert fig["layout"]["meta"]["doc"] == f"stub {chart}"
    assert built[-1] == ("y", ["second", "first"]), "the shown runs, in the order ticked"


def test_the_page_wears_the_projects_title_and_lists_its_pieces(two_runs) -> None:
    root, out_dir = two_runs
    lab = Lab(root, out_dir, every=lambda cb, ms: None, toast=lambda _w: None)
    header = lab.page().objects[0]
    assert ">Toy Lab</b>" in header.objects[0].object
    assert lab.piece_select.options == {"Wave": "wave", "Lag": "lag", "Fit": "fit"}
    assert [r["name"] for r in state.records(root, out_dir)] == ["second", "first"]


def test_the_labs_own_command_line_says_what_the_lab_does() -> None:
    from runlab.lab import cli as lab_cli
    parser = lab_cli.build_parser()
    assert parser.prog == "lab" and "the runs in progress along the bottom" in parser.description
    [out_dir] = [a for a in parser._actions if a.dest == "out_dir"]
    assert out_dir.help.startswith("where runs write records")


def test_the_line_the_lab_prints_is_the_side_door_command() -> None:
    """Moved from DeePC's ``tests/test_lab.py`` with the Lab (its argv tests), on the toy."""
    argv = jobs.run_argv("wave", ["amplitude=2"], "probe")
    assert argv == ["uv", "run", "toy", "run", "wave", "--set", "amplitude=2", "--name", "probe"]
    assert jobs.run_argv("wave", [], "p", "elsewhere")[-2:] == ["--out-dir", "elsewhere"]
    line = jobs.line_of(jobs.run_argv("wave", ["amplitude=2"], "a.b-c_1"))
    assert shlex.split(line) == jobs.run_argv("wave", ["amplitude=2"], "a.b-c_1"), "it reads back"
    with pytest.raises(ValueError, match=r"unknown piece 'bogus'; registered: \['wave', 'lag', 'fit'\]"):
        jobs.run_argv("bogus", [], "probe")


# --- runs in progress, on the page -------------------------------------------------------------

def _lab(root: str, out_dir: str, queue: jobs.Queue, toasts: list[str] | None = None) -> Lab:
    lab = Lab(root, out_dir, queue=queue, every=lambda cb, ms: None,
              toast=(toasts if toasts is not None else []).append)
    lab.page()
    return lab


def _strip(lab: Lab) -> list[str]:
    """Each row of the strip as its words, newest first: name · piece, state, clock, error."""
    return [" ".join(w for w in (r["name"], "·", r["piece"], r["words"], r["clock"], r["error"]) if w)
            for r in lab.strip_rows.rows]


def test_run_queues_the_form_and_the_list_shows_what_the_runs_wrote(two_runs, toy_installed) -> None:
    """End to end on the page: a sweep's runs, each its own process, side by side; when they end
    their records are listed and shown, and the strip says what each did."""
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=2)
    lab = _lab(root, out_dir, queue)
    assert not lab.strip_list.visible and "Nothing running" in lab.strip_summary.object
    lab.open_drawer()
    lab._on_sweep(field="frequency", values="1,3")
    lab._on_name("sw")
    lab._run()
    assert not lab.drawer.visible and lab.strip_list.visible, "Run shuts the form, opens the strip"
    assert [r.state for r in queue.runs()] == ["running", "running"]
    assert _strip(lab)[0].startswith("sw-frequency-3 · Wave Running")
    settled(lambda: all(r.finished for r in queue.runs()),
            lambda: [(r.name, r.state, r.error) for r in queue.runs()], timeout=60)
    lab._poll()
    assert {"sw-frequency-1", "sw-frequency-3"} <= {r["name"] for r in lab.runs()}
    assert lab.shown[-2:] == ["sw-frequency-1", "sw-frequency-3"], "listed and shown"
    assert "2 done" in lab.strip_summary.object
    assert all(" Done " in row for row in _strip(lab)), _strip(lab)


def test_a_refused_name_is_said_before_run_and_nothing_is_queued(two_runs) -> None:
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab._on_name("a b")
    assert lab.banner.visible and "cannot name a record" in lab.banner.object, "said before Run"
    lab._run()
    assert queue.runs() == [] and "cannot name a record" in lab.banner.object
    lab._on_name("ok")
    assert not lab.banner.visible


def test_run_never_waits_for_the_last_run_it_queues_beside_it(two_runs) -> None:
    root, out_dir = two_runs
    started: list[Process] = []
    queue = jobs.Queue(at_once=1, start=lambda run: started.append(Process()) or started[-1])
    lab = _lab(root, out_dir, queue)
    for name in ("one", "two"):
        lab._on_name(name)
        lab._run()
    assert [(r.name, r.state) for r in queue.runs()] == [("one", "running"), ("two", "queued")]
    assert _strip(lab)[0].startswith("two · Wave Queued") and "1 queued" in lab.strip_summary.object
    queue.stop_all()


def test_the_strip_says_each_state_and_stops_or_clears_a_run(two_runs) -> None:
    root, out_dir = two_runs
    started: list[Process] = []
    toasts: list[str] = []
    queue = jobs.Queue(at_once=1, start=lambda run: started.append(Process()) or started[-1])
    lab = _lab(root, out_dir, queue, toasts)
    for name in ("one", "two", "three"):
        lab._on_name(name)
        lab._run()
    one, two, three = queue.runs()
    lab.strip_rows._handle_msg({"stop": two.id})      # its Stop: a queued run never starts
    assert toasts[-1] == "Stopping…" and two.state == "stopped"
    started[0].end(1, "", "Traceback (most recent call last):\nValueError: no good\n")
    settled(lambda: one.finished and three.state == "running", lambda: _strip(lab))
    lab._poll()
    rows = _strip(lab)
    assert rows[0].startswith("three · Wave Running") and rows[1].startswith("two · Wave Stopped")
    assert rows[2].startswith("one · Wave Failed") and rows[2].endswith("ValueError: no good")
    assert [r["finished"] for r in lab.strip_rows.rows] == [False, True, True], "Stop, ✕, ✕"
    lab.strip_rows._handle_msg({"dismiss": one.id})  # its ✕
    assert [r.name for r in queue.runs()] == ["two", "three"] and len(_strip(lab)) == 2
    queue.stop_all()


def test_a_run_that_ended_before_the_page_opened_is_listed_but_not_ticked(two_runs) -> None:
    root, out_dir = two_runs
    started: list[Process] = []
    queue = jobs.Queue(at_once=1, start=lambda run: started.append(Process()) or started[-1])
    [run] = queue.submit("wave", planned("first"), root=root, out_dir=out_dir)
    started[0].end(0, '{"saved": "x"}')
    settled(lambda: run.finished, lambda: run.state)
    lab = _lab(root, out_dir, queue)
    assert "first" in {r["name"] for r in lab.runs()} and "first" not in lab.shown
    lab._poll()
    assert "first" not in lab.shown and _strip(lab)[0].startswith("first · Wave Done")


def test_reading_the_runs_failing_says_so_on_the_page(two_runs, monkeypatch) -> None:
    """Panel's periodic callback has no exception hook: a poll that raises is shown, not lost."""
    root, out_dir = two_runs
    started: list[Process] = []
    queue = jobs.Queue(at_once=1, start=lambda run: started.append(Process()) or started[-1])
    lab = _lab(root, out_dir, queue)
    lab._on_name("x")
    lab._run()

    def raises() -> None:
        raise OSError("the folder went away")

    monkeypatch.setattr(lab, "reload", raises)
    started[0].end(0, '{"saved": "x"}')
    settled(lambda: queue.runs()[0].finished, lambda: queue.runs()[0].state)
    lab._poll()                                       # does not propagate
    assert lab.banner.visible and "reading the runs failed: the folder went away" in lab.banner.object


def test_two_runs_with_the_name_box_empty_get_two_names(two_runs) -> None:
    """The name offered skips the names runs in progress write, not only those on disk: two
    runs of one record at once would lose one (2a review)."""
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab._run()
    assert lab.run_name.placeholder == "wave-2", "the first run's name is taken while it runs"
    lab._run()
    assert [r.name for r in queue.runs()] == ["wave-1", "wave-2"]
    queue.stop_all()


def test_a_name_a_run_in_progress_writes_is_refused_before_run(two_runs) -> None:
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab._on_name("same")
    lab._run()
    lab._on_name("same")
    assert lab.banner.visible and "same is queued or running already" in lab.banner.object
    lab._run()
    assert [r.name for r in queue.runs()] == ["same"]
    queue.stop_all()


def test_the_strip_shows_how_long_each_run_has_run(two_runs) -> None:
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab._on_name("timed")
    lab._run()
    [run] = queue.runs()
    run.started -= 75                                  # it started 75 s ago
    lab._poll()
    assert lab.strip_rows.rows[0]["clock"] == "1:15" and "1 running" in lab.strip_summary.object
    queue.stop_all()


def test_the_form_ends_where_the_strip_begins(two_runs) -> None:
    """A run can be stopped while the next is set up: the drawer never covers the strip, whose
    Stop replaced the header's (2a review)."""
    from runlab.lab import skin
    root, out_dir = two_runs
    lab = _lab(root, out_dir, jobs.Queue(at_once=1, start=lambda run: Process()))
    assert lab.drawer.styles["height"] == f"calc(100vh - {skin.HEADER_PX + skin.STRIP_PX}px)"
    lab._open_strip(True)
    assert lab.drawer.styles["height"] == (
        f"calc(100vh - {skin.HEADER_PX + skin.STRIP_PX + skin.STRIP_LIST_PX}px)")


# --- no hovers (``docs/design.md`` decision 5) -----------------------------------------------

def _drawn(lab: Lab) -> list[Any]:
    """Every Panel object the page draws: the header, both panes, the drawer, the strip."""
    import panel as pn
    page = lab.page()
    return [o for part in (page, lab.split.left, lab.split.right) for o in part.select()
            if isinstance(o, pn.viewable.Viewable)]


def test_no_setting_number_chart_or_plain_button_wears_a_hover(two_runs) -> None:
    """The mockup's round 2: no hover on a setting, a compare row, a card's title or foot, a
    button of the list or the index, or a card's close. A greyed card control keeps its reason
    on its hover: those words are RunLab's own."""
    import panel as pn

    from runlab.lab import skin
    root, out_dir = two_runs
    lab = _lab(root, out_dir, jobs.Queue(at_once=1, start=lambda run: Process()))
    lab.tick_listed()
    lab._on_settings("all")
    lab._on_chart("u", True)
    lab.open_number("rms_y")
    lab.open_drawer()
    drawn = _drawn(lab)
    titled = [o.object for o in drawn if isinstance(o, pn.pane.HTML) and "title=" in o.object]
    assert titled and all(skin.GREYED in t for t in titled), \
        [t for t in titled if skin.GREYED not in t]
    assert not [o for o in drawn if isinstance(o, pn.widgets.TooltipIcon)]
    assert not [o.name or o.label for o in drawn
                if isinstance(o, pn.widgets.Widget) and getattr(o, "description", None)]
    assert lab.compare_table.rows and not [r for r in lab.compare_table.rows if "hover" in r]


def _note(lab: Lab, name: str) -> str:
    """The words under a setting, as the page shows them; ``""`` when it shows none."""
    note = lab._notes[name]
    return re.sub(r"<[^>]+>", "", note.object) if note.visible else ""


def test_a_greyed_setting_says_why_under_it(two_runs) -> None:
    """Behind a closed gate, or as the sweep axis, a setting is greyed and says why under it:
    what its hover used to say."""
    root, out_dir = two_runs
    lab = _lab(root, out_dir, jobs.Queue(at_once=1, start=lambda run: Process()))
    lab.open_drawer()
    assert lab._controls["duty"].disabled
    assert _note(lab, "duty") == "Duty applies only when Shape is square; it is sine"
    lab._on_pick("shape", "square")
    assert not lab._controls["duty"].disabled and _note(lab, "duty") == ""
    lab._on_sweep(field="frequency", values="1,2")
    assert _note(lab, "frequency") == "f is the sweep axis; its values come from the sweep row"
    assert _note(lab, "amplitude") == "", "an open setting says nothing"


@pytest.mark.parametrize("picks, name, text, words", [
    ({}, "amplitude", "-1", "A must be at least 0, got -1"),
    ({}, "samples", "2.5", "N takes a whole number, got 2.5"),
    ({}, "frequency", "fast", "f takes a number, got fast"),
    ({"shape": "square"}, "duty", "1", "Duty must be below 1, got 1"),
    ({"shape": "square"}, "duty", "0", "Duty must be above 0, got 0"),
    ({}, "noise", "11", "σ must be at most 10, got 11"),
])
def test_a_value_its_setting_refuses_is_said_under_it_and_nothing_is_queued(
        two_runs, picks, name, text, words) -> None:
    """``docs/design.md`` decision 5, the developer's answer of 2026-11-14: refused when Run is
    pressed, under the setting; the form stays open and nothing is queued. Edited, the words go."""
    from runlab.lab import skin
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab.open_drawer()
    for pick, value in picks.items():
        lab._on_pick(pick, value)
    lab._on_type(name, text)
    assert _note(lab, name) == "", "not before Run: the range is not shown"
    lab._run()
    assert queue.runs() == [] and lab.drawer.visible
    assert _note(lab, name) == words and skin.SIGNAL in lab._notes[name].object, "in red"
    lab._on_type(name, text + "0" if text != "fast" else "3")
    assert _note(lab, name) == "", "edited, its words go"


def test_a_sweep_value_its_setting_refuses_is_said_under_the_sweep_row(two_runs) -> None:
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab.open_drawer()
    lab._on_sweep(field="amplitude", values="1, -1, 2")
    lab._run()
    assert queue.runs() == [] and lab.drawer.visible
    assert lab.sweep_note.visible and "A must be at least 0, got -1" in lab.sweep_note.object
    lab._on_sweep(values="1, 2")
    assert not lab.sweep_note.visible
    lab._run()
    assert [r.name for r in queue.runs()] == ["wave-1-amplitude-1", "wave-1-amplitude-2"]
    queue.stop_all()


def test_another_piece_leaves_no_box_holding_the_last_forms_words(two_runs) -> None:
    """The name and sweep boxes outlive a form: picking a piece left them, and the form's head,
    saying what the last form held, which the next Run no longer used (found driving 2b's
    hand-off, 2026-11-14). The toy declares one piece; picking it again is a new form too."""
    root, out_dir = two_runs
    lab = _lab(root, out_dir, jobs.Queue(at_once=1, start=lambda run: Process()))
    lab.open_drawer(from_run="second")
    lab.sweep_field.value = "frequency"
    lab.sweep_values.value_input = "1, 3"
    lab.run_name.value_input = "mine"
    assert (lab.form.name, lab.form.sweep_values) == ("mine", "1, 3")
    assert "From second" in lab.from_words.object
    lab._on_piece("wave")
    assert (lab.run_name.value_input, lab.sweep_values.value_input, lab.sweep_field.value) == \
        ("", "", "")
    assert (lab.form.name, lab.form.sweep_values, lab.form.set) == ("", "", {})
    assert "From defaults" in lab.from_words.object


def test_a_refusal_goes_with_clear_with_use_and_with_a_gate_that_shuts(two_runs) -> None:
    """What Run refused is said until what it was said of is gone (2b review): Clear empties the
    form, Use loads another run's values, a gate that shuts takes the value back -- and then the
    setting says why it is greyed, not what was refused."""
    root, out_dir = two_runs
    lab = _lab(root, out_dir, jobs.Queue(at_once=1, start=lambda run: Process()))
    lab.open_drawer()
    for leave in (lab._clear, lambda: lab.open_drawer(from_run="first")):
        lab._on_type("amplitude", "-1")
        lab._run()
        assert _note(lab, "amplitude") == "A must be at least 0, got -1"
        leave()
        assert _note(lab, "amplitude") == "", leave
    lab._on_pick("shape", "square")
    lab._on_type("duty", "1")
    lab._run()
    assert _note(lab, "duty") == "Duty must be below 1, got 1"
    lab._on_pick("shape", "sine")
    assert _note(lab, "duty") == "Duty applies only when Shape is square; it is sine"


def test_a_refusal_in_a_folded_group_opens_it(two_runs) -> None:
    """Said under a setting whose group is folded, a refusal was on no line the page showed, and
    Run changed nothing on screen (2b review): Run opens that group."""
    root, out_dir = two_runs
    queue = jobs.Queue(at_once=1, start=lambda run: Process())
    lab = _lab(root, out_dir, queue)
    lab.open_drawer()
    fold = lab._folds["Run"]
    assert not fold.value, "the toy's Run group starts folded"
    lab._on_type("delay", "-1")
    lab._run()
    assert queue.runs() == [] and fold.value, "opened"
    body = lab.form_box.objects[-1].objects[1]
    assert body.visible and _note(lab, "delay") == "Delay must be at least 0, got -1"
