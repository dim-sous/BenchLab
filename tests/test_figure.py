"""The figure layer draws what records declare, and figures describe: a legend only when there is
more than one label, no title (``CLAUDE.md``, "Figures describe, they never conclude"). DeePC's
``tests/test_figure.py``, moved here onto the made-up project in branch R1."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pytest

import runlab.figure.render as render_module
from runlab import Figure, Series, cli
from runlab.figure import draw, draw_sweep
from runlab.figure.chart import INDEX_LABEL, chart_of, sweep_of
from runlab.figure.own import TEMPLATE, own_figure
from runlab.figure.render import (DASHES, LEGEND_LINE, SHORT, Axes, Line, Panel, broken,
                                  has_legend, log_refusal, render, table_of)
from runlab.figure.twin import figure_of
from runlab.figure.style import GRID, LINE_WIDTH, SERIES, SURFACE, _hsl, series_color, shade
from runlab.figure.twin import MORE_ROW_PX, ONE_PX
from runlab.record import stamp
from tests.toy import lag, wave


@pytest.fixture
def source(tmp_path) -> str:
    """A saved default wave run: its path."""
    return str(wave.run(wave.Config()).save(tmp_path / "wave.json"))


@pytest.fixture
def runs(source, tmp_path) -> dict[str, object]:
    """The saved wave run, and a lag on it drawing both its traces, each loaded back."""
    both = lag.run(lag.Config(wave_run=source, keep=["u", "y"])).save(tmp_path / "lag.json")
    return {"wave": wave.Record.load(source), "lag": lag.Record.load(both)}


def test_every_declared_panel_draws_with_no_title_and_a_legend_only_for_several_labels(
        runs, tmp_path, monkeypatch) -> None:
    seen = []
    keep = render_module.save_figure

    def spy(fig, out_dir, stem, facts, prov):
        ax = fig.axes[0]
        seen.append((stem, ax.get_title(), ax.get_legend() is not None, list(fig.texts)))
        return keep(fig, out_dir, stem, facts, prov)

    monkeypatch.setattr(render_module, "save_figure", spy)
    legends = set()
    for key, rec in runs.items():
        paths = draw([(key, rec)], tmp_path / key)
        assert len(paths) == len(rec.series())
        for p in paths:
            assert p.exists() and (p.parent / f"{p.name}.json").exists()
        for s in rec.series():
            panel = chart_of([(key, rec)], s.name)
            stem, title, legend, suptitle = next(x for x in seen if x[0] == s.name)
            assert title == "" and suptitle == []
            labels = {t for t, _ in s.traces} | {r for r, _ in s.refs} | {b[0] for b in s.bands}
            assert legend == has_legend(panel) == (len(labels) > 1)
            legends.add(legend)
        seen.clear()
    assert legends == {True, False}, "the runs here hold a panel of each kind"


def test_an_overlay_names_each_run_and_draws_what_both_hold_identically_once(runs, source) -> None:
    one = runs["wave"]
    panel = chart_of([("a", one), ("b", wave.run(wave.Config(amplitude=2.0)))], "u")
    assert [ln.label for ln in panel.axes[0].lines] == ["a", "b"]   # a run alone names its trace
    assert len({ln.color for ln in panel.axes[0].lines}) == 2
    fast, slow = lag.run(lag.Config(wave_run=source)), lag.run(lag.Config(wave_run=source, tau=0.2))
    bounded = chart_of([("a", fast), ("b", slow)], "output")
    assert [r.label for r in bounded.axes[0].refs] == ["Lower bound of y [-]",
                                                       "Upper bound of y [-]"]   # each bound once
    same = chart_of([("a", one), ("b", one)], "u")
    assert [ln.label for ln in same.axes[0].lines] == ["a, b — u (identical)"]


def test_a_reference_line_is_never_solid_and_two_of_a_panel_differ(source) -> None:
    """One run, the runs overlaid and a row per run: the two bounds wear the patterns after the
    solid one, the same two however the runs are shown, so a bound keeps its dash when a second
    run is ticked and is never drawn as a trace is."""
    fast, slow = lag.run(lag.Config(wave_run=source)), lag.run(lag.Config(wave_run=source, tau=0.2))
    for pairs, how in (([("a", fast)], {}), ([("a", fast), ("b", slow)], {}),
                       ([("a", fast), ("b", slow)], {"runs": "rows"})):
        for axes in chart_of(pairs, "output", **how).axes:
            assert [r.dash for r in axes.refs] == ["dash", "dot"], (len(pairs), how)


def test_a_panel_no_run_declares_is_refused(runs, tmp_path) -> None:
    with pytest.raises(ValueError, match="no run declares"):
        draw([("a", runs["wave"])], tmp_path, panels=["no-such-panel"])


def test_a_run_without_the_panel_or_of_another_piece_is_refused_not_left_out(runs) -> None:
    whole = runs["wave"]

    class WithoutY(type(whole)):
        """A run of the same piece that declares no ``y`` panel."""

        def series(self):
            return tuple(s for s in super().series() if s.name != "y")

    fewer = WithoutY(**{f.name: getattr(whole, f.name) for f in dataclasses.fields(whole)})
    with pytest.raises(ValueError, match="declare no panel"):
        chart_of([("all", whole), ("fewer", fewer)], "y")
    with pytest.raises(ValueError, match="different pieces"):
        chart_of([("wave", whole), ("lag", runs["lag"])], "u")
    with pytest.raises(ValueError, match="different pieces"):
        sweep_of([("wave", whole), ("lag", runs["lag"])], "rms_u", vs="seed")


def test_a_sweep_puts_one_point_per_run_at_its_settings_value(source) -> None:
    pairs = [(f"a-{v}", wave.run(wave.Config(amplitude=v))) for v in (2.0, 5.0)]
    panel = sweep_of(pairs, "rms_u", vs="amplitude")
    (line,) = panel.axes[0].lines                         # one colour: only the amplitude differs
    assert list(line.drawn_x()) == [2.0, 5.0] and line.points
    assert line.y == [rec.numbers["rms_u"] for _, rec in pairs]
    lags = [(f"tau-{v}", lag.run(lag.Config(wave_run=source, tau=v))) for v in (0.05, 0.1)]
    spec = next(n for n in lags[0][1].number_specs() if n.name == "corner")
    assert sweep_of(lags, "corner", vs="tau").axes[0].y_label == f"{spec.label} [rad/s]"
    with pytest.raises(ValueError, match="not a setting"):
        sweep_of(pairs, "rms_u", vs="amplitudes")
    with pytest.raises(ValueError, match="declare no number"):
        sweep_of(pairs, "rms_nothing", vs="amplitude")


def test_a_draw_writes_what_it_prints(source, tmp_path, capsys) -> None:
    cli.main(["draw", source, "--panel", "y", "--out-dir", str(tmp_path / "out")])
    printed = capsys.readouterr().out.split()
    assert printed == [str(tmp_path / "out" / "y.png")]
    sidecar = json.loads((tmp_path / "out" / "y.png.json").read_text())
    assert sidecar["runs"] == ["wave"] and "git_sha" in sidecar


@pytest.mark.parametrize("flags,words", [
    (["--vs", "amplitude"], "--vs shapes a --number draw"),
    (["--vs", ""], "--vs shapes a --number draw"),
    (["--number", "rms_u"], "--number needs --vs"),
    (["--number", "rms_u", "--vs", "samples", "--panel", "y"], "--number draws one summary number"),
    (["--runs", "each"], "runs is one of"),
    (["--number", "rms_u", "--vs", "samples", "--runs", "rows"], "runs is one of"),
])
def test_a_draw_refuses_a_flag_it_would_not_use(source, tmp_path, flags, words) -> None:
    """``--vs`` and ``--runs`` shape one kind of draw each: given to the other, or left out
    where it is needed, the draw is refused in words, not drawn without it."""
    with pytest.raises(SystemExit, match=re.escape(words)):
        cli.main(["draw", source, *flags, "--out-dir", str(tmp_path / "out")])


def test_a_number_against_a_list_setting_places_each_list_by_name(source) -> None:
    """A sweep over a list puts each list on the bottom axis by name, as a choice is put, rather
    than raising (a list cannot key a dict; DeePC's code review, 2026-11-11)."""
    a = lag.run(lag.Config(wave_run=source))
    b = lag.run(lag.Config(wave_run=source, limits=[-2.0, 2.0]))
    panel = sweep_of([("a", a), ("b", b)], "peak_y", vs="limits", by=())
    assert [words for _, words in panel.x_ticks] == ["[-1.0, 1.0]", "[-2.0, 2.0]"]
    [line] = panel.axes[0].lines
    assert list(line.x) == [0.0, 1.0]
    assert list(line.y) == [a.numbers["peak_y"], b.numbers["peak_y"]]


def test_a_log_axis_the_record_declares_reaches_both_drawings(runs, tmp_path) -> None:
    """A Bode plot reads ω and |G| in decades: the record declares the axes logarithmic, and the
    still and the Lab's twin draw them so; a card offers no log control (the developer's cut)."""
    rec = runs["lag"]
    magnitude = chart_of([("a", rec)], "bode-magnitude")
    assert magnitude.x_log and magnitude.y_log
    twin = figure_of(magnitude)
    assert twin["layout"]["xaxis"]["type"] == "log" and twin["layout"]["yaxis"]["type"] == "log"
    phase = figure_of(chart_of([("a", rec)], "bode-phase"))
    assert phase["layout"]["xaxis"]["type"] == "log" and "type" not in phase["layout"]["yaxis"]
    output = figure_of(chart_of([("a", rec)], "output"))
    assert "type" not in output["layout"]["xaxis"]
    [png, *_] = render(magnitude, tmp_path, stamp(0.0))
    assert png.exists()


# --- a figure the piece draws itself (branch R3) ---------------------------------------------

def test_a_records_own_figures_are_listed_after_its_charts_and_the_file_keeps_none(
        runs, source, tmp_path) -> None:
    """The run file keeps the record's fields and the figures' names; a figure is drawn when
    shown, from those fields."""
    rec = runs["lag"]
    header = rec.header()
    assert header["panels"] == ["output", "bode-magnitude", "bode-phase", "pole"]
    assert header["panel_groups"]["pole"] == "Frequency"
    raw = json.loads(rec.save(tmp_path / "again.json").read_text())
    fields = {f.name for f in dataclasses.fields(rec)}
    assert set(raw) == fields | set(header), "the header and the record's own fields, no figure"
    assert runs["wave"].header()["panels"] == ["u", "y"], "a record that draws none lists none"


def test_a_figure_named_as_a_chart_is_refused_when_saved(runs, tmp_path) -> None:
    rec = runs["lag"]

    class Twice(type(rec)):
        def figures(self):
            return (Figure(name="output", figure={"data": []}),)

    twice = Twice(**{f.name: getattr(rec, f.name) for f in dataclasses.fields(rec)})
    with pytest.raises(ValueError, match=r"declares the panel\(s\) \['output'\] more than once"):
        twice.save(tmp_path / "twice.json")
    assert not (tmp_path / "twice.json").exists()


def test_a_pieces_own_figure_reaches_the_page_as_it_drew_it_on_the_cards_paper(runs) -> None:
    rec = runs["lag"]
    drawn = own_figure(rec, "pole")
    [trace] = drawn["data"]
    assert trace["x"] == [-1.0 / rec.config.tau] and trace["y"] == [0.0] and trace["mode"] == "markers"
    assert drawn["layout"]["xaxis"]["title"]["text"] == "Re [rad/s]", "the piece's own words"
    assert "title" not in drawn["layout"], "RunLab titles no figure"
    under = drawn["layout"]["template"]["layout"]
    assert under["paper_bgcolor"] == under["plot_bgcolor"] == SURFACE, "the card's paper, under it"
    assert under["xaxis"]["gridcolor"] == under["yaxis"]["gridcolor"] == GRID, "a grid that shows on it"
    assert drawn["layout"]["height"] == ONE_PX and drawn["layout"]["meta"] == {"panel": "pole"}
    assert "paper_bgcolor" not in drawn["layout"], "laid under, never over what a piece may set"
    assert own_figure(rec, "pole") is not drawn and "template" not in rec.figures()[0].figure["layout"], \
        "the piece's figure is not written on"
    assert own_figure(rec, "output") is None, "a chart is not a figure"
    assert own_figure(runs["wave"], "pole") is None


def test_a_figure_built_with_plotlys_own_classes_is_taken_and_what_the_piece_set_is_kept(runs) -> None:
    rec = runs["lag"]

    class Own(type(rec)):
        def figures(self):
            histogram = go.Figure(go.Histogram(x=list(self.y)))
            histogram.update_layout(paper_bgcolor="#123456", height=200)
            dark = go.Figure(go.Histogram(x=list(self.y)), layout={"template": "plotly_dark"})
            return (Figure(name="spread", figure=histogram, title="Spread of y"),
                    Figure(name="dark", figure=dark),
                    Figure(name="broken", figure=[1, 2, 3]))

    own = Own(**{f.name: getattr(rec, f.name) for f in dataclasses.fields(rec)})
    drawn = own_figure(own, "spread")
    assert drawn["data"][0]["type"] == "histogram" and len(drawn["data"][0]["x"]) == len(rec.y)
    assert drawn["layout"]["paper_bgcolor"] == "#123456" and drawn["layout"]["height"] == 200
    assert drawn["layout"]["template"] is TEMPLATE, \
        "plotly's stock template, which its classes give every figure, makes way for the card's"
    assert go.Figure(drawn).layout.plot_bgcolor is None, "plotly reads it back; the paper stays under"
    chosen = own_figure(own, "dark")["layout"]["template"]
    assert chosen is not TEMPLATE and chosen["layout"]["paper_bgcolor"] != SURFACE, \
        "a template the piece chose is kept"
    with pytest.raises(TypeError, match="a figure is a plotly figure or the dict of one"):
        own_figure(own, "broken")


def test_draw_writes_the_charts_and_names_the_figures_it_left_out(runs, tmp_path, capsys) -> None:
    """The developer, 2026-11-17: a piece's own figure is the page's to show; ``draw`` says which
    it left out, and refuses one asked for by name."""
    path = runs["lag"].save(tmp_path / "lag.json")
    capsys.readouterr()
    assert cli.main(["draw", str(path), "--out-dir", str(tmp_path / "out")]) == 0
    said = capsys.readouterr()
    assert sorted(p.name for p in (tmp_path / "out").glob("*.png")) == [
        "bode-magnitude.png", "bode-phase.png", "output.png"]
    assert said.out.split() == [str(tmp_path / "out" / f"{n}.png")
                                for n in ("output", "bode-magnitude", "bode-phase")]
    assert said.err.strip() == ("not drawn, the piece's own figures, which the Lab's page shows: "
                                "pole")
    with pytest.raises(SystemExit, match="pole: drawn by the piece itself"):
        cli.main(["draw", str(path), "--panel", "pole", "--out-dir", str(tmp_path / "out")])
    cli.main(["draw", str(path), "--panel", "output", "--out-dir", str(tmp_path / "one")])
    assert capsys.readouterr().err == "", "asked for a chart by name, it has nothing to add"


# --- a card's controls, as the figure layer's keywords (BESS's ``tests/test_figure.py``) ------

@pytest.fixture
def lags(tmp_path) -> list:
    """Three lags drawing both their traces: ``a`` and ``b`` on one wave, so they hold its u
    identically, and ``c`` on a wave of twice the amplitude, so it holds no trace of theirs."""
    one = str(wave.run(wave.Config()).save(tmp_path / "one.json"))
    two = str(wave.run(wave.Config(amplitude=2.0)).save(tmp_path / "two.json"))
    return [("a", lag.run(lag.Config(wave_run=one, keep=["u", "y"]))),
            ("b", lag.run(lag.Config(wave_run=one, keep=["u", "y"], tau=0.2))),
            ("c", lag.run(lag.Config(wave_run=two, keep=["u", "y"])))]


def test_colour_by_quantity_swaps_what_the_colour_and_the_dash_tell_apart(lags) -> None:
    apart = [lags[0], lags[2]]                       # no trace held by both
    by_run = chart_of(apart, "output").axes[0].lines
    by_quantity = chart_of(apart, "output", colour_by="quantity").axes[0].lines
    assert [ln.label for ln in by_run] == [ln.label for ln in by_quantity] \
        == ["a — u", "a — y", "c — u", "c — y"]
    assert [(ln.color, ln.dash) for ln in by_run] == \
        [(shade(series_color(i), j), DASHES[j]) for i in (0, 1) for j in (0, 1)], \
        "the run picks the hue, the quantity its shade and the dash"
    assert [(ln.color, ln.dash) for ln in by_quantity] == \
        [(shade(series_color(j), i), DASHES[i]) for i in (0, 1) for j in (0, 1)], \
        "the quantity picks the hue, the run its shade and the dash"
    # a line every run holds is drawn once either way, in the first colour nothing else wears:
    # after the three runs, or after the two quantities
    same = lags[:2] + [("b2", lags[1][1])]
    for colour_by, slot in (("run", 3), ("quantity", 2)):
        first = chart_of(same, "output", colour_by=colour_by).axes[0].lines[0]
        assert (first.label, first.color) == ("3 runs — u (identical)", series_color(slot))
    with pytest.raises(ValueError, match="colour_by is one of"):
        chart_of(apart, "output", colour_by="piece")


def test_a_logarithmic_axis_the_chart_does_not_declare_is_refused_at_or_below_zero(runs) -> None:
    pairs = [("w", runs["wave"])]
    u = chart_of(pairs, "u")
    assert (u.x_log, u.y_log) == (False, False)
    assert log_refusal(u, "x") == "its bottom axis holds 1 value(s) at or below zero"
    assert re.fullmatch(r"it holds \d+ value\(s\) at or below zero", log_refusal(u, "y"))
    with pytest.raises(ValueError, match="cannot take a logarithmic bottom axis: its bottom"):
        chart_of(pairs, "u", x_log=True)
    with pytest.raises(ValueError, match="cannot take a logarithmic ordinate: it holds"):
        chart_of(pairs, "u", y_log=True)
    with pytest.raises(ValueError, match="axis is 'x' or 'y'"):
        log_refusal(u, "z")
    lag_pairs = [("l", runs["lag"])]
    bode = chart_of(lag_pairs, "bode-magnitude")
    assert (bode.x_log, bode.y_log) == (True, True), "a card opens on what the chart declares"
    plain = chart_of(lag_pairs, "bode-magnitude", x_log=False, y_log=False)
    assert (plain.x_log, plain.y_log) == (False, False), "and either is switched off"
    assert (log_refusal(plain, "x"), log_refusal(plain, "y")) == ("", "")
    phase = chart_of(lag_pairs, "bode-phase")
    assert (phase.x_log, phase.y_log) == (True, False)
    assert log_refusal(phase, "y"), "the phase runs from 0 down"


class _Declaring:
    """A record that declares one panel and nothing else a chart reads."""
    component = "declaring"

    def __init__(self, series: Series) -> None:
        self._series = series

    def series(self) -> tuple[Series, ...]:
        return (self._series,)


def test_a_logarithmic_axis_the_chart_declares_is_drawn_whatever_it_holds() -> None:
    """A release takes no chart from a project: a panel that declares a logarithmic axis over a
    value at or below zero is drawn as it was before a drawing could be asked for an axis (the
    plan of 2026-11-18, departure 2). Over the sample index it declares no logarithm."""
    rec = _Declaring(Series(name="p", x=[0.0, 1.0, 2.0], x_label="t [s]", y_label="e [-]",
                            traces=(("e", [0.0, 1.0, 10.0]),), x_log=True, y_log=True))
    for asked in ({}, {"x_log": True, "y_log": True}):
        panel = chart_of([("r", rec)], "p", **asked)
        assert (panel.x_log, panel.y_log) == (True, True)
        assert log_refusal(panel, "x") and log_refusal(panel, "y"), "each holds a zero"
    over_index = chart_of([("r", rec)], "p", x="index")
    assert (over_index.x_log, over_index.y_log) == (False, True)
    with pytest.raises(ValueError, match="logarithmic bottom axis"):
        chart_of([("r", rec)], "p", x="index", x_log=True)


def test_the_sample_index_counts_the_samples_from_zero_and_names_the_axis(runs) -> None:
    rec = runs["lag"]
    n = len(rec.t)
    assert INDEX_LABEL == "Sample index [-]"
    for how in ("one", "rows"):
        panel = chart_of([("a", rec), ("b", rec)], "output", x="index", runs=how)
        assert panel.x_label == INDEX_LABEL
        assert all(list(ln.x) == list(range(n)) for ax in panel.axes for ln in ax.lines)
    assert chart_of([("a", rec)], "output").x_label == "t [s]"
    with pytest.raises(ValueError, match="x is one of"):
        chart_of([("a", rec)], "output", x="time")


def test_the_shaping_reaches_both_drawings(runs, tmp_path) -> None:
    pairs = [("l", runs["lag"])]
    shaping = {"points": True, "y_log": False, "x": "index"}
    fig = figure_of(chart_of(pairs, "bode-magnitude", **shaping))
    assert fig["layout"]["xaxis"]["title"]["text"] == INDEX_LABEL
    assert "type" not in fig["layout"]["xaxis"] and "type" not in fig["layout"]["yaxis"]
    drawn = [t for t in fig["data"] if t.get("line", {}).get("width") == LINE_WIDTH]
    assert drawn and all(t["mode"] == "markers" for t in drawn)
    joined = figure_of(chart_of(pairs, "bode-magnitude"))
    assert joined["layout"]["xaxis"]["type"] == joined["layout"]["yaxis"]["type"] == "log"
    assert all(t["mode"] == "lines" for t in joined["data"]
               if t.get("line", {}).get("width") == LINE_WIDTH)
    [still] = draw(pairs, tmp_path, panels=["bode-magnitude"], **shaping)
    side = json.loads((still.parent / f"{still.name}.json").read_text())
    assert side["shaping"] == shaping and side["x_label"] == INDEX_LABEL
    for how in ("rows", "mean"):
        seeds = [(f"s{seed}", wave.run(wave.Config(noise=0.5, seed=seed))) for seed in (1, 2)]
        panel = chart_of(seeds, "y", runs=how, points=True)
        assert all(ln.points for ax in panel.axes for ln in ax.lines), how


def _swept(values, seeds=(0, 1)) -> list:
    return [(f"A{a}-s{s}", wave.run(wave.Config(amplitude=a, seed=s)))
            for a in values for s in seeds]


def test_a_sweep_over_positive_values_takes_a_log_axis_with_its_runs_side_by_side() -> None:
    """Spread by a share of the span, two seeds at 0.001 of a sweep up to 1 were drawn at
    -0.005 and the log axis was greyed (BESS's code review, 2026-10-27)."""
    pairs = _swept((0.001, 0.01, 1.0))
    plain = sweep_of(pairs, "rms_u", vs="amplitude")
    assert (plain.x_log, plain.y_log) == (False, False)
    assert log_refusal(plain, "x") == ""
    assert np.min(plain.axes[0].lines[0].drawn_x()) < 0, "spread by a share of the span"
    panel = sweep_of(pairs, "rms_u", vs="amplitude", x_log=True, y_log=True)
    (line,) = panel.axes[0].lines
    drawn = line.drawn_x()
    assert (panel.x_log, panel.y_log) == (True, True)
    assert np.all(drawn > 0) and drawn[0] < 0.001 < drawn[1], drawn
    assert list(line.x) == [0.001, 0.001, 0.01, 0.01, 1.0, 1.0], "the numbers keep x"
    joined = sweep_of(pairs, "rms_u", vs="amplitude", points=False)
    assert not joined.axes[0].lines[0].points and plain.axes[0].lines[0].points
    with pytest.raises(ValueError, match="logarithmic bottom axis: its bottom axis holds 1"):
        sweep_of(_swept((0.0, 1.0)), "rms_u", vs="amplitude", x_log=True)
    named = [(shape, wave.run(wave.Config(shape=shape))) for shape in ("sine", "square")]
    with pytest.raises(ValueError, match="its bottom axis holds names"):
        sweep_of(named, "rms_u", vs="shape", x_log=True)


def test_the_table_is_exactly_what_the_chart_draws(lags) -> None:
    rec = lags[0][1]
    s = next(x for x in rec.series() if x.name == "output")
    table = table_of(chart_of([lags[0]], "output"))
    assert table.header == ("t [s]", "u", "y")
    assert [row[0] for row in table.rows] == list(np.asarray(s.x, float))
    for j, (_, y) in enumerate(s.traces, start=1):
        assert [row[j] for row in table.rows] == list(np.asarray(y, float))
    assert table.beside == (("Lower bound of y [-]", (-1.0,)), ("Upper bound of y [-]", (1.0,)))
    # a row per run: each row's traces under its run's name
    rows = table_of(chart_of([lags[0], lags[2]], "output", runs="rows"))
    assert rows.header == ("t [s]", "a · u", "a · y", "c · u", "c · y")
    # a band that varies is its two edges; the mean of two seeds holds one about it
    seeds = [(f"s{seed}", wave.run(wave.Config(noise=0.5, seed=seed))) for seed in (1, 2)]
    mean = chart_of(seeds, "y", runs="mean")
    pooled = table_of(mean)
    (band,) = mean.axes[0].bands
    assert pooled.header == ("t", "Mean of 2 runs · y", f"{band.label} (lower)",
                             f"{band.label} (upper)")
    assert [row[2] for row in pooled.rows] == list(np.asarray(band.lo, float))
    # a number against a setting: a row per point, named by its run, the setting's own value
    sweep = table_of(sweep_of(_swept((1.0, 2.0)), "rms_u", vs="amplitude"))
    assert sweep.header == ("trace", "point", "A", "RMS of u [-]")
    assert [(row[1], row[2]) for row in sweep.rows] == \
        [("A1.0-s0", 1.0), ("A1.0-s1", 1.0), ("A2.0-s0", 2.0), ("A2.0-s1", 2.0)], \
        "where a point is drawn to the side, the table keeps the setting itself"


# --- what a Save writes: the span of the bottom axis, and the numbers beside the still --------

def test_the_span_of_the_bottom_axis_reaches_both_drawings(runs, tmp_path) -> None:
    pairs = [("w", runs["wave"])]
    panel = chart_of(pairs, "u", x_range=(0.2, 0.6))
    assert panel.x_range == (0.2, 0.6) and chart_of(pairs, "u").x_range is None
    xaxis = figure_of(panel)["layout"]["xaxis"]
    assert (xaxis["range"], xaxis["autorange"]) == ([0.2, 0.6], False)
    assert "range" not in figure_of(chart_of(pairs, "u"))["layout"]["xaxis"]
    [still] = draw(pairs, tmp_path, panels=["u"], x_range=(0.2, 0.6))
    side = json.loads((still.parent / f"{still.name}.json").read_text())
    assert side["xlim"] == [0.2, 0.6] and side["shaping"] == {"x_range": [0.2, 0.6]}
    # on a logarithmic axis the span is in the axis's own units; plotly holds its powers of ten
    lag_pairs = [("l", runs["lag"])]
    bode = figure_of(chart_of(lag_pairs, "bode-magnitude", x_range=(1.0, 100.0)))
    assert bode["layout"]["xaxis"]["range"] == [0.0, 2.0]
    [still] = draw(lag_pairs, tmp_path, panels=["bode-magnitude"], x_range=(1.0, 100.0))
    assert json.loads((still.parent / f"{still.name}.json").read_text())["xlim"] == [1.0, 100.0]
    with pytest.raises(ValueError, match="runs from low to high"):
        chart_of(pairs, "u", x_range=(0.6, 0.2))
    with pytest.raises(ValueError, match="a logarithmic bottom axis shows no span from -1.0"):
        chart_of(lag_pairs, "bode-magnitude", x_range=(-1.0, 100.0))


def test_a_draw_with_its_table_writes_the_numbers_every_digit(lags, tmp_path) -> None:
    """BESS's ``test_a_shaped_draw_writes_the_card_and_its_numbers_every_digit``: beside the
    still, what it draws as a CSV, each number as Python writes it whole, with a sidecar of its
    own holding the still's facts."""
    pairs = [lags[0], lags[2]]
    paths = draw(pairs, tmp_path, panels=["output"], colour_by="quantity", table=True)
    assert [p.name for p in paths] == ["output.png", "output.csv"]
    side = json.loads((tmp_path / "output.csv.json").read_text())
    assert side["table"] == "output.csv" and side["runs"] == ["a", "c"]
    assert side["shaping"] == {"colour_by": "quantity"}
    assert json.loads((tmp_path / "output.png.json").read_text())["shaping"] == side["shaping"]
    rows = (tmp_path / "output.csv").read_text().splitlines()
    assert rows[0] == "t [s],a — u,a — y,c — u,c — y"
    a, c = lags[0][1], lags[2][1]
    assert rows[4] == ",".join(repr(float(v)) for v in (a.t[3], a.u[3], a.y[3], c.u[3], c.y[3]))
    assert len(rows) == 1 + len(a.t) + 2, "the header, a row a sample, the two bounds beside"
    assert rows[-2:] == ["Lower bound of y [-],-1.0", "Upper bound of y [-],1.0"]
    assert [p.name for p in draw(pairs, tmp_path / "plain", panels=["output"])] == ["output.png"]
    swept = draw_sweep(_swept((1.0, 2.0)), tmp_path, "rms_u", vs="amplitude", table=True)
    assert [p.name for p in swept] == ["rms_u-vs-amplitude.png", "rms_u-vs-amplitude.csv"]
    assert (tmp_path / "rms_u-vs-amplitude.csv").read_text().splitlines()[:2] == \
        ["trace,point,A,RMS of u [-]", f"RMS of u,A1.0-s0,1.0,{_swept((1.0,))[0][1].numbers['rms_u']!r}"]



# --- the figure layer's own checks, carried from BESS's ``tests/test_figure.py`` (2026-11-19) ---

ROOT = Path(__file__).resolve().parent.parent


def test_every_save_goes_through_the_one_chokepoint() -> None:
    hits = [str(p.relative_to(ROOT)) for p in sorted((ROOT / "runlab").rglob("*.py"))
            if "savefig(" in p.read_text() or "csv.writer(" in p.read_text()]
    assert hits == ["runlab/figure/style.py"], hits


def test_the_colours_cycle_and_a_shade_keeps_its_hue() -> None:
    """Colour goes by position and cycles past the last; a run's traces are shades of its hue:
    the same hue at another lightness, the zeroth the colour itself."""
    assert [series_color(i) for i in range(2 * len(SERIES))] == list(SERIES) * 2
    for c in SERIES:
        assert shade(c, 0) == c
        hue, sat, light = _hsl(c)
        for k in (1, 2, 3):
            h, _, l = _hsl(shade(c, k))
            assert l != pytest.approx(light, abs=0.02), (c, k)
            if sat > 0:
                assert abs((h - hue + 180) % 360 - 180) < 3, (c, k, h, hue)


def test_a_long_legend_name_breaks_at_its_own_separators_and_keeps_every_word() -> None:
    name = "p-power_kw-100, p-power_kw-50, p-power_kw-20 — estimate +/- its own 1 sigma"
    lines = broken(name).split("\n")
    assert len(lines) > 1 and all(len(line) <= LEGEND_LINE for line in lines), lines
    assert "".join(lines).replace(" ", "") == name.replace(" ", "")
    assert broken("truth") == "truth"


def test_the_twin_keeps_its_legend_small_and_writes_every_name_whole() -> None:
    pairs = [("a", wave.run(wave.Config())), ("b", wave.run(wave.Config(amplitude=2.0)))]
    fig = figure_of(chart_of(pairs, "u"))
    legend = fig["layout"]["legend"]
    assert legend["maxheight"] <= 0.3 and (legend["xanchor"], legend["yanchor"]) == ("right", "bottom")
    assert fig["layout"]["hoverlabel"]["namelength"] == -1, "plotly cuts a name at 15 characters"
    assert all((fig["layout"][a]["exponentformat"], fig["layout"][a]["minexponent"]) ==
               ("power", 5) for a in ("xaxis", "yaxis")), "powers of ten past 5 decades only"
    assert not figure_of(chart_of(pairs, "u"), legend=False)["layout"]["showlegend"]
    # a number card draws no legend: its hover names the run and, beside it, the curve
    sweep = figure_of(sweep_of(pairs, "rms_u", vs="amplitude"), legend=False)
    assert all("<extra></extra>" not in t["hovertemplate"] for t in sweep["data"])


def test_a_short_line_marks_its_samples() -> None:
    short = Line("a", list(range(SHORT - 1)), [1.0] * (SHORT - 1), SERIES[0])
    long = Line("b", list(range(SHORT)), [2.0] * SHORT, SERIES[1])
    fig = figure_of(Panel("p", "t [s]", (Axes("v [V]", (short, long)),)))
    assert [t["mode"] for t in fig["data"]] == ["lines+markers", "lines"]


def test_a_band_belongs_to_the_longest_trace_its_name_starts_with() -> None:
    """``x_hat ± 2σ`` is the uncertainty of ``x_hat``, not of ``x`` (BESS's code review,
    2026-10-27)."""
    s = Series(name="p", x=[0.0, 1.0], x_label="t [s]", y_label="v [V]",
               traces=(("x", [0.0, 1.0]), ("x_hat", [0.0, 1.0])),
               bands=(("x_hat ± 2σ", -1.0, 1.0),))
    rec = type("OnePanel", (), {"component": "p", "series": lambda self: (s,)})()
    (band,) = chart_of([("r", rec)], "p").axes[0].bands
    assert band.color == SERIES[1]


def test_a_row_each_keeps_every_row_its_height_however_many_rows() -> None:
    """A fixed gap between rows left no height for a row from 11 rows on (BESS's code review,
    2026-10-27)."""
    one = wave.run(wave.Config())
    fig = figure_of(chart_of([(f"r{i}", one) for i in range(12)], "u", runs="rows"))
    domains = [fig["layout"]["yaxis" if i == 0 else f"yaxis{i + 1}"]["domain"] for i in range(12)]
    assert all(hi > lo for lo, hi in domains), domains
    assert all(below[1] < above[0] for above, below in zip(domains, domains[1:])), domains


def test_a_panel_spec_is_a_value() -> None:
    assert dataclasses.is_dataclass(Panel) and Panel.__dataclass_params__.frozen


def test_a_row_each_is_one_time_axis_with_one_legend_and_the_quantity_said_once() -> None:
    one, two = wave.run(wave.Config()), wave.run(wave.Config(amplitude=2.0))
    panel = chart_of([("a", one), ("b", two)], "u", runs="rows")
    quantity = chart_of([("a", one)], "u").axes[0].y_label
    assert [ax.y_label for ax in panel.axes] == ["a", "b"] and panel.quantity == quantity
    fig = figure_of(panel)
    assert {t["yaxis"] for t in fig["data"]} == {"y", "y2"}
    assert all(t.get("xaxis", "x") == "x" for t in fig["data"]), "one time axis: zoom follows"
    assert fig["layout"]["xaxis"]["anchor"] == "y2"
    assert fig["layout"]["yaxis"]["domain"][0] > fig["layout"]["yaxis2"]["domain"][1], \
        "the first run is the top row"
    in_legend = [t for t in fig["data"] if t.get("showlegend")]
    assert in_legend and all(t["yaxis"] == "y" for t in in_legend), "one legend, from row one"
    assert all(t["legendgroup"] == t["name"] for t in fig["data"]), "a click toggles every row"
    # each row's words flat above it, the quantity once up the side
    assert [a["text"] for a in fig["layout"]["annotations"]] == ["a", "b", quantity]
    assert [fig["layout"][k]["title"]["text"] for k in ("yaxis", "yaxis2")] == ["", ""]
    assert fig["layout"]["height"] == ONE_PX + MORE_ROW_PX
