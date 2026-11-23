"""A setting that holds another piece's whole settings, a part (1.2): its settings named by dotted
names on every surface, only the groups it composes, set by a path, refused outside those groups
and behind its gate, saved as a dict and read back, swept, shown on the form and in the compare
table. On the made-up lag's ``wave``: the wave it builds when it is not driven by a saved run, of
which it composes the Wave group alone."""

from __future__ import annotations

import json

import param
import pytest

from runlab import Settings, cli, with_overrides
from runlab.figure.chart import distinct, sweep_of
from runlab.lab import jobs, view
from runlab.lab.form import Form
from runlab.lab.state import pieces, records
from runlab.record.config import fields_of, flat, from_dict, from_saved, parameter_at, saved
from tests.toy import lag, wave

BUILT = [("drive", "built")]


def _fields() -> dict[str, dict]:
    return {f["name"]: f for f in fields_of(lag.Config)}


def test_a_parts_settings_are_listed_by_dotted_names_in_the_groups_it_composes() -> None:
    fields = _fields()
    inner = [name for name in fields if name.startswith("wave.")]
    assert inner == ["wave.shape", "wave.duty", "wave.amplitude", "wave.frequency",
                     "wave.samples"], "the Wave group alone: its noise and its run are the lag's"
    assert "wave" not in fields, "the part itself is not a setting of its own on any surface"
    duty = fields["wave.duty"]
    assert duty["group"] == "Built wave · Wave" and duty["label"] == "Duty"
    assert duty["part"] == "wave" and fields["tau"]["part"] == ""
    assert duty["needs"] == {"drive": {"in": ["built"]}, "wave.shape": {"in": ["square"]}}, \
        "its own gate by dotted names, and the part's gate besides"
    assert (duty["default"], duty["low"], duty["low_exclusive"]) == (0.5, 0.0, True)
    assert parameter_at(lag.Config, "wave.duty").name == "duty"
    assert ("wave.amplitude", "A") in [(n, w) for n, w in Form(pieces()[1]).axes()], \
        "a setting inside a part can be swept"


def test_a_part_is_set_by_its_path_and_saved_as_the_dict_of_its_settings() -> None:
    cfg = with_overrides(lag.Config(), [*BUILT, ("wave.shape", "square"), ("wave.duty", "0.2")])
    assert isinstance(cfg.wave, wave.Config) and (cfg.wave.shape, cfg.wave.duty) == ("square", 0.2)
    held = saved(cfg)["wave"]
    assert held == {**saved(wave.Config()), "shape": "square", "duty": 0.2}
    assert saved(from_saved(lag.Config, json.loads(json.dumps(saved(cfg))))) == saved(cfg)
    assert flat(lag.Config, saved(cfg))["wave.duty"] == 0.2
    assert "wave.seed" not in flat(lag.Config, saved(cfg)), "not composed: not spread out"
    # the whole part, then one setting in it, in the order given
    both = with_overrides(lag.Config(), [*BUILT, ("wave", json.dumps({"amplitude": 3})),
                                         ("wave.frequency", "5")])
    assert (both.wave.amplitude, both.wave.frequency) == (3.0, 5.0)
    assert from_dict(lag.Config, {"drive": "built", "wave": {"samples": 9}}).wave.samples == 9


@pytest.mark.parametrize("pairs, words", [
    ([("wave.amplitude", "2")], "wave is set, but wave applies only when drive is one of "
                                "\\['built'\\]"),
    ([*BUILT, ("wave.seed", "3")], "wave.seed=3 is set, but wave applies only its groups "
                                   "\\['Wave'\\]; wave.seed is the run Config makes of it"),
    ([*BUILT, ("wave.duty", "0.2")], "^wave: duty=0.2 is set, but duty applies only when shape"),
    ([*BUILT, ("wave.nope", "1")], "^wave: unknown setting 'nope' on Config"),
    ([("tau.x", "1")], "'tau' holds no rows, so nothing is inside it"),
])
def test_a_setting_set_where_the_run_would_ignore_it_is_refused_naming_it(pairs, words) -> None:
    with pytest.raises(ValueError, match=words):
        with_overrides(lag.Config(), pairs)


def test_a_part_naming_a_group_it_has_not_is_refused_when_its_settings_are_read() -> None:
    class Wrong(Settings):
        wave = param.ClassSelector(class_=wave.Config, default=wave.Config(),
                                   metadata={"group": "g", "composes": ("Shape",)})
    with pytest.raises(ValueError, match="wave composes the groups \\['Shape'\\], which Config "
                                         "has not; its groups are \\['Noise', 'Run', 'Wave'\\]"):
        fields_of(Wrong)


def test_a_run_driven_by_a_built_wave_runs_by_it_and_keeps_it(tmp_path) -> None:
    out = tmp_path / "results"
    cli.main(["run", "lag", "--name", "built", "--out-dir", str(out),
              "--set", "drive=built", "--set", "wave.shape=square", "--set", "wave.samples=60"])
    rec = lag.Record.load(out / "lag" / "built.json")
    assert rec.config.wave.shape == "square" and len(rec.u) == 60
    built = wave.run(wave.Config(shape="square", samples=60))
    assert (rec.u == built.u).all(), "the u of the wave its settings build"


def test_a_sweep_over_a_setting_inside_a_part_is_a_run_each_and_a_number_against_it(
        tmp_path) -> None:
    out = tmp_path / "results"
    cli.main(["run", "lag", "--name", "amp", "--out-dir", str(out), "--set", "drive=built",
              "--sweep", "wave.amplitude=1,2,3"])
    pairs = [(p.stem, lag.Record.load(p)) for p in sorted((out / "lag").glob("amp-*.json"))]
    assert [rec.config.wave.amplitude for _, rec in pairs] == [1.0, 2.0, 3.0]
    assert distinct(pairs) == ["wave.amplitude"]
    drawn = sweep_of(pairs, "peak_y", vs="wave.amplitude")
    assert list(drawn.axes[0].lines[0].x) == [1.0, 2.0, 3.0]
    assert drawn.x_label == "A", "the bottom axis worded by the setting inside the part"


def test_the_page_reads_a_runs_part_by_dotted_names_and_the_form_greys_it_behind_its_gate(
        tmp_path) -> None:
    out = tmp_path / "results"
    cli.main(["run", "lag", "--name", "built", "--out-dir", str(out), "--set", "drive=built",
              "--set", "wave.amplitude=2.5"])
    [run] = [r for r in records(str(tmp_path), "results") if r["piece"] == "lag"]
    assert run["config"]["wave.amplitude"] == 2.5 and "wave" not in run["config"]
    form = Form(pieces()[1])
    off, why = form.state_of(form.by_name["wave.amplitude"])
    assert off and "Drive" in why, "greyed while the lag is driven by a saved run"
    landed, dropped = form.use(run["config"])
    assert form.set == {"drive": "built", "wave.amplitude": "2.5"} and not dropped
    assert not form.state_of(form.by_name["wave.amplitude"])[0], "open once it is built"
    rows = view.compare_rows([run, {**run, "name": "other", "config": {**run["config"],
                                                                        "wave.amplitude": 1.0}}],
                             fields_of(lag.Config), settings="differ")
    differ = [(r["group"], r["term"], r["values"]) for r in rows if r["kind"] == "setting"]
    assert differ == [("Built wave · Wave", "A", ["2.5", "1"])]


def test_run_refuses_a_setting_inside_a_part_by_its_own_bounds() -> None:
    refused, _ = jobs.refusals("lag", {"drive": "built", "wave.amplitude": "-1"})
    assert set(refused) == {"wave.amplitude"} and "A" in refused["wave.amplitude"]
    assert jobs.refusals("lag", {"drive": "built", "wave.amplitude": "2"}) == ({}, "")
