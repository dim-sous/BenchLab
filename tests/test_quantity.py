"""A quantity named once, and the words of a chart made from it (0.22): its title, its axes and
its lines, by name as the chart is built, by symbol when the page's Names / Symbols switch asks.
Words a project writes in full stay as written either way, and a chart built by position, as a
project builds one, keeps its meaning."""

from __future__ import annotations

import numpy as np
import pytest

from runlab import cli
from runlab.figure.chart import chart_of
from runlab.lab import view
from runlab.record import Quantity, Series
from tests.toy import fit

T = np.arange(4.0)
SOC = Quantity("soc", name="State of charge", symbol="SOC")
TIME = Quantity("time", name="Time", symbol="t", unit="s")


def _words(s: Series) -> tuple:
    return s.title, s.x_label, s.y_label, [label for label, _ in s.traces]


def test_a_quantity_is_worded_by_its_name_or_its_symbol_with_its_unit() -> None:
    assert (SOC.word("names"), SOC.word("symbols")) == ("State of charge", "SOC")
    assert (TIME.axis("names"), TIME.axis("symbols")) == ("Time [s]", "t [s]")
    assert SOC.axis("names") == "State of charge [-]", "no unit: [-]"
    only_symbol, only_name = Quantity("y1", symbol="y1"), Quantity("h", name="Height", unit="mm")
    assert [only_symbol.word(w) for w in ("names", "symbols")] == ["y1", "y1"]
    assert [only_name.axis(w) for w in ("names", "symbols")] == ["Height [mm]", "Height [mm]"]


def test_a_quantity_with_neither_word_and_a_wording_not_known_are_refused() -> None:
    with pytest.raises(ValueError, match="neither a name nor a symbol"):
        Quantity("k")
    with pytest.raises(ValueError, match="one of"):
        SOC.word("both")
    with pytest.raises(ValueError, match="one of"):
        Series("soc", T, quantity=SOC, traces=(("Truth", T),)).in_words("both")


def test_a_chart_is_worded_by_its_quantities_by_name_as_built_and_by_symbol_on_asking() -> None:
    s = Series("soc", T, quantity=SOC, x_quantity=TIME, traces=(("Truth", T), (SOC, T)))
    assert _words(s) == ("State of charge", "Time [s]", "State of charge [-]",
                         ["Truth", "State of charge"])
    assert _words(s.in_words("symbols")) == ("SOC", "t [s]", "SOC [-]", ["Truth", "SOC"])
    assert _words(s)[0] == "State of charge", "the chart as built stays in names"
    assert s.in_words("names") is s


def test_words_written_in_full_stay_as_written_by_name_and_by_symbol() -> None:
    by_position = Series("height", T, "t [s]", "H [mm]", (("H", T),))     # as a project builds one
    assert _words(by_position) == ("height", "t [s]", "H [mm]", ["H"])
    assert _words(by_position.in_words("symbols")) == _words(by_position)
    force = Quantity("force", name="Force", symbol="F", unit="N")
    titled = Series("lift-drag", T, quantity=force, x_quantity=TIME, traces=(("Lift", T),),
                    title="Lift and drag")
    assert _words(titled.in_words("symbols")) == ("Lift and drag", "t [s]", "F [N]", ["Lift"])


def test_a_chart_that_says_an_axis_twice_is_refused() -> None:
    with pytest.raises(ValueError, match="says one or the other"):
        Series("soc", T, y_label="SOC [-]", quantity=SOC, traces=(("Truth", T),))
    with pytest.raises(ValueError, match="says one or the other"):
        Series("soc", T, x_label="t [s]", x_quantity=TIME, traces=(("Truth", T),))
    with pytest.raises(ValueError, match="declares no trace"):
        Series("soc", T, quantity=SOC)


def test_the_chart_builder_draws_a_chart_in_the_words_it_is_asked(tmp_path) -> None:
    """The made-up fit's loss chart, made from two quantities: in names the words it wrote in
    full before 0.22, in symbols its symbols; its line, written in full, the same in both."""
    cli.main(["run", "fit", "--name", "a", "--out-dir", str(tmp_path)])
    pairs = [("a", fit.Record.load(tmp_path / "fit" / "a.json"))]
    names, symbols = chart_of(pairs, "loss"), chart_of(pairs, "loss", words="symbols")
    assert (names.x_label, names.axes[0].y_label) == ("Step [-]", "Mean squared error [-]")
    assert (symbols.x_label, symbols.axes[0].y_label) == ("k [-]", "MSE [-]")
    assert [ln.label for ln in symbols.axes[0].lines] == [ln.label for ln in names.axes[0].lines]


def test_the_chart_list_titles_a_chart_in_the_page_s_words() -> None:
    run = {"name": "a", "panels": ["loss"], "panel_groups": {"loss": "Fit"},
           "panel_titles": {"loss": "Mean squared error"}, "panel_symbols": {"loss": "MSE"}}
    assert [r["title"] for r in view.chart_rows([run], [])] == ["Mean squared error"]
    assert [r["title"] for r in view.chart_rows([run], [], words="symbols")] == ["MSE"]
