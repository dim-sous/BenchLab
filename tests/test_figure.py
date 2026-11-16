"""The figure layer draws what records declare, and figures describe: a legend only when there is
more than one label, no title (``CLAUDE.md``, "Figures describe, they never conclude"). DeePC's
``tests/test_figure.py``, moved here onto the made-up project in branch R1."""

from __future__ import annotations

import dataclasses
import json
import re

import plotly.graph_objects as go
import pytest

import benchlab.figure.render as render_module
from benchlab import Figure, cli
from benchlab.figure import draw
from benchlab.figure.chart import chart_of, sweep_of
from benchlab.figure.own import TEMPLATE, own_figure
from benchlab.figure.render import has_legend, render
from benchlab.figure.twin import figure_of
from benchlab.figure.style import GRID, SURFACE
from benchlab.figure.twin import ONE_PX
from benchlab.record import stamp
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
    assert "title" not in drawn["layout"], "Benchlab titles no figure"
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
