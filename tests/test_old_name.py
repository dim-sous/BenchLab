"""The name RunLab had until 0.10, ``benchlab``: a project written for it runs unchanged. It
still imports what a project may use and nothing deeper, a project declared in its entry-point
group is found, and the check still refuses a file reaching past it."""

from __future__ import annotations

import importlib
from importlib.metadata import EntryPoint

import pytest

import benchlab
import benchlab.cli
import benchlab.lab
import benchlab.testing
import runlab
import runlab.cli
import runlab.lab
import runlab.testing
import tests.toy as toy
from runlab import project


def test_the_old_name_holds_what_a_project_may_use_and_nothing_deeper() -> None:
    assert benchlab.__all__ == runlab.__all__
    for name in runlab.__all__:
        assert getattr(benchlab, name) is getattr(runlab, name), name
    assert benchlab.cli.main is runlab.cli.main and benchlab.lab.main is runlab.lab.main
    assert benchlab.testing.check_project is runlab.testing.check_project
    for deeper in ("benchlab.record", "benchlab.runner", "benchlab.project", "benchlab.figure"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(deeper)


def test_a_piece_runs_and_is_checked_through_the_old_name(tmp_path) -> None:
    assert benchlab.cli.main(["run", "wave", "--name", "one", "--out-dir", str(tmp_path)]) == 0
    path = tmp_path / "wave" / "one.json"
    benchlab.testing.check_project(runs=[path], sources=[toy.ROOT / "tests" / "toy"])
    assert benchlab.Record.load.__func__ is runlab.Record.load.__func__


def _declare(monkeypatch, by_group: dict[str, list[str]]) -> None:
    monkeypatch.setattr(project, "entry_points", lambda group: [
        EntryPoint(name="project", value=module, group=group) for module in by_group.get(group, [])])
    project.declared.cache_clear()


def test_a_project_declared_under_the_old_name_or_under_both_is_found_once(monkeypatch) -> None:
    assert project.GROUPS == ("runlab", "benchlab")
    _declare(monkeypatch, {"benchlab": ["tests.toy"]})
    assert project.declared() is toy
    _declare(monkeypatch, {"runlab": ["tests.toy"], "benchlab": ["tests.toy"]})
    assert project.declared() is toy


def test_two_projects_one_under_each_name_are_refused(monkeypatch) -> None:
    _declare(monkeypatch, {"runlab": ["tests.toy"], "benchlab": ["tests.toy.wave"]})
    with pytest.raises(LookupError, match="2 projects declare themselves to RunLab"):
        project.declared()


@pytest.mark.parametrize("line, beyond", [
    ("from benchlab.lab.app import Lab", "benchlab.lab.app.Lab"),
    ("from benchlab.record import Record", "benchlab.record.Record"),
    ("from benchlab.cli import folder_of", "benchlab.cli.folder_of"),
    ("import benchlab.record", "benchlab.record")])
def test_the_check_refuses_a_file_reaching_past_the_old_name(tmp_path, line, beyond) -> None:
    (tmp_path / "piece.py").write_text(
        "from benchlab import Settings, Record\nfrom benchlab.cli import main\n"
        "from benchlab.testing import check_project\nimport benchlab\n" + line + "\n")
    with pytest.raises(AssertionError, match=rf"piece\.py:5 imports {beyond}: RunLab's own"):
        runlab.testing.check_project(sources=[tmp_path])
