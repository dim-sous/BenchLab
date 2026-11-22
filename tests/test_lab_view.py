"""The page, driven in Python (DeePC's ``tests/test_lab_view.py``, itself BESS's, moved here onto
the made-up project in branch R1).

A screen is validated by DRIVING it, never by a checklist (RCWS's own Lab incident: four designs
passed their checklists and were rejected on first contact). These tests drive the widgets a
person touches -- not the handlers behind them -- with the queue, ``every`` and ``toast``
injected. How a run is queued, followed and stopped is ``tests/test_runner.py``'s and
``tests/test_lab.py``'s.
"""

from __future__ import annotations

import copy
import dataclasses
import html
import json
import os
import re
import shutil
import socket
import threading
import time
import types
import urllib.request
from pathlib import Path

import panel as pn
import pytest

from runlab import cli
from runlab.figure.chart import chart_of
from runlab.figure.render import DASHES
from runlab.figure.style import series_color, shade
from runlab.figure.twin import figure_of
import runlab.lab.app as app_module
from runlab.lab import jobs, shaping, skin, state
from runlab.lab.app import Lab, page, serve
from runlab.lab.form import interval


def _wave(root: str, out_dir: str, name: str, *sets: str) -> str:
    """A saved wave run under ``<root>/<out_dir>/wave/``, written by the command line; its path
    as the Lab offers it."""
    cli.main(["run", "wave", "--name", name, "--out-dir", str(Path(root) / out_dir),
              *(w for item in sets for w in ("--set", item))])
    return f"{out_dir}/wave/{name}.json"


@pytest.fixture
def lag_runs(two_runs) -> tuple[str, str]:
    """Beside the wave's two runs, two of the lag on the wave's ``first``: ``first`` (the
    defaults) and ``second`` (τ = 0.2), the first older by the clock."""
    root, out_dir = two_runs
    out = Path(root) / out_dir
    base = ["run", "lag", "--set", f"wave_run={out / 'wave' / 'first.json'}", "--out-dir", str(out)]
    cli.main(base + ["--name", "first"])
    cli.main(base + ["--set", "tau=0.2", "--name", "second"])
    now = (out / "lag" / "second.json").stat().st_mtime
    os.utime(out / "lag" / "first.json", (now - 60, now - 60))
    return root, out_dir


class _Ticker:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.stopped = 0

    def __call__(self, callback, period_ms):
        self.calls.append((callback, period_ms))
        return self

    def stop(self) -> None:
        self.stopped += 1


class _Unstarted:
    """A run's process, stood in for: it never runs a piece and ends only when stopped."""

    returncode = None

    def __init__(self) -> None:
        self._ended = threading.Event()

    def communicate(self) -> tuple[str, str]:
        self._ended.wait()
        return "", ""

    def terminate(self) -> None:
        self.returncode = -15
        self._ended.set()


def _lab(runs, piece: str = "") -> tuple[Lab, jobs.Queue, _Ticker, list[str]]:
    """The page over ``runs``, on ``piece`` when one is named, its runs queued but never run
    (their processes stand-ins)."""
    root, out_dir = runs
    queue, ticker, toasts = jobs.Queue(start=lambda run: _Unstarted()), _Ticker(), []
    lab = Lab(root, out_dir, queue=queue, every=ticker, toast=toasts.append)
    lab.page()
    if piece:
        lab.piece_select.value = piece
    return lab, queue, ticker, toasts


def _queued(queue: jobs.Queue) -> list[tuple[str, list[tuple[str, str]]]]:
    """What Run queued: each run's record name and setting pairs."""
    return [(r.name, r.pairs) for r in queue.runs()]


def _type(lab: Lab, name: str, text: str) -> None:
    """Type into a box as a person does: the browser sends both of its values."""
    box = lab._controls[name]
    box.value = text
    box.value_input = text


def _pick(lab: Lab, name: str, value: str) -> None:
    lab._controls[name].value = value


def _name(lab: Lab, text: str) -> None:
    lab.run_name.value = text
    lab.run_name.value_input = text


def _sweep(lab: Lab, field: str, values: str) -> None:
    lab.sweep_field.value = field
    lab.sweep_values.value = values
    lab.sweep_values.value_input = values


def _names(lab: Lab) -> list[str]:
    """The run names the list shows, newest first."""
    return [row["name"] for row in lab.run_list.rows]


def _tick(lab: Lab, name: str, on: bool = True) -> None:
    """Click a row in the list: the component toggles the name in ``shown``."""
    shown = list(lab.run_list.shown)
    if on and name not in shown:
        shown.append(name)
    elif not on and name in shown:
        shown.remove(name)
    lab.run_list.shown = shown


def _tabs(lab: Lab) -> dict[str, pn.widgets.Toggle]:
    return lab.toggles()


def _card_of(lab: Lab, chart: str = "", number: str = ""):
    return next(c for c in lab.cards if (c.chart == chart if chart else c.number == number))


def _rows_of(lab: Lab, panel: str) -> list[str]:
    """The runs a chart card draws, in order."""
    return list(lab.drawn.get(_card_of(lab, panel).id, []))


def _card(lab: Lab, panel: str) -> pn.Column:
    for card in lab.cards_box.objects:
        top = getattr(card, "objects", [None])[0]
        title = getattr(top, "objects", [None])[0] if top is not None else None
        if f"data-panel='{html.escape(panel)}'" in getattr(title, "object", ""):
            return card
    raise AssertionError(f"no card for {panel}; cards: {lab.cards_box.objects}")


def _card_words(lab: Lab, panel: str) -> list[str]:
    """The lines a card carries beside or instead of its figure, as words: its foot."""
    return [html.unescape(re.sub(r"<[^>]+>", "", o.object))
            for o in _card(lab, panel).objects[1:] if isinstance(o, pn.pane.HTML)]


def _greyed(lab: Lab, panel: str) -> dict[str, str]:
    """A card's greyed controls: their words -> the reason on their hover."""
    out = {}
    tools = next(o for o in _card(lab, panel).objects[1:] if isinstance(o, pn.FlexBox))
    for group in tools.objects:
        for o in group.objects:
            if isinstance(o, pn.pane.HTML) and "opacity:.45" in o.object:
                words = html.unescape(re.sub(r"<[^>]+>", "", o.object))
                out[words] = html.unescape(re.search(r'title="([^"]*)"', o.object).group(1))
    return out


def _control(lab: Lab, panel: str, words: str) -> pn.widgets.Toggle:
    tools = next(o for o in _card(lab, panel).objects[1:] if isinstance(o, pn.FlexBox))
    return next(o for g in tools.objects for o in g.objects
                if isinstance(o, pn.widgets.Toggle) and o.name == words)


def _figure(lab: Lab, panel: str) -> dict | None:
    """The figure a card draws, as its Plotly pane holds it; ``None`` when it draws none."""
    pane = next((o for o in _card(lab, panel).objects if isinstance(o, pn.pane.Plotly)), None)
    return None if pane is None else pane.object


def _columns(lab: Lab) -> list[str]:
    """The compare table's column heads: one per shown run, in the order they were ticked."""
    return list(lab.compare_table.heads)


# ---------------------------------------------------------------- running a piece

def test_use_loads_a_runs_settings_into_the_form_and_the_widgets_and_clear_empties(lag_runs) -> None:
    lab, _queue, _ticker, toasts = _lab(lag_runs, "lag")
    lab.open_drawer("second")                        # what the list's `use` reaches
    assert lab.drawer.visible and "From second" in lab.from_words.object
    data = str(Path(lag_runs[0]) / lag_runs[1] / "wave" / "first.json")
    assert lab.form.set == {"wave_run": data, "tau": "0.2"}
    assert lab._controls["tau"].value == "0.2" and lab._controls["wave_run"].value == data
    assert lab._controls["gain"].value == ""
    assert skin.CHANGED in lab._controls["tau"].stylesheets, "a value away from its default"
    assert skin.CHANGED not in lab._controls["gain"].stylesheets
    assert "1 of 3 changed" in lab._group_notes["Lag"].object
    assert toasts[-1] == "2 settings loaded from second"
    lab._clear()
    assert lab.form.set == {} and lab._controls["tau"].value == ""
    assert skin.CHANGED not in lab._controls["tau"].stylesheets
    assert "From defaults" in lab.from_words.object
    lab.close_drawer()
    assert not lab.drawer.visible


def test_a_value_the_page_itself_wrote_does_not_hide_the_next_keystroke(two_runs) -> None:
    """A box carries two values and a programmatic write sets one: retyping what ``use`` loaded
    over must reach the form, or the run uses a number the box does not show."""
    lab, _queue, _ticker, _toasts = _lab(two_runs)
    _type(lab, "amplitude", "2")
    lab._use("second")                               # writes A = 2 over the typed 2
    _type(lab, "amplitude", "5")
    assert lab.form.set["amplitude"] == "5"
    overrides = lab.form.launch_words()[0]
    assert "amplitude=5" in overrides and "amplitude=2" not in overrides


def test_a_sweep_the_page_cleared_is_not_resurrected_by_picking_an_axis(two_runs) -> None:
    lab, _queue, _ticker, _toasts = _lab(two_runs)
    _sweep(lab, "amplitude", "1,5")
    assert lab.form.launch_words()[1] == ["amplitude=1,5"]
    lab._clear()
    lab.sweep_field.value = "samples"                # an axis, with the values box now empty
    assert lab.form.launch_words() == ([], []) and lab.form.sweep_values == ""


def test_a_saved_run_setting_is_picked_from_that_pieces_saved_runs(tmp_path) -> None:
    """RCWS's record picker (``record_of``): the lag's form offers the wave piece's saved runs by
    name, the default first, and queues the path picked."""
    runs = str(tmp_path), "results"
    _wave(*runs, "default")
    noisy = _wave(*runs, "noisy", "noise=0.05")
    lab, queue, *_ = _lab(runs, "lag")
    assert lab._controls["wave_run"].options == {"default (default)": "", "noisy": noisy}
    _pick(lab, "wave_run", noisy)
    _name(lab, "on-noisy")
    lab._run()
    assert _queued(queue) == [("on-noisy", [("wave_run", noisy)])]


def test_a_folded_groups_settings_are_folded_until_opened_and_say_what_changed(two_runs) -> None:
    """The wave's three Run settings, folded: the heading opens them, its note counts what
    changed, and a redraw keeps them open."""
    lab, *_ = _lab(two_runs)

    def head_and_body():
        for section in lab.form_box.objects:
            head, body = section.objects[0].objects[0], section.objects[1]
            if isinstance(head, pn.widgets.Toggle) and head.label.endswith("Run"):
                return head, body
        raise AssertionError("no folded group for the Run settings")

    head, body = head_and_body()
    assert head.label == "▸ Run" and not body.visible
    assert "3 at defaults" in lab._group_notes["Run"].object
    head.value = True
    assert head.label == "▾ Run" and body.visible
    _type(lab, "delay", "0.5")
    assert "1 of 3 changed" in lab._group_notes["Run"].object
    lab._draw_form()
    head, body = head_and_body()
    assert body.visible and head.value, "opened, it stays open"


def test_a_setting_with_a_range_shows_it_under_its_box_and_one_without_shows_nothing(
        two_runs) -> None:
    """The range is on the page before anything is typed; BESS's page had it in a mouse-over."""
    lab, *_ = _lab(two_runs)
    whole = lab.page()
    under: dict[str, list[str]] = {}
    for col in whole.select(pn.Column):
        for f in lab.form.fields:
            if col.objects and col.objects[0] is lab._controls.get(f["name"]):
                under[f["name"]] = [re.sub(r"<[^>]+>", "", o.object) for o in col.objects[1:]
                                    if isinstance(o, pn.pane.HTML)]
    assert under["duty"][0] == "(0 … 1)" and under["samples"][0] == "[2 … ∞)"
    ranged = [n for n in under if interval(lab.form.by_name[n])]
    assert all(under[n][0] == interval(lab.form.by_name[n]) and len(under[n]) == 2 for n in ranged)
    plain = [n for n in under if n not in ranged]
    assert plain and all(len(under[n]) == 1 for n in plain), "the note's line alone"


def test_a_typed_box_is_empty_and_greyed_once_a_pick_shuts_its_gate(two_runs) -> None:
    lab, *_ = _lab(two_runs)
    _pick(lab, "shape", "square")                    # the duty applies to the square wave only
    _type(lab, "duty", "0.3")
    assert lab._controls["duty"].value == "0.3" and lab.form.set == {"shape": "square", "duty": "0.3"}
    _pick(lab, "shape", "")
    box = lab._controls["duty"]
    assert box.value == "" and box.value_input == "" and box.disabled
    assert lab.form.set == {}
    assert lab._notes["duty"].visible and \
        "applies only when Shape is square" in lab._notes["duty"].object, "said under it"
    assert "taken back" in lab.form_note.object      # said, not silently dropped
    _pick(lab, "shape", "square")
    assert not box.disabled


def test_the_sweep_axis_box_is_greyed_once_the_sweep_row_names_it_and_holds_values(two_runs) -> None:
    lab, queue, *_ = _lab(two_runs)
    _type(lab, "amplitude", "10")
    lab.sweep_field.value = "amplitude"
    assert not lab._controls["amplitude"].disabled           # named, no values yet
    _sweep(lab, "amplitude", "1,5")
    assert lab._controls["amplitude"].disabled and lab._controls["amplitude"].value == ""
    assert lab._notes["amplitude"].visible and "is the sweep axis" in lab._notes["amplitude"].object
    _name(lab, "sw")
    lab._run()
    assert _queued(queue) == [("sw-amplitude-1", [("amplitude", "1")]),
                              ("sw-amplitude-5", [("amplitude", "5")])]


def test_a_record_that_cannot_be_read_is_listed_and_offers_nothing_to_load(two_runs, tmp_path) -> None:
    root, out_dir = two_runs
    folder = tmp_path / "elsewhere" / out_dir / "wave"
    folder.mkdir(parents=True)
    shutil.copy(Path(root) / out_dir / "wave" / "first.json", folder / "good.json")
    (folder / "kept-setup.json").write_text('{"amplitude": 2}')
    lab = Lab(str(tmp_path / "elsewhere"), out_dir, every=_Ticker(), toast=lambda _w: None)
    lab.page()
    rows = {row["name"]: row for row in lab.run_list.rows}
    assert sorted(rows) == ["good", "kept-setup"]
    assert not rows["good"]["stale"]
    assert "carries no" in rows["kept-setup"]["stale"], "a stale row says why under its name"
    assert lab.shown == ["good"]


def test_a_page_that_cannot_be_built_shows_why_instead_of_nothing(tmp_path: Path) -> None:
    lab = Lab(str(tmp_path), "results", every=_Ticker(), toast=lambda _w: None)
    assert isinstance(lab.page(), pn.Column)               # the healthy case, for contrast

    def raises(*_a, **_k):
        raise ValueError("the registry would not read")

    import runlab.lab.app as app_module
    original = app_module.Lab
    app_module.Lab = raises
    try:
        shown = page(str(tmp_path), "results")
    finally:
        app_module.Lab = original
    assert isinstance(shown, pn.pane.HTML)
    assert "could not build its page" in shown.object and "would not read" in shown.object


def test_the_page_is_served_on_127_0_0_1_and_builds_for_that_root(two_runs) -> None:
    root, out_dir = two_runs
    assert isinstance(page(root, out_dir), pn.Column), "a traceback pane would also carry a title"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    handler = pn.config.exception_handler
    server = serve(port, root, out_dir, show=False, threaded=True)
    try:
        deadline = time.time() + 20
        while True:
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read()
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.2)
        assert "<title>Toy Lab</title>" in body.decode()
    finally:
        server.stop()
        pn.config.exception_handler = handler          # `serve` sets it process-wide


# ---------------------------------------------------------------- reading the runs

def test_one_browser_message_carrying_both_values_of_a_box_is_one_edit(two_runs) -> None:
    """A paste, or a key and Tab together, reach the page as ONE message holding the box's two
    values. One watcher over both got two events from it and the run kept its default while the
    box showed the value (2026-10-27, headless Chromium): the box is read on `value_input`."""
    lab, *_ = _lab(two_runs)
    lab._controls["amplitude"].param.update(value="4", value_input="4")
    assert lab.form.set == {"amplitude": "4"} and lab.form.launch_words()[0] == ["amplitude=4"]
    lab.run_name.param.update(value="probe", value_input="probe")
    assert lab.form.name == "probe"
    lab.sweep_values.param.update(value="1,2", value_input="1,2")
    assert lab.form.sweep_values == "1,2"


def test_the_newest_run_is_shown_and_charted_and_ticking_another_adds_it_and_a_column(two_runs) -> None:
    lab, *_ = _lab(two_runs)
    assert lab.shown == ["second"], "the newest, so the screen is never empty"
    assert lab.open_charts == ["u"] and _rows_of(lab, "u") == ["second"], "and its first panel open"
    assert _columns(lab) == ["second"]
    assert "tick another run" in lab.compare_count.object
    _tick(lab, "first")
    assert lab.shown == ["second", "first"]
    assert _columns(lab) == ["second", "first"], "the columns follow the order ticked"
    assert _rows_of(lab, "u") == ["second", "first"], "every shown run, in that order"
    assert "1 setting" in lab.compare_count.object and "differ" in lab.compare_count.object
    colours = [r["colour"] for r in lab.run_list.rows]
    assert colours[0] and colours[1] and colours[0] != colours[1], "a shown run's dot is its colour"
    _tick(lab, "second", False)
    assert lab.shown == ["first"] and _columns(lab) == ["first"] and _rows_of(lab, "u") == ["first"]


def test_opening_a_chart_is_the_figure_layers_and_queues_no_run(lag_runs) -> None:
    lab, queue, *_ = _lab(lag_runs, "lag")
    _tabs(lab)["bode-phase"].value = True
    assert queue.runs() == [], "a chart is drawn by the figure layer in the page, not a run"
    assert [lab.cards_box.objects.index(_card(lab, p))
            for p in ("output", "bode-phase")] == [0, 1], "cards in the record's declared order"
    fig = _figure(lab, "bode-phase")
    assert fig["layout"]["yaxis"]["title"]["text"] == "∠G [deg]", "the record's own words"
    assert fig["layout"]["xaxis"]["title"]["text"] == "ω [rad/s]"
    title = _card(lab, "bode-phase").objects[0].objects[0].object
    assert "title=" not in title, "no hover on the title"
    assert not any("down to -90" in w for w in _card_words(lab, "bode-phase")), \
        "nor its description anywhere on the card"
    assert "2 of 4 open" in lab.open_count.object
    assert list(lab._lines) == ["Time", "Frequency"], "listed in the record's groups"
    assert all(f">{group}<" in line.objects[0].object for group, line in lab._lines.items())
    _tabs(lab)["output"].value = False
    assert lab.open_charts == ["bode-phase"]


def test_a_control_a_card_cannot_use_is_greyed_with_the_reason_on_its_hover(lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    greyed = _greyed(lab, "output")
    log_y = greyed.pop("Log y")
    assert greyed == {"Log x": "Its bottom axis holds 1 value(s) at or below zero",
                      "Run | Quantity": "One run shown",
                      "Overlay | Split | Mean | RMS": "One run shown"}
    assert re.fullmatch(r"It holds \d+ value\(s\) at or below zero", log_y), \
        "the figure layer's own words, begun with a capital"
    _tick(lab, "first")
    greyed = _greyed(lab, "output")
    assert greyed["Mean"] == "The chart declares no statistic"
    assert greyed["RMS"] == "The chart declares no statistic"
    assert sorted(greyed) == ["Log x", "Log y", "Mean", "RMS"], "two runs: the colour is free"
    _control(lab, "output", "Split").value = True
    assert _greyed(lab, "output")["Run | Quantity"] == \
        "Split: the colour tells the quantities apart"


def test_runs_that_differ_in_their_seed_alone_pool_on_a_card_into_one_line(tmp_path) -> None:
    """The wave's y declares Mean and RMS; two seeds of one wave pool into one line. The lag holds
    no seed, so its charts declare no statistic (the test above)."""
    runs = str(tmp_path), "results"
    for seed in (1, 2):
        _wave(*runs, f"seed-{seed}", "noise=0.5", f"seed={seed}")
    lab, *_ = _lab(runs)
    _tick(lab, "seed-1")
    _tabs(lab)["y"].value = True
    assert "Mean" not in _greyed(lab, "y")
    _control(lab, "y", "Mean").value = True
    fig = _figure(lab, "y")
    names = [t["name"] for t in fig["data"] if t.get("showlegend") is not False]
    assert names == ["95% interval of the mean, N = 2", "Mean of 2 runs · y"]
    assert _greyed(lab, "y")["Run | Quantity"] == "The pooled runs are one line per quantity"


# --- a card's controls: the axes, the runs, the drawing, the view ------------------------------

def _row(lab: Lab, panel: str) -> list[list[str]]:
    """A card's row of controls, group by group, as the words on it: a label or a greyed
    control's words, a button's, a list's choice in brackets."""
    tools = next(o for o in _card(lab, panel).objects[1:] if isinstance(o, pn.FlexBox))
    out = []
    for group in tools.objects:
        words = []
        for o in group.objects:
            if isinstance(o, pn.widgets.Toggle):
                words.append(o.name)
            elif isinstance(o, pn.widgets.Select):
                words.append(f"[{next((w for w, v in o.options.items() if v == o.value), '')}]")
            else:
                words.append(html.unescape(re.sub(r"<[^>]+>", "", o.object)))
        out.append(words)
    return out


def _list(lab: Lab, panel: str) -> pn.widgets.Select:
    """A card's one list: the bottom axis."""
    tools = next(o for o in _card(lab, panel).objects[1:] if isinstance(o, pn.FlexBox))
    return next(o for g in tools.objects for o in g.objects if isinstance(o, pn.widgets.Select))


def _lines(lab: Lab, panel: str) -> list[dict]:
    """The traces a card's figure draws as lines or dots: not a band's edges, not a reference."""
    return [t for t in _figure(lab, panel)["data"]
            if t.get("line", {}).get("width") and "dash" in t["line"] and "marker" in t]


def _table(lab: Lab, panel: str) -> tuple[list[str], list[list[str]], list[str]]:
    """The table in a card's place: its header, its rows, the lines beside it."""
    sheet = next(o for o in _card(lab, panel).objects
                 if isinstance(o, pn.pane.HTML) and "class='numbers'" in o.object).object
    cells = lambda tag, text: [html.unescape(c) for c in re.findall(rf"<{tag}>(.*?)</{tag}>", text)]
    rows = [cells("td", row) for row in re.findall(r"<tr>(.*?)</tr>", sheet.split("<tbody>")[1])]
    return (cells("th", sheet), rows,
            [html.unescape(re.sub(r"<[^>]+>", "", w))
             for w in re.findall(r"<div(?: class='dim')?>(.*?)</div>", sheet.split("class='beside'>")[1])])


def test_a_chart_card_carries_every_control_in_four_groups_and_opens_as_it_drew(lag_runs) -> None:
    """The developer's answers of 2026-11-17: X, Log x, Log y; Colour by, Runs; Dots or Lines;
    Chart or Table. A card opens on the drawing it made before it had them."""
    lab, *_ = _lab(lag_runs, "lag")
    _tick(lab, "first")
    before = copy.deepcopy(_figure(lab, "output"))
    assert _row(lab, "output") == [
        ["X", "[t [s]]", "Log x", "Log y"],
        ["Colour by", "Run", "Quantity", "Runs", "Overlay", "Split", "Mean", "RMS"],
        ["Dots", "Lines"], ["Chart", "Table"]]
    assert list(_list(lab, "output").options) == ["t [s]", "Sample index [-]"]
    held = {name: _control(lab, "output", name).value
            for name in ("Run", "Quantity", "Overlay", "Dots", "Lines", "Chart", "Table")}
    assert held == {"Run": True, "Quantity": False, "Overlay": True, "Dots": False, "Lines": True,
                    "Chart": True, "Table": False}
    panel = chart_of([(run["name"], lab._record_of(run)[0]) for run in lab.shown_runs()], "output")
    assert _figure(lab, "output") == before == figure_of(panel), \
        "the figure layer's drawing with no keyword given"
    # each control reaches the drawing
    _control(lab, "output", "Quantity").value = True
    assert [(t["line"]["color"], t["line"]["dash"]) for t in _lines(lab, "output")] == \
        [(shade(series_color(0), i), DASHES[i]) for i in (0, 1)], \
        "one quantity, y: one hue, each run a shade and a dash of it"
    _control(lab, "output", "Dots").value = True
    assert all(t["mode"] == "markers" for t in _lines(lab, "output"))
    _list(lab, "output").value = "index"
    fig = _figure(lab, "output")
    assert fig["layout"]["xaxis"]["title"]["text"] == "Sample index [-]"
    assert _lines(lab, "output")[0]["x"][:3] == [0.0, 1.0, 2.0]
    card = _card_of(lab, "output")
    assert (card.colour_by, card.points, card.x) == ("quantity", True, "index")
    # a card keeps its choices while it is open; closed and opened again, it starts over
    _tick(lab, "first", on=False)
    _tick(lab, "first")
    assert all(t["mode"] == "markers" for t in _lines(lab, "output"))
    assert _row(lab, "output")[0][1] == "[Sample index [-]]"
    _tabs(lab)["output"].value = False
    _tabs(lab)["output"].value = True
    assert _figure(lab, "output") == before


def test_a_logarithmic_axis_opens_as_the_chart_declares_and_is_switched_on_the_card(
        lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    _tabs(lab)["bode-magnitude"].value = True
    axes = lambda: tuple(_figure(lab, "bode-magnitude")["layout"][a].get("type")
                         for a in ("xaxis", "yaxis"))
    assert (_control(lab, "bode-magnitude", "Log x").value,
            _control(lab, "bode-magnitude", "Log y").value) == (True, True), "as declared"
    assert axes() == ("log", "log") and not _greyed(lab, "bode-magnitude").keys() & {"Log x", "Log y"}
    _control(lab, "bode-magnitude", "Log y").value = False
    assert axes() == ("log", None)
    _control(lab, "bode-magnitude", "Log y").value = True
    assert axes() == ("log", "log")
    # over the sample index the chart declares no logarithm, and the index holds a zero
    _list(lab, "bode-magnitude").value = "index"
    assert axes() == (None, "log")
    assert _greyed(lab, "bode-magnitude")["Log x"] == \
        "Its bottom axis holds 1 value(s) at or below zero"
    _list(lab, "bode-magnitude").value = "own"
    assert axes() == ("log", "log"), "back on its own axis, as declared again"
    # switched on by hand and then put over the index: refused in the figure layer's words,
    # the switch left to press off
    _control(lab, "bode-magnitude", "Log x").value = False
    _control(lab, "bode-magnitude", "Log x").value = True
    _list(lab, "bode-magnitude").value = "index"
    assert _figure(lab, "bode-magnitude") is None
    assert any("cannot take a logarithmic bottom axis" in w
               for w in _card_words(lab, "bode-magnitude"))
    _control(lab, "bode-magnitude", "Log x").value = False
    assert axes() == (None, "log")


def test_a_table_in_a_cards_place_is_the_numbers_on_its_chart(lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    _tick(lab, "first")
    record = {run["name"]: lab._record_of(run)[0] for run in lab.shown_runs()}
    _control(lab, "output", "Table").value = True
    assert _figure(lab, "output") is None and _card_of(lab, "output").id not in lab._panes, \
        "no chart, and nothing for a zoom to reach"
    header, rows, beside = _table(lab, "output")
    assert header == ["t [s]", "second", "first"], "one column per line"
    assert len(rows) == len(record["first"].t)
    assert rows[3] == [f"{v:.6g}" for v in (record["first"].t[3], record["second"].y[3],
                                            record["first"].y[3])]
    assert beside == ["Lower bound of y [-]: -1", "Upper bound of y [-]: 1",
                      "Six significant digits here; Save writes every digit to a file beside "
                      "the picture"]
    _control(lab, "output", "Split").value = True
    assert _table(lab, "output")[0] == ["t [s]", "second · y", "first · y"]
    _control(lab, "output", "Chart").value = True
    assert _figure(lab, "output") is not None
    assert lab.page().get_root() is not None, "the page builds with a table on it"


def test_a_number_card_carries_the_same_row_and_colours_by_the_settings_picked(tmp_path) -> None:
    runs = str(tmp_path), "results"
    for amplitude in (1, 2):
        for shape in ("sine", "square"):
            _wave(*runs, f"{shape}-{amplitude}", f"amplitude={amplitude}", f"shape={shape}")
    lab, *_ = _lab(runs)
    lab.all_btn.clicks += 1
    lab.compare_table._handle_msg({"number": "rms_u"})
    card = _card_of(lab, number="rms_u")
    assert _row(lab, "rms_u") == [["X", f"[{'Shape' if card.x == 'shape' else 'A'}]", "Log x", "Log y"],
                                  ["Colour by", "A" if card.x == "shape" else "Shape", "Runs",
                                   "All | Mean | RMS"],
                                  ["Dots", "Lines"], ["Chart", "Table"]]
    _list(lab, "rms_u").value = "amplitude"
    assert _control(lab, "rms_u", "Dots").value and _control(lab, "rms_u", "Shape").value
    names = lambda: [t["name"] for t in _lines(lab, "rms_u")]
    assert names() == ["Shape = sine", "Shape = square"] or names() == ["Shape = square",
                                                                        "Shape = sine"]
    _control(lab, "rms_u", "Shape").value = False
    assert names() == ["RMS of u"] and card.by == (), "none picked: one colour over every run"
    assert "Log x" not in _greyed(lab, "rms_u"), "amplitudes 1 and 2"
    _control(lab, "rms_u", "Log x").value = True
    assert _figure(lab, "rms_u")["layout"]["xaxis"]["type"] == "log"
    _control(lab, "rms_u", "Lines").value = True
    assert all(t["mode"] != "markers" for t in _lines(lab, "rms_u"))
    _control(lab, "rms_u", "Table").value = True
    header, rows, _ = _table(lab, "rms_u")
    assert header == ["trace", "point", "A", "RMS of u [-]"] and len(rows) == 4
    # over the shapes the bottom axis holds names; with the amplitude alone varying, nothing
    # else tells the runs apart
    _control(lab, "rms_u", "Chart").value = True
    _control(lab, "rms_u", "Log x").value = False
    _list(lab, "rms_u").value = "shape"
    assert _greyed(lab, "rms_u")["Log x"] == "Its bottom axis holds names"
    for name in ("square-1", "square-2"):
        _tick(lab, name, on=False)
    assert _greyed(lab, "rms_u")["Colour by"] == "Nothing else tells the runs apart"


def test_a_card_no_shown_run_draws_and_a_pieces_own_figure_keep_what_they_had(lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    _tabs(lab)["pole"].value = True
    assert _row(lab, "pole") == [["Runs", "Overlay | Split | Mean | RMS"]], \
        "a figure the piece draws itself: its one greyed control"
    lab.cards.append(shaping.Card(99, "chart", chart="no-such-chart"))
    lab._draw_cards()
    assert not [o for o in _card(lab, "no-such-chart").objects[1:] if isinstance(o, pn.FlexBox)], \
        "nothing to shape: no controls"


# --- a zoom on one chart reaches every open chart over the same bottom axis -------------------

def _pane(lab: Lab, panel: str) -> pn.pane.Plotly:
    return next(o for o in _card(lab, panel).objects if isinstance(o, pn.pane.Plotly))


def _span(lab: Lab, panel: str) -> list | None:
    """The range a card's figure shows of its bottom axis; ``None`` for the whole of it."""
    xaxis = _figure(lab, panel)["layout"]["xaxis"]
    return None if xaxis.get("autorange", True) else list(xaxis["range"])


def test_a_zoom_on_one_chart_is_on_the_other_and_on_every_card_drawn_after_it(two_runs) -> None:
    lab, *_ = _lab(two_runs)                         # ``second`` is shown on arrival
    for name in ("u", "y"):
        _tabs(lab)[name].value = True
    assert (_span(lab, "u"), _span(lab, "y")) == (None, None)
    _pane(lab, "u").relayout_data = {"xaxis.range[0]": 0.2, "xaxis.range[1]": 0.6}
    assert _span(lab, "y") == [0.2, 0.6]
    assert _span(lab, "u") is None, "the zoomed chart is on it already: nothing is pushed back"
    _tick(lab, "first")                              # every card is drawn again
    assert (_span(lab, "u"), _span(lab, "y")) == ([0.2, 0.6], [0.2, 0.6])
    _control(lab, "y", "Split").value = True
    assert _span(lab, "y") == [0.2, 0.6]
    lab.compare_table._handle_msg({"number": "rms_u"})
    assert _card_of(lab, number="rms_u").id not in lab._panes, \
        "a number card's bottom axis is a setting"
    assert _span(lab, "u") == [0.2, 0.6], "the number card opened, the charts drawn again"
    _pane(lab, "y").relayout_data = {"yaxis.range[0]": -1.0, "yaxis.range[1]": 1.0}
    assert _span(lab, "u") == [0.2, 0.6], "a zoom of the ordinate says nothing of the bottom axis"
    _pane(lab, "y").relayout_data = {"xaxis.autorange": True}       # a double click
    assert _span(lab, "u") is None
    _tick(lab, "first", on=False)
    assert (_span(lab, "u"), _span(lab, "y")) == (None, None), "a reset is kept too"


def test_a_zoom_moves_the_charts_over_its_own_axis_alone_and_another_piece_starts_whole(
        lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    for name in ("output", "bode-magnitude", "bode-phase", "pole"):
        _tabs(lab)[name].value = True
    _pane(lab, "bode-magnitude").relayout_data = {"xaxis.range[0]": 0.5, "xaxis.range[1]": 2.0}
    assert _span(lab, "bode-phase") == [0.5, 2.0], "a log axis: the powers of ten, as reported"
    assert _span(lab, "output") is None, "over t, not ω"
    assert _card_of(lab, "pole").id not in lab._panes, "a figure the piece draws itself"
    _tick(lab, "first")
    assert (_span(lab, "bode-magnitude"), _span(lab, "bode-phase"), _span(lab, "output")) == \
        ([0.5, 2.0], [0.5, 2.0], None)
    lab.piece_select.value = "wave"
    lab.piece_select.value = "lag"
    _tabs(lab)["bode-phase"].value = True
    assert _span(lab, "bode-phase") is None, "another piece and back: the range is forgotten"


def test_a_zoom_crosses_a_logarithmic_and_a_linear_card_as_the_same_span(lag_runs) -> None:
    """A card switches its own axis, so two charts over ω may differ: the span a zoom left is
    set on each in its own terms, the powers of ten on the logarithmic one (the plan of
    2026-11-18, departure 3)."""
    lab, *_ = _lab(lag_runs, "lag")
    for name in ("bode-magnitude", "bode-phase"):
        _tabs(lab)[name].value = True
    _control(lab, "bode-phase", "Log x").value = False        # the phase over ω itself
    _pane(lab, "bode-magnitude").relayout_data = {"xaxis.range[0]": 0.5, "xaxis.range[1]": 2.0}
    assert _span(lab, "bode-phase") == [10.0 ** 0.5, 100.0], "10^0.5 to 10^2 rad/s"
    _pane(lab, "bode-phase").relayout_data = {"xaxis.range[0]": 10.0, "xaxis.range[1]": 1000.0}
    assert _span(lab, "bode-magnitude") == [1.0, 3.0]
    _tick(lab, "first")                              # every card is drawn again
    assert (_span(lab, "bode-magnitude"), _span(lab, "bode-phase")) == ([1.0, 3.0], [10.0, 1000.0])
    _control(lab, "bode-phase", "Log x").value = True
    assert _span(lab, "bode-phase") == [1.0, 3.0], "switched, the card shows the same span"
    _control(lab, "bode-phase", "Log x").value = False
    # a span reaching zero cannot stand on a logarithmic axis: that chart shows its whole axis
    _pane(lab, "bode-phase").relayout_data = {"xaxis.range[0]": -5.0, "xaxis.range[1]": 50.0}
    assert _span(lab, "bode-magnitude") is None
    _tick(lab, "first", on=False)
    assert (_span(lab, "bode-magnitude"), _span(lab, "bode-phase")) == (None, [-5.0, 50.0])
    _pane(lab, "bode-phase").relayout_data = {"xaxis.autorange": True}
    _tick(lab, "first")
    assert (_span(lab, "bode-magnitude"), _span(lab, "bode-phase")) == (None, None)
    # over the sample index a card leaves the charts over ω and joins the ones over the index
    _list(lab, "bode-phase").value = "index"
    _pane(lab, "bode-magnitude").relayout_data = {"xaxis.range[0]": 0.5, "xaxis.range[1]": 2.0}
    assert _span(lab, "bode-phase") is None


def test_a_number_clicked_in_the_compare_table_is_a_card_every_run_a_point(two_runs) -> None:
    lab, *_ = _lab(two_runs)
    _tick(lab, "first")
    lab.compare_table._handle_msg({"number": "rms_u"})
    card = _card_of(lab, number="rms_u")
    assert card.x == "amplitude", "the setting that varies is the bottom axis"
    assert lab.drawn[card.id] == ["second", "first"]
    assert _card(lab, "rms_u") is not None
    assert next(r for r in lab.compare_table.rows if r["key"] == "rms_u")["open"]
    greyed = _greyed(lab, "rms_u")
    assert greyed["All | Mean | RMS"] == "No colour holds two runs at one value"
    lab.compare_table._handle_msg({"number": "rms_u"})
    assert not [c for c in lab.cards if c.kind == "numbers"], "asked again, it closes"


def _on_show(lab: Lab) -> list[str]:
    """The groups whose lines the chart list shows below its index, in its order."""
    return [group for group, line in lab._lines.items() if group and line.visible]


def test_the_chart_list_opens_on_an_index_of_its_groups(lag_runs, monkeypatch) -> None:
    """RCWS #255, the developer's: above the lines, the groups by name, read down three columns,
    each name a toggle that shows its group's lines -- 45 charts in 15 groups, every group shown,
    put the first chart below the bottom of a 1700 x 1100 window. A chart opened shows its group,
    by its toggle, the address or as the first chart a page opens on; hiding a group closes
    nothing and stays; show all and hide all; a list with no groups has no index."""
    lab, *_ = _lab(lag_runs, "lag")
    named = ["Time", "Frequency"]
    index = lab.tabs.objects[0]
    columns = [[toggle.label for toggle in column.objects] for column in index.objects]
    assert len(columns) == 3 and [label[2:] for column in columns for label in column] == named
    assert list(lab.group_toggles()) == named and "output" in lab.toggles()
    assert _on_show(lab) == ["Time"]                      # the first chart a page opens on
    assert lab.group_toggles()["Time"].label == "▾ Time"
    assert lab.group_toggles()["Frequency"].label == "▸ Frequency"
    lab.group_toggles()["Frequency"].value = True
    assert _on_show(lab) == ["Time", "Frequency"]
    lab.group_toggles()["Frequency"].value = False
    assert _on_show(lab) == ["Time"]
    _tabs(lab)["bode-phase"].value = True                 # a hidden group's toggle is still there
    assert _on_show(lab) == ["Time", "Frequency"]
    lab.group_toggles()["Frequency"].value = False
    _tick(lab, "first")                                   # a redraw keeps the developer's choice
    assert _on_show(lab) == ["Time"] and "bode-phase" in lab.open_charts, "hiding closes nothing"
    assert lab.show_all.visible and lab.hide_all.visible
    lab.show_all.clicks += 1
    assert _on_show(lab) == named
    lab.hide_all.clicks += 1
    assert _on_show(lab) == []
    # the address's charts show their groups; the address is the first piece's, the wave's
    location = types.SimpleNamespace(query_params={"shown": "first", "open": "y"},
                                     update_query=lambda **query: None)
    monkeypatch.setattr(type(pn.state), "location", property(lambda state: location))
    linked, *_ = _lab(lag_runs)
    assert linked.shown == ["first"] and linked.open_charts == ["y"] and _on_show(linked) == ["Wave"]
    # charts in no group: no index, and nothing to show or hide
    monkeypatch.setattr(lab, "_drawable", lambda run: {**run, "panel_groups": {}})
    lab._draw_tabs()
    assert not lab.group_toggles() and not lab._lines and not lab.show_all.visible
    assert "output" in lab.toggles()


def test_the_chart_list_is_what_the_records_class_declares_not_what_its_file_lists(two_runs) -> None:
    """A run's file lists the charts its class declared when it was saved. After a chart change
    that list is behind: read off the file, the Lab offered charts the class no longer draws and
    none it now does, until every run was saved again (RCWS #257). The list is what the class
    declares now -- and a chart of it opens."""
    root, out_dir = two_runs
    path = Path(root) / out_dir / "wave" / "second.json"
    raw = json.loads(path.read_text())
    raw["panels"] = ["u", "a-chart-no-longer-declared"]
    path.write_text(json.dumps(raw))
    lab, *_ = _lab(two_runs)
    assert lab.shown == ["second"]
    record = lab._record_of(next(r for r in lab.runs() if r["name"] == "second"))[0]
    assert list(lab.toggles()) == [s.name for s in record.series()]
    assert "a-chart-no-longer-declared" not in lab.toggles()
    _tabs(lab)["y"].value = True
    assert _rows_of(lab, "y") == ["second"]


def test_a_refused_record_is_read_once_per_version_of_its_file(two_runs, monkeypatch) -> None:
    """Read again at every redraw, a run the class refuses cost a read and a parse per click
    (code review, 2026-10-27): the refusal is kept with the version of the file it was for."""
    lab, *_ = _lab(two_runs)
    calls: list[str] = []

    def refuse(run):
        calls.append(run["name"])
        raise ValueError("refused in the class's own words")

    monkeypatch.setattr(state, "load", refuse)
    lab._loaded.clear()
    run = lab.runs()[0]
    assert lab._record_of(run) == (None, "refused in the class's own words")
    assert lab._record_of(run) == (None, "refused in the class's own words")
    assert calls == [run["name"]]


def test_the_header_counts_the_pieces_own_records(lag_runs) -> None:
    """With two pieces, the count beside a piece's folder was every piece's (2026-10-27)."""
    root, out_dir = lag_runs
    _wave(root, out_dir, "third")
    lab, *_ = _lab(lag_runs)
    assert lab.piece["name"] == "wave" and "· 3 records" in lab.where.object
    lab.piece_select.value = "lag"
    assert "· 2 records" in lab.where.object


def test_a_click_on_the_chart_list_builds_none_of_it_again(lag_runs) -> None:
    """RCWS #256: the toggles are built again only when what the list holds changes. Built again
    on every click, a click landing while the page drew the new ones was lost -- 2 of 5 charts
    clicked 80 ms apart in headless Chromium (2026-10-27). A click on the index, on a chart, on
    show all or hide all, or a card closed, sets the toggles already there."""
    lab, *_ = _lab(lag_runs, "lag")
    on_screen, toggles, index = list(lab.tabs.objects), lab.toggles(), lab.group_toggles()
    lab.group_toggles()["Frequency"].value = True
    _tabs(lab)["bode-phase"].value = True
    assert lab.toggles()["bode-phase"].value and lab.group_toggles()["Frequency"].label == "▾ Frequency"
    lab.show_all.clicks += 1
    lab.hide_all.clicks += 1
    lab._close(_card_of(lab, "bode-phase"))
    assert len(lab.tabs.objects) == len(on_screen)
    assert all(now is before for now, before in zip(lab.tabs.objects, on_screen))
    assert all(lab.toggles()[name] is toggle for name, toggle in toggles.items())
    assert all(lab.group_toggles()[group] is toggle for group, toggle in index.items())
    assert not lab.toggles()["bode-phase"].value
    assert lab.group_toggles()["Frequency"].label == "▸ Frequency"
    assert "1 of 4 open" in lab.open_count.object


def _older(record):
    """``record`` declaring its ``u`` panel alone, a record of the same piece (the figure layer
    refuses to compare runs of two pieces)."""
    keep = [s for s in record.series() if s.name == "u"]
    older = type("Older", (), {"component": type(record).component})()
    for name, value in (("series", lambda: tuple(keep)), ("figures", tuple),
                        ("config", record.config), ("numbers", record.numbers),
                        ("number_specs", record.number_specs)):
        setattr(older, name, value)
    return older


def test_a_run_without_the_panel_is_left_out_of_the_card_by_name(two_runs) -> None:
    """The chart is drawn over the runs that declare it, and the card's foot names the run it
    leaves out (the developer's design of 2026-11-13: "a chart card that says which run it
    leaves out")."""
    lab, *_ = _lab(two_runs)
    # `first` is made to declare its u only, as an older record of the piece would
    real = lab._record_of
    lab._record_of = lambda run: ((_older(real(run)[0]), "") if run["name"] == "first"
                                  else real(run))
    for row in lab.records:
        if row["name"] == "first":
            row["panels"] = ["u"]
    _tick(lab, "first")
    _tabs(lab)["y"].value = True
    assert _rows_of(lab, "y") == ["second"] and _figure(lab, "y") is not None
    assert any("first declares no such chart" in w for w in _card_words(lab, "y"))
    subs = [o.object for o in lab.tabs.select(pn.pane.HTML)]
    assert any("1 of 2 runs" in s for s in subs)


def test_a_record_that_does_not_load_is_a_line_on_the_card_in_the_loaders_words(two_runs) -> None:
    """A header the listing reads and a body the class refuses: listed, tickable, and the card
    says why in the class's own words rather than guessing."""
    root, out_dir = two_runs
    folder = Path(root) / out_dir / "wave"
    raw = json.loads((folder / "first.json").read_text())
    raw["t"] = "oops"
    (folder / "zz-odd-body.json").write_text(json.dumps(raw))
    # stamped older than `second`, which stays the run shown first
    newest = (folder / "second.json").stat().st_mtime
    os.utime(folder / "zz-odd-body.json", (newest - 30, newest - 30))
    lab, *_ = _lab(two_runs)
    assert "zz-odd-body" in _names(lab)
    _tick(lab, "zz-odd-body")
    assert _columns(lab) == ["second", "zz-odd-body"], "its header reads; it compares"
    assert _rows_of(lab, "u") == ["second"]
    words = " ".join(_card_words(lab, "u"))
    assert "zz-odd-body" in words and "in a form the current Record does not read" in words


def _beside(two_runs, name: str, edit) -> None:
    """A file ``name`` beside the two runs: ``first``'s content changed by ``edit``, stamped
    older than ``second``, which stays the run shown first."""
    root, out_dir = two_runs
    folder = Path(root) / out_dir / "wave"
    raw = json.loads((folder / "first.json").read_text())
    edit(raw)
    (folder / f"{name}.json").write_text(json.dumps(raw))
    newest = (folder / "second.json").stat().st_mtime
    os.utime(folder / f"{name}.json", (newest - 30, newest - 30))


def test_a_run_whose_file_holds_more_than_its_piece_reads_is_ticked_compared_and_drawn(
        two_runs) -> None:
    """A run saved by another bench of the piece, which kept Python's version where the run came
    from, and by code that kept a field the piece no longer reads: its lines say how its file
    differs, it keeps its tick box, and it is compared and drawn like any other."""
    def edit(raw) -> None:
        raw["provenance"]["python"] = "3.11.9"
        raw["mood"] = [1, 2]
    _beside(two_runs, "old", edit)
    lab, *_ = _lab(two_runs)
    row = next(r for r in lab.run_list.rows if r["name"] == "old")
    assert row["stale"] == ""
    assert row["notes"] == ["holds gone field mood", "where it came from also holds python"]
    _tick(lab, "old")
    assert _columns(lab) == ["second", "old"]
    assert _rows_of(lab, "u") == ["second", "old"]
    assert not any("old" in w for w in _card_words(lab, "u")), "nothing left out, nothing said"


def test_a_run_whose_file_lacks_what_its_charts_read_is_compared_and_left_out_by_name(
        two_runs) -> None:
    """Saved before the piece kept ``y``, by a piece that declares no value for it absent: the
    run is listed with its line, ticked and compared from its file, and each card draws the
    other run and names this one with the field its file lacks."""
    _beside(two_runs, "older", lambda raw: raw.pop("y"))
    lab, *_ = _lab(two_runs)
    row = next(r for r in lab.run_list.rows if r["name"] == "older")
    assert row["stale"] == "" and row["notes"] == ["predates the field y"]
    _tick(lab, "older")
    assert _columns(lab) == ["second", "older"], "its numbers and settings are its file's"
    assert _rows_of(lab, "u") == ["second"]
    assert "older: the file older.json holds no 'y'" in " ".join(_card_words(lab, "u"))


def test_the_settings_are_shown_when_asked_and_a_number_never_hidden(two_runs) -> None:
    lab, *_ = _lab(two_runs)
    _tick(lab, "first")
    assert lab.settings_choice.value == "none", "the numbers alone until asked"
    kinds = lambda: [r["kind"] for r in lab.compare_table.rows]
    assert "setting" not in kinds() and "number" in kinds()
    lab.settings_choice.value = "differ"
    differ = [r["term"] for r in lab.compare_table.rows if r["kind"] == "setting"]
    lab.settings_choice.value = "all"
    every = [r["term"] for r in lab.compare_table.rows if r["kind"] == "setting"]
    assert len(differ) == 1 and len(every) > len(differ)
    assert "RMS of y" in [r["term"] for r in lab.compare_table.rows]


def test_the_constants_a_run_used_are_compared_too(lag_runs) -> None:
    """What a run used beyond its Config -- what independent truth needs when a number is judged
    -- read off the loaded record."""
    lab, *_ = _lab(lag_runs, "lag")
    _tick(lab, "first")
    lab.settings_choice.value = "all"
    terms = [r["term"] for r in lab.compare_table.rows]
    assert "Constants" in terms and "gain" in terms, "the value the code resolved"
    assert terms.index("Peak of y") < terms.index("Constants"), "numbers first, constants last"


def test_the_filter_lists_the_runs_holding_every_word_and_all_and_none_tick_them(two_runs) -> None:
    lab, *_ = _lab(two_runs)
    lab.run_filter.value_input = "fir"
    assert _names(lab) == ["first"] and "1 listed" in lab.runs_count.object
    lab.tick_listed()
    assert lab.shown == ["second", "first"]
    lab.untick_listed()
    assert lab.shown == ["second"], "a run the filter does not list keeps its tick"


def test_deleting_a_run_asks_first_and_then_takes_only_its_record(two_runs, capsys) -> None:
    root, out_dir = two_runs
    lab, _queue, _ticker, toasts = _lab(two_runs)
    lab.run_list._handle_msg({"delete": "first"})
    assert "Delete results/wave/first.json?" in lab.question.object
    lab._on_no()
    assert (Path(root) / out_dir / "wave" / "first.json").exists(), "cancel deletes nothing"
    lab.run_list._handle_msg({"delete": "first"})
    lab._on_yes()
    assert not (Path(root) / out_dir / "wave" / "first.json").exists()
    assert _names(lab) == ["second"] and toasts[-1] == "Deleted results/wave/first.json"
    assert "lab: deleted results/wave/first.json" in capsys.readouterr().out
    lab._on_yes()                                    # a second yes finds nothing left to do
    assert _names(lab) == ["second"]


# --- Save, and the pictures it wrote ----------------------------------------------------------

def _save_button(lab: Lab, panel: str) -> pn.widgets.Button | None:
    """A card's Save, beside its close; ``None`` on a card that has none."""
    top = _card(lab, panel).objects[0]
    return next((o for o in top.objects
                 if isinstance(o, pn.widgets.Button) and o.name == "Save"), None)


def _foot(lab: Lab, panel: str) -> tuple[str, bool]:
    """A card's last line, and whether it is written in red."""
    last = [o for o in _card(lab, panel).objects[1:] if isinstance(o, pn.pane.HTML)][-1]
    return html.unescape(re.sub(r"<[^>]+>", "", last.object)), skin.SIGNAL in last.object


def test_save_writes_the_card_as_it_is_shown_and_its_folder_is_listed(
        two_runs, monkeypatch, capsys) -> None:
    """The developer's answer of 2026-11-17 ("Save and the saved list"): the picture of a card
    with its controls' choices and the span a zoom left, in the folder named after its runs."""
    root, out_dir = two_runs
    lab, *_ = _lab(two_runs)                         # ``second`` is shown on arrival
    _tick(lab, "first")
    _tabs(lab)["y"].value = True
    asked, real = [], app_module.draw
    monkeypatch.setattr(app_module, "draw",
                        lambda pairs, folder, **kw: asked.append((pairs, kw)) or real(pairs, folder, **kw))
    assert lab.saved_list.rows == [] and lab.saved_count.object == ""
    _control(lab, "y", "Dots").value = True
    _pane(lab, "u").relayout_data = {"xaxis.range[0]": 0.2, "xaxis.range[1]": 0.6}
    _save_button(lab, "y").clicks += 1
    folder = Path(root) / out_dir / "wave" / "second+first"
    assert sorted(p.name for p in folder.iterdir()) == ["y.png", "y.png.json"]
    [(pairs, kw)] = asked
    assert kw == {"panels": ["y"], "table": False, "x": "own", "x_log": False, "y_log": False,
                  "colour_by": "run", "runs": "one", "points": True, "x_range": (0.2, 0.6)}
    shaped = {k: v for k, v in kw.items() if k not in ("panels", "table")}
    assert figure_of(chart_of(pairs, "y", **shaped)) == _figure(lab, "y"), \
        "the still is drawn from what the card shows: its choices and its span"
    side = json.loads((folder / "y.png.json").read_text())
    assert side["runs"] == ["second", "first"] and side["xlim"] == [0.2, 0.6]
    assert side["shaping"]["points"] is True and side["shaping"]["x_range"] == [0.2, 0.6]
    assert _foot(lab, "y") == (f"Wrote {out_dir}/wave/second+first/y.png", False)
    assert f"lab: wrote {out_dir}/wave/second+first/y.png" in capsys.readouterr().out
    [row] = lab.saved_list.rows
    assert (row["name"], row["pictures"]) == ("second+first", "y.png")
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d · 1 picture", row["when"])
    assert "1 folder" in lab.saved_count.object
    # with its table picked, its numbers too; the picture is replaced, not added to
    _control(lab, "y", "Table").value = True
    _save_button(lab, "y").clicks += 1
    assert sorted(p.name for p in folder.iterdir()) == ["y.csv", "y.csv.json", "y.png",
                                                        "y.png.json"]
    assert _foot(lab, "y")[0] == (f"Wrote {out_dir}/wave/second+first/y.png "
                                  f"{out_dir}/wave/second+first/y.csv")
    assert lab.saved_list.rows[0]["when"].endswith("· 1 picture and 1 table")
    # a number card writes its own into the same folder
    lab.compare_table._handle_msg({"number": "rms_u"})
    _save_button(lab, "rms_u").clicks += 1
    assert (folder / "rms_u-vs-amplitude.png").exists()
    [row] = lab.saved_list.rows
    assert row["pictures"] == "rms_u-vs-amplitude.png, y.png"
    assert row["when"].endswith("· 2 pictures and 1 table") and "1 folder" in lab.saved_count.object
    # another piece has its own folders; back, this one's are listed again
    lab.piece_select.value = "lag"
    assert lab.saved_list.rows == []
    lab.piece_select.value = "wave"
    assert [r["name"] for r in lab.saved_list.rows] == ["second+first"]
    assert lab.page().get_root() is not None, "the page builds with the list on it"


def test_a_save_that_cannot_write_says_why_and_some_cards_have_no_save(
        lag_runs, monkeypatch) -> None:
    root, out_dir = lag_runs
    lab, *_ = _lab(lag_runs, "lag")
    _tabs(lab)["pole"].value = True
    assert _save_button(lab, "pole") is None, "a figure the piece draws itself is not saved"
    lab.cards.append(shaping.Card(99, "chart", chart="no-such-chart"))
    lab._draw_cards()
    assert _save_button(lab, "no-such-chart") is None, "a card that draws nothing"
    real = app_module.draw

    def refused(*args, **kwargs):
        raise ValueError("the figure layer said no")

    monkeypatch.setattr(app_module, "draw", refused)
    _save_button(lab, "output").clicks += 1
    assert _foot(lab, "output") == ("Not saved: the figure layer said no", True)
    assert lab.saved_list.rows == [] and not (Path(root) / out_dir / "lag" / "second").exists()
    monkeypatch.setattr(app_module, "draw", real)
    _save_button(lab, "output").clicks += 1          # asked again, it writes: nothing is latched
    assert _foot(lab, "output") == (f"Wrote {out_dir}/lag/second/output.png", False)


def test_a_saved_folder_is_deleted_after_asking_and_only_if_save_wrote_all_of_it(two_runs) -> None:
    root, out_dir = two_runs
    lab, _queue, _ticker, toasts = _lab(two_runs)
    folder = Path(root) / out_dir / "wave" / "second"
    _save_button(lab, "u").clicks += 1
    lab.saved_list._handle_msg({"delete": "second"})
    assert "Delete the pictures in results/wave/second/?" in lab.question.object
    lab._on_no()
    assert (folder / "u.png").exists(), "cancel deletes nothing"
    (folder / "notes.txt").write_text("mine")
    lab.saved_list._handle_msg({"delete": "second"})
    lab._on_yes()
    assert toasts[-1] == ("Not deleted: results/wave/second/ holds notes.txt, which Save does "
                          "not write; it is left as it is")
    assert (folder / "u.png").exists() and [r["name"] for r in lab.saved_list.rows] == ["second"]
    (folder / "notes.txt").unlink()
    lab.saved_list._handle_msg({"delete": "second"})
    lab._on_yes()
    assert not folder.exists() and lab.saved_list.rows == []
    assert toasts[-1] == "Deleted results/wave/second/"
    assert (Path(root) / out_dir / "wave" / "second.json").exists(), "the run stays"
    assert lab.shown == ["second"]


def test_a_bar_sets_the_centreline_on_its_children_and_the_form_is_one_set_of_tracks(two_runs) -> None:
    """The two shapes the page is laid out with, and why neither is the obvious one.

    A BAR is a row of text panes beside widgets. The centreline is set on the CHILDREN
    (`skin.BAR`, a stylesheet reaching the row's shadow root), never by `align="center"` on the
    row: Panel reads that as "align THIS ROW inside its container", and every child keeps its own
    `align`, default `start`, which beats any `align-items` the row carries. Measured on the live
    page 2026-10-06: without this a text pane sat 9.5-10px off the button beside it.

    The FORM is one grid per section wearing the SAME fixed tracks, so a box in one section sits
    under a box in another -- tracks that size to their own content line up only within one grid,
    which left the boxes 196px apart across sections. The cells go in bare, three per field: a
    row of its own is a separate flex box and two of them share no geometry.
    """
    lab, *_ = _lab(two_runs)
    whole = lab.page()

    bars = [r for r in whole.select(pn.Row)
            if any(isinstance(o, pn.pane.HTML) for o in r)
            and any(isinstance(o, pn.widgets.Widget) for o in r)]
    assert len(bars) >= 4, f"the page's bars should be found, got {len(bars)}"
    for bar in bars:
        assert skin.BAR in (bar.stylesheets or []), \
            f"a bar whose children are left on their own align: {[type(o).__name__ for o in bar]}"
    assert not [r for r in whole.select(pn.Row) if r.align == "center"], \
        "align='center' on a Row aligns the ROW in its container, not its children"

    grids = whole.select(pn.GridBox)
    assert grids, "the form's sections are grids"
    per_group: dict[str, int] = {}
    for f in lab.form.fields:
        per_group[f["group"]] = per_group.get(f["group"], 0) + 1
    assert sorted(len(g.objects) for g in grids) == sorted(n * 3 for n in per_group.values()), \
        "three cells per field, and nothing else in the grid"
    for g in grids:
        assert g.ncols == 6 and skin.FORM_GRID in (g.stylesheets or []), \
            "every section wears the same six tracks, or the sections do not line up"


def test_the_page_renders_with_two_runs_and_every_kind_of_card(two_runs) -> None:
    """The page is BUILT here, not just driven: the figure dicts are validated by the Plotly
    pane when the document is rendered, after `page()` has returned."""
    lab, *_ = _lab(two_runs)
    _tick(lab, "first")
    _tabs(lab)["y"].value = True
    _control(lab, "y", "Split").value = True
    lab.open_number("rms_u")
    lab.open_drawer("first")
    assert lab.page().get_root() is not None
    assert lab.split.left_px == 400
    lab.split.left_px = 520                          # what a drag sets; the page can set it too
    assert lab.split.left_px == 520


def test_a_record_that_cannot_be_read_is_not_shown_by_itself(two_runs) -> None:
    """The list gives a stale row no tick, so it must never be the run the screen shows."""
    root, out_dir = two_runs
    (Path(root) / out_dir / "wave" / "zz-kept-setup.json").write_text('{"amplitude": 2}')
    time.sleep(0.01)
    os.utime(Path(root) / out_dir / "wave" / "zz-kept-setup.json", None)   # the newest file
    lab, *_ = _lab(two_runs)
    assert lab.shown == ["second"], "the newest READABLE run"
    assert _columns(lab) == ["second"]
    stale = next(r for r in lab.run_list.rows if r["name"] == "zz-kept-setup")
    assert "carries no" in stale["stale"]
    lab.run_list.shown = ["second", "zz-kept-setup"]   # a component cannot be trusted either
    assert lab.shown == ["second"]


def test_a_number_a_record_does_not_declare_well_is_listed_and_not_fatal(two_runs) -> None:
    root, out_dir = two_runs
    (Path(root) / out_dir / "wave" / "zz-odd.json").write_text(json.dumps(
        {"component": "wave", "panels": ["u"], "number_specs": {"rms_u": 1}}))
    lab, *_ = _lab(two_runs)
    assert lab.page().get_root() is not None
    row = next(r for r in lab.runs() if r["name"] == "zz-odd")
    assert "'number_specs' header is not a list" in row["stale"] and row["number_specs"] == []


def test_switching_the_piece_forgets_what_was_ticked_and_open(lag_runs) -> None:
    """Every run name belongs to the piece it came from: the wave's ``first`` and the lag's are
    two runs."""
    lab, *_ = _lab(lag_runs)
    _tick(lab, "first")
    _tabs(lab)["y"].value = True
    lab._on_piece("lag")
    assert lab.shown == ["second"] and lab.open_charts == ["output"], \
        "the lag's newest and its first chart, not the wave's two runs and its y"
    lab._on_piece("wave")
    assert lab.shown == ["second"] and lab.open_charts == ["u"]
    assert not lab._loaded or all(p.endswith(".json") for p in lab._loaded)


def _rows_of_editor(editor) -> list:
    """An editor's rows as (label words, box, ✕), its last object being the add button."""
    return [tuple(row.objects) for row in editor.view.objects[:-1]]


def _labels(editor) -> list[str]:
    return [html.unescape(r[0].object).split(">")[1].split("<")[0] for r in _rows_of_editor(editor)]


def test_a_list_setting_with_rows_draws_a_labelled_box_per_item_and_its_edits_reach_the_run(
        two_runs) -> None:
    """The developer, 2026-11-11, of DeePC's System form: "rows for each state equation and each
    observation equation", labelled, with add and remove; the list reaches the run as JSON, the
    default unset."""
    lab, *_ = _lab(two_runs, "lag")
    keep, limits = lab._controls["keep"], lab._controls["limits"]
    rows = _rows_of_editor(keep)
    assert _labels(keep) == ["Trace 1 ="] and _labels(limits) == ["Limit 1 =", "Limit 2 ="]
    assert rows[0][1].value == "y" and "keep" not in lab.form.set
    rows[0][1].value_input = "u"
    assert json.loads(lab.form.set["keep"]) == ["u"]
    assert _rows_of_editor(keep)[0][1] is rows[0][1], "the box typed in stays (code review)"
    keep.view.objects[-1].clicks += 1                    # + Trace
    assert len(_rows_of_editor(keep)) == 2 and json.loads(lab.form.set["keep"]) == ["u", ""]
    _rows_of_editor(keep)[1][1].value_input = "y"
    keep.view.objects[-1].clicks += 1
    assert _labels(keep) == ["Trace 1 =", "Trace 2 =", "Trace 3 ="]
    _rows_of_editor(keep)[2][2].clicks += 1              # its ✕
    _rows_of_editor(keep)[1][2].clicks += 1              # and the second row's
    assert json.loads(lab.form.set["keep"]) == ["u"]
    assert _labels(keep) == ["Trace 1 ="], "labels renumber"
    _rows_of_editor(limits)[0][1].value_input = "1,5"    # not a number: kept whole, as typed
    assert json.loads(lab.form.set["limits"]) == ["1,5", 1.0]
    _rows_of_editor(limits)[0][1].value_input = "-1"     # the default, typed again
    assert "limits" not in lab.form.set, "a number list back at its default is unset"
    overrides = lab.form.launch_words()[0]
    assert any(o.startswith("keep=[") for o in overrides)
    assert not any(o.startswith("limits=") for o in overrides)
    lab._clear()
    assert len(_rows_of_editor(keep)) == 1 and lab.form.set == {}
    lab.form.use({"keep": ["u", "y"], "limits": [0.5]})
    lab._fill_controls()
    assert [r[1].value for r in _rows_of_editor(keep)] == ["u", "y"]
    assert [r[1].value for r in _rows_of_editor(limits)] == ["0.5"]


# ---------------------------------------------------------------- a figure the piece draws itself

def _own_panes(lab: Lab, panel: str) -> list[dict]:
    """The figures an own-figure card draws, top to bottom, as its Plotly panes hold them."""
    return [pane.object for pane in _card(lab, panel).select(pn.pane.Plotly)]


def _own_names(lab: Lab, panel: str) -> list[str]:
    """The run names an own-figure card writes above its figures, top to bottom."""
    return [name for o in _card(lab, panel).select(pn.pane.HTML)
            for name in re.findall(r"data-run='([^']+)'", o.object)]


def test_a_pieces_own_figure_is_listed_with_the_charts_and_opens_a_card(lag_runs) -> None:
    """Branch R3: the lag draws its pole itself, a plotly figure; the page lists it in its group
    after the charts and shows it as the piece drew it."""
    lab, queue, *_ = _lab(lag_runs, "lag")
    assert list(lab.toggles()) == ["output", "bode-magnitude", "bode-phase", "pole"]
    _tabs(lab)["pole"].value = True
    assert queue.runs() == [] and lab.open_charts == ["output", "pole"]
    assert "data-panel='pole'" in _card(lab, "pole").objects[0].objects[0].object
    assert ">Pole<" in _card(lab, "pole").objects[0].objects[0].object, "its own title"
    [fig] = _own_panes(lab, "pole")
    assert fig["data"][0]["x"] == [-1.0 / 0.2], "the shown run's, `second`, whose τ is 0.2"
    assert fig["layout"]["xaxis"]["title"]["text"] == "Re [rad/s]"
    assert _rows_of(lab, "pole") == ["second"] and _own_names(lab, "pole") == [], \
        "one run shown: no name above its figure"
    assert _greyed(lab, "pole") == {
        "Overlay | Split | Mean | RMS": "A piece's own figure is drawn once per run"}
    assert lab.group_toggles()["Frequency"].label == "▾ Frequency", "opened, its group shows"


def test_several_runs_stack_a_figure_each_under_its_runs_name(lag_runs) -> None:
    """The developer, 2026-11-17: one figure per run, stacked. The page cannot merge what only
    the piece can read."""
    lab, *_ = _lab(lag_runs, "lag")
    _tabs(lab)["pole"].value = True
    _tick(lab, "first")
    assert _rows_of(lab, "pole") == ["second", "first"] == _own_names(lab, "pole"), \
        "in the order ticked, each named"
    assert [fig["data"][0]["x"] for fig in _own_panes(lab, "pole")] == [[-5.0], [-20.0]]
    assert _greyed(lab, "pole") == {
        "Overlay | Split | Mean | RMS": "A piece's own figure is drawn once per run"}, \
        "two runs shown, and still nothing to pick"
    assert _rows_of(lab, "output") == ["second", "first"], "the chart beside it overlays, as ever"
    assert lab.page().get_root() is not None, "the page builds with it"
    _tick(lab, "second", False)
    assert _rows_of(lab, "pole") == ["first"] and _own_names(lab, "pole") == []


def test_a_shown_run_that_draws_no_such_figure_is_named_on_the_card(lag_runs) -> None:
    lab, *_ = _lab(lag_runs, "lag")
    real = lab._record_of

    def without(run):
        """``first`` as a record saved before the piece drew its pole would read under a class
        that draws none."""
        record, why = real(run)
        if run["name"] != "first":
            return record, why
        older = type("Older", (type(record),), {"figures": lambda self: ()})
        return older(**{f.name: getattr(record, f.name) for f in dataclasses.fields(record)}), why

    lab._record_of = without
    _tabs(lab)["pole"].value = True
    _tick(lab, "first")
    assert _rows_of(lab, "pole") == ["second"] and len(_own_panes(lab, "pole")) == 1
    assert _own_names(lab, "pole") == ["second"], "two runs shown: the one drawn is named"
    assert "first declares no such figure" in _card_words(lab, "pole")


def test_the_switch_words_the_chart_list_the_card_and_its_axes_and_keeps_a_zoom(tmp_path) -> None:
    """0.22, the header's Names / Symbols switch over a chart made from quantities (the made-up
    fit's loss): the chart list's title, the card's title and both axes in the other words; the
    line, written in full, the same; a zoom kept across the switch, by its bottom axis's words in
    names; and back."""
    for name in ("a", "b"):
        cli.main(["run", "fit", "--name", name, "--out-dir", str(tmp_path / "results")])
    lab, *_ = _lab((str(tmp_path), "results"), piece="fit")
    _tick(lab, "a")
    if "loss" not in lab.open_charts:
        _tabs(lab)["loss"].value = True

    def seen() -> tuple:
        fig = lab._panes[_card_of(lab, "loss").id][0].object
        title = _card(lab, "loss").objects[0].objects[0].object
        return (_tabs(lab)["loss"].label, html.unescape(re.sub(r"<[^>]+>", "", title)),
                fig["layout"]["xaxis"]["title"]["text"], fig["layout"]["yaxis"]["title"]["text"],
                [t.get("name") for t in fig["data"]])

    names = seen()
    assert names[:4] == ("Mean squared error", "Mean squared error", "Step [-]",
                         "Mean squared error [-]")
    lab._on_zoom(_card_of(lab, "loss").id, {"xaxis.range[0]": 2, "xaxis.range[1]": 5})
    lab.wording_choice.value = "symbols"
    symbols = seen()
    assert symbols[:4] == ("MSE", "MSE", "k [-]", "MSE [-]")
    assert symbols[4] == names[4], "the line, written in full, the same"
    xaxis = lab._panes[_card_of(lab, "loss").id][0].object["layout"]["xaxis"]
    assert list(xaxis["range"]) == [2, 5], "the zoom kept across the switch"
    lab.wording_choice.value = "names"
    assert seen() == names
    assert lab._chart_cells["loss"].width == app_module._tab_width("Mean squared error"), \
        "the toggle's cell as wide as its title again, set in place"


def test_the_switch_words_the_compare_table_a_number_card_and_its_saved_picture(tmp_path) -> None:
    """0.23: the made-up fit's final loss, made from a quantity and a statistic. The header's
    switch words it in the compare table, on its number card's title and its chart's axis; a
    number written in full stays; a picture saved in symbols says so in its note."""
    for name, rate in (("a", "0.5"), ("b", "0.3")):
        cli.main(["run", "fit", "--name", name, "--out-dir", str(tmp_path / "results"),
                  "--set", f"rate={rate}"])
    lab, *_ = _lab((str(tmp_path), "results"), piece="fit")
    _tick(lab, "a")
    _tick(lab, "b")
    lab.open_number("loss")
    assert _card_of(lab, number="loss").x == "rate", "the setting that varies"

    def seen() -> tuple:
        terms = {r["key"]: r["term"] for r in lab.compare_table.rows if r["kind"] == "number"}
        title = _card(lab, "loss").objects[0].objects[0].object
        return (terms["loss"], terms["w0"], html.unescape(re.sub(r"<[^>]+>", "", title)),
                _figure(lab, "loss")["layout"]["yaxis"]["title"]["text"])

    assert seen() == ("Final mean squared error", "Fitted intercept",
                      "Final mean squared error vs Rate", "Final mean squared error [-]")
    lab.wording_choice.value = "symbols"
    assert seen() == ("Final MSE", "Fitted intercept", "Final MSE vs Rate", "Final MSE [-]")
    save = next(b for b in _card(lab, "loss").objects[0].objects
                if isinstance(b, pn.widgets.Button) and b.label == "Save")
    save.clicks += 1
    [note] = (tmp_path / "results" / "fit").rglob("*.png.json")
    assert json.loads(note.read_text())["shaping"]["words"] == "symbols"
    lab.wording_choice.value = "names"
    assert seen()[0] == "Final mean squared error"
