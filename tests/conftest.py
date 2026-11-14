"""Every test runs with the made-up project (``tests/toy``) as the declared one. An installed
project is found through the entry point its ``pyproject.toml`` declares; the toy is not
installed, so its entry point is stood in for here, and the finding is done afresh per test."""

from __future__ import annotations

from importlib.metadata import EntryPoint

import pytest

from benchlab import project

TOY = EntryPoint(name="project", value="tests.toy", group=project.GROUP)


@pytest.fixture(autouse=True)
def toy_declared(monkeypatch):
    monkeypatch.setattr(project, "entry_points",
                        lambda group: [TOY] if group == project.GROUP else [])
    project.declared.cache_clear()
    yield
    project.declared.cache_clear()
