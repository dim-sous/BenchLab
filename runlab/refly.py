"""Re-fly (from 1.12): a saved run flown again from its own settings, compared with what its file
holds, and -- only when every value it holds comes back the same -- completed with what it lacks.
Carried from RCWS's ``record/__init__.py`` (``compared``, ``refilled``) and its ``sim run
--refly``: a run saved before its piece's record gained a field is made whole without a second
run under another name.

Compared: every field the file holds but its name, its provenance, its numbers and its settings,
and a field the record declares measured on the clock (``field(metadata={"clock": True})``); a
record held inside another, without its own name, provenance, settings and numbers. Text, yes/no
and whole numbers must be equal; numbers within ``RTOL``/``ATOL``, not-a-number where it was.
Completed: the fields and the settings the file lacks added, its numbers today's, and the
re-flight written under ``provenance.filled``. Otherwise the file is left as it is and what
differs is said.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import os
import typing
from pathlib import Path
from typing import Any

import numpy as np

from runlab.project import get_component
from runlab.record import Record, _jsonable, stamp
from runlab.record.config import from_saved

__all__ = ["RTOL", "ATOL", "Refly", "refly"]

#: How far a number flown again may stand from the one the file holds (RCWS's REFLY_RTOL/ATOL).
RTOL, ATOL = 1e-9, 1e-12

_NONFINITE = {"nan": np.nan, "inf": np.inf, "-inf": -np.inf}


@dataclasses.dataclass(frozen=True)
class Refly:
    """What a re-flight found: what ``differs`` (in words), the ``fields`` and ``settings`` the
    file lacked, and each number that changed, ``{name: [held, flown]}``."""
    differs: tuple[str, ...]
    fields: tuple[str, ...]
    settings: tuple[str, ...]
    numbers: dict[str, list[Any]]

    @property
    def matches(self) -> bool:
        return not self.differs


def _back(value: Any) -> Any:
    if isinstance(value, list):
        return [_back(v) for v in value]
    return _NONFINITE.get(value, value) if isinstance(value, str) else value


def _differences(held: Any, flown: Any, where: str, out: list[str]) -> None:
    if isinstance(held, dict) and isinstance(flown, dict):
        for key in held:
            if key not in flown:
                out.append(f"{where}.{key}: the re-flight has none")
            else:
                _differences(held[key], flown[key], f"{where}.{key}", out)
        return
    if held == flown:
        return
    if isinstance(held, (bool, str)) or isinstance(flown, (bool, str)):
        out.append(f"{where}: {held!r} held, {flown!r} flown")
        return
    try:
        x = np.asarray(_back(held), dtype=float)
        y = np.asarray(_back(flown), dtype=float)
    except (TypeError, ValueError):
        out.append(f"{where}: {held!r} held, {flown!r} flown")
        return
    if x.shape != y.shape:
        out.append(f"{where}: shape {x.shape} held, {y.shape} flown")
        return
    if np.allclose(x, y, rtol=RTOL, atol=ATOL, equal_nan=True):
        return
    gap = np.where(np.isnan(x) & np.isnan(y), 0.0, np.abs(x - y))
    gap = np.where(np.isnan(gap), np.inf, gap)
    at = np.unravel_index(int(np.argmax(gap)), gap.shape) if gap.ndim else ()
    out.append(f"{where}: largest difference {float(gap[at]):.3g} at {list(map(int, at))}, "
               f"{float(x[at])!r} held, {float(y[at])!r} flown")


def _is_record(hint: Any) -> bool:
    args = [a for a in typing.get_args(hint) if a is not type(None)] or [hint]
    return isinstance(args[0], type) and issubclass(args[0], Record)


def compared(raw: dict[str, Any], again: Record) -> Refly:
    """The saved file ``raw`` held against ``again``, the run flown from its own settings."""
    now = {f.name: _jsonable(getattr(again, f.name)) for f in dataclasses.fields(again)}
    hints = typing.get_type_hints(type(again))
    differs: list[str] = []
    missing: list[str] = []
    for f in dataclasses.fields(again):
        if f.name in ("name", "provenance", "numbers", "config"):
            continue
        if f.name not in raw:
            missing.append(f.name)
        elif (f.metadata or {}).get("clock"):
            continue
        elif _is_record(hints[f.name]) and isinstance(raw[f.name], dict):
            held, flown = dict(raw[f.name]), dict(now[f.name] or {})
            for key in ("name", "provenance", "config", "numbers"):
                held.pop(key, None)
                flown.pop(key, None)
            _differences(held, flown, f.name, differs)
        else:
            _differences(raw[f.name], now[f.name], f.name, differs)
    held_cfg, flown_cfg = raw.get("config") or {}, now["config"] or {}
    settings = [k for k in flown_cfg if k not in held_cfg]
    _differences({k: v for k, v in held_cfg.items() if k in flown_cfg}, flown_cfg, "config",
                 differs)
    held, numbers_now = raw.get("numbers") or {}, now.get("numbers") or {}
    numbers = {k: [held.get(k), numbers_now.get(k)]
               for k in [*held, *(k for k in numbers_now if k not in held)]
               if held.get(k) != numbers_now.get(k)}
    return Refly(tuple(differs), tuple(missing), tuple(settings), numbers)


def refly(path: str | os.PathLike[str]) -> Refly:
    """Fly the run saved at ``path`` again from its own settings; when every value it holds comes
    back the same, write in what it lacks (the module). The file is left as it is otherwise."""
    path = Path(path)
    raw = json.loads(path.read_text())
    piece = get_component(raw["component"])
    config_cls = typing.get_type_hints(piece.Record)["config"]
    cfg = from_saved(config_cls, raw.get("config") or {})
    again = dataclasses.replace(piece.run(cfg), name=raw.get("name", path.stem))
    found = compared(raw, again)
    if not found.matches:
        return found
    now = {f.name: _jsonable(getattr(again, f.name)) for f in dataclasses.fields(again)}
    out = dict(raw)
    for name in found.fields:
        out[name] = now[name]
    out["config"] = {**now["config"], **(raw.get("config") or {})}
    out["config"].update({k: now["config"][k] for k in found.settings})
    out["numbers"] = now["numbers"]
    prov = dict(raw.get("provenance") or {})
    filled = stamp(0.0)
    prov.setdefault("filled", []).append({
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "git_sha": filled.git_sha, "git_dirty": filled.git_dirty,
        "fields": list(found.fields), "settings": list(found.settings),
        "numbers": found.numbers})
    out["provenance"] = prov
    out.update({k: v for k, v in again.header().items()})
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(out, indent=1, allow_nan=False))
    os.replace(tmp, path)
    return found

