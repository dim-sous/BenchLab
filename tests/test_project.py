"""The one door to the project (``benchlab/project.py``): the declared module found once and kept,
refused in words when no project is declared, when two are, or when the module lacks a name; and
what a record's provenance takes from it."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
import types
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

import tests.toy as toy
from benchlab import project
from benchlab.record import stamp


def _declare(monkeypatch, *modules: str) -> list[str]:
    """Stand in for the entry points ``modules`` declare; return the groups asked for."""
    asked: list[str] = []
    points = [EntryPoint(name="project", value=m, group=project.GROUP) for m in modules]

    def entry_points(group):
        asked.append(group)
        return points

    monkeypatch.setattr(project, "entry_points", entry_points)
    project.declared.cache_clear()
    return asked


def test_benchlab_itself_declares_no_project() -> None:
    """Benchlab is installed beside every project it serves: a declaration of its own would make
    every project's environment declare two, which is refused. Read off the installed metadata,
    not the stand-in ``tests/conftest.py`` puts in its place."""
    assert list(importlib.metadata.entry_points(group=project.GROUP)) == []


def test_the_declared_module_is_found_once_and_kept(monkeypatch) -> None:
    asked = _declare(monkeypatch, "tests.toy")
    assert project.declared() is toy
    assert project.piece_names() == ("wave",)
    assert project.get_component("wave") is sys.modules["tests.toy.wave"]
    assert asked == [project.GROUP], "looked up once, in its own group"


def test_no_project_declared_is_refused_naming_what_to_declare(monkeypatch) -> None:
    _declare(monkeypatch)
    with pytest.raises(LookupError, match=r"no project declares itself to Benchlab: .*"
                                          r"\[project\.entry-points\.benchlab\]"):
        project.declared()


def test_two_projects_declared_are_refused_naming_both(monkeypatch) -> None:
    _declare(monkeypatch, "tests.toy", "other.registry")
    with pytest.raises(LookupError, match=r"2 projects declare themselves to Benchlab "
                                          r"\(other\.registry, tests\.toy\)"):
        project.declared()


def test_one_project_seen_twice_is_named_with_where_each_was_found(monkeypatch) -> None:
    """A distribution renamed leaves its old metadata folder behind, and the project then declares
    itself twice: the refusal names each distribution and its folder, not just the module twice."""
    def point(dist: str, folder: str) -> types.SimpleNamespace:
        return types.SimpleNamespace(value="harness", dist=types.SimpleNamespace(
            name=dist, locate_file=lambda _path, f=folder: Path(f)))

    monkeypatch.setattr(project, "entry_points", lambda group: [point("deepc-sandbox", "/venv"),
                                                                point("deepc_old", "/repo")])
    project.declared.cache_clear()
    with pytest.raises(LookupError, match=r"\(harness by deepc-sandbox in /venv, harness by "
                                          r"deepc_old in /repo\)"):
        project.declared()


def test_a_module_lacking_a_declared_name_is_refused_naming_each(monkeypatch) -> None:
    lacking = types.ModuleType("lacking")
    lacking.NAMES, lacking.get_component, lacking.TITLE = ("a",), (lambda name: None), "A Lab"
    monkeypatch.setitem(sys.modules, "lacking", lacking)
    _declare(monkeypatch, "lacking")
    with pytest.raises(LookupError, match=r"^lacking, the module declared to Benchlab, does not "
                                          r"hold COMMAND, ROOT, LIBRARIES, WORDS$"):
        project.declared()


def test_a_record_is_stamped_from_the_projects_root_and_libraries_then_benchlab() -> None:
    prov = stamp(0.5)
    assert list(prov.versions) == [*toy.LIBRARIES, "benchlab"]
    assert prov.versions["benchlab"] == importlib.metadata.version("benchlab")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=toy.ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    assert prov.git_sha == head and prov.duration_s == 0.5


def test_the_commit_is_read_in_the_declared_root_and_nowhere_else(monkeypatch, tmp_path) -> None:
    """The toy's ROOT is Benchlab's own repository, which is also where the record layer's own
    folder and the tests' working directory lead: pointed at a repository with no commit, the
    stamp must fail there, as a record stamped from nowhere would read as one from nowhere."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.setattr(toy, "ROOT", tmp_path)
    with pytest.raises(subprocess.CalledProcessError) as refused:
        stamp(0.5)
    assert refused.value.cmd == ["git", "rev-parse", "--short", "HEAD"]
