"""The pages of the figures that play, where the Lab's server answers for them.

A figure of a piece's own that holds frames is shown in a frame on its card, as the page plotly
writes for it (:func:`runlab.figure.own.own_page`). The browser asks for that page at an address
of its own; it is never sent through the card, because every frame's data would go with it.
The page reads plotly's library from an address beside it, answered out of the installed
``plotly`` package (4.8 MB in plotly 7.1.0), so the Lab's page still needs no internet.

The pages are files in a folder of this process's own, outside the project (the system's
temporary folder), made on first use and removed when the process ends; the Lab's server
answers for the folder as it does for the fonts. A page drawn again takes its file's place.
"""

from __future__ import annotations

import atexit
import functools
import hashlib
import shutil
import tempfile
from pathlib import Path

__all__ = ["ROUTE", "LIBRARY_ROUTE", "LIBRARY", "folder", "address", "page_of"]

#: Where the pages are answered: ``/ROUTE/<file>``.
ROUTE = "runlab-frames"
#: Where plotly's own files are answered (``figure.own.library_dir``).
LIBRARY_ROUTE = "runlab-plotly"
#: The address a playing figure's page reads plotly's library from.
LIBRARY = f"/{LIBRARY_ROUTE}/plotly.min.js"


@functools.cache
def folder() -> Path:
    """The folder the pages are written in, made the first time it is asked for."""
    made = Path(tempfile.mkdtemp(prefix="runlab-frames-"))
    atexit.register(shutil.rmtree, made, ignore_errors=True)
    return made


def address(key: str, page: str) -> str:
    """Write ``page`` as the file of ``key`` and give the address it is answered at. The
    address changes with the page, so a frame given it again loads only what changed."""
    name = hashlib.sha256(key.encode()).hexdigest()[:24] + ".html"
    (folder() / name).write_text(page, encoding="utf-8")
    return f"/{ROUTE}/{name}?v={hashlib.sha256(page.encode()).hexdigest()[:12]}"


def page_of(at: str) -> str:
    """The page written for the address ``at``, as :func:`address` gave it."""
    return (folder() / at.split("?")[0].rsplit("/", 1)[-1]).read_text(encoding="utf-8")
