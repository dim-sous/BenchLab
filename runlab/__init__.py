"""RunLab: the bench every project shares. A project brings its pieces; RunLab brings their
settings and run files (:mod:`runlab.record`), the charts drawn from them
(:mod:`runlab.figure`), the command line that runs and draws them (:mod:`runlab.cli`) and the
Lab's page over them (:mod:`runlab.lab`). It reaches the project only through the declaration
the project makes (:mod:`runlab.project`; ``README.md`` says how).

What a project may use is what this module holds, :mod:`runlab.testing`, and the two commands
its ``pyproject.toml`` names (``runlab.cli:main``, ``runlab.lab:main``). Nothing here is
removed, renamed or changed in meaning before 2.0 (``README.md``, "What a project may use";
``tests/test_shore.py`` holds the list). Everything deeper is RunLab's own and may change in
any version. ``run_files`` and ``files_of`` (from 0.8) are held and not promised: no project has
used them yet.
"""

from runlab.record import (TIME, Figure, Number, Provenance, Quantity, Record, Role, Series,
                             bound_refs, ci, files_of, run_files, stamp)
from runlab.record.config import Settings, with_overrides

__all__ = ["Settings", "with_overrides", "Record", "Series", "Quantity", "Figure", "Number",
           "Provenance", "stamp", "bound_refs", "Role", "ci", "TIME", "run_files", "files_of"]
