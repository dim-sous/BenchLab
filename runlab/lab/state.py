"""What the page lists, as plain data; every value is read, none computed.

Two sources only: the declarations (the registry and :func:`record.config.fields_of`) and the
files under the out-dir. A record is LISTED as the JSON it is -- its header, config,
provenance and numbers, never the traces -- and a record that is SHOWN is loaded through its
own class (:func:`load`), every rule of that loading the class's own, so the figure layer's
twin can draw what it declares.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runlab.project import get_component, piece_names
from runlab.record import (COMPONENT_KEY, FILES_KEY, NUMBER_SPECS_KEY, PANEL_GROUPS_KEY,
                             PANELS_KEY, differences, read_header)
from runlab.record.config import fields_of, flat
from runlab.record.files import kept

from .words import say, say_n

#: The keys every listed record carries, and nothing else. ``stale``: why it cannot be shown,
#: empty for one that can. ``notes``: a line for each way a file that can be shown departs
#: from what its piece reads now.
RECORD_KEYS = ("piece", "name", "path", "mtime", "panels", "panel_groups", "number_specs",
               "numbers", "config", "provenance", "stale", "notes", "files")
_CACHE: dict[str, tuple[tuple[float, int], dict[str, Any]]] = {}


def pieces() -> list[dict[str, Any]]:
    """Every registered piece: its name, its own words, the command that writes a record, and
    its settings as :func:`fields_of` declares them."""
    out = []
    for name in piece_names():
        component = get_component(name)
        out.append({"name": name, "label": component.Record.label or name,
                    "produced_by": component.Record.produced_by,
                    "provides": tuple(component.Record.provides),
                    "fields": fields_of(component.Config)})
    return out


def records(root: str, out_dir: str) -> list[dict[str, Any]]:
    """Every ``<root>/<out_dir>/<piece>/*.json``, newest first. An absent folder is an empty
    list; a file that is not a record is listed carrying the refusal as its ``stale`` words.
    Each file its run file lists (``files``: ``name``, ``bytes``) carries ``there``, whether
    it is in the run's folder now, read at every listing."""
    rows = []
    for name in piece_names():
        folder = Path(root) / out_dir / name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.suffix == ".json" and path.is_file():
                row = _record(path, name)
                rows.append({**row, "files": [
                    {**f, "there": (kept(path) / f["name"]).is_file()} for f in row["files"]]}
                            if row["files"] else row)
    rows.sort(key=lambda r: r["mtime"], reverse=True)
    return rows


def _record(path: Path, piece: str) -> dict[str, Any]:
    st = path.stat()
    key = (st.st_mtime, st.st_size)
    hit = _CACHE.get(str(path))
    if hit and hit[0] == key:
        return hit[1]
    row = _read(path, piece, st.st_mtime)
    _CACHE[str(path)] = (key, row)
    return row


def _read(path: Path, piece: str, mtime: float) -> dict[str, Any]:
    """One row. A JSON that is not a record is LISTED, carrying ``read_header``'s words as its
    staleness, never raised: the out-dir is a folder people keep things in (a saved settings
    file is how a setup is kept, and ``<command> draw`` can be pointed at it), and one such file must
    not take the page down with it."""
    row = {"piece": piece, "name": path.stem, "path": str(path), "mtime": mtime,
           "panels": [], "panel_groups": {}, "number_specs": [], "numbers": {}, "config": {},
           "provenance": {}, "stale": "", "notes": [], "files": []}
    try:
        header = read_header(path)                    # the authority on what a record is
    except ValueError as exc:
        row["stale"] = str(exc)
        return row
    with open(path) as fh:
        raw = json.load(fh)
    panels, panel_words = _panels(header.get(PANELS_KEY))
    specs, spec_words = _number_specs(header.get(NUMBER_SPECS_KEY))
    row.update({
        "name": path.stem,                 # the file is the identity; `<command> draw` takes the path
        "panels": panels,
        "panel_groups": _groups(header.get(PANEL_GROUPS_KEY), panels),
        "number_specs": specs,
        "numbers": dict(raw.get("numbers", {})),
        "config": _settings(piece, raw.get("config", {})),
        "provenance": dict(raw.get("provenance", {})),
        "files": _files(header.get(FILES_KEY)),
        "stale": "; ".join(w for w in (_stale(piece, raw), panel_words, spec_words) if w),
        "notes": _notes(piece, raw),
    })
    return row


def _settings(piece: str, held: Any) -> dict[str, Any]:
    """A run file's settings as the form and the compare table name them: a part's spread out
    by dotted names (:func:`record.config.flat`). Settings of another shape are left as they are,
    for the run's notes to say."""
    if not isinstance(held, dict):
        return {}
    try:
        cls = get_component(piece).Config
    except (KeyError, LookupError, ImportError):
        return dict(held)
    return flat(cls, held)


def _panels(held: Any) -> tuple[list[str], str]:
    """The panel names, or none of them and the words why: whatever a page reads here it will
    subscript, so a header of another shape is refused ONCE, here, not where it is used."""
    if held is None:
        return [], ""
    if not isinstance(held, list) or not all(isinstance(p, str) for p in held):
        return [], say("runs.stale.panels", key=repr(PANELS_KEY))
    return list(held), ""


def _files(held: Any) -> list[dict[str, Any]]:
    """The files the run file lists, each a name and a size in bytes; none for a run that wrote
    none, a file written before runs wrote files, or a list of another shape."""
    if not isinstance(held, list) or not all(
            isinstance(f, dict) and isinstance(f.get("name"), str)
            and isinstance(f.get("bytes"), int) for f in held):
        return []
    return [{"name": f["name"], "bytes": f["bytes"]} for f in held]


def _groups(held: Any, panels: list[str]) -> dict[str, str]:
    """Each panel's group as the header holds it; none for a file written before groups were
    declared, or one whose groups are not names, so that it lists ungrouped rather than fails."""
    if not isinstance(held, dict) or not all(isinstance(v, str) for v in held.values()):
        return {}
    return {p: held[p] for p in panels if p in held}


def _number_specs(held: Any) -> tuple[list[dict[str, Any]], str]:
    """The number declarations, each with at least the name and the words to show it by."""
    if held is None:
        return [], ""
    if not isinstance(held, list):
        return [], say("runs.stale.specs", key=repr(NUMBER_SPECS_KEY))
    out = []
    for spec in held:
        if not isinstance(spec, dict) or not isinstance(spec.get("name"), str) \
                or not isinstance(spec.get("label"), str):
            return [], say("runs.stale.spec", key=repr(NUMBER_SPECS_KEY))
        out.append(spec)
    return out, ""


def _stale(piece: str, raw: dict[str, Any]) -> str:
    """Words for a record of another piece, which cannot be shown here; else an empty string."""
    held_piece = raw.get(COMPONENT_KEY)
    if held_piece != piece:
        return say("runs.stale.piece", held=repr(held_piece), piece=piece)
    return ""


def _notes(piece: str, raw: dict[str, Any]) -> list[str]:
    """A line for each way the file departs from what its piece reads now: in its fields, in
    where it came from, in its settings. The record layer's own statement of them
    (``record.differences``), worded; the file is shown all the same. A saved value the piece
    no longer admits (a bound narrowed, a choice withdrawn) is not among them: it is seen where
    it is read, when the record is loaded, in its own words."""
    if raw.get(COMPONENT_KEY) != piece:
        return []
    return [_note(d.place, d.kind, len(d.names), ", ".join(d.names))
            for d in differences(get_component(piece).Record, raw)]


def _note(place: str, kind: str, n: int, fields: str) -> str:
    """The words for ``n`` entries of ``place`` the file lacks, or holds past what is read."""
    lacks = kind == "lacks"
    if place == "result":
        return (say_n("runs.stale.predates", n, fields=fields) if lacks
                else say_n("runs.stale.gone", n, fields=fields))
    if place == "settings":
        return (say_n("runs.differs.settings_lacks", n, fields=fields) if lacks
                else say_n("runs.differs.settings_extra", n, fields=fields))
    return (say_n("runs.differs.origin_lacks", n, fields=fields) if lacks
            else say_n("runs.differs.origin_extra", n, fields=fields))


#: A run's own folders beside its run file (``record.files``): never a folder of saved pictures.
RUN_FILES = (".files", ".files.partial")


def folders(root: str, out_dir: str, piece: str) -> list[dict[str, Any]]:
    """The folders of saved pictures under ``<root>/<out_dir>/<piece>/``, newest first: each
    one's name, its pictures (``.png``), how many tables (``.csv``) beside them, and when it
    last changed -- what a Save or a draw wrote, read off the folder (BESS's ``lab/state.py``).
    A run's own folder of files is not one, whatever it holds."""
    base = Path(root) / out_dir / piece
    if not base.is_dir():
        return []
    out = []
    for folder in base.iterdir():
        if not folder.is_dir() or folder.name.endswith(RUN_FILES):
            continue
        pictures = sorted(f.name for f in folder.iterdir() if f.suffix == ".png")
        if not pictures:
            continue
        tables = sum(1 for f in folder.iterdir() if f.suffix == ".csv")
        out.append({"name": folder.name, "path": str(folder), "pictures": pictures,
                    "tables": tables, "mtime": max(f.stat().st_mtime for f in folder.iterdir())})
    out.sort(key=lambda f: f["mtime"], reverse=True)
    return out


def load(run: dict[str, Any]) -> Any:
    """The record behind a listed row, through its own class: READ off disk, with every rule of
    the reading the class's own (a body that no longer decodes, a value the Config no longer
    admits, are refused in its words). What the page hands to the figure layer's twin, and
    where it reads a record's constants."""
    return get_component(run["piece"]).Record.load(run["path"])
