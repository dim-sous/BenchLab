"""Settings of other kinds than the six (``runlab/record/config.py``, ``other_kind``): a
matrix, a date, a pair, a table. Each is typed as the text param reads, saved as param writes it
and loaded as the real thing; the six kinds are read and written as before. On a Config of its
own, then on the made-up ``fit``, whose ``scale`` is a matrix and whose ``day`` a calendar date."""

from __future__ import annotations

import dataclasses
import datetime
import json

import numpy as np
import param
import pytest

from runlab import Provenance, Record, Settings, cli, with_overrides
from runlab.lab import jobs, state, view
from runlab.lab.form import Form, as_text
from runlab.record.config import fields_of, other_kind, saved
from runlab.runner import planned
from tests.test_runner import _ended, _real
from tests.toy import fit


class _Config(Settings):
    matrix = param.Array(np.eye(2), metadata={"group": "G"})
    moment = param.Date(datetime.datetime(2026, 1, 1), metadata={"group": "G"})
    day = param.CalendarDate(datetime.date(2026, 1, 1), metadata={"group": "G"})
    pair = param.Tuple((1.0, 2.0), metadata={"group": "G"})
    table = param.Dict({"a": 1}, metadata={"group": "G"})
    absent = param.Array(None, allow_None=True, metadata={"group": "G"})
    mode = param.Selector(default="a", objects=["a", "b"], metadata={"group": "G"})
    behind = param.Array(np.zeros(2), metadata={"group": "G", "needs": {"mode": {"in": ["b"]}}})
    share = param.Magnitude(0.5, metadata={"group": "G"})


@dataclasses.dataclass(frozen=True)
class _Record(Record):
    name: str
    config: _Config
    provenance: Provenance | None
    numbers: dict

    component = "other"


TYPED = [("matrix", "[[1, 2], [3, 4]]"), ("moment", "2026-02-03T04:05:06.000000"),
         ("day", "2026-02-03"), ("pair", "[3, 4]"), ("table", '{"b": 2}'),
         ("absent", "[5, 6]")]
WRITTEN = {"matrix": [[1.0, 2.0], [3.0, 4.0]], "moment": "2026-02-03T04:05:06.000000",
           "day": "2026-02-03", "pair": [3, 4], "table": {"b": 2}, "absent": [5.0, 6.0],
           "mode": "a", "behind": [0.0, 0.0], "share": 0.5}


def test_a_setting_of_another_kind_is_typed_as_text_saved_as_param_writes_it_and_loaded_whole(
        tmp_path) -> None:
    cfg = with_overrides(_Config(), TYPED)
    assert cfg.matrix.tolist() == [[1, 2], [3, 4]] and isinstance(cfg.matrix, np.ndarray)
    assert cfg.moment == datetime.datetime(2026, 2, 3, 4, 5, 6)
    assert cfg.day == datetime.date(2026, 2, 3)
    assert cfg.pair == (3, 4) and cfg.table == {"b": 2} and cfg.absent.tolist() == [5, 6]
    assert saved(cfg) == WRITTEN
    path = _Record("one", cfg, None, {}).save(tmp_path / "one.json")
    assert json.loads(path.read_text())["config"] == WRITTEN
    back = _Record.load(path).config
    assert saved(back) == WRITTEN and isinstance(back.matrix, np.ndarray)
    assert back.day == cfg.day and back.pair == cfg.pair and back.moment == cfg.moment
    assert with_overrides(cfg, [("absent", "none")]).absent is None
    assert with_overrides(cfg, [("matrix", np.ones((1, 1)))]).matrix.tolist() == [[1.0]]


def test_the_six_kinds_are_not_of_another_kind_and_a_date_is() -> None:
    by = {f["name"]: f for f in fields_of(_Config)}
    assert {n for n, f in by.items() if not f["other"]} == {"mode", "share"}
    assert not any(f["other"] for piece in (fit,) for f in fields_of(piece.Config)
                   if f["name"] not in ("scale", "day"))
    assert other_kind(_Config.param.day) and isinstance(_Config.param.day, param.Number)
    assert by["matrix"]["default"] == [[1.0, 0.0], [0.0, 1.0]] and by["day"]["default"] == "2026-01-01"
    assert (by["moment"]["low"], by["moment"]["high"]) == (None, None)


@pytest.mark.parametrize("name, text, kind", [
    ("day", "tomorrow", "CalendarDate"), ("matrix", "[[1, 2], [3", "Array"),
    ("absent", "none of it", "Array")])
def test_a_text_param_cannot_read_is_refused_naming_the_setting(name, text, kind) -> None:
    with pytest.raises(ValueError, match=rf"^{name}: .* is not what a {kind} setting reads \("):
        with_overrides(_Config(), [(name, text)])


def test_a_text_param_reads_into_a_value_the_setting_does_not_take_is_refused_by_param() -> None:
    """``three`` reads as a tuple of five letters; the pair's own length refuses it."""
    with pytest.raises(ValueError, match=r"Tuple parameter '_Config.pair' is not of the correct "
                                         r"length \(5 instead of 2\)"):
        with_overrides(_Config(), [("pair", "three")])


def test_a_matrix_behind_a_closed_gate_is_refused_and_one_at_its_default_is_not() -> None:
    _Config(behind=np.zeros(2))
    assert _Config(mode="b", behind=np.ones(2)).behind.tolist() == [1.0, 1.0]
    with pytest.raises(ValueError, match="behind applies only when mode is one of"):
        _Config(behind=np.ones(2))


def test_a_run_takes_a_matrix_and_a_date_and_the_identity_typed_is_the_default(tmp_path) -> None:
    for name, words in (("plain", []), ("same", ["scale=[[1, 0], [0, 1]]"]),
                        ("half", ["scale=[[1, 0], [0, 0.5]]", "day=2026-02-03"])):
        cli.main(["run", "fit", "--name", name, "--out-dir", str(tmp_path),
                  *[w for item in words for w in ("--set", item)]])
    plain, same, half = (fit.Record.load(tmp_path / "fit" / f"{n}.json")
                         for n in ("plain", "same", "half"))
    assert plain.numbers == same.numbers and plain.numbers != half.numbers
    assert half.config.scale.tolist() == [[1.0, 0.0], [0.0, 0.5]]
    assert half.config.day == datetime.date(2026, 2, 3)
    held = json.loads((tmp_path / "fit" / "half.json").read_text())["config"]
    assert (held["scale"], held["day"]) == ([[1.0, 0.0], [0.0, 0.5]], "2026-02-03")


def test_the_form_words_a_matrix_as_its_text_and_run_refuses_one_it_cannot_read(tmp_path) -> None:
    cli.main(["run", "fit", "--name", "half", "--out-dir", str(tmp_path / "results"),
              "--set", "scale=[[1, 0], [0, 0.5]]"])
    cli.main(["run", "fit", "--name", "plain", "--out-dir", str(tmp_path / "results")])
    piece = next(p for p in state.pieces() if p["name"] == "fit")
    form = Form(piece)
    by = form.by_name
    assert form.shown_default(by["scale"]) == "[[1.0, 0.0], [0.0, 1.0]]"
    assert form.shown_default(by["day"]) == "2026-01-01" and form.options(by["scale"]) is None
    assert not {"scale", "day"} & {name for name, _ in form.axes()}
    rows = {r["name"]: r for r in state.records(str(tmp_path), "results")}
    assert form.use(rows["half"]["config"]) == (1, [])
    assert form.launch_words() == (["scale=[[1.0, 0.0], [0.0, 0.5]]"], [])
    assert jobs.refusals("fit", form.set) == ({}, "")
    assert jobs.refusals("fit", {"scale": "[[1, 0], [0", "day": "tomorrow", "steps": "x"}) == (
        {"scale": "Scale cannot read [[1, 0], [0", "day": "Day cannot read tomorrow",
         "steps": "Steps takes a whole number, got x"}, "")
    table = view.compare_rows([rows["plain"], rows["half"]], piece["fields"], settings="differ")
    [row] = [r for r in table if r["kind"] == "setting"]
    assert (row["term"], row["values"], row["differs"]) == (
        "Scale", ["[[1.0, 0.0], [0.0, 1.0]]", "[[1.0, 0.0], [0.0, 0.5]]"], True)
    assert as_text({"b": 2}) == '{"b": 2}'


def test_the_lab_runs_what_the_form_words_and_saves_the_side_doors_file(tmp_path,
                                                                       toy_installed) -> None:
    words = ["scale=[[1.0, 0.0], [0.0, 0.5]]", "day=2026-02-03"]
    queue = _real()
    [run] = queue.submit("fit", planned("lab", words), root=str(tmp_path), out_dir="results")
    _ended(queue)
    assert run.state == "done", run.error
    assert run.line == ("uv run toy run fit --set 'scale=[[1.0, 0.0], [0.0, 0.5]]' "
                        "--set day=2026-02-03 --name lab")
    cli.main(["run", "fit", *[w for item in words for w in ("--set", item)], "--name", "side",
              "--out-dir", str(tmp_path / "results")])
    lab, side = (json.loads((tmp_path / "results" / "fit" / f"{n}.json").read_text())
                 for n in ("lab", "side"))
    for record in (lab, side):
        record.pop("provenance"), record.pop("name")
    assert lab == side
