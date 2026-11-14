"""The one project Benchlab serves, found through the entry point its ``pyproject.toml`` declares:

    [project.entry-points.benchlab]
    project = "harness"            # the module holding its registry and its declaration

That module holds the project's registry -- ``NAMES``, its pieces in the order every surface shows
them, and ``get_component(name)``, a piece's module -- and its declaration: ``COMMAND``, the
command its ``pyproject.toml`` installs (the Lab launches ``uv run <COMMAND> run``), ``TITLE``,
the Lab's title, ``ROOT``, the repository whose commit stamps a record, and ``LIBRARIES``, the
libraries whose versions a record keeps.

Nothing is looked up when Benchlab is imported: the project is found on first use and kept. Every
other module of Benchlab reaches the project through this one (``tests/test_layers.py``).
"""

from __future__ import annotations

import functools
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from types import ModuleType

__all__ = ["GROUP", "DECLARED", "declared", "piece_names", "get_component", "command", "title"]

#: The entry-point group a project declares itself in.
GROUP = "benchlab"
#: The names the declared module must hold (the module docstring says what each is).
DECLARED = ("NAMES", "get_component", "COMMAND", "TITLE", "ROOT", "LIBRARIES")


@functools.cache
def declared() -> ModuleType:
    """The declared project's module. Refused, naming the cause: no project declared, more than
    one, or a module missing a name of :data:`DECLARED`."""
    found = list(entry_points(group=GROUP))
    if not found:
        raise LookupError(f"no project declares itself to Benchlab: the project's pyproject.toml "
                          f"needs [project.entry-points.{GROUP}] project = \"<its registry "
                          f"module>\", and `uv sync` after it is added")
    if len(found) > 1:
        raise LookupError(f"{len(found)} projects declare themselves to Benchlab "
                          f"({', '.join(sorted(_where(ep) for ep in found))}); one environment "
                          f"serves one project")
    module = found[0].load()
    missing = [name for name in DECLARED if not hasattr(module, name)]
    if missing:
        raise LookupError(f"{found[0].value}, the module declared to Benchlab, does not hold "
                          f"{', '.join(missing)}")
    return module


def _where(entry_point: EntryPoint) -> str:
    """The declared module, with the distribution that declares it and the folder its metadata
    sits in when known: one project's metadata left in two folders reads as two projects."""
    dist = getattr(entry_point, "dist", None)
    if dist is None:
        return entry_point.value
    return f"{entry_point.value} by {dist.name} in {Path(str(dist.locate_file(''))).resolve()}"


def piece_names() -> tuple[str, ...]:
    """The declared project's pieces, in the order every surface shows them."""
    return tuple(declared().NAMES)


def get_component(name: str) -> ModuleType:
    """The declared project's piece ``name``, as its registry imports it."""
    return declared().get_component(name)


def command() -> str:
    """The command the declared project installs, which the Lab launches as ``uv run <it> run``."""
    return declared().COMMAND


def title() -> str:
    """The Lab's title, the declared project's."""
    return declared().TITLE
