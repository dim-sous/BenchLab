"""One run of a piece: what the side door (:mod:`benchlab.cli`) and the Lab both run.

``planned`` turns a record name, the ``SETTING=VALUE`` texts and the ``--sweep`` texts into the
runs they make, one per sweep combination, each with its record name and its setting pairs;
``run_once`` takes the piece's Config (the one given, as the command line reads a config file,
else the defaults), applies those pairs once (so a gate a sweep opens is open when the setting
behind it is checked), runs it, names the record and saves it. So the same settings make the same file whichever way they come in (``docs/design.md`` §4).

Run as a program, ``python -m benchlab.runner <piece> <name> <out_dir> <pairs as JSON>``, it is
one run started by the Lab (decision 3: each run its own process, never the command line). Its
answer is one JSON line on the stdout it was started with: ``{"saved": "<path>"}``, written
once the record is whole on disk. Everything else it or its piece writes goes to stderr, a line at
a time, so no print can be read as the answer and none lands after the error that ends the run. A
refusal (``ValueError``, ``KeyError``, ``FileNotFoundError``, the errors the command line also
turns into words) ends it with those words on one line of stderr, its last; any other failure
ends it with its own traceback.
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from benchlab.project import get_component
from benchlab.record.config import Settings, parse_override, with_overrides
from benchlab.record.files import keep, writing

__all__ = ["planned", "run_once", "main"]

#: One run: its record name and its ``(setting, text)`` pairs, the sweep's value among them.
Planned = tuple[str, list[tuple[str, str]]]


def planned(name: str, overrides: Sequence[str] = (), sweeps: Sequence[str] = ()) -> list[Planned]:
    """The runs ``name``, the ``SETTING=VALUE`` texts ``overrides`` and the ``SETTING=V1,V2,...``
    texts ``sweeps`` make: one per sweep combination, named ``<name>[-<setting>-<value>]...``.
    Refused in words: an empty sweep, a setting swept twice or also set, a repeated value, a
    value holding a path separator."""
    pairs = [parse_override(item) for item in overrides]
    axes, swept = [], []
    for item in sweeps:
        field, values = parse_override(item)
        if not values:
            raise ValueError(f"--sweep expects SETTING=V1,V2,..., got {item!r}")
        if field in swept or any(f == field for f, _ in pairs):
            raise ValueError(f"{field!r} is given twice (--sweep/--set); a setting is swept "
                             f"once, and not also set")
        texts = [v.strip() for v in values.split(",")]
        if len(set(texts)) != len(texts):
            raise ValueError(f"--sweep {item!r} repeats a value; each run would overwrite the last")
        parted = [v for v in texts if "/" in v or os.sep in v]
        if parted:
            raise ValueError(f"--sweep {field}: {parted[0]!r} holds a path separator, and each "
                             f"run is named <name>-{field}-<value>; run each with --set")
        swept.append(field)
        axes.append([(field, v) for v in texts])
    return [("-".join([name] + [f"{f}-{v}" for f, v in combo]), pairs + list(combo))
            for combo in (itertools.product(*axes) if axes else [()])]


def run_once(piece: str, pairs: Sequence[tuple[str, str]], name: str, out_dir: str,
             config: Settings | None = None):
    """Run ``piece`` once on its Config (``config``, else the defaults) with ``pairs`` applied,
    name the record ``name`` and save it as ``<out_dir>/<piece>/<name>.json``, the files it wrote
    (``benchlab.run_files``) in ``<name>.files/`` beside it. Returns the path and the record."""
    component = get_component(piece)
    cfg = with_overrides(config if config is not None else component.Config(), list(pairs))
    path = os.path.join(out_dir, piece, f"{name}.json")
    with writing(path):
        rec = dataclasses.replace(component.run(cfg), name=name)
        keep(path)
        return rec.save(path), rec


def main(argv: Sequence[str] | None = None) -> int:
    piece, name, out_dir, pairs = list(sys.argv[1:] if argv is None else argv)
    answer = os.fdopen(os.dup(sys.stdout.fileno()), "w")    # the channel to the Lab
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())        # a piece's prints go to stderr,
    sys.stdout.reconfigure(line_buffering=True)              # each before what follows it
    try:
        path, _ = run_once(piece, [tuple(p) for p in json.loads(pairs)], name, out_dir)
    except (ValueError, KeyError, FileNotFoundError) as exc:     # the command line's refusals
        raise SystemExit(" ".join(str(exc).split())) from exc   # on one line: the strip's
    answer.write(json.dumps({"saved": str(Path(path))}) + "\n")
    answer.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
