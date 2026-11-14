"""Stand-ins the tests drive the runs in progress with, where a real process would only be slower."""

from __future__ import annotations

import threading
import time


class Process:
    """A run's process, stood in for: it ends when the test says, as the test says. Like a
    ``subprocess.Popen``, ``terminate`` signals only a process that has not ended."""

    def __init__(self) -> None:
        self.ended = threading.Event()
        self.returncode, self.out, self.err, self.terminated = None, "", "", 0

    def communicate(self) -> tuple[str, str]:
        self.ended.wait()
        return self.out, self.err

    def terminate(self) -> None:
        self.terminated += 1
        if self.returncode is None:
            self.end(-15)

    def end(self, code: int = 0, out: str = "", err: str = "") -> None:
        self.returncode, self.out, self.err = code, out, err
        self.ended.set()


def settled(condition, what, timeout: float = 20.0) -> None:
    """Wait for ``condition()`` -- a watcher thread records a run's end -- or fail saying
    ``what()``."""
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        time.sleep(0.02)
    assert condition(), what()
