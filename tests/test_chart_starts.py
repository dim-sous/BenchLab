"""How a chart starts and what belongs to a line (1.5): a chart of events starts as dots, one that
describes a single run starts a row per run, two quantities in two units drawn as rows of one
figure, the shares of one whole stacked as areas, and a band or a reference line drawn in the
colour of the line it names. On records built here, as a project's would be."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from runlab import Series
from runlab.figure.chart import chart_of
from runlab.figure.render import render
from runlab.figure.style import INK_SECONDARY, NEUTRAL, series_color, shade
from runlab.figure.twin import figure_of
from runlab.lab import shaping
from runlab.record import stamp

X = np.linspace(0.0, 1.0, 11)


class _Run:
    """A record of the made-up piece ``made``, declaring the panels it is given."""
    component = "made"

    def __init__(self, *panels: Series) -> None:
        self._panels = panels

    def series(self) -> tuple[Series, ...]:
        return self._panels


def _rows(k: float = 1.0) -> Series:
    return Series(name="both", x=X, x_label="t [s]", y_label="", rows=(
        Series(name="speed", x=X, x_label="t [s]", y_label="speed [m/s]",
               traces=(("speed", k * X),), refs=(("cruise", 0.5),)),
        Series(name="height", x=X, x_label="t [s]", y_label="height [m]",
               traces=(("height", 2.0 * k * X),))))


def test_a_chart_of_events_starts_as_dots_and_can_be_drawn_as_lines() -> None:
    events = Series(name="miss", x=X, x_label="try [-]", y_label="miss [m]",
                    traces=(("miss", X),), points=True)
    pairs = [("a", _Run(events))]
    assert chart_of(pairs, "miss").axes[0].lines[0].points
    assert not chart_of(pairs, "miss", points=False).axes[0].lines[0].points
    ctx = shaping.Context("chart", runs=1, declared_points=True)
    assert shaping.draw_keywords(shaping.Card(1, "chart", chart="miss"), ctx)["points"] is True


def test_a_chart_of_one_run_starts_a_row_per_run_and_overlays_on_asking() -> None:
    ctx = shaping.Context("chart", runs=2, declared_split=True)
    card = shaping.Card(1, "chart", chart="modes")
    assert shaping.draw_keywords(card, ctx)["runs"] == "rows"
    card.runs = "one"
    assert shaping.draw_keywords(card, ctx)["runs"] == "one"
    alone = shaping.Context("chart", runs=1, declared_split=True)
    assert shaping.draw_keywords(shaping.Card(2, "chart"), alone)["runs"] == "one"


def test_rows_are_drawn_as_stacked_axes_of_one_figure_over_every_run() -> None:
    pairs = [("a", _Run(_rows())), ("b", _Run(_rows(2.0)))]
    panel = chart_of(pairs, "both")
    assert [ax.y_label for ax in panel.axes] == ["speed [m/s]", "height [m]"]
    assert [[line.label for line in ax.lines] for ax in panel.axes] == [["a", "b"], ["a", "b"]]
    assert [r.label for r in panel.axes[0].refs] == ["cruise"] and not panel.axes[1].refs
    with pytest.raises(ValueError, match="drawn a row per quantity; its runs are overlaid"):
        chart_of(pairs, "both", runs="rows")
    fig = figure_of(panel)
    assert fig["layout"]["meta"]["rows"] == ["speed [m/s]", "height [m]"]
    assert {t["yaxis"] for t in fig["data"]} == {"y", "y2"}


def test_a_panel_of_rows_carries_nothing_of_its_own_and_rows_do_not_nest() -> None:
    row = _rows().rows[0]
    with pytest.raises(ValueError, match="is drawn as its rows; it carries no traces"):
        Series(name="x", x=X, x_label="t", y_label="", traces=(("a", X),), rows=(row,))
    with pytest.raises(ValueError, match="rows do not nest"):
        Series(name="x", x=X, x_label="t", y_label="", rows=(_rows(),))
    with pytest.raises(ValueError, match="a row's x is its panel's"):
        Series(name="x", x=X[:5], x_label="t", y_label="", rows=(row,))


def test_shares_of_one_whole_are_stacked_as_areas(tmp_path: Path) -> None:
    shares = Series(name="modes", x=X, x_label="t [s]", y_label="probability [-]",
                    traces=(("CV", 0.25 + 0 * X), ("CA", 0.75 + 0 * X)), stacked=True,
                    split=True)
    panel = chart_of([("a", _Run(shares))], "modes")
    assert [line.stack for line in panel.axes[0].lines] == ["a", "a"]
    fig = figure_of(panel)
    assert [t.get("stackgroup") for t in fig["data"]] == ["a", "a"]
    split = chart_of([("a", _Run(shares)), ("b", _Run(shares))], "modes", runs="rows")
    assert [[line.stack for line in ax.lines] for ax in split.axes] == [["a", "a"], ["b", "b"]]
    [png] = render(panel, tmp_path, stamp(0.0))
    assert png.stat().st_size > 0
    with pytest.raises(ValueError, match="nothing to put a band around"):
        Series(name="m", x=X, x_label="t", y_label="p", traces=(("a", X),),
               bands=(("b", X, X),), stacked=True)


def test_a_band_or_a_reference_line_wears_the_colour_of_the_line_it_names() -> None:
    est = Series(name="pos", x=X, x_label="t [s]", y_label="x [m]",
                 traces=(("truth", X), ("estimate", X)),
                 bands=(("95% interval", X - 0.1, X + 0.1, "estimate"),),
                 refs=(("limit", 0.9), ("estimate's mean", 0.5, "estimate")))
    alone = chart_of([("a", _Run(est))], "pos")
    assert alone.axes[0].bands[0].color == series_color(1), "the estimate's, not the truth's"
    assert [r.color for r in alone.axes[0].refs] == [INK_SECONDARY, series_color(1)]
    other = Series(name="pos", x=X, x_label="t [s]", y_label="x [m]",
                   traces=(("truth", X), ("estimate", X)),
                   bands=(("95% interval", X - 0.2, X + 0.2, "estimate"),))
    two = chart_of([("a", _Run(est)), ("b", _Run(other))], "pos")
    assert [b.color for b in two.axes[0].bands] == [shade(series_color(0), 1),
                                                    shade(series_color(1), 1)], \
        "each run's band in its run's hue, its estimate's shade"
    assert NEUTRAL not in [b.color for b in two.axes[0].bands]
    with pytest.raises(ValueError, match="belongs to \\['speed'\\], which is not one of its "
                                         "traces"):
        Series(name="p", x=X, x_label="t", y_label="x", traces=(("x", X),),
               bands=(("b", X, X, "speed"),))
