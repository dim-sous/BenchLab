"""The files a run writes beside its run file: a trained network, a checkpoint, in any format.

A run saved as ``<folder>/<name>.json`` keeps them in ``<folder>/<name>.files/``. While it runs,
the piece asks for its folder (:func:`run_files`) and is given a waiting one,
``<name>.files.partial/``; it takes the kept folder's place only when the run ends well
(:func:`writing`, then :func:`keep`), just before the run file is written, so a run that fails
leaves the earlier run of that name whole. The run file lists what the folder holds
(:func:`listed`): each file's name and its size in bytes. Nothing here opens a file.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

__all__ = ["run_files", "files_of", "kept", "waiting", "writing", "keep", "listed", "discard"]

_CURRENT: Path | None = None


def kept(path: str | os.PathLike[str]) -> Path:
    """The folder holding the files of the run saved as ``path``."""
    path = Path(path)
    return path.parent / f"{path.stem}.files"


def waiting(path: str | os.PathLike[str]) -> Path:
    """The folder a run in progress writes into, until it ends well."""
    path = Path(path)
    return path.parent / f"{path.stem}.files.partial"


def run_files() -> Path:
    """The folder of the run in progress, made on first asking; what the piece writes there is
    kept with its run file. Refused outside a run started by the command or the Lab."""
    if _CURRENT is None:
        raise LookupError("no run is in progress, so there is no folder for its files: run the "
                          "piece through its command or the Lab, which name the run")
    _CURRENT.mkdir(parents=True, exist_ok=True)
    return _CURRENT


def files_of(path: str | os.PathLike[str]) -> Path:
    """The folder holding the files of the saved run ``path``. Refused when there is no such
    run file, or when that run wrote no file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no run file at {path}, so no files of its run")
    folder = kept(path)
    if not folder.is_dir():
        raise FileNotFoundError(f"the run at {path} wrote no file: there is no {folder}")
    return folder


@contextlib.contextmanager
def writing(path: str | os.PathLike[str]) -> Iterator[None]:
    """While the run to be saved as ``path`` runs: :func:`run_files` gives its waiting folder,
    emptied of what an earlier run left there. A run that raises leaves no waiting folder."""
    global _CURRENT
    discard(path)
    _CURRENT = waiting(path)
    try:
        yield
    except BaseException:
        discard(path)
        raise
    finally:
        _CURRENT = None


def keep(path: str | os.PathLike[str]) -> None:
    """The waiting folder takes the kept folder's place: what the earlier run of that name
    wrote goes, and a run that wrote nothing keeps no folder."""
    old, new = kept(path), waiting(path)
    if old.is_dir():
        shutil.rmtree(old)
    if new.is_dir():
        if any(p.is_file() for p in new.rglob("*")):
            os.replace(new, old)
        else:
            shutil.rmtree(new)


def discard(path: str | os.PathLike[str]) -> None:
    """Remove the waiting folder of the run to be saved as ``path``, when there is one."""
    folder = waiting(path)
    if folder.is_dir():
        shutil.rmtree(folder)


def listed(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """What the kept folder of the run ``path`` holds: each file's ``name``, its path under the
    folder with forward slashes, and its size in ``bytes``; sorted by name, none without one."""
    folder = kept(path)
    if not folder.is_dir():
        return []
    return [{"name": p.relative_to(folder).as_posix(), "bytes": p.stat().st_size}
            for p in sorted(folder.rglob("*")) if p.is_file()]
