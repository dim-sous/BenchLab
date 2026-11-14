"""Every test runs with the made-up project (``tests/toy``) as the declared one. An installed
project is found through the entry point its ``pyproject.toml`` declares; the toy is not
installed, so its entry point is stood in for here, and the finding is done afresh per test.

A run's own process (``python -m benchlab.runner``) finds its project afresh, in a new
interpreter: ``toy_installed`` gives such processes the toy as installed metadata of its own (a
``.dist-info`` folder declaring the entry point, written per test) on their ``PYTHONPATH``,
with the repository root, so ``tests.toy`` imports there too."""

from __future__ import annotations

import os
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

from benchlab import project

TOY = EntryPoint(name="project", value="tests.toy", group=project.GROUP)
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def toy_declared(monkeypatch):
    monkeypatch.setattr(project, "entry_points",
                        lambda group: [TOY] if group == project.GROUP else [])
    project.declared.cache_clear()
    yield
    project.declared.cache_clear()


@pytest.fixture
def toy_installed(tmp_path_factory, monkeypatch) -> Path:
    """The toy as an installed project for the processes this test starts; the folder holding
    its metadata."""
    site = tmp_path_factory.mktemp("site")
    meta = site / "benchlab_toy-0.0.0.dist-info"
    meta.mkdir()
    (meta / "METADATA").write_text("Metadata-Version: 2.1\nName: benchlab-toy\nVersion: 0.0.0\n")
    (meta / "entry_points.txt").write_text(f"[{project.GROUP}]\nproject = tests.toy\n")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(site), str(ROOT)]))
    return site
