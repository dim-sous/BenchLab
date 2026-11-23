"""RunLab's shape. It reaches a project only through ``runlab/project.py``, and its layers
import one way: ``project``, ``record``, then ``figure`` and ``runner``, then ``cli``, then
``lab``, then ``testing``; the package's own ``__init__`` holds names of ``record`` (DeePC's ``tests/test_devkit_layers.py``, its half about these layers, moved here with
them).

The layers only ever touch a Config or a Record and never know what is inside: if a line of their
code names a piece, it is in the wrong place. Stdlib and ``ast`` only, reading the files: what is
held is what the code says, not what an import happens to do.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from runlab import project

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "runlab"
SOURCES = sorted(p for p in PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)
#: Who may import whom inside RunLab. The Lab reaches the figure layer for what a card draws
#: (``figure.chart``, ``figure.twin``); that every chart on the page IS the figure layer's is held
#: by ``tests/test_lab.py``, not by this table.
_MAY_IMPORT = {"project": set(), "record": {"project"}, "figure": {"record"},
               # a saved run flown again, its file completed when it comes back the same (1.12)
               "refly": {"project", "record"},
               "runner": {"project", "record", "refly"},
               "cli": {"project", "record", "figure", "runner", "refly"},
               "lab": {"project", "record", "figure", "runner", "cli"},
               # the names a project may use, and the check it calls (tests/test_shore.py)
               "__init__": {"record"}, "testing": {"project", "record", "figure", "lab"}}
#: RunLab's dependencies (``pyproject.toml``), by the name they are imported by.
_DEPENDENCIES = {"matplotlib", "numpy", "panel", "param", "plotly"}
#: What finds or imports a module by a name read at run time: the project's door, and only its.
_LOOKUPS = {"entry_points", "import_module", "__import__"}


def _layer(path: Path) -> str:
    """``runlab/<layer>/...`` or ``runlab/<layer>.py``; the package's own ``__init__``."""
    rel = path.relative_to(PACKAGE)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _package(path: Path) -> list[str]:
    """The dotted package a file's relative imports start from: its folder, ``runlab.<layer>``."""
    return list(path.relative_to(ROOT).parent.parts)


def _imports(path: Path):
    """Every module a file imports, absolute: a relative import resolved against the file's own
    package, and ``from a import b`` also as ``a.b``, since ``b`` may be a module (``from
    runlab import lab`` reaches the Lab as surely as ``import runlab.lab``)."""
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            base = _package(path)[:len(_package(path)) - node.level + 1] if node.level else []
            module = ".".join(base + ([node.module] if node.module else []))
            yield module
            for alias in node.names:
                yield f"{module}.{alias.name}"


def _ids(paths: list[Path]) -> list[str]:
    return [str(p.relative_to(PACKAGE)) for p in paths]


def test_every_layer_is_in_the_import_table() -> None:
    layers = {_layer(p) for p in SOURCES}
    assert layers == set(_MAY_IMPORT), f"runlab holds {sorted(layers)}; the table names " \
                                       f"{sorted(_MAY_IMPORT)}"


@pytest.mark.parametrize("path", SOURCES, ids=_ids(SOURCES))
def test_runlab_imports_only_itself_the_standard_library_and_its_dependencies(path: Path) -> None:
    """A project is never imported by its name: RunLab serves whichever one declares itself."""
    for name in _imports(path):
        top = name.split(".")[0]
        assert top == "runlab" or top in _DEPENDENCIES or top in sys.stdlib_module_names, \
            f"{path.relative_to(ROOT)} imports {name}"


@pytest.mark.parametrize("path", SOURCES, ids=_ids(SOURCES))
def test_only_the_project_module_finds_and_imports_a_project(path: Path) -> None:
    if path == PACKAGE / "project.py":
        return
    tree = ast.parse(path.read_text())
    used = ({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            | {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
               for a in n.names})
    assert not used & _LOOKUPS, f"{path.relative_to(ROOT)} uses {sorted(used & _LOOKUPS)}: a " \
                                f"second door to the project"


@pytest.mark.parametrize("layer", sorted(_MAY_IMPORT))
def test_the_dependency_runs_one_way_between_the_layers(layer: str) -> None:
    allowed = _MAY_IMPORT[layer] | {layer}
    for path in (p for p in SOURCES if _layer(p) == layer):
        crossing = sorted({n for n in _imports(path)
                           if n.startswith("runlab.") and n.split(".")[1] not in allowed})
        assert not crossing, (f"{path.relative_to(ROOT)} imports {crossing}; {layer} may reach "
                              f"only {sorted(allowed)}")


@pytest.mark.parametrize("path", SOURCES, ids=_ids(SOURCES))
def test_runlab_never_names_a_piece_in_its_code(path: Path) -> None:
    """A string literal, an attribute or an imported name equal to a piece's name couples RunLab
    to that piece. Held against the made-up project's pieces; prose, comments and local
    variables cannot couple."""
    names = set(project.piece_names())
    for node in ast.walk(ast.parse(path.read_text())):
        spelled = ((isinstance(node, ast.Constant) and node.value in names)
                   or (isinstance(node, ast.Attribute) and node.attr in names)
                   or (isinstance(node, ast.alias) and node.name in names))
        assert not spelled, f"{path.relative_to(ROOT)}:{node.lineno} names a piece"
