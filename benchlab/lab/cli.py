"""``uv run lab`` -- start the local page and open it.

Runs from the project root, because the out-dir and a setting naming a saved run are relative to
it: each run starts there, as the command a person types there would. Under WSL the
browser may not open by itself: pass ``--no-open`` and open the printed address.
"""

from __future__ import annotations

import argparse
import os
import signal

from benchlab.cli import DEFAULT_OUT_DIR

from . import jobs, words
from .app import serve

DEFAULT_PORT = 8765


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lab",
        description="The Lab: one local page over a piece -- its runs on the left, ticked and "
                    "compared column by column; their panels on the right as live charts, one "
                    "row per shown run; a form over its settings in a drawer; the runs in "
                    "progress along the bottom, each its own process. It computes nothing "
                    "itself.")
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"port on 127.0.0.1 (default: {DEFAULT_PORT})")
    p.add_argument("--no-open", action="store_true",
                   help="do not open a browser; just print the address")
    p.add_argument("--root", default=None,
                   help="project root each run starts in (default: the current directory)")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                   help=f"where runs write records, relative to the root "
                        f"(default: {DEFAULT_OUT_DIR})")
    return p


def stop_runs_on_sigterm() -> None:
    """A Lab ended by SIGTERM (``kill``, a task runner's stop) ends as on ctrl-c: its runs are
    stopped with it. Panel answers SIGINT alone, and a process ended by SIGTERM runs no exit hook,
    so without this its runs were left going with no Lab (2026-11-14, the 2a review)."""
    def ended(signum, _frame):
        jobs.QUEUE.stop_all()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, ended)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        words.words()                       # a missing word stops the Lab before it serves
    except (ValueError, LookupError, OSError) as exc:
        raise SystemExit(f"lab: {exc}") from exc
    root = os.path.abspath(args.root or os.getcwd())
    stop_runs_on_sigterm()
    print(f"Lab on http://127.0.0.1:{args.port}   (root {root}, records under {args.out_dir}/, "
          f"ctrl-c to stop)")
    serve(args.port, root, args.out_dir, show=not args.no_open)     # until ctrl-c
    print("\nstopped")
    return 0
