"""Runs in progress (``benchlab/lab/jobs.py``) and the program each run is (``benchlab/runner.py``).

The queue's rules are driven with stand-in processes, which end when the test says: never more at
once than it allows, the rest started in order as runs end; Stop ends one run and nothing else;
how a run ended is read off its answer and its last line. Then real runs of the made-up project,
each its own process as the Lab starts them: the same file as the command line's for the same
settings (``docs/design.md`` §4), a refusal and a crash in their own words, a piece's print kept
off the answer, a stopped run that saves nothing.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from benchlab import cli
from benchlab.lab import jobs
from benchlab.runner import planned
from tests.stand_ins import Process, settled

SAVED = '{"saved": "results/wave/x.json"}'


def _queue(at_once: int) -> tuple[jobs.Queue, list[Process]]:
    started: list[Process] = []

    def start(_run: jobs.Run) -> Process:
        started.append(Process())
        return started[-1]

    return jobs.Queue(at_once=at_once, start=start), started


def _states(queue: jobs.Queue) -> list[str]:
    return [r.state for r in queue.runs()]


def _submit(queue: jobs.Queue, name: str = "s", *words: str, sweep: str = "") -> list[jobs.Run]:
    return queue.submit("wave", planned(name, list(words), [sweep] if sweep else []),
                        root=".", out_dir="results")


# --- the queue, on stand-in processes --------------------------------------------------------

def test_never_more_run_at_once_than_allowed_and_the_rest_start_in_order() -> None:
    queue, started = _queue(2)
    runs = _submit(queue, "s", sweep="frequency=1,2,3")
    assert [r.name for r in runs] == ["s-frequency-1", "s-frequency-2", "s-frequency-3"]
    assert _states(queue) == ["running", "running", "queued"] and len(started) == 2
    started[0].end(0, SAVED)
    settled(lambda: _states(queue) == ["done", "running", "running"], lambda: _states(queue))
    assert runs[0].saved == "results/wave/x.json" and len(started) == 3


def test_stop_ends_that_run_alone_and_the_next_starts() -> None:
    """``docs/design.md`` §4: Stop ends that process and nothing else."""
    queue, started = _queue(2)
    runs = _submit(queue, "s", sweep="seed=1,2,3")
    assert _states(queue) == ["running", "running", "queued"]
    assert queue.stop(runs[0].id) is True and started[0].terminated == 1
    settled(lambda: _states(queue) == ["stopped", "running", "running"], lambda: _states(queue))
    assert started[1].terminated == 0, "the run beside it goes on"
    assert queue.stop(runs[0].id) is False, "a run that ended cannot be stopped"
    started[1].end(0, SAVED)
    settled(lambda: runs[1].state == "done", lambda: _states(queue))
    queue.stop_all()


def test_a_queued_run_stopped_never_starts() -> None:
    queue, started = _queue(1)
    first, second = _submit(queue, "a"), _submit(queue, "b")
    assert queue.stop(second[0].id) is True and second[0].state == "stopped"
    started[0].end(0, SAVED)
    settled(lambda: first[0].state == "done", lambda: _states(queue))
    assert len(started) == 1 and second[0].started is None


def test_a_run_stopped_too_late_to_stop_it_reads_done() -> None:
    """It saved its record before the signal reached it: the strip must not say Stopped beside
    a record on disk."""
    queue, started = _queue(1)
    [run] = _submit(queue)
    started[0].returncode, started[0].out = 0, SAVED          # ended, not yet read
    assert queue.stop(run.id) is True and started[0].terminated == 1
    started[0].ended.set()
    settled(lambda: run.state == "done", lambda: _states(queue))


@pytest.mark.parametrize("code, out, err, state, words", [
    (0, SAVED, "", "done", ""),
    (-15, SAVED, "", "done", ""),                  # answered before the signal: its record is whole
    (-9, "", "UserWarning: Solution may be inaccurate.\n  self.problem.solve()\n", "failed",
     "ended by signal SIGKILL"),
    (1, "", "Traceback (most recent call last):\n  ...\nRuntimeError: boom\n", "failed",
     "RuntimeError: boom"),
    (1, "", "Number parameter 'Config.amplitude' must be at least 0.0, not -1.0.\n", "failed",
     "Number parameter 'Config.amplitude' must be at least 0.0, not -1.0."),
    (0, "not an answer", "", "failed", "its answer could not be read"),
    (0, "", "", "failed", "ended with exit 0"),
    (-9, "", "", "failed", "ended by signal SIGKILL"),
])
def test_how_a_run_ended_is_read_off_its_answer_and_its_last_line(code, out, err, state,
                                                                   words) -> None:
    queue, started = _queue(1)
    [run] = _submit(queue)
    started[0].end(code, out, err)
    settled(lambda: run.finished, lambda: _states(queue))
    assert run.state == state and words in run.error and run.ended is not None


def test_a_process_that_cannot_start_fails_in_its_words_and_the_next_still_starts() -> None:
    tries: list[str] = []

    def start(run: jobs.Run) -> Process:
        tries.append(run.name)
        if run.name == "a":
            raise OSError("no such interpreter")
        return Process()

    queue = jobs.Queue(at_once=1, start=start)
    first, second = queue.submit("wave", [("a", []), ("b", [])], root=".", out_dir="results")
    assert first.state == "failed" and first.error == "could not start: no such interpreter"
    assert second.state == "running" and tries == ["a", "b"], "in the same submit"
    queue.stop_all()


class _Unreadable(Process):
    """A process whose end cannot be read: reading its pipes fails, as a broken pipe's would."""

    def communicate(self) -> tuple[str, str]:
        raise OSError(5, "Input/output error")


def test_a_run_whose_end_cannot_be_read_fails_saying_so_and_its_process_is_ended(
        monkeypatch) -> None:
    """Not left Running for ever, nor its process running unseen, nor the next run waiting; and
    the reason is raised on, to the Lab's console, not swallowed."""
    raised: list[BaseException] = []
    monkeypatch.setattr(threading, "excepthook", lambda args: raised.append(args.exc_value))
    started: list[Process] = []

    def start(_run: jobs.Run) -> Process:
        started.append(Process() if started else _Unreadable())
        return started[-1]

    queue = jobs.Queue(at_once=1, start=start)
    first, second = queue.submit("wave", [("a", []), ("b", [])], root=".", out_dir="results")
    settled(lambda: raised and second.state == "running", lambda: (_states(queue), raised))
    assert first.state == "failed", _states(queue)
    assert first.error == "its end could not be read: OSError(5, 'Input/output error')"
    assert started[0].terminated == 1, "its process ended, not left running unseen"
    assert [type(e) for e in raised] == [OSError]
    queue.stop_all()


def test_only_a_finished_run_is_taken_off_the_list() -> None:
    queue, started = _queue(1)
    [run] = _submit(queue)
    assert queue.dismiss(run.id) is False
    started[0].end(0, SAVED)
    settled(lambda: run.finished, lambda: _states(queue))
    version = queue.version
    assert queue.dismiss(run.id) is True and queue.runs() == [] and queue.version > version


@pytest.mark.parametrize("name, words, error", [
    ("s", ["nope=1"], "'nope' is not a setting of wave"),
    ("a b", [], "cannot name a record"),
    ("--x", [], "cannot name a record"),
])
def test_every_word_is_checked_before_any_run_is_queued(name, words, error) -> None:
    queue, started = _queue(2)
    with pytest.raises(ValueError, match=error):
        _submit(queue, name, *words)
    assert queue.runs() == [] and started == []


@pytest.mark.parametrize("name, opened", [
    ("amplitude", {}), ("frequency", {}), ("samples", {}), ("noise", {}), ("seed", {}),
    ("delay", {}), ("duty", {"shape": "square"}),
])
def test_the_lab_refuses_a_value_exactly_when_the_settings_would(name, opened) -> None:
    """The one rule the Lab restates (:func:`jobs.refusals`), held to its source: for values at,
    just inside and just outside each declared bound, NaN, both infinities and text that is no
    number, the Lab refuses exactly when reading the text as the run does and building the Config
    with it raises -- which only a test may do. ``opened``: the gate the setting needs, open."""
    from benchlab.record.config import coerce_value
    from tests.toy.wave import Config
    p = Config.param[name]
    texts = ["nan", "inf", "-inf", "2.5", "fast", "0", "-1"]
    for bound in p.bounds or ():
        if bound is not None:
            texts += [repr(bound), repr(bound - 1e-9), repr(bound + 1e-9), str(bound - 1),
                      str(bound + 1)]
    for text in texts:
        said = jobs.refusals("wave", {name: text})[0].get(name, "")
        try:
            Config(**opened, **{name: coerce_value(p, text)})
        except ValueError:
            assert said, (name, text, "the settings refuse it; the Lab took it")
        else:
            assert not said, (name, text, said)


def test_a_name_a_run_in_progress_writes_is_refused_until_it_ends() -> None:
    """Two runs saving one record at once lose one, or leave it unreadable (2a review)."""
    queue, started = _queue(2)
    _submit(queue, "same")
    with pytest.raises(ValueError, match=r"^same is queued or running already; give this run "
                                         r"another name$"):
        _submit(queue, "same", "amplitude=3")
    with pytest.raises(ValueError, match="is queued or running already"):
        queue.check_free("wave", ["other", "same"], root=".", out_dir="results")
    assert queue.in_progress("wave", ".", "results") == {"same"} and len(started) == 1
    queue.check_free("wave", ["same"], root=".", out_dir="elsewhere")     # another out-dir: free
    started[0].end(0, SAVED)
    settled(lambda: queue.runs()[0].finished, lambda: _states(queue))
    _submit(queue, "same", "amplitude=3")                # ended: its name may be run again
    queue.stop_all()


def test_the_line_a_run_prints_is_the_side_door_command_that_makes_the_same_record() -> None:
    queue, _started = _queue(1)
    [run] = _submit(queue, "s", "amplitude=2", sweep="frequency=3")
    assert run.line == "uv run toy run wave --set amplitude=2 --set frequency=3 --name s-frequency-3"
    queue.stop_all()


# --- real runs, each its own process ---------------------------------------------------------

def _real(at_once: int = 4) -> jobs.Queue:
    return jobs.Queue(at_once=at_once)


def _ended(queue: jobs.Queue) -> None:
    settled(lambda: all(r.finished for r in queue.runs()),
            lambda: [(r.name, r.state, r.error) for r in queue.runs()], timeout=60)


def test_the_lab_and_the_side_door_write_the_same_file(tmp_path, toy_installed) -> None:
    """``docs/design.md`` §4: the same settings run from the Lab and from the side door give
    identical files, provenance aside (its date and duration differ by nature)."""
    words = ["amplitude=2", "noise=0.3", "seed=4", "shape=square"]
    queue = _real()
    [run] = queue.submit("wave", planned("lab", words), root=str(tmp_path), out_dir="results")
    _ended(queue)
    assert run.state == "done", run.error
    assert cli.main(["run", "wave", *[w for item in words for w in ("--set", item)],
                     "--name", "side", "--out-dir", str(tmp_path / "results")]) == 0
    lab, side = (json.loads((tmp_path / "results" / "wave" / f"{n}.json").read_text())
                 for n in ("lab", "side"))
    for record in (lab, side):
        record.pop("provenance"), record.pop("name")
    assert lab == side


def test_a_refusal_and_a_crash_end_failed_in_their_own_words(tmp_path, toy_installed) -> None:
    """The words are the run's last line, so whatever it printed before must come before them,
    and a refusal written over several lines is kept whole, on one."""
    queue = _real()
    refused, crashed, long = (
        queue.submit("wave", planned(n, w), root=str(tmp_path), out_dir="results")[0]
        for n, w in (("refused", ["amplitude=-1"]), ("crashed", ["fail=crash", "noisy=true"]),
                     ("long", ["fail=refuse", "noisy=true"])))
    _ended(queue)
    assert refused.state == "failed" and refused.error == (
        "Number parameter 'Config.amplitude' must be at least 0.0, not -1.0.")
    assert crashed.state == "failed" and crashed.error == "RuntimeError: the wave was told to fail"
    assert long.state == "failed" and long.error == (
        "no Record record at results/wave/gone.json. Run it first: uv run toy run wave which "
        "writes that file.")
    assert not (tmp_path / "results" / "wave").exists(), "none saved a record"


def test_a_piece_that_prints_even_a_byte_utf8_has_no_word_for_does_not_confuse_the_answer(
        tmp_path, toy_installed) -> None:
    queue = _real()
    [run] = queue.submit("wave", planned("noisy", ["noisy=true"]), root=str(tmp_path),
                         out_dir="results")
    _ended(queue)
    assert run.state == "done", run.error
    assert Path(tmp_path, run.saved).is_file() and run.saved.endswith("wave/noisy.json")


def test_a_stopped_run_saves_nothing(tmp_path, toy_installed) -> None:
    queue = _real()
    [run] = queue.submit("wave", planned("long", ["delay=60"]), root=str(tmp_path),
                         out_dir="results")
    assert run.state == "running" and queue.stop(run.id) is True
    _ended(queue)
    assert run.state == "stopped" and run.process.returncode != 0
    assert not (tmp_path / "results" / "wave").exists()


def test_a_sweep_runs_side_by_side(tmp_path, toy_installed) -> None:
    """Three runs that each wait 3 s end within 8 s: one after another they need at least 9."""
    queue = _real(at_once=3)
    runs = queue.submit("wave", planned("sw", ["delay=3"], ["seed=1,2,3"]), root=str(tmp_path),
                        out_dir="results")
    assert [r.state for r in runs] == ["running"] * 3
    _ended(queue)
    assert [r.state for r in runs] == ["done"] * 3
    took = max(r.ended for r in runs) - min(r.started for r in runs)
    assert took < 8, f"{took:.1f} s: they did not run together"


_LAB_WITH_A_LONG_RUN = """
import sys, time
from benchlab.lab import cli, jobs
from benchlab.runner import planned
cli.stop_runs_on_sigterm()
[run] = jobs.QUEUE.submit("wave", planned("long", ["delay=60"]), root=sys.argv[1], out_dir="results")
print(run.process.pid, flush=True)
if sys.argv[2] == "wait":
    time.sleep(60)
"""


def _gone(pid: int, timeout: float = 10.0) -> bool:
    """Whether process ``pid`` is gone, asked at once and then until ``timeout``."""
    deadline = time.time() + timeout
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.1)


@pytest.mark.parametrize("how", ["exits", "is sent SIGTERM"])
def test_when_the_lab_ends_its_runs_end_with_it(tmp_path, toy_installed, how) -> None:
    """A Lab that ends, by its own exit or by SIGTERM, leaves no run going without it."""
    lab = subprocess.Popen([sys.executable, "-c", _LAB_WITH_A_LONG_RUN, str(tmp_path),
                            "wait" if how == "is sent SIGTERM" else "exit"],
                           stdout=subprocess.PIPE, text=True)
    pid = int(lab.stdout.readline())
    if how == "is sent SIGTERM":
        time.sleep(0.5)
        lab.send_signal(signal.SIGTERM)
    lab.wait(30)
    try:
        assert _gone(pid), f"the run {pid} outlived the Lab"
    finally:
        if not _gone(pid, 0):
            os.kill(pid, signal.SIGKILL)
