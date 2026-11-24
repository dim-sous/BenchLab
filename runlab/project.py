"""The one project RunLab serves, found through the entry point its ``pyproject.toml`` declares:

    [project.entry-points.runlab]
    project = "harness"            # the module holding its registry and its declaration

That module holds the project's registry -- ``NAMES``, its pieces in the order every surface shows
them, and ``get_component(name)``, a piece's module -- and its declaration: ``COMMAND``, the
command its ``pyproject.toml`` installs (the side door; the Lab prints its line beside each run),
``TITLE``, the Lab's title, ``ROOT``, the repository whose commit stamps a record, and
``LIBRARIES``, the libraries whose versions a record keeps. It may also hold ``WORDS``, the path
of a words file listing the words of the Lab's page it wants different from RunLab's own
(:mod:`runlab.lab.words`), and ``OUT_DIR`` (from 1.16), the folder under its root its runs write
their records to when no ``--out-dir`` is given (``results`` when it names none).

Nothing is looked up when RunLab is imported: the project is found on first use and kept. Every
other module of RunLab reaches the project through this one (``tests/test_layers.py``).
"""

from __future__ import annotations

import functools
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from types import ModuleType

__all__ = ["GROUP", "DECLARED", "declared", "piece_names", "get_component", "carriers", "command",
           "title", "words_path", "DEFAULT_OUT_DIR", "out_dir"]

#: The entry-point group a project declares itself in.
GROUP = "runlab"
#: The names the declared module must hold (the module docstring says what each is).
DECLARED = ("NAMES", "get_component", "COMMAND", "TITLE", "ROOT", "LIBRARIES")


@functools.cache
def declared() -> ModuleType:
    """The declared project's module. Refused, naming the cause: no project declared, more than
    one, or a module missing a name of :data:`DECLARED`."""
    found = list(entry_points(group=GROUP))
    if not found:
        raise LookupError(f"no project declares itself to RunLab: the project's pyproject.toml "
                          f"needs [project.entry-points.{GROUP}] project = \"<its registry "
                          f"module>\", and `uv sync` after it is added")
    if len(found) > 1:
        raise LookupError(f"{len(found)} projects declare themselves to RunLab "
                          f"({', '.join(sorted(_where(ep) for ep in found))}); one environment "
                          f"serves one project")
    module = found[0].load()
    missing = [name for name in DECLARED if not hasattr(module, name)]
    if missing:
        raise LookupError(f"{found[0].value}, the module declared to RunLab, does not hold "
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


def carriers(what: str) -> tuple[str, ...]:
    """The pieces whose saved runs a setting naming ``what`` (``record_of``) may name, in the
    order every surface shows them: the piece called ``what``, and every piece whose record
    declares it carries ``what`` (``Record.provides``). Reading it imports every piece."""
    return tuple(name for name in piece_names()
                 if name == what or what in get_component(name).Record.provides)


def command() -> str:
    """The command the declared project installs: the side door, whose line the Lab prints
    beside each run it starts."""
    return declared().COMMAND


def title() -> str:
    """The Lab's title, the declared project's."""
    return declared().TITLE


#: The folder under a project's root its runs write their records to, when the project names
#: none (``OUT_DIR``) and no ``--out-dir`` is given.
DEFAULT_OUT_DIR = "results"


def out_dir() -> str:
    """The folder under the declared project's root its runs write their records to: its
    ``OUT_DIR`` (from 1.16), else :data:`DEFAULT_OUT_DIR`."""
    return str(getattr(declared(), "OUT_DIR", DEFAULT_OUT_DIR))


def words_path() -> Path | None:
    """The declared project's words file, the words of the Lab's page it changes; ``None`` when
    it names no file and the page keeps RunLab's own."""
    path = getattr(declared(), "WORDS", None)
    return None if path is None else Path(path)
