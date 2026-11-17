"""The made-up project RunLab's own tests run on: its registry and its declaration, as a project
writes them (``README.md``), and three pieces: ``wave``; ``lag``, which a saved wave run
drives; and ``fit``, which writes files beside its run file. It uses of RunLab only what a project may (``tests/test_testing.py`` holds that), and
names no words file: its page keeps RunLab's own words. It is not installed:
``tests/conftest.py`` stands in for the entry point an installed project's ``pyproject.toml``
gives.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

#: The pieces, in the order every surface shows them.
NAMES: tuple[str, ...] = ("wave", "lag", "fit")
#: The command a project's ``pyproject.toml`` would install; the tests call ``runlab.cli.main``.
COMMAND = "toy"
TITLE = "Toy Lab"
#: The repository whose commit stamps a record: RunLab's own, which holds this file.
ROOT = Path(__file__).resolve().parents[2]
#: Not in alphabetical order, so a record's versions can only have taken theirs from here.
LIBRARIES: tuple[str, ...] = ("param", "numpy")


def get_component(name: str) -> ModuleType:
    """The piece's module, imported on first use; an unknown name is refused with the list."""
    if name not in NAMES:
        raise KeyError(f"unknown piece {name!r}; registered: {list(NAMES)}")
    return import_module(f".{name}", __name__)
