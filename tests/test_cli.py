"""The command line, driven on the made-up project as a person types it: a run saves one record per
sweep value and prints where, a draw writes each panel as a still with its sidecar, and a refusal
is said in the project's own command."""

from __future__ import annotations

import json
import os

import pytest

from runlab import cli


def _run(out, *words: str) -> None:
    assert cli.main(["run", "wave", *words, "--out-dir", str(out)]) == 0


def test_the_command_is_the_projects_and_its_pieces_are_the_choices() -> None:
    parser = cli.build_parser()
    assert parser.prog == "toy"
    assert parser.description.startswith("``toy``: run a piece, draw its records, list its "
                                         "settings.")
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "bogus"])


def test_a_run_saves_its_record_and_prints_its_path_and_numbers(tmp_path, capsys) -> None:
    _run(tmp_path, "--set", "amplitude=2", "--name", "probe")
    path = tmp_path / "wave" / "probe.json"
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == str(path)
    assert [line.split(" = ")[0] for line in lines[1:]] == ["  rms_u", "  rms_y"]
    raw = json.loads(path.read_text())
    assert raw["component"] == "wave" and raw["name"] == "probe"
    assert raw["config"]["amplitude"] == 2.0 and raw["numbers"]["rms_u"] == pytest.approx(2 ** 0.5,
                                                                                          rel=0.05)


def test_a_sweep_saves_one_record_per_value(tmp_path) -> None:
    _run(tmp_path, "--sweep", "frequency=1,3", "--sweep", "shape=sine,square")
    assert sorted(os.listdir(tmp_path / "wave")) == [
        f"default-frequency-{f}-shape-{s}.json" for f in (1, 3) for s in ("sine", "square")]


def test_a_refusal_is_said_in_the_projects_command(tmp_path) -> None:
    with pytest.raises(SystemExit, match=r"^toy: unknown setting 'nope'"):
        _run(tmp_path, "--set", "nope=1")
    with pytest.raises(SystemExit, match=r"^toy: Number parameter 'Config\.amplitude' must be at "
                                         r"least 0\.0, not -1\.0"):
        _run(tmp_path, "--set", "amplitude=-1")


def test_a_draw_writes_each_panel_beside_the_record_with_its_sidecar(tmp_path) -> None:
    _run(tmp_path, "--name", "a")
    record = tmp_path / "wave" / "a.json"
    assert cli.main(["draw", str(record)]) == 0
    folder = tmp_path / "wave" / "a"
    assert sorted(os.listdir(folder)) == ["u.png", "u.png.json", "y.png", "y.png.json"]
    sidecar = json.loads((folder / "y.png.json").read_text())
    assert sidecar["figure"] == "y.png" and sidecar["runs"] == ["a"] and sidecar["git_sha"]


def test_settings_lists_a_pieces_settings_under_their_groups(capsys) -> None:
    """A line per setting: the variable ``--set`` takes, the name the piece gives it, its unit,
    its default, its range, its choices, its description."""
    assert cli.main(["settings", "lag"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:4] == ["", "Source", "  drive \"Drive\" = 'saved' one of ['saved', 'built']: "
                                       "The u that drives the lag: a saved wave run's, or a wave "
                                       "built here.",
                         "  wave_run \"Wave run\" = 'results/wave/default.json': "
                         "The saved wave run whose u drives the lag."]
    assert "  wave.shape \"Shape\" = 'sine' one of ['sine', 'square']: The wave's shape." in lines, \
        "a setting inside the built wave, by its dotted name"
    assert not any(line.startswith("  wave.seed") for line in lines), "its noise is not composed"
    assert "  tau \"τ\" [s] = 0.05 in (0 … ∞): The lag's time constant." in lines
    assert ("  hold \"Hold\" = None one of ['exact', 'euler']: How the lag is sampled; none: "
            "exact.") in lines
    groups = [line for line in lines if line and not line.startswith(" ")]
    assert groups[:3] == ["Source", "Built wave · Wave", "Lag"], "each group once, where it first comes"
    assert cli.main(["settings", "wave"]) == 0
    wave = {line.split()[0]: line for line in capsys.readouterr().out.splitlines() if line[:2] == "  "}
    assert " = 40 in [2 … ∞):" in wave["samples"] and " = 0.5 in (0 … 1):" in wave["duty"]
    assert " in " not in wave["shape"].split(":")[0], "no range, nothing new"
    with pytest.raises(SystemExit):
        cli.main(["settings", "no-such-piece"])


def test_a_draw_of_a_run_whose_file_differs_draws_it_and_says_how(tmp_path, capsys) -> None:
    """A file that holds more than its piece reads now is drawn all the same. How it differs is
    said on the error stream, so the output stream still holds only what was drawn."""
    _run(tmp_path, "--name", "a")
    record = tmp_path / "wave" / "a.json"
    raw = json.loads(record.read_text())
    raw["provenance"]["python"] = "3.11.9"
    raw["mood"] = [1, 2]
    record.write_text(json.dumps(raw))
    capsys.readouterr()
    assert cli.main(["draw", str(record)]) == 0
    said = capsys.readouterr()
    assert "a: its result also holds mood" in said.err
    assert "a: its provenance also holds python" in said.err
    assert "also holds" not in said.out
    assert sorted(os.listdir(tmp_path / "wave" / "a")) == ["u.png", "u.png.json", "y.png",
                                                            "y.png.json"]


def test_runs_that_differ_in_their_seed_alone_are_drawn_pooled(tmp_path) -> None:
    _run(tmp_path, "--set", "noise=0.5", "--sweep", "seed=1,2,3", "--name", "n")
    records = sorted(str(p) for p in (tmp_path / "wave").glob("*.json"))
    out = tmp_path / "drawn"
    assert cli.main(["draw", *records, "--panel", "y", "--runs", "mean", "--out-dir", str(out)]) == 0
    sidecar = json.loads((out / "y.png.json").read_text())
    assert sidecar["traces"] == ["Mean of 3 runs · y"] and sidecar["shaping"] == {"runs": "mean"}


def test_a_number_is_drawn_against_a_setting(tmp_path) -> None:
    _run(tmp_path, "--sweep", "amplitude=1,2,4")
    records = sorted(str(p) for p in (tmp_path / "wave").glob("*.json"))
    out = tmp_path / "drawn"
    assert cli.main(["draw", *records, "--number", "rms_u", "--vs", "amplitude",
                     "--out-dir", str(out)]) == 0
    sidecar = json.loads((out / "rms_u-vs-amplitude.png.json").read_text())
    assert sidecar["x_label"] == "A" and sidecar["number"] == "rms_u"


@pytest.mark.parametrize("words, error", [
    (["--sweep", "frequency=1,1"], r"^toy: --sweep 'frequency=1,1' repeats a value"),
    (["--set", "frequency=1", "--sweep", "frequency=2,3"], r"^toy: 'frequency' is given twice"),
    (["--sweep", "frequency="], r"^toy: --sweep expects SETTING=V1,V2,..."),
])
def test_a_sweep_is_refused_in_the_projects_command_by_the_runner_s_rule(tmp_path, words,
                                                                        error) -> None:
    """The sweep's rule is the runner's (``runlab.runner.planned``), which the Lab uses too."""
    with pytest.raises(SystemExit, match=error):
        _run(tmp_path, *words)
    assert not (tmp_path / "wave").exists()
