"""The files a run writes beside its run file (``benchlab/record/files.py``), on the made-up
``fit``: they are kept in the run's folder and listed in its run file, a later run reads them,
they go with the run, and a run that writes none saves what it saved before."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

import benchlab
from benchlab import cli
from benchlab.lab import jobs, state, view
from benchlab.runner import planned
from benchlab.testing import check_project
from tests.stand_ins import settled
from tests.test_runner import _ended, _real
from tests.toy import fit

TOY = Path(fit.__file__).parent
LISTED = [{"name": "checkpoints/half.npy", "bytes": 144}, {"name": "weights.npy", "bytes": 144}]


def _fit(out: Path, name: str, *words: str) -> Path:
    cli.main(["run", "fit", "--name", name, "--out-dir", str(out),
              *[w for item in words for w in ("--set", item)]])
    return out / "fit" / f"{name}.json"


def test_a_runs_files_are_kept_beside_its_run_file_and_listed_in_it(tmp_path, capsys) -> None:
    path = _fit(tmp_path, "one")
    folder = tmp_path / "fit" / "one.files"
    assert f"  files in {folder}\n" in capsys.readouterr().out
    assert sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()) \
        == ["checkpoints/half.npy", "weights.npy"]
    assert json.loads(path.read_text())["files"] == LISTED
    record = fit.Record.load(path)
    assert np.load(folder / "weights.npy").tolist() == [record.numbers["w0"], record.numbers["w1"]]
    assert sorted(p.name for p in (tmp_path / "fit").iterdir()) == ["one.files", "one.json"]


def test_a_run_that_writes_no_file_saves_no_list_and_keeps_no_folder(tmp_path, capsys) -> None:
    cli.main(["run", "wave", "--out-dir", str(tmp_path)])
    assert "files in" not in capsys.readouterr().out
    assert "files" not in json.loads((tmp_path / "wave" / "default.json").read_text())
    assert [p.name for p in (tmp_path / "wave").iterdir()] == ["default.json"]


def test_a_later_run_starts_from_an_earlier_runs_file(tmp_path) -> None:
    first = _fit(tmp_path, "first", "steps=6")
    second = fit.Record.load(_fit(tmp_path, "second", "steps=6", f"start_from={first}"))
    whole = fit.Record.load(_fit(tmp_path, "whole", "steps=12"))
    assert second.numbers == pytest.approx(whole.numbers, rel=1e-12)
    assert benchlab.files_of(first) == tmp_path / "fit" / "first.files"


def test_a_run_that_fails_leaves_the_earlier_run_of_its_name_whole(tmp_path) -> None:
    path = _fit(tmp_path, "one")
    before = path.read_bytes(), (tmp_path / "fit" / "one.files" / "weights.npy").read_bytes()
    with pytest.raises(RuntimeError, match="the fit was told to fail"):
        _fit(tmp_path, "one", "slope=5", "fail=true")
    assert (path.read_bytes(), (tmp_path / "fit" / "one.files" / "weights.npy").read_bytes()) \
        == before
    assert sorted(p.name for p in (tmp_path / "fit").iterdir()) == ["one.files", "one.json"]


def test_a_run_again_under_one_name_replaces_the_folder(tmp_path) -> None:
    _fit(tmp_path, "one")
    (tmp_path / "fit" / "one.files" / "left-over.txt").write_text("from the earlier run")
    path = _fit(tmp_path, "one", "slope=5")
    assert json.loads(path.read_text())["files"] == LISTED
    assert not (tmp_path / "fit" / "one.files" / "left-over.txt").exists()


def test_the_folder_is_refused_in_words_where_there_is_none(tmp_path) -> None:
    with pytest.raises(LookupError, match="no run is in progress"):
        benchlab.run_files()
    with pytest.raises(LookupError, match="no run is in progress"):
        fit.run(fit.Config())
    with pytest.raises(FileNotFoundError, match="no run file at"):
        benchlab.files_of(tmp_path / "absent.json")
    cli.main(["run", "wave", "--out-dir", str(tmp_path)])
    with pytest.raises(FileNotFoundError, match="wrote no file"):
        benchlab.files_of(tmp_path / "wave" / "default.json")


def test_the_lab_and_the_side_door_keep_the_same_files(tmp_path, toy_installed) -> None:
    queue = _real()
    [run] = queue.submit("fit", planned("lab", ["slope=3"]), root=str(tmp_path), out_dir="results")
    _ended(queue)
    assert run.state == "done", run.error
    _fit(tmp_path / "results", "side", "slope=3")
    lab, side = (tmp_path / "results" / "fit" / f"{n}.files" for n in ("lab", "side"))
    for name in ("weights.npy", "checkpoints/half.npy"):
        assert (lab / name).read_bytes() == (side / name).read_bytes()
    held = [json.loads((tmp_path / "results" / "fit" / f"{n}.json").read_text())["files"]
            for n in ("lab", "side")]
    assert held == [LISTED, LISTED]


def test_a_run_stopped_or_crashed_in_the_lab_leaves_no_folder(tmp_path, toy_installed) -> None:
    queue = _real()
    stopped, crashed = (
        queue.submit("fit", planned(n, w), root=str(tmp_path), out_dir="results")[0]
        for n, w in (("stopped", ["delay=60"]), ("crashed", ["fail=true"])))
    waiting = tmp_path / "results" / "fit" / "stopped.files.partial" / "weights.npy"
    settled(waiting.is_file, lambda: "the fit never wrote its weights")
    assert queue.stop(stopped.id) is True
    _ended(queue)
    assert (stopped.state, crashed.state) == ("stopped", "failed")
    assert crashed.error == "RuntimeError: the fit was told to fail"
    left = lambda: list((tmp_path / "results" / "fit").iterdir())
    settled(lambda: not left(), left)       # a stopped run reads stopped before its process ends


def test_deleting_a_run_takes_its_folder_and_says_so(tmp_path) -> None:
    out = tmp_path / "results"
    _fit(out, "one"), _fit(out, "two")
    gone = jobs.delete("fit", records=["one"], root=str(tmp_path), out_dir="results")
    assert gone == [os.path.join("results", "fit", "one.json"),
                    os.path.join("results", "fit", "one.files") + os.sep]
    assert sorted(p.name for p in (out / "fit").iterdir()) == ["two.files", "two.json"]


def test_the_page_lists_each_runs_files_by_size_and_says_which_is_gone(tmp_path) -> None:
    out = tmp_path / "results"
    _fit(out, "one"), _fit(out, "two")
    cli.main(["run", "wave", "--out-dir", str(out)])
    (out / "fit" / "two.files" / "weights.npy").unlink()
    (out / "fit" / "one.files" / "weights.npy").write_bytes(b"x" * 2500)   # the list is the run file's
    rows = {r["name"]: r for r in state.records(str(tmp_path), "results")}
    assert rows["default"]["files"] == []
    assert rows["one"]["files"] == [{**f, "there": True} for f in LISTED]
    assert [f["there"] for f in rows["two"]["files"]] == [True, False]
    table = view.compare_rows([rows["one"], rows["two"], rows["default"]], [])
    assert [(r["kind"], r["term"], r["values"], r["differs"]) for r in table[-3:]] == [
        ("head", "Files", [], False),
        ("file", "checkpoints/half.npy", ["144 B", "144 B", "—"], True),
        ("file", "weights.npy", ["144 B", "144 B, no longer there", "—"], True)]
    assert not any(r["kind"] == "file" for r in view.compare_rows([rows["default"]], []))
    assert [view.size(n) for n in (0, 999, 1440, 3_200_000, 5_000_000_000)] \
        == ["0 B", "999 B", "1.44 kB", "3.2 MB", "5 GB"]


def test_the_check_refuses_a_run_whose_listed_file_is_gone_or_of_another_size(tmp_path) -> None:
    path = _fit(tmp_path, "one")
    check_project(runs=[path], sources=[TOY])
    weights = tmp_path / "fit" / "one.files" / "weights.npy"
    weights.write_bytes(b"short")
    with pytest.raises(AssertionError, match=r"lists 'weights.npy' at 144 bytes; .* holds 5"):
        check_project(runs=[path], sources=[TOY])
    weights.unlink()
    with pytest.raises(AssertionError, match=r"lists the file 'weights.npy'; there is no "):
        check_project(runs=[path], sources=[TOY])
