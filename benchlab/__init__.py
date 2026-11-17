"""The name RunLab had until 0.10, kept so that a project written for it needs no change: what a
project may use (``README.md``, "What a project may use"), handed over from :mod:`runlab`, with
:mod:`benchlab.cli`, :mod:`benchlab.lab` and :mod:`benchlab.testing` beside it. Nothing deeper
is here: the rest of RunLab was never a project's to use.
"""

from runlab import *            # noqa: F403 -- every name runlab holds for a project
from runlab import __all__      # noqa: F401 -- and the list of them
