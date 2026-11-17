"""Runs in progress: each run its own process, queued and started by the Lab, never more at once
than the machine has cores (``docs/design.md`` decision 3 and §4).

A run is the program ``python -m runlab.runner`` (:mod:`runlab.runner`) under the Lab's own
interpreter, in the project root: the Lab never goes through the command line. A run moves
``queued`` -> ``running`` -> ``done`` | ``failed`` | ``stopped``; ``queued`` -> ``stopped`` (never
started) or ``failed`` (could not start); and ``stopped`` -> ``done`` when its process had saved
its record before the Stop reached it. A run reads Stopped as soon as Stop is pressed, before its
process has ended. Two runs of one record never go at once: a name already queued or running is
refused. The queue is the Lab's, one per process: every browser tab shows the same runs, and
when the Lab stops, whatever still runs is stopped with it.

Every word that becomes a run is checked against a declaration this module read (the registry,
:func:`runlab.record.config.fields_of`); what the run makes of it is the runner's, refusals
included, and a failed run says so in the last line it wrote. One rule is restated, and held to
its source by a test: a typed value outside the bounds its setting declares, or one its setting
cannot read, is refused before any run is queued (:func:`refusals`, ``docs/design.md``
decision 5), in param's own comparisons; the piece's Config is still never built.
"""

from __future__ import annotations

import atexit
import itertools
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

import param

from runlab.cli import DEFAULT_OUT_DIR
from runlab.project import command, get_component, piece_names
from runlab.record.config import coerce_value, fields_of
from runlab.record.files import discard, kept

from .form import as_text
from .words import say, say_n

QUEUED, RUNNING, DONE, FAILED, STOPPED = "queued", "running", "done", "failed", "stopped"

#: A record's name: letters, digits, '.', '_' or '-', starting with a letter or digit, so it
#: can never read as a flag, a path or a second word.
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def line_of(argv: Sequence[str]) -> str:
    """The argv as one typeable line; ``shlex.split`` of it gives the argv back."""
    return shlex.join(argv)


def _piece(piece: str) -> str:
    if piece not in piece_names():
        raise ValueError(f"unknown piece {piece!r}; registered: {list(piece_names())}")
    return piece


def _setting(item: str, piece: str, names: set[str]) -> str:
    key, sep, value = item.partition("=")
    if not sep or not key or not value:
        raise ValueError(f"{item!r} is not SETTING=VALUE")
    if key not in names:
        raise ValueError(f"{key!r} is not a setting of {piece}; its settings: {sorted(names)}")
    return item


def _name(name: str) -> str:
    if not _NAME.match(name or ""):
        raise ValueError(say("form.bad_name", name=repr(name)))
    return name


def checked(piece: str, planned: Sequence[tuple[str, Sequence[tuple[str, str]]]]
            ) -> list[tuple[str, list[tuple[str, str]]]]:
    """``planned`` -- ``(record name, setting pairs)`` per run, as :func:`runlab.runner.planned`
    makes them -- with every word checked against what ``piece`` declares; refused in words."""
    piece = _piece(piece)
    names = {f["name"] for f in fields_of(get_component(piece).Config)}
    out = []
    for name, pairs in planned:
        for key, value in pairs:
            _setting(f"{key}={value}", piece, names)
        out.append((_name(name), [(key, value) for key, value in pairs]))
    return out


def refusals(piece: str, typed: Mapping[str, str], swept: str = "",
             rungs: Sequence[str] = ()) -> tuple[dict[str, str], str]:
    """What ``piece``'s settings refuse before any run is queued (``docs/design.md`` decision
    5): each ``typed`` value, by setting, and the first refused rung of the ``swept`` setting, in
    words; ``({}, "")`` when they take everything. A value is read as the run will read it
    (:func:`runlab.record.config.coerce_value`, on the setting's declaration) and held to the
    bounds the setting declares; the piece's Config is never built."""
    cls = get_component(_piece(piece)).Config
    fields = {f["name"]: f for f in fields_of(cls)}
    by_setting = {name: words for name, text in typed.items()
                  if (words := _refusal(cls.param[name], fields[name], text))}
    sweep = next((words for rung in rungs
                  if (words := _refusal(cls.param[swept], fields[swept], rung))), "") \
        if swept else ""
    return by_setting, sweep


def _refusal(p: param.Parameter, f: dict[str, Any], text: str) -> str:
    """Why the setting ``f`` (declared as ``p``) refuses ``text``, or ``""``: a text its kind
    cannot read, then a value outside its bounds. The bounds are compared as param compares
    them (param 2.4.2, ``Number._validate_bounds``): the upper bound first, ``not v <= high`` for
    an included end and ``not v < high`` for an excluded one, so a NaN is outside every bound."""
    try:
        value = coerce_value(p, text)
    except ValueError as exc:
        label = f["label"]
        if f.get("other"):
            return say("refuse.unread", setting=label, text=text)
        if isinstance(p, param.Integer):
            return say("refuse.whole", setting=label, text=text)
        if isinstance(p, param.Number):
            return say("refuse.number", setting=label, text=text)
        if isinstance(p, param.Boolean):
            return say("refuse.yes_no", setting=label, text=text)
        if isinstance(p, param.Selector):
            return say("refuse.choice", setting=label, text=text,
                       choices=", ".join(as_text(o) for o in p.objects))
        if isinstance(p, param.List):
            return say("refuse.texts" if p.item_type is str else "refuse.numbers",
                       setting=label, text=text)
        return str(exc)
    if not isinstance(p, param.Number) or value is None:
        return ""
    low, high = f["low"], f["high"]
    if high is not None and not (value < high if f["high_exclusive"] else value <= high):
        return say("refuse.below" if f["high_exclusive"] else "refuse.at_most",
                   setting=f["label"], bound=as_text(high), text=text)
    if low is not None and not (value > low if f["low_exclusive"] else value >= low):
        return say("refuse.above" if f["low_exclusive"] else "refuse.at_least",
                   setting=f["label"], bound=as_text(low), text=text)
    return ""


def run_argv(piece: str, overrides: Sequence[str] = (), name: str = "",
             out_dir: str = DEFAULT_OUT_DIR) -> list[str]:
    """``uv run <command> run <piece> [--set K=V]* --name <name> [--out-dir D]``, ``--out-dir``
    only when it is not the command line's default: the side-door command that makes the same
    record as one run. Every word checked."""
    piece = _piece(piece)
    names = {f["name"] for f in fields_of(get_component(piece).Config)}
    argv = ["uv", "run", command(), "run", piece]
    for item in overrides:
        argv += ["--set", _setting(item, piece, names)]
    argv += ["--name", _name(name)]
    if out_dir != DEFAULT_OUT_DIR:
        argv += ["--out-dir", out_dir]
    return argv


def delete(piece: str, records: Sequence[str] = (), *,
           root: str, out_dir: str = DEFAULT_OUT_DIR) -> list[str]:
    """Delete the named records (``<out_dir>/<piece>/<name>.json``), each with the folder of
    files its run wrote (``<name>.files/``), and return what went, as paths under ``root``.
    Anything else is refused in words and nothing is deleted: a name that is not a record's, a
    path outside the out-dir."""
    piece = _piece(piece)
    base = os.path.realpath(os.path.join(root, out_dir, piece))
    targets: list[str] = []
    for name in records:
        path = os.path.join(base, f"{_name(name)}.json")
        if not os.path.isfile(path):
            raise ValueError(say("messages.delete_no_record", name=repr(name),
                                 folder=f"{out_dir}/{piece}/"))
        if not os.path.realpath(path).startswith(base + os.sep):
            raise ValueError(say("messages.delete_outside", path=path, folder=f"{out_dir}/{piece}/"))
        targets.append(path)
    gone: list[str] = []
    for path in targets:
        os.remove(path)
        gone.append(path)
        discard(path)
        if kept(path).is_dir():
            shutil.rmtree(kept(path))
            gone.append(str(kept(path)) + os.sep)
    return [os.path.relpath(path, root) + (os.sep if path.endswith(os.sep) else "")
            for path in gone]


@dataclass
class Run:
    """One run: the piece, the record name and the setting pairs it was given, where it writes,
    and how far it got. ``saved`` is the record's path once done, ``error`` the last line it
    wrote once failed. ``started`` and ``ended`` are read off a clock that never steps back
    (``time.monotonic``): only the time between them is shown."""

    id: int
    piece: str
    name: str
    pairs: list[tuple[str, str]]
    root: str
    out_dir: str
    state: str = QUEUED
    started: Optional[float] = None
    ended: Optional[float] = None
    saved: str = ""
    error: str = ""
    process: Optional[subprocess.Popen] = field(default=None, repr=False)

    @property
    def finished(self) -> bool:
        return self.state in (DONE, FAILED, STOPPED)

    def elapsed(self, now: float) -> float:
        """Seconds it has run, up to ``now`` or to its end; 0 before it starts."""
        if self.started is None:
            return 0.0
        return (self.ended if self.ended is not None else now) - self.started

    @property
    def line(self) -> str:
        """The side-door command that makes the same record."""
        return line_of(run_argv(self.piece, [f"{k}={v}" for k, v in self.pairs], self.name,
                                self.out_dir))


def start_process(run: Run) -> subprocess.Popen:
    """``run`` as its own program: the runner, under this interpreter, in the project root."""
    argv = [sys.executable, "-m", "runlab.runner", run.piece, run.name, run.out_dir,
            json.dumps(run.pairs)]
    return subprocess.Popen(argv, cwd=run.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, errors="replace")


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _ended_by(code: int) -> str:
    """How a process that wrote nothing telling ended: its exit code, or the signal that ended it."""
    if code < 0:
        try:
            return say("strip.signal", signal=signal.Signals(-code).name)
        except ValueError:
            return say("strip.signal", signal=-code)
    return say("strip.exit", code=code)


class Queue:
    """The Lab's runs, in the order given. At most ``at_once`` run (the machine's cores unless
    said); the rest wait, and each one that ends starts the next. ``version`` grows with every
    change, so a page redraws only when something moved."""

    def __init__(self, at_once: Optional[int] = None,
                 start: Callable[[Run], subprocess.Popen] = start_process) -> None:
        self.at_once = at_once or os.cpu_count() or 1
        self._start = start
        self._lock = threading.Lock()
        self._runs: list[Run] = []
        self._ids = itertools.count(1)
        self.version = 0

    def runs(self) -> list[Run]:
        with self._lock:
            return list(self._runs)

    def in_progress(self, piece: str, root: str, out_dir: str) -> set[str]:
        """The record names runs of ``piece`` queued or running now write, under that out-dir."""
        with self._lock:
            return self._busy(piece, root, out_dir)

    def check_free(self, piece: str, names: Sequence[str], *, root: str, out_dir: str) -> None:
        """Refuse, in words, a record name a queued or running run of ``piece`` already writes:
        two runs saving one record at once lose one, or leave it unreadable."""
        with self._lock:
            self._refuse_busy(piece, names, root, out_dir)

    def _busy(self, piece: str, root: str, out_dir: str) -> set[str]:
        return {r.name for r in self._runs if not r.finished and
                (r.piece, r.root, r.out_dir) == (piece, root, out_dir)}

    def _refuse_busy(self, piece: str, names: Sequence[str], root: str, out_dir: str) -> None:
        busy = sorted(set(names) & self._busy(piece, root, out_dir))
        if busy:
            raise ValueError(say_n("form.busy", len(busy), names=", ".join(busy)))

    def submit(self, piece: str, planned: Sequence[tuple[str, Sequence[tuple[str, str]]]], *,
               root: str, out_dir: str = DEFAULT_OUT_DIR) -> list[Run]:
        """Queue one run per ``(record name, setting pairs)`` -- every word checked before any is
        queued -- and start what may start. A name a queued or running run of the piece already
        writes is refused (:meth:`check_free`)."""
        words = checked(piece, planned)
        with self._lock:
            self._refuse_busy(piece, [name for name, _ in words], root, out_dir)
            runs = [Run(next(self._ids), piece, name, pairs, root, out_dir)
                    for name, pairs in words]
            self._runs += runs
            self._fill()
            self.version += 1
        return runs

    def stop(self, run_id: int) -> bool:
        """Stop one run: a queued one never starts, a running one's process is terminated, and a
        record it had not saved whole is never written (it is written to ``.partial`` and renamed
        only when whole). False when it already ended or is not known."""
        with self._lock:
            run = next((r for r in self._runs if r.id == run_id), None)
            if run is None or run.finished:
                return False
            was = run.state
            run.state = STOPPED
            if was == QUEUED:
                run.ended = time.monotonic()
            else:
                run.process.terminate()
            self.version += 1
            return True

    def dismiss(self, run_id: int) -> bool:
        """Take a finished run off the list; False for one still queued or running."""
        with self._lock:
            run = next((r for r in self._runs if r.id == run_id), None)
            if run is None or not run.finished:
                return False
            self._runs.remove(run)
            self.version += 1
            return True

    def stop_all(self) -> None:
        for run in self.runs():
            self.stop(run.id)

    def _fill(self) -> None:
        """Start queued runs, oldest first, while fewer than ``at_once`` run. Under the lock."""
        running = sum(r.state == RUNNING for r in self._runs)
        for run in self._runs:
            if running >= self.at_once:
                break
            if run.state != QUEUED:
                continue
            run.started = time.monotonic()
            try:
                run.process = self._start(run)
            except OSError as exc:                 # said on the run, which ends there
                run.state, run.ended = FAILED, time.monotonic()
                run.error = say("strip.not_started", words=exc)
                continue
            run.state = RUNNING
            running += 1
            threading.Thread(target=self._watch, args=(run,), daemon=True).start()

    def _watch(self, run: Run) -> None:
        """Wait for one run to end, then record how and start the next. The end is recorded
        whatever happens while reading, or the run would read as running for ever. If its end
        cannot be read, the run fails saying so, its process is ended rather than left running
        unseen, and the reason is raised on."""
        out = err = ""
        try:
            out, err = run.process.communicate()
        except BaseException as exc:
            err = say("strip.end_unread", words=repr(exc))
            raise
        finally:
            with self._lock:
                self._end(run, out, err)
                if run.process.returncode is None:
                    run.process.terminate()
                self._fill()
                self.version += 1

    @staticmethod
    def _end(run: Run, out: str, err: str) -> None:
        """Done when it answered with the record it saved -- it answers only once the record is
        whole on disk, so a run stopped too late to stop it reads Done, whatever its exit, and the
        strip never says Stopped beside a record on disk; else stopped, or failed: by a signal
        said as such, else with the last line it wrote."""
        run.ended = time.monotonic()
        code = run.process.returncode
        try:
            answer = json.loads(out) if out.strip() else {}
        except json.JSONDecodeError as exc:
            answer, err = {}, f"{err}\n" + say("strip.answer_unread", words=exc)
        if answer.get("saved"):
            run.state, run.saved = DONE, answer["saved"]
        elif run.state != STOPPED:
            run.state = FAILED
            run.error = (_ended_by(code) if code is not None and code < 0
                         else _last_line(err) or _ended_by(code))
        if run.state != DONE:            # a run ended by a signal removes nothing itself
            discard(os.path.join(run.root, run.out_dir, run.piece, f"{run.name}.json"))


#: The Lab's queue: one per process, shared by every browser tab.
QUEUE = Queue()
atexit.register(QUEUE.stop_all)
