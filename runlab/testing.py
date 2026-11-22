"""What a project's own suite calls to check that it plugs into RunLab, from one test:

    from runlab.testing import check_project

    def test_the_pieces_plug_into_the_bench(tmp_path):
        ...                                   # runs made through the project's own command
        check_project(runs=[first, second])

RunLab's own suite checks RunLab, on a made-up project. This checks the one thing only the
project can: that what it declares is what RunLab reads. It runs no piece: the project makes
the runs it hands over, since only it knows settings that run quickly.
"""

from __future__ import annotations

import ast
import os
import tempfile
import warnings
from collections.abc import Sequence
from pathlib import Path

import plotly.graph_objects as go

import runlab
from runlab.figure.chart import chart_of, mean_band_of
from runlab.figure.draw import draw
from runlab.figure.own import own_figure
from runlab.figure.twin import figure_of
from runlab.lab import state, words
from runlab.lab.form import Form
from runlab.project import declared, get_component, piece_names
from runlab.record import COMPONENT_KEY, FILES_KEY, Record, read_header
from runlab.record.config import Settings
from runlab.record.files import kept

__all__ = ["check_project"]

_OWN = __name__.split(".")[0]
_SHORE = tuple(runlab.__all__)
#: The modules of RunLab a project file may import from, each with the names it may take
#: (``None``: any): the package's own names, this module, and the two commands its
#: ``pyproject.toml`` names.
_OPEN: dict[str, set[str] | None] = {
    _OWN: {*_SHORE, "testing"}, f"{_OWN}.testing": None,
    f"{_OWN}.cli": {"main"}, f"{_OWN}.lab": {"main"}}
_PIECE = ("Config", "run", "Record")


def check_project(runs: Sequence[str | os.PathLike[str]] = (), *,
                  sources: Sequence[str | os.PathLike[str]] | None = None) -> None:
    """Refuse, naming the piece or the file and the cause, when the declared project does not
    plug into RunLab:

    - the declaration is incomplete (:func:`runlab.project.declared`'s own refusal);
    - a piece does not hold ``Config`` (a ``Settings``), ``run`` and ``Record`` (a ``Record``
      whose ``component`` is the piece's registered name), or its defaults do not build;
    - a piece's settings do not build the Lab's form;
    - one of ``runs``, record files the project made, is of no registered piece, does not load
      through its piece's ``Record``, declares a chart that does not draw, as a still or on
      the page, or whose band of a mean (``Series.mean_band``) does not answer for the run's
      own draws, or a figure of its own that plotly does not take, or lists a file its run
      wrote that is not in its folder at the size listed;
    - a Python file under ``sources`` (the declared ``ROOT`` when ``None``; folders whose name
      starts with a dot are skipped) imports more of RunLab than a project may use.

    What of the project's words file RunLab leaves out is a warning, never a refusal: a slot
    renamed in a later RunLab must not fail a project's suite.
    """
    names = piece_names()
    for name in names:
        _check_piece(name)
    for piece in state.pieces():
        _check_form(piece)
    left_out = words.left_out()
    if left_out:
        warnings.warn(left_out, stacklevel=2)
    with tempfile.TemporaryDirectory() as out:
        for path in runs:
            _check_run(Path(path), names, Path(out))
    for folder in ([declared().ROOT] if sources is None else sources):
        _check_imports(Path(folder))


def _check_piece(name: str) -> None:
    piece = get_component(name)
    missing = [n for n in _PIECE if not hasattr(piece, n)]
    assert not missing, f"the piece {name!r} does not hold {', '.join(missing)}"
    assert issubclass(piece.Config, Settings), \
        f"the piece {name!r}: its Config is not a runlab Settings"
    assert callable(piece.run), f"the piece {name!r}: its run cannot be called"
    assert issubclass(piece.Record, Record), \
        f"the piece {name!r}: its Record is not a runlab Record"
    assert piece.Record.component == name, \
        (f"the piece {name!r}: its Record.component is {piece.Record.component!r}, so its runs "
         f"would be saved and listed under another piece")
    piece.Config()


def _check_form(piece: dict) -> None:
    form = Form(piece)
    for f in form.fields:
        form.shown_default(f)
        form.options(f)
        form.state_of(f)


def _check_run(path: Path, names: Sequence[str], out: Path) -> None:
    header = read_header(path)
    piece = header[COMPONENT_KEY]
    assert piece in names, f"{path} is a run of {piece!r}; the registered pieces are {list(names)}"
    record = get_component(piece).Record.load(path)
    pairs = [(record.name, record)]
    for series in record.series():
        try:
            draw(pairs, out, panels=[series.name])
            figure_of(chart_of(pairs, series.name))
            mean_band_of(series, series.averaged)
        except Exception as exc:        # whatever stops a chart, raised again naming its run
            raise AssertionError(f"{path}: the chart {series.name!r} does not draw "
                                 f"({type(exc).__name__}: {exc})") from exc
    for held in header.get(FILES_KEY, []):
        file = kept(path) / held["name"]
        assert file.is_file(), f"{path} lists the file {held['name']!r}; there is no {file}"
        assert file.stat().st_size == held["bytes"], \
            (f"{path} lists {held['name']!r} at {held['bytes']} bytes; {file} holds "
             f"{file.stat().st_size}")
    for figure in record.figures():
        try:
            go.Figure(own_figure(record, figure.name))
        except Exception as exc:        # whatever plotly refuses, raised again naming its run
            raise AssertionError(f"{path}: the figure {figure.name!r} is not one plotly takes "
                                 f"({type(exc).__name__}: {exc})") from exc


def _beyond(node: ast.AST) -> list[str]:
    """What an import statement takes from RunLab that a project may not use."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names
                if a.name.split(".")[0] == _OWN and a.name not in (_OWN, f"{_OWN}.testing")]
    if isinstance(node, ast.ImportFrom) and not node.level \
            and (node.module or "").split(".")[0] == _OWN:
        allowed = _OPEN.get(node.module, set())
        if allowed is not None:
            return [f"{node.module}.{a.name}" for a in node.names if a.name not in allowed]
    return []


def _check_imports(folder: Path) -> None:
    for path in sorted(folder.rglob("*.py")):
        if any(part.startswith(".") or part == "__pycache__"
               for part in path.relative_to(folder).parts):
            continue
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            beyond = _beyond(node)
            assert not beyond, \
                (f"{path}:{node.lineno} imports {', '.join(beyond)}: RunLab's own, which may "
                 f"change in any version. A project may use the names `{_OWN}` holds "
                 f"({', '.join(_SHORE)}), `{_OWN}.testing`, and `main` of `{_OWN}.cli` and "
                 f"`{_OWN}.lab`")
