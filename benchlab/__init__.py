"""Benchlab: the bench every project shares. A project brings its pieces; Benchlab brings their
settings and run files (:mod:`benchlab.record`), the charts drawn from them
(:mod:`benchlab.figure`), the command line that runs and draws them (:mod:`benchlab.cli`) and the
Lab's page over them (:mod:`benchlab.lab`). It reaches the project only through the declaration
the project makes (:mod:`benchlab.project`; ``README.md`` says how).

What a project may use is what this module holds, :mod:`benchlab.testing`, and the two commands
its ``pyproject.toml`` names (``benchlab.cli:main``, ``benchlab.lab:main``). Nothing here is
removed, renamed or changed in meaning before 1.0 (``README.md``, "What a project may use";
``tests/test_shore.py`` holds the list). Everything deeper is Benchlab's own and may change in
any version.
"""

from benchlab.record import Number, Provenance, Record, Series, bound_refs, stamp
from benchlab.record.config import Settings, with_overrides

__all__ = ["Settings", "with_overrides", "Record", "Series", "Number", "Provenance", "stamp",
           "bound_refs"]
