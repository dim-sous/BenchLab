"""A quantity named once, and the words of a chart made from it (0.22): its title, its axes and
its lines, by name as the chart is built, by symbol when the page's Names / Symbols switch asks.
Words a project writes in full stay as written either way, and a chart built by position, as a
project builds one, keeps its meaning. A number made from a quantity and a statistic (0.23): its
words and unit RunLab's, saved with its parts; a number saved before shows its words as saved.
A line's role, a bound line, a band's confidence interval and the time axis (0.25): RunLab's
words, worded by the switch where a quantity is in them."""

from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

from runlab import cli
from runlab.figure.chart import chart_of, sweep_of
from runlab.lab import state, view
from runlab.record import TIME, Number, Quantity, Role, Series, bound_refs, ci, number_words
from tests.toy import fit

T = np.arange(4.0)
SOC = Quantity("soc", name="State of charge", symbol="SOC")


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


T_C = Quantity("temperature", name="Temperature", symbol="T", unit="°C")


def test_a_number_is_worded_by_its_quantity_and_its_statistic_with_its_unit() -> None:
    rc1 = Quantity("vrc1", name="RC1 voltage", symbol="V_RC1", unit="V")
    cases = {("final", SOC): ("Final state of charge", "Final SOC", ""),
             ("initial", SOC): ("Initial state of charge", "Initial SOC", ""),
             ("max", T_C): ("Max temperature", "Max T", "°C"),
             ("min", T_C): ("Min temperature", "Min T", "°C"),
             ("mean", rc1): ("Mean RC1 voltage", "Mean V_RC1", "V"),       # two capitals kept
             ("std", T_C): ("Temperature std", "T std", "°C"),             # a name that opens it
             ("rmse", SOC): ("State of charge RMSE", "SOC RMSE", ""),
             ("snr", T_C): ("Temperature SNR", "T SNR", "")}               # a ratio: no unit
    for (statistic, quantity), (names, symbols, unit) in cases.items():
        n = Number(statistic, quantity=quantity, statistic=statistic)
        assert (n.label, n.unit) == (names, unit), statistic
        assert (n.in_words("symbols").label, n.in_words("symbols").unit) == (symbols, unit)
    share = Number("clipped", statistic="share_of_steps", condition="clipped")
    assert (share.label, share.unit, share.in_words("symbols").label) == \
        ("Share of steps clipped", "", "Share of steps clipped")
    assert Number("t", statistic="share_of_time", condition="in band").label == \
        "Share of time in band"
    itself = Number("corner", quantity=Quantity("wc", name="Corner frequency", symbol="ω_c",
                                                 unit="rad/s"))
    assert (itself.label, itself.unit, itself.in_words("symbols").label) == \
        ("Corner frequency", "rad/s", "ω_c")


def test_a_number_written_in_full_or_by_position_stays_as_written() -> None:
    by_position = Number("final_soc", "Final SOC", "", headline=True)   # as a project builds one
    assert (by_position.label, by_position.unit) == ("Final SOC", "")
    assert by_position.in_words("symbols") is by_position


def test_a_number_that_says_its_words_twice_or_its_statistic_wrongly_is_refused() -> None:
    for bad, words in ((lambda: Number("x", "Final SOC", quantity=SOC, statistic="final"),
                        "says one or the other"),
                       (lambda: Number("x", unit="V", quantity=SOC, statistic="final"),
                        "says one or the other"),
                       (lambda: Number("x", quantity=SOC, statistic="median"), "is not one of"),
                       (lambda: Number("x", statistic="share_of_time"), "is a share"),
                       (lambda: Number("x", quantity=SOC, statistic="share_of_time",
                                       condition="in band"), "is a share"),
                       (lambda: Number("x", statistic="rmse"), "of a quantity"),
                       (lambda: Number("x", "X", condition="clipped"), "only a share"),
                       (lambda: Number("x"), "neither words nor a quantity")):
        with pytest.raises(ValueError, match=words):
            bad()


def test_a_saved_number_is_worded_from_its_parts_and_one_saved_before_as_saved() -> None:
    saved = dataclasses.asdict(Number("rmse_soc", quantity=SOC, statistic="rmse"))
    assert number_words(saved, "names") == ("State of charge RMSE", "")
    assert number_words(saved, "symbols") == ("SOC RMSE", "")
    before = json.loads(open("tests/runs/v0.22.0.json").read())["number_specs"]   # a 0.22 run
    for spec in before:
        assert number_words(spec, "symbols") == (spec["label"], spec.get("unit") or "")


def test_a_run_saves_its_numbers_parts_and_the_table_and_the_number_chart_word_them(
        tmp_path) -> None:
    for name, rate in (("a", "0.5"), ("b", "0.3")):
        cli.main(["run", "fit", "--name", name, "--out-dir", str(tmp_path / "results"),
                  "--set", f"rate={rate}"])
    held = json.loads((tmp_path / "results" / "fit" / "a.json").read_text())["number_specs"]
    loss = next(spec for spec in held if spec["name"] == "loss")
    assert (loss["label"], loss["statistic"], loss["quantity"]["key"]) == \
        ("Final mean squared error", "final", "mse"), "its words in names, its parts beside them"
    runs = [r for r in state.records(str(tmp_path), "results") if r["piece"] == "fit"]

    def terms(words: str) -> dict[str, str]:
        return {r["key"]: r["term"] for r in view.compare_rows(runs, [], words=words)
                if r["kind"] == "number"}
    assert terms("names")["loss"] == "Final mean squared error"
    assert terms("symbols")["loss"] == "Final MSE"
    assert terms("names")["w0"] == terms("symbols")["w0"] == "Fitted intercept", "in full"
    pairs = [(n, fit.Record.load(tmp_path / "results" / "fit" / f"{n}.json")) for n in "ab"]
    assert sweep_of(pairs, "loss", vs="rate").axes[0].y_label == "Final mean squared error [-]"
    assert sweep_of(pairs, "loss", vs="rate", words="symbols").axes[0].y_label == "Final MSE [-]"


def _lines(s: Series) -> tuple:
    return ([label for label, _ in s.traces], [label for label, _ in s.refs],
            [label for label, *_ in s.bands])


def test_every_role_has_one_spelling_the_same_by_name_and_by_symbol() -> None:
    assert [(r.word("names"), r.word("symbols")) for r in Role] == [
        (w, w) for w in ("Truth", "Estimate", "Measured", "Estimation error",
                         "Measurement error", "Setpoint", "Applied")]
    misspelt = "ESTIMAT"
    with pytest.raises(AttributeError):
        getattr(Role, misspelt)                        # a misspelt role fails where it is written
    with pytest.raises(ValueError, match="one of"):
        Role.TRUTH.word("both")


def test_a_chart_s_lines_bounds_and_bands_are_worded_from_their_parts() -> None:
    s = Series("soc", T, quantity=SOC, x_quantity=TIME,
               traces=((Role.TRUTH, T), (Role.ESTIMATE, T), ("Mine", T)),
               refs=bound_refs([0.1, 0.9], SOC) + ((Role.SETPOINT, 0.5),),
               bands=((ci(Role.ESTIMATE), T, T), (ci(SOC, 99), T, T), ("Own band", T, T)))
    assert (s.x_label, s.in_words("symbols").x_label) == ("Time [s]", "t [s]")
    assert _lines(s) == (["Truth", "Estimate", "Mine"],
                         ["Lower bound of state of charge [-]", "Upper bound of state of charge [-]",
                          "Setpoint"],
                         ["Estimate 95% CI", "State of charge 99% CI", "Own band"])
    assert _lines(s.in_words("symbols")) == (["Truth", "Estimate", "Mine"],
                                             ["Lower bound of SOC [-]", "Upper bound of SOC [-]",
                                              "Setpoint"],
                                             ["Estimate 95% CI", "SOC 99% CI", "Own band"])


def test_bound_refs_in_words_keeps_its_meaning_and_a_quantity_holds_its_unit() -> None:
    assert bound_refs([-1.0, float("inf")], "y", "-") == (("Lower bound of y [-]", -1.0),)
    t_c = [ref for ref, _ in bound_refs([0.0, 40.0], T_C)]
    assert [b.word("names") for b in t_c] == ["Lower bound of temperature [°C]",
                                             "Upper bound of temperature [°C]"]
    assert [b.word("symbols") for b in t_c] == ["Lower bound of T [°C]", "Upper bound of T [°C]"]
    with pytest.raises(ValueError, match="holds its unit"):
        bound_refs([0.0, 1.0], SOC, "V")
    with pytest.raises(ValueError, match="its unit is needed"):
        bound_refs([0.0, 1.0], "y")


def test_the_made_up_lag_s_bound_lines_read_as_before(tmp_path) -> None:
    from tests.toy import lag
    cli.main(["run", "wave", "--name", "w", "--out-dir", str(tmp_path / "results")])
    cli.main(["run", "lag", "--name", "one", "--out-dir", str(tmp_path / "results"),
              "--set", f"wave_run={tmp_path / 'results' / 'wave' / 'w.json'}"])
    output = next(s for s in lag.Record.load(tmp_path / "results" / "lag" / "one.json").series()
                  if s.name == "output")
    for words in ("names", "symbols"):
        assert [label for label, _ in output.in_words(words).refs] == \
            [f"{side} bound of y [-]" for side in ("Lower", "Upper")][:len(output.refs)]
