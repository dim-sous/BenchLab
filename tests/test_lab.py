"""The Lab: its constraints, read off its own files (DeePC's ``tests/test_lab.py``, the half that
reads them, moved here with the Lab), and its page built over the made-up project's runs without a
browser.

The Lab holds no logic of its own: it imports only what lets it read declarations and files and
launch the project's command, reaches no third-party package but Panel, and never calls anything
that could compute on what it reads.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import re
import sys
import types
from pathlib import Path

import pytest

from benchlab import cli, project, record
from benchlab.lab import jobs, state
from benchlab.lab.app import Lab

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "benchlab" / "lab"
SOURCES = sorted(p for p in LAB.glob("*.py"))
#: Exactly what the Lab may take from the rest of Benchlab, by module and name.
_ALLOWED = {# the declared project: its pieces, and its command and title -- words, never the
            # project's module, which holds every piece (before the move: NAMES, get_component)
            "benchlab.project": {"piece_names", "get_component", "command", "title"},
            # a record's header keys, and how every word the page shows begins (the developer's
            # rule, 2026-10-27)
            "benchlab.record": {"read_header", "COMPONENT_KEY", "PANELS_KEY", "NUMBER_SPECS_KEY",
                                "PANEL_GROUPS_KEY", "HEADER_KEYS", "capital"},
            "benchlab.record.config": {"fields_of"},
            # the one constant saying where records live
            "benchlab.cli": {"DEFAULT_OUT_DIR"},
            # what a card draws is the figure layer's own: the panel built from what the records
            # declare and the card's controls hold, the refusal a control is greyed with, and the
            # twin of it the page shows; the colour a run wears is the figure layer's slot, so
            # its dot in the list matches its lines; the page's paper, inks, rules and type are
            # the figure layer's, so a chart sits on its card's paper
            "benchlab.figure.chart": {"chart_of", "sweep_of", "pool_refusal", "distinct"},
            "benchlab.figure.twin": {"figure_of"},
            "benchlab.figure.style": {"series_color", "FONT", "MONO", "SURFACE", "INK",
                                      "INK_SECONDARY", "GRID"}}
_THIRD_PARTY = {"panel", "param"}
_OWN = {"benchlab"}
#: The Lab's own package: what a Lab file takes from another Lab file is not checked here.
_LAB = "benchlab.lab"
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

@pytest.fixture
def two_runs(tmp_path) -> tuple[str, str]:
    """``first`` (the defaults) and ``second`` (A = 2), the first older by the clock."""
    out = tmp_path / "results"
    for words in (["--name", "first"], ["--set", "amplitude=2", "--name", "second"]):
        cli.main(["run", "wave", *words, "--out-dir", str(out)])
    first, second = out / "wave" / "first.json", out / "wave" / "second.json"
    now = second.stat().st_mtime
    os.utime(first, (now - 60, now - 60))            # the clock can step; pin the order
    return str(tmp_path), "results"


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
    it is run: the Lab may read a piece's declarations and must never exercise it."""
    stand_in = _tripwire(project.get_component("wave"))
    for module in (state, jobs):
        monkeypatch.setattr(module, "get_component", lambda _n, s=stand_in: s)
    root, out_dir = two_runs
    launched: list[list[str]] = []

    def launch(argv, cwd=None):
        launched.append(list(argv))
        return jobs.Job(list(argv))

    lab = Lab(root, out_dir, launch=launch, every=lambda cb, ms: None, toast=lambda _w: None)
    lab.page()
    lab._on_type("amplitude", "3")
    lab._on_pick("shape", "square")
    lab._on_sweep(field="frequency", values="1,3")
    lab._on_name("probe")
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
    assert launched and launched[0][:5] == ["uv", "run", "toy", "run", "wave"]
    assert not lab.banner.visible, lab.banner.object
    assert dataclasses.fields(stand_in.Record)      # the declarations WERE readable


def test_every_chart_on_the_page_is_the_figure_layers(monkeypatch, two_runs) -> None:
    """The page draws nothing of its own: with the figure layer's twin stubbed, every chart on
    the page is exactly what the stub returned, of exactly the panel the figure layer built for
    the shown runs' records in the order they were ticked."""
    import panel as pn

    import benchlab.lab.app as app_module
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
    assert lab.piece_select.options == {"Wave": "wave"}
    assert [r["name"] for r in state.records(root, out_dir)] == ["second", "first"]


def test_the_labs_own_command_line_names_the_projects_command() -> None:
    from benchlab.lab import cli as lab_cli
    parser = lab_cli.build_parser()
    assert parser.prog == "lab" and "It launches `toy run` for you" in parser.description
    [out_dir] = [a for a in parser._actions if a.dest == "out_dir"]
    assert out_dir.help.startswith("where `toy run` writes records")


def test_the_lab_launches_the_projects_command() -> None:
    assert jobs.run_argv("wave", ["amplitude=2"], "probe") == [
        "uv", "run", "toy", "run", "wave", "--set", "amplitude=2", "--name", "probe"]
    with pytest.raises(ValueError, match=r"unknown piece 'bogus'; registered: \['wave'\]"):
        jobs.run_argv("bogus", [], "probe")
