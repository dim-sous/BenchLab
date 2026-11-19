"""A setting that is a list of rows, a table: read, written, set by a path, shown as a table on
the form and worded in the compare table. On the made-up lag's ``steps``, each row a time, a
shape and a size added to the wave's u."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import param
import pytest

from runlab import Settings, cli, with_overrides
from runlab.figure.chart import distinct
from runlab.lab import jobs, view
from runlab.lab.app import _Table
from runlab.lab.form import Form
from runlab.lab.state import pieces
from runlab.record.config import fields_of, from_dict, from_saved, saved, to_dict
from tests.toy import lag, wave

ROWS = [{"at": 0.25, "shape": "step", "size": 1.0}, {"at": 0.5, "shape": "ramp", "size": -2.0}]


def _field() -> dict:
    return next(f for f in fields_of(lag.Config) if f["name"] == "steps")


def test_a_list_of_rows_is_declared_with_its_rows_own_settings() -> None:
    f = _field()
    assert f["type"] == "rows" and f["default"] == []
    assert [(c["name"], c["label"], c["unit"], c["type"]) for c in f["element_fields"]] == [
        ("at", "From", "s", "float"), ("shape", "Shape", "", "choice"), ("size", "Size", "", "float")]
    assert f["element_fields"][1]["lines"] == {"step": "step [-]", "ramp": "ramp [1/s]"}
    assert f["element_default"] == {"at": 0.5, "shape": "step", "size": 1.0}
    assert "steps" not in [name for name, _ in Form(pieces()[1]).axes()], "a table is not swept"


def test_a_list_of_rows_is_written_as_dicts_and_read_back_as_rows() -> None:
    cfg = from_dict(lag.Config, {"steps": ROWS})
    assert all(isinstance(row, lag.Step) for row in cfg.steps)
    assert saved(cfg)["steps"] == ROWS
    assert saved(from_saved(lag.Config, json.loads(json.dumps(saved(cfg))))) == saved(cfg)
    assert saved(from_dict(lag.Config, {"steps": json.dumps(ROWS)}))["steps"] == ROWS


def test_one_cell_of_one_row_is_set_by_its_path() -> None:
    cfg = from_dict(lag.Config, {"steps": ROWS})
    assert [r.size for r in with_overrides(cfg, [("steps.1.size", "3")]).steps] == [1.0, 3.0]
    assert with_overrides(cfg, [("steps.0.shape", "ramp")]).steps[0].shape == "ramp"
    # the whole table, then one cell of it, in the order given
    both = with_overrides(lag.Config(), [("steps", json.dumps(ROWS[:1])), ("steps.0.at", "0.75")])
    assert saved(both)["steps"] == [{"at": 0.75, "shape": "step", "size": 1.0}]


@pytest.mark.parametrize("pairs, words", [
    ([("steps.7.size", "1")], "steps holds 2 row\\(s\\), numbered from 0; '7' is not one of them"),
    ([("steps.0.nope", "1")], "a row of steps holds no 'nope'; it holds \\['at', 'shape', 'size'\\]"),
    ([("tau.0.x", "1")], "'tau' holds no rows, so nothing is inside it"),
    ([("steps", "[1, 2]")], "steps: row 0 is 1, not a row"),
    ([("steps", "nonsense")], "steps: 'nonsense' is not a list of rows as JSON"),
    ([("steps.0.shape", "never")], "shape: 'never' is not one of \\['ramp', 'step'\\]"),
    ([("steps.0.size", "big")], "size: 'big' is not a number"),
])
def test_a_wrong_path_or_cell_is_refused_naming_it(pairs, words) -> None:
    with pytest.raises(ValueError, match=words):
        with_overrides(from_dict(lag.Config, {"steps": ROWS}), pairs)


def test_a_settings_file_refuses_a_row_it_does_not_know_and_a_run_file_reads_it() -> None:
    """A stray key in a hand-written settings file is a slip; a run file is read as it was
    saved, a row's cell its class no longer holds left out."""
    row = {**ROWS[0], "gone": 1}
    with pytest.raises(ValueError, match=r"unknown setting\(s\) \['gone'\] in steps row 0"):
        from_dict(lag.Config, {"steps": [row]})
    assert saved(from_saved(lag.Config, {"steps": [row], "also_gone": 2}))["steps"] == ROWS[:1]


def test_a_run_made_with_a_table_keeps_it_and_runs_by_it(two_runs) -> None:
    root, out_dir = two_runs
    source = Path(root) / out_dir / "wave" / "first.json"
    cli.main(["run", "lag", "--set", f"wave_run={source}", "--set", f"steps={json.dumps(ROWS[:1])}",
              "--set", "steps.0.size=2", "--name", "stepped", "--out-dir", str(Path(root) / out_dir)])
    path = Path(root) / out_dir / "lag" / "stepped.json"
    assert json.loads(path.read_text())["config"]["steps"] == [
        {"at": 0.25, "shape": "step", "size": 2.0}]
    record = lag.Record.load(path)
    assert [type(row) for row in record.config.steps] == [lag.Step]
    wave_u = wave.Record.load(source).u
    assert np.array_equal(record.u, wave_u + 2.0 * (record.t >= 0.25))


def test_the_form_holds_a_table_as_the_text_set_takes_and_edits_it_by_the_cell() -> None:
    said: list[str] = []
    table = _Table(_field(), on_edit=said.append)
    assert table.value == "[]"
    at, shape, size = _field()["element_fields"]
    table._add()
    assert json.loads(said[-1]) == [{"at": 0.5, "shape": "step", "size": 1.0}], "a first row"
    table._typed(0, at, "0.25")
    table._typed(0, shape, "ramp")
    table._add()
    assert json.loads(said[-1]) == [{"at": 0.25, "shape": "ramp", "size": 1.0}] * 2, \
        "an added row is a copy of the last"
    table._typed(1, size, "many")
    assert json.loads(said[-1])[1]["size"] == "many", "kept as typed: Run refuses it"
    table._typed(1, size, "")
    assert json.loads(said[-1])[1]["size"] == 1.0, "an emptied cell is back at its default"
    table._drop(0)
    assert json.loads(said[-1]) == [{"at": 0.25, "shape": "ramp", "size": 1.0}]
    table.value = ""                                # written, not typed: no edit is said
    assert table.value == "[]" and len(said) == 7, "seven edits by hand, each said once"


def test_run_refuses_a_cell_under_the_setting_naming_its_row() -> None:
    bad = json.dumps([ROWS[0], {"at": -1.0, "shape": "step", "size": 1.0}])
    refused, _ = jobs.refusals("lag", {"steps": bad})
    assert set(refused) == {"steps"} and refused["steps"].startswith("steps row 1: ")
    assert jobs.refusals("lag", {"steps": json.dumps(ROWS)}) == ({}, "")


def test_the_compare_table_words_a_table_row_by_row() -> None:
    assert view.text(ROWS) == "0.25 · step · 1; 0.5 · ramp · -2"
    assert view.text([]) == ""


# --- rows compare by what they hold, carried from BESS's ``tests/test_record_rows.py`` and its
# battery's tests (2026-11-19) -------------------------------------------------------------------

class _Row(Settings):
    power = param.Number(1.0, label="power", metadata={"group": "rows", "unit": "kW"})
    until = param.Selector(default="time", objects=["time", "soc"], label="until",
                           metadata={"group": "rows"})


class _Config(Settings):
    rows = param.List([_Row(), _Row(power=2.0)], item_type=_Row, bounds=(1, None), label="rows",
                      metadata={"group": "rows"})


class _Gated(Settings):
    mode = param.Selector(default="a", objects=["a", "b"], label="mode", metadata={"group": "g"})
    rows = param.List([_Row()], item_type=_Row, label="rows",
                      metadata={"group": "g", "needs": {"mode": {"in": ["a"]}}})


def test_an_empty_list_is_refused_by_its_declared_length() -> None:
    with pytest.raises(ValueError):
        with_overrides(_Config(), [("rows", "[]")])


def test_a_gated_list_of_rows_at_its_default_is_not_set_behind_its_gate() -> None:
    """A row object carries an instance name of its own, so a rebuilt default list never matched
    the declared one (BESS's code review, 2026-10-27)."""
    back = from_dict(_Gated, {**to_dict(_Gated()), "mode": "b"})
    assert back.mode == "b"
    with pytest.raises(ValueError, match="applies only when"):
        with_overrides(_Gated(), [("mode", "b"), ("rows", '[{"power": 9}]')])


def test_runs_whose_rows_are_equal_differ_only_in_what_differs(tmp_path) -> None:
    """Two runs with equal rows are told apart by their other settings alone (BESS's code
    review, 2026-10-27: equal rows never compared equal)."""
    source = str(wave.run(wave.Config()).save(tmp_path / "wave.json"))
    a, b = (lag.run(with_overrides(lag.Config(wave_run=source),
                                   [("steps", json.dumps(ROWS)), ("tau", tau)]))
            for tau in ("0.05", "0.1"))
    assert distinct([("a", a), ("b", b)]) == ["tau"]
