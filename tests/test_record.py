"""The record layer: a saved run loads back exactly, and what it cannot hold is refused in words."""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import param
import pytest

from runlab.record import (Absent, AbsentField, Number, Provenance, Record, Series, differences,
                           read_header, stamp)
from runlab.record.config import Settings, from_dict, with_overrides


class _Config(Settings):
    gain = param.Number(1.0, bounds=(0.0, None), metadata={"group": "G"})
    mode = param.Selector(default="a", objects=["a", "b"], metadata={"group": "G"})
    extra = param.Integer(default=None, allow_None=True,
                          metadata={"group": "G", "needs": {"mode": {"in": ["b"]}}})


@dataclasses.dataclass(frozen=True)
class _Record(Record):
    name: str
    config: _Config
    provenance: Provenance | None
    values: np.ndarray
    labels: list
    numbers: dict

    component = "probe"
    produced_by = "the test"

    def series(self):
        return (Series(name="values", x=np.arange(len(self.values)), x_label="i",
                       y_label="v", traces=(("v", self.values),)),)

    def number_specs(self):
        return (Number("total", "total"),)


def _rec(**kw) -> _Record:
    base = dict(name="r", config=_Config(gain=2.5), provenance=stamp(0.1),
                values=np.array([0.1, 1 / 3, np.nan, np.inf, -np.inf, 1e-300]),
                labels=["optimal", "optimal_inaccurate"], numbers={"total": 3.0})
    return _Record(**{**base, **kw})


def test_a_saved_record_loads_back_bit_for_bit(tmp_path) -> None:
    rec = _rec()
    back = _Record.load(rec.save(tmp_path / "r.json"))
    assert back.values.tobytes() == rec.values.tobytes()
    assert back.labels == rec.labels and back.numbers == rec.numbers
    assert back.config.gain == 2.5 and back.provenance == rec.provenance
    assert read_header(tmp_path / "r.json")["component"] == "probe"


@pytest.mark.parametrize("numbers, words", [({"total": math.nan}, "not finite"),
                                            ({"total": 1.0, "other": 2.0}, "carry no words")])
def test_a_number_that_is_not_finite_or_not_declared_is_refused(tmp_path, numbers, words) -> None:
    with pytest.raises(ValueError, match=words):
        _rec(numbers=numbers).save(tmp_path / "r.json")


def _edited(tmp_path, edit) -> Path:
    """A saved record's file, its content changed by ``edit``."""
    path = _rec().save(tmp_path / "r.json")
    raw = json.loads(path.read_text())
    edit(raw)
    path.write_text(json.dumps(raw))
    return path


def _differs(cls, path: Path) -> list[tuple]:
    """How the file at ``path`` departs from ``cls``, as plain tuples."""
    return [(d.place, d.field, d.kind, d.names)
            for d in differences(cls, json.loads(path.read_text()))]


def test_a_file_of_another_piece_is_refused(tmp_path) -> None:
    with pytest.raises(ValueError, match="not 'probe'"):
        _Record.load(_edited(tmp_path, lambda raw: raw.update(component="other")))


def test_a_file_that_holds_more_than_its_class_reads_loads_and_keeps_it(tmp_path) -> None:
    """An entry the class does not read, in the result, the settings or the provenance: the
    record loads whole, each is named, and the file keeps it."""
    def edit(raw) -> None:
        raw["stranger"] = 1
        raw["config"]["old_setting"] = 4
        raw["provenance"]["python"] = "3.13.1"
    path = _edited(tmp_path, edit)
    back = _Record.load(path)
    assert back.values.tobytes() == _rec().values.tobytes() and back.config.gain == 2.5
    assert _differs(_Record, path) == [
        ("result", "", "extra", ("stranger",)),
        ("settings", "config", "extra", ("old_setting",)),
        ("provenance", "provenance", "extra", ("python",))]
    assert json.loads(path.read_text())["provenance"]["python"] == "3.13.1", "the file keeps it"
    assert [s.name for s in back.series()] == ["values"], "what it holds is drawn"


def test_a_field_the_file_lacks_is_no_value_and_says_so_when_used(tmp_path) -> None:
    path = _edited(tmp_path, lambda raw: raw.pop("values"))
    back = _Record.load(path)
    assert _differs(_Record, path) == [("result", "", "lacks", ("values",))]
    assert back.labels == _rec().labels and back.numbers == {"total": 3.0}, "the rest is read"
    assert isinstance(back.values, Absent)
    for use in (lambda: len(back.values), lambda: back.values + 1, lambda: 2 * back.values,
                lambda: np.asarray(back.values), lambda: back.values.mean(),
                lambda: back.values[0], lambda: bool(back.values), lambda: back.series()):
        with pytest.raises(AbsentField, match="the file r.json holds no 'values'"):
            use()
    with pytest.raises(ValueError, match="not saved again"):
        back.save(tmp_path / "again.json")


def test_a_field_the_file_lacks_takes_the_default_its_class_declares(tmp_path) -> None:
    @dataclasses.dataclass(frozen=True)
    class Later(_Record):
        added: np.ndarray | None = None

    path = _rec().save(tmp_path / "r.json")
    back = Later.load(path)
    assert back.added is None and back.values.tobytes() == _rec().values.tobytes()
    assert _differs(Later, path) == [("result", "", "lacks", ("added",))]


def test_a_saved_value_the_class_cannot_read_is_no_value_in_the_readers_words(tmp_path) -> None:
    path = _edited(tmp_path, lambda raw: raw.update(values="oops"))
    back = _Record.load(path)
    assert back.labels == _rec().labels and _differs(_Record, path) == []
    with pytest.raises(AbsentField, match="in a form the current _Record does not read"):
        len(back.values)
    # a setting saved below the bound the class holds it to now
    back = _Record.load(_edited(tmp_path, lambda raw: raw["config"].update(gain=-1.0)))
    assert back.values.tobytes() == _rec().values.tobytes()
    with pytest.raises(AbsentField, match="gain"):
        _ = back.config.gain


def test_a_provenance_entry_the_file_lacks_reads_as_none(tmp_path) -> None:
    path = _edited(tmp_path, lambda raw: raw["provenance"].pop("duration_s"))
    back = _Record.load(path)
    assert back.provenance.duration_s is None and back.provenance.git_sha
    assert _differs(_Record, path) == [("provenance", "provenance", "lacks", ("duration_s",))]


def test_a_loaded_record_holds_its_fields_and_nothing_more(tmp_path) -> None:
    """A project rebuilds a record from its own ``__dict__`` (DeePC's suite does); a loaded one
    carries nothing its class's ``__init__`` does not take."""
    path = _edited(tmp_path, lambda raw: raw.update(stranger=1))
    back = _Record.load(path)
    assert set(back.__dict__) == {f.name for f in dataclasses.fields(_Record)}
    again = _Record(**{**back.__dict__, "labels": ["other"]})
    assert again.labels == ["other"] and again.values.tobytes() == back.values.tobytes()
    assert _differs(_Record, _rec().save(tmp_path / "fresh.json")) == []


def test_a_setting_is_refused_in_words() -> None:
    with pytest.raises(ValueError, match="unknown setting"):
        from_dict(_Config, {"gian": 1.0})
    with pytest.raises(ValueError, match="applies only when"):
        _Config(extra=3)
    assert with_overrides(_Config(), [("mode", "b"), ("extra", "3")]).extra == 3   # a gate opened in the same call
    assert with_overrides(_Config(mode="b", extra=3), [("extra", "none")]).extra is None
