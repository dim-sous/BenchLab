"""The check a project calls from one test (``benchlab.testing``): it passes on the made-up
project and a run of it, and refuses each way of not plugging in, naming the piece or the file.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

import tests.toy as toy
from benchlab import cli, project, testing
from benchlab.testing import check_project
from tests.toy import wave

TOY = Path(toy.__file__).parent


@pytest.fixture
def run(tmp_path) -> Path:
    cli.main(["run", "wave", "--name", "one", "--out-dir", str(tmp_path / "results")])
    return tmp_path / "results" / "wave" / "one.json"


class _Point:
    """An entry point, stood in for: it loads the module it was given."""

    value = "a stand-in"

    def __init__(self, module: object) -> None:
        self._module = module

    def load(self) -> object:
        return self._module


def _declare(monkeypatch, piece: object) -> None:
    """The toy's declaration, with ``piece`` as its one piece."""
    module = types.SimpleNamespace(**{name: getattr(toy, name) for name in project.DECLARED})
    module.get_component = lambda name: piece
    monkeypatch.setattr(project, "entry_points", lambda group: [_Point(module)])
    project.declared.cache_clear()


def test_the_made_up_project_and_its_run_plug_in(run) -> None:
    check_project(runs=[run], sources=[TOY])


def test_a_piece_lacking_a_name_is_refused_naming_it(monkeypatch) -> None:
    _declare(monkeypatch, types.SimpleNamespace(Config=wave.Config, Record=wave.Record))
    with pytest.raises(AssertionError, match="the piece 'wave' does not hold run"):
        check_project(sources=[TOY])


def test_a_record_registered_under_another_name_is_refused(monkeypatch) -> None:
    class Other(wave.Record):
        component = "other"

    _declare(monkeypatch, types.SimpleNamespace(Config=wave.Config, run=wave.run, Record=Other))
    with pytest.raises(AssertionError, match="Record.component is 'other'"):
        check_project(sources=[TOY])


def test_an_entry_of_the_words_file_benchlab_leaves_out_is_a_warning_not_a_refusal(
        tmp_path, monkeypatch) -> None:
    """A slot renamed in a later Benchlab must not fail a project's suite."""
    named = tmp_path / "words.toml"
    named.write_text('[strip]\ntoggel = "Runs under way"\n', encoding="utf-8")
    monkeypatch.setattr(toy, "WORDS", named, raising=False)
    with pytest.warns(UserWarning, match=r"strip.toggel \(Benchlab names no such slot\)"):
        check_project(sources=[TOY])


def test_a_file_that_is_no_run_is_refused_in_the_loaders_words(tmp_path) -> None:
    path = tmp_path / "stray.json"
    path.write_text('{"a": 1}')
    with pytest.raises(ValueError, match="is not a record"):
        check_project(runs=[path], sources=[TOY])


def test_a_chart_that_does_not_draw_is_refused_naming_its_run(run, monkeypatch) -> None:
    def figure_of(panel):
        raise RuntimeError("no ink")

    monkeypatch.setattr(testing, "figure_of", figure_of)
    with pytest.raises(AssertionError, match=r"one\.json: the chart 'u' does not draw \(RuntimeError: no ink\)"):
        check_project(runs=[run], sources=[TOY])


_MAY = """\
import benchlab
import benchlab.testing
import numpy
from benchlab import Record as _Record
from benchlab import Settings, stamp, testing
from benchlab.cli import main
from benchlab.lab import main as lab
from benchlab.testing import check_project
from . import sibling
"""


def test_a_file_importing_only_what_a_project_may_use_passes(tmp_path) -> None:
    (tmp_path / "piece.py").write_text(_MAY)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "installed.py").write_text("from benchlab.lab.app import Lab\n")
    check_project(sources=[tmp_path])


@pytest.mark.parametrize("line,named", [
    ("from benchlab.lab.app import Lab", "benchlab.lab.app.Lab"),
    ("from benchlab.record import Record", "benchlab.record.Record"),
    ("from benchlab import cli", "benchlab.cli"),
    ("from benchlab.cli import folder_of", "benchlab.cli.folder_of"),
    ("import benchlab.record", "benchlab.record"),
])
def test_a_file_importing_benchlabs_own_is_refused_naming_the_line(tmp_path, line, named) -> None:
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "piece.py").write_text(f"import numpy\n{line}\n")
    with pytest.raises(AssertionError) as refusal:
        check_project(sources=[tmp_path])
    assert f"piece.py:2 imports {named}:" in str(refusal.value)
