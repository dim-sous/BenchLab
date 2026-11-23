"""Re-fly (1.12): a saved run flown again from its own settings and seed. When every value its file
holds comes back the same, what the file lacks is added and the re-flight is written under its
provenance; otherwise nothing is written and what differs is said. Carried from RCWS's ``sim run
--refly``."""

from __future__ import annotations

import json

import pytest

from runlab import cli
from runlab.refly import refly
from tests.toy import wave


@pytest.fixture
def saved(tmp_path):
    cli.main(["run", "wave", "--name", "w", "--out-dir", str(tmp_path),
              "--set", "noise=0.2", "--set", "seed=3"])
    return tmp_path / "wave" / "w.json"


def test_a_run_whose_file_lacks_a_field_is_made_whole_by_flying_it_again(saved) -> None:
    whole = json.loads(saved.read_text())
    cut = json.loads(saved.read_text())
    del cut["y"]
    del cut["config"]["draws"]
    saved.write_text(json.dumps(cut))
    found = refly(saved)
    assert found.matches and found.fields == ("y",) and found.settings == ("draws",)
    back = json.loads(saved.read_text())
    assert back["y"] == whole["y"] and back["config"]["draws"] == whole["config"]["draws"]
    [filled] = back["provenance"]["filled"]
    assert filled["fields"] == ["y"] and filled["settings"] == ["draws"]
    assert wave.Record.load(saved).y.shape == (40,), "it reads whole"


def test_a_run_whose_values_no_longer_come_back_is_left_as_it_is_and_the_difference_said(
        saved, capsys) -> None:
    held = json.loads(saved.read_text())
    held["u"][5] += 1.0
    saved.write_text(json.dumps(held))
    before = saved.read_text()
    assert cli.main(["run", "wave", "--refly", str(saved)]) == 3
    assert saved.read_text() == before, "nothing written"
    said = capsys.readouterr().out
    assert "not written" in said and "u: largest difference 1 at [5]" in said


def test_refly_takes_no_other_settings_and_a_run_of_its_own_piece(saved) -> None:
    with pytest.raises(SystemExit, match="give it no config"):
        cli.main(["run", "wave", "--refly", str(saved), "--set", "seed=1"])
    with pytest.raises(SystemExit, match="is a run of 'wave', not 'fit'"):
        cli.main(["run", "fit", "--refly", str(saved)])


def test_the_page_queues_a_reflight_as_a_run_of_its_own(saved, monkeypatch) -> None:
    """1.12, the page's re-fly: a run of its own in the runs in progress, the runner's own
    program given the saved run's path; a second re-flight of a run already queued is refused."""
    import subprocess

    from runlab.lab import jobs
    from tests.stand_ins import Process

    started = []
    queue = jobs.Queue(start=lambda run: started.append(run) or Process())
    run = queue.submit_refly("wave", "w", str(saved), root=str(saved.parent.parent))
    assert run.refly == str(saved) and started == [run]
    with pytest.raises(ValueError):
        queue.submit_refly("wave", "w", str(saved), root=str(saved.parent.parent))
    seen = []
    monkeypatch.setattr(subprocess, "Popen", lambda argv, **kw: seen.append(argv))
    jobs.start_process(run)
    assert seen[0][-3:] == ["runlab.runner", "--refly", str(saved)]
    queue.stop_all()
