"""A run saved by any released version is still listed, read and drawn (``CLAUDE.md``, "The run
file is a contract with every project"). ``tests/runs/`` holds one run of the made-up project's
wave from every release, each made by that release's own code at its tag; a release adds its
own once it is tagged."""

from __future__ import annotations

import json
import shutil
from importlib.metadata import version
from pathlib import Path

import pytest

from runlab.lab import state
from runlab.project import get_component
from runlab.testing import check_project


def _release(path: Path) -> tuple[int, ...]:
    return tuple(int(part) for part in path.stem.removeprefix("v").split("."))


RUNS = sorted((Path(__file__).parent / "runs").glob("v*.json"), key=_release)
#: The made-up project's own files: what ``check_project`` reads for what a project imports.
TOY = Path(__file__).parent / "toy"
#: How each archived run's file departs from the wave of today, as the list words it: the wave
#: gained ``draws`` in 0.14, so every run of an earlier release predates it.
NOTES = {"v0.1.0": ["predates the settings delay, draws, duty, fail, noisy: today's defaults "
                    "are read"],
         "v0.2.0": ["predates the settings draws, duty: today's defaults are read"]}
_DRAWS = ["predates the setting draws: today's default is read"]


def test_the_archive_holds_the_release_before_this_one() -> None:
    """Every release from 0.1.0, none skipped; the newest is this version or the one before it,
    so a version raised without its predecessor's run archived fails here."""
    held = [_release(path) for path in RUNS]
    assert held == [(0, minor, 0) for minor in range(1, len(held) + 1)], held
    major, minor = (int(part) for part in version("benchlab").split(".")[:2])
    assert held[-1][:2] in {(major, minor), (major, minor - 1)}, \
        f"this is {major}.{minor}; the newest run archived is of {held[-1]}"


@pytest.mark.parametrize("path", RUNS, ids=[path.stem for path in RUNS])
def test_a_run_of_a_release_is_listed_read_and_drawn(path: Path, tmp_path) -> None:
    folder = tmp_path / "results" / "wave"
    folder.mkdir(parents=True)
    held = Path(shutil.copy(path, folder / path.name))
    [row] = state.records(str(tmp_path), "results")
    assert row["stale"] == ""
    assert row["notes"] == NOTES.get(path.stem, _DRAWS if _release(path) < (0, 14, 0) else [])
    assert row["panels"] == ["u", "y"]
    raw = json.loads(held.read_text())
    assert raw["provenance"]["versions"]["benchlab"] == path.stem.removeprefix("v"), \
        "made by the release it is named after"
    assert raw["provenance"]["git_dirty"] is False
    record = get_component("wave").Record.load(held)
    assert record.numbers == raw["numbers"]
    assert [s.name for s in record.series()] == ["u", "y"]
    check_project(runs=[held], sources=[TOY])       # every chart it declares draws
