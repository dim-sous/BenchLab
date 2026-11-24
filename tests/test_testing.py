"""The check a project calls from one test (``runlab.testing``): it passes on the made-up
project and a run of it, and refuses each way of not plugging in, naming the piece or the file.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

import runlab
import tests.toy as toy
from runlab import cli, project, testing
from runlab.testing import check_project
from tests.toy import lag, wave

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


@pytest.fixture
def lag_run(run) -> Path:
    """A lag on ``run``: a record with a figure of its own."""
    cli.main(["run", "lag", "--set", f"wave_run={run}", "--name", "one",
              "--out-dir", str(run.parent.parent)])
    return run.parent.parent / "lag" / "one.json"


def test_the_made_up_project_and_its_runs_plug_in(run, lag_run) -> None:
    check_project(runs=[run, lag_run], sources=[TOY])


def test_a_figure_plotly_does_not_take_is_refused_naming_its_run(lag_run, monkeypatch) -> None:
    bad = runlab.Figure(name="pole", figure={"data": [{"type": "scatter", "no_such": 1}]})
    monkeypatch.setattr(lag.Record, "figures", lambda self: (bad,))
    with pytest.raises(AssertionError, match=r"one\.json: the figure 'pole' is not one plotly takes"):
        check_project(runs=[lag_run], sources=[TOY])


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


def test_an_entry_of_the_words_file_runlab_leaves_out_is_a_warning_not_a_refusal(
        tmp_path, monkeypatch) -> None:
    """A slot renamed in a later RunLab must not fail a project's suite."""
    named = tmp_path / "words.toml"
    named.write_text('[strip]\ntoggel = "Runs under way"\n', encoding="utf-8")
    monkeypatch.setattr(toy, "WORDS", named, raising=False)
    with pytest.warns(UserWarning, match=r"strip.toggel \(RunLab names no such slot\)"):
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
import runlab
import runlab.testing
import numpy
from runlab import Record as _Record
from runlab import Settings, stamp, testing
from runlab.cli import main
from runlab.lab import main as lab
from runlab.testing import check_project
from . import sibling
"""


def test_a_file_importing_only_what_a_project_may_use_passes(tmp_path) -> None:
    (tmp_path / "piece.py").write_text(_MAY)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "installed.py").write_text("from runlab.lab.app import Lab\n")
    check_project(sources=[tmp_path])


@pytest.mark.parametrize("line,named", [
    ("from runlab.lab.app import Lab", "runlab.lab.app.Lab"),
    ("from runlab.record import Record", "runlab.record.Record"),
    ("from runlab import cli", "runlab.cli"),
    ("from runlab.cli import folder_of", "runlab.cli.folder_of"),
    ("import runlab.record", "runlab.record"),
])
def test_a_file_importing_runlabs_own_is_refused_naming_the_line(tmp_path, line, named) -> None:
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "piece.py").write_text(f"import numpy\n{line}\n")
    with pytest.raises(AssertionError) as refusal:
        check_project(sources=[tmp_path])
    assert f"piece.py:2 imports {named}:" in str(refusal.value)


def test_a_setting_asking_for_a_run_nothing_carries_is_refused(monkeypatch) -> None:
    """1.4: a ``record_of`` names a piece, or what a piece's runs carry; one naming neither would
    offer nothing."""
    monkeypatch.setattr(lag.Config.param["wave_run"], "metadata",
                        {**lag.Config.param["wave_run"].metadata, "record_of": "v"})
    with pytest.raises(AssertionError, match="wave_run asks for a saved run of 'v', and no piece "
                                             "is called that or carries it"):
        check_project()


def test_a_form_that_does_not_draw_is_refused_naming_its_piece(monkeypatch) -> None:
    """1.15: a piece's form is drawn as the page draws it on picking the piece, not only read --
    the other project's flight form read and did not draw."""
    from runlab.lab import app

    real = app.Lab._field_cells

    def fails(self, f):
        if f["name"] == "noise":
            raise AttributeError("'function' object has no attribute 'get'")
        return real(self, f)

    monkeypatch.setattr(app.Lab, "_field_cells", fails)
    with pytest.raises(AssertionError, match="the piece 'wave': its form does not draw -- "
                                             "AttributeError: 'function' object has no "
                                             "attribute 'get'"):
        check_project(sources=[TOY])


def test_a_link_to_nowhere_is_no_file_of_the_project(tmp_path) -> None:
    """1.16, found on the other project's computer: a stale build's links point at a folder that
    is gone; the check of imports reads the project's files, and a link to nowhere is none."""
    (tmp_path / "ok.py").write_text("from runlab import Settings\n")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "setup.py").symlink_to(tmp_path / "gone" / "setup.py")
    check_project(sources=[tmp_path])
