"""The record layer: what one run of a piece leaves behind, as one JSON file. Adapted from BESS's
``devkit/record/__init__.py`` (itself RCWS's), trimmed to what DeePC's pieces use.

A piece's ``Record`` is a frozen dataclass whose first field is ``name`` (also the file stem) and
which carries ``config`` (the Config the run used), ``provenance`` and ``numbers: dict[str,
float]``, plus the arrays its figures will draw. It declares, from its own fields, the panels a
figure layer may draw (``series()``), the figures it draws itself (``figures()``: what lines
against an abscissa cannot say) and the words and units of its numbers (``number_specs()``), so a
drawing and a listing cannot drift from the data. What a run writes beyond its run file, a
trained network or a checkpoint, is kept in a folder beside it (:mod:`runlab.record.files`).

A number with no answer is left out of ``numbers``, never saved as NaN. Non-finite values inside
an array ride as the tokens ``"nan"``, ``"inf"``, ``"-inf"`` and load back as floats. A float is
written with Python's shortest exact repr, so an array loads back bit for bit.
"""

from __future__ import annotations

import copy
import dataclasses
import enum
import json
import math
import os
import platform
import subprocess
import types
import typing
from collections.abc import Callable
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar, Mapping

import numpy as np

from runlab.project import declared
from runlab.record.config import Settings, from_saved, saved, setting_names
from runlab.record.files import files_of, listed, run_files

__all__ = ["Provenance", "stamp", "Quantity", "WORDS", "STATISTICS", "SHARES", "TIME", "Role", "ci",
           "Series", "Figure",
           "bound_refs", "Number", "number_words", "Record", "read_header", "capital",
           "run_files", "files_of", "Absent", "AbsentField", "Difference", "differences",
           "COMPONENT_KEY", "PANELS_KEY", "NUMBER_SPECS_KEY", "PANEL_GROUPS_KEY", "FILES_KEY",
           "HEADER_KEYS"]

COMPONENT_KEY, PANELS_KEY, NUMBER_SPECS_KEY = "component", "panels", "number_specs"
#: Each panel's group, ``{panel: group}``.
PANEL_GROUPS_KEY = "panel_groups"
#: The files the run wrote beside its run file, ``[{name, bytes}]``; left out when it wrote none.
FILES_KEY = "files"
HEADER_KEYS = (COMPONENT_KEY, PANELS_KEY, NUMBER_SPECS_KEY, PANEL_GROUPS_KEY, FILES_KEY)
#: The name RunLab is installed by, and so stamped under (``pyproject.toml``); a run saved before
#: 1.0 holds its version under ``benchlab``, the name it was installed by then.
INSTALLED = "runlab"
_NONFINITE = {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}


# ---------------------------------------------------------------------------
#  Provenance
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Provenance:
    """What produced a record. Stamped by ``stamp``; never hand-written."""

    git_sha: str
    git_dirty: bool
    date: str              # UTC, ISO 8601
    duration_s: float
    versions: dict         # {name: version}: Python's, the project's LIBRARIES, then RunLab's own


def _git(*args: str) -> str:
    # check=True: a record stamped from nowhere would read as a record from nowhere.
    return subprocess.run(["git", *args], cwd=declared().ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def stamp(duration_s: float) -> Provenance:
    return Provenance(git_sha=_git("rev-parse", "--short", "HEAD"),
                      git_dirty=bool(_git("status", "--porcelain")),
                      date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      duration_s=float(duration_s),
                      versions={"python": platform.python_version(),
                                **{lib: version(lib)
                                   for lib in (*declared().LIBRARIES, INSTALLED)}})


# ---------------------------------------------------------------------------
#  Declarations a figure layer and a listing read
# ---------------------------------------------------------------------------

def capital(words: str) -> str:
    """``words`` with a capital first letter and the rest as written: how a label, a legend and a
    heading begin (the developer's rule, BESS 2026-10-27), acronyms and symbols keeping their own."""
    return words[:1].upper() + words[1:]


#: The two ways the page words a quantity: by its name or by its symbol (the switch in its header).
WORDS = ("names", "symbols")


@dataclasses.dataclass(frozen=True)
class Quantity:
    """One quantity a project measures or sets, named once: ``key``, how it is found (kebab or
    snake case, never shown); ``name`` and ``symbol``, the two words the page chooses between
    ("State of charge", "SOC"), either of which may be left out, the other then shown both ways;
    ``unit``, "" for none."""

    key: str
    name: str = ""
    symbol: str = ""
    unit: str = ""

    def __post_init__(self) -> None:
        if not (self.name or self.symbol):
            raise ValueError(f"quantity {self.key!r} has neither a name nor a symbol; it needs "
                             f"one of them")

    def word(self, words: str) -> str:
        """Its word in ``words`` (:data:`WORDS`); the other one when it has not this one."""
        if words not in WORDS:
            raise ValueError(f"words {words!r}: one of {list(WORDS)}")
        return (self.symbol or self.name) if words == "symbols" else (self.name or self.symbol)

    def axis(self, words: str) -> str:
        """The label of an axis it lies along: its word and its unit, "[-]" for none (the
        developer's spelling of a quantity with no unit, 2026-11-21)."""
        return f"{self.word(words)} [{self.unit or '-'}]"

    def inside(self, words: str) -> str:
        """Its word as it reads inside a phrase ("Final state of charge"): a name with its first
        letter small, unless it opens with two capitals ("RC1 voltage"); a symbol as written."""
        word = self.word(words)
        by_name = word == self.name and not (words == "symbols" and self.symbol)
        return word[:1].lower() + word[1:] if by_name and not word[:2].isupper() else word


#: RunLab's statistics, one spelling each (the developer's design of 2026-11-21, section 3, "As
#: written"): the words a number is made from its quantity's word by, and whether it keeps the
#: quantity's unit. A share counts the steps or the time of a condition, and has no quantity.
STATISTICS: dict[str, tuple[str, bool]] = {
    "final": ("Final {quantity}", True), "initial": ("Initial {quantity}", True),
    "max": ("Max {quantity}", True), "min": ("Min {quantity}", True),
    "mean": ("Mean {quantity}", True), "std": ("{quantity} std", True),
    "rmse": ("{quantity} RMSE", True), "snr": ("{quantity} SNR", False),
    "share_of_steps": ("Share of steps {condition}", False),
    "share_of_time": ("Share of time {condition}", False)}
SHARES = ("share_of_steps", "share_of_time")

#: The time a run's samples are taken at, in seconds: "Time [s]" by name, "t [s]" by symbol. A
#: project whose time is in other units names its own.
TIME = Quantity("time", name="Time", symbol="t", unit="s")


class Role(enum.Enum):
    """What a line is among the lines of one quantity, one spelling each (the developer's design of
    2026-11-21, section 3, "As written"): its words the same by name and by symbol."""

    TRUTH = "Truth"
    ESTIMATE = "Estimate"
    MEASURED = "Measured"
    ESTIMATION_ERROR = "Estimation error"
    MEASUREMENT_ERROR = "Measurement error"
    SETPOINT = "Setpoint"
    APPLIED = "Applied"

    def word(self, words: str) -> str:
        """Its words, in ``words`` (:data:`WORDS`): the same either way."""
        if words not in WORDS:
            raise ValueError(f"words {words!r}: one of {list(WORDS)}")
        return self.value


@dataclasses.dataclass(frozen=True)
class _Bound:
    """A reference line's words: the lower or upper bound of a quantity, with its unit."""

    side: str
    quantity: Quantity

    def word(self, words: str) -> str:
        return f"{self.side} bound of {self.quantity.inside(words)} [{self.quantity.unit or '-'}]"


@dataclasses.dataclass(frozen=True)
class _Band:
    """A band's words: the confidence interval, at ``level`` percent, of what it is about."""

    of: Any
    level: float

    def word(self, words: str) -> str:
        return f"{_said(self.of, words)} {self.level:g}% CI"


def ci(of: Any, level: float = 95) -> _Band:
    """A band's words, the ``level`` percent confidence interval of ``of``: a :class:`Role`
    ("Estimate 95% CI"), a :class:`Quantity`, worded by the switch, or words in full."""
    return _Band(of, float(level))


def _said(part: Any, words: str) -> Any:
    """A chart's part in ``words``: one that knows its words in names and in symbols (a
    quantity, a role, a bound, a band) says them; words in full are as written."""
    return part.word(words) if hasattr(part, "word") else part


@dataclasses.dataclass(frozen=True)
class Series:
    """One panel: an abscissa, one or more traces on one ordinate unit, optional references and
    bands. The unit lives in the axis label -- one unit per panel. An axis or a line may be a
    :class:`Quantity` instead of words: the panel's words are then made from it, in names when it
    is built, in symbols on asking (:meth:`in_words`)."""

    name: str                                        # the figure's file stem, kebab-case
    x: Any                                           # (M,)
    x_label: str = ""                                # with its unit; "" when ``x_quantity`` says it
    y_label: str = ""                                # with its unit; "" when ``quantity`` says it
    traces: tuple[tuple[str | Quantity, Any], ...] = ()   # (legend label or quantity, (M,) values)
    refs: tuple[tuple[str, float], ...] = ()         # (label, constant value)
    bands: tuple[tuple[str, Any, Any], ...] = ()     # (label, lo, hi): scalars or (M,) arrays
    doc: str = ""
    group: str = ""                                  # the heading a listing puts it under
    #: The words a listing and a card show for the panel; left out, its name. The name stays the
    #: file's stem and the address's key, kebab-case, whatever the words.
    title: str = ""
    #: The statistics its traces may be pooled by across runs ("mean", "rms"); () for none.
    pooled: tuple[str, ...] = ()
    #: How many independent draws each trace is a mean of (a statistic a run averages over its
    #: seeds): runs pooled together are weighted by it, and their draws counted together.
    averaged: int = 1
    #: The band of a mean of ``n`` independent draws, as an entry of ``bands``, ``(label, lo,
    #: hi)``: drawn about the mean of runs pooled together, ``n`` all their draws. The formula
    #: is the piece's own (BESS's is a chi-square band about a NEES); None for none.
    mean_band: Callable[[int], tuple[str, Any, Any]] | None = None
    #: A logarithmic bottom axis or ordinate, declared by the record for a quantity read in
    #: decades (a Bode plot's ω and |G|): what a card's Log x and Log y open on.
    x_log: bool = False
    y_log: bool = False
    #: The quantity along the ordinate, and the one along the abscissa: each writes its axis's
    #: label, and the ordinate's the title when none is written. Last among the fields, so that a
    #: panel built by position keeps its meaning.
    quantity: Quantity | None = None
    x_quantity: Quantity | None = None

    def __post_init__(self) -> None:
        for axis, quantity, label in (("x", self.x_quantity, self.x_label),
                                      ("y", self.quantity, self.y_label)):
            if quantity is not None and label:
                raise ValueError(f"panel {self.name!r} names the quantity {quantity.key!r} for its "
                                 f"{axis} axis and writes that axis's label {label!r} too; it "
                                 f"says one or the other")
        # what in_words words again: whether the title was written in full, and each line's own
        # label (a quantity, or words); kept beside the fields, which hold the words in names
        object.__setattr__(self, "_parts", (bool(self.title),
                                            tuple(label for label, _ in self.traces),
                                            tuple(label for label, _ in self.refs),
                                            tuple(label for label, *_ in self.bands)))
        self._word("names")
        if not self.traces:
            raise ValueError(f"panel {self.name!r} declares no trace")
        unknown = sorted(set(self.pooled) - {"mean", "rms"})
        if unknown:
            raise ValueError(f"panel {self.name!r} pools by {unknown}; a panel pools by "
                             f"'mean' or 'rms'")
        if self.mean_band is not None and "mean" not in self.pooled:
            raise ValueError(f"panel {self.name!r} declares the band of a mean but no 'mean' "
                             f"pooling")
        if int(self.averaged) < 1:
            raise ValueError(f"panel {self.name!r} averages {self.averaged} draws; at least 1")
        n = len(self.x)
        for label, y in self.traces:
            if len(y) != n:
                raise ValueError(f"panel {self.name!r}: trace {label!r} has {len(y)} values "
                                 f"against {n} abscissa values")
        for label, lo, hi in self.bands:
            for edge in (lo, hi):
                if np.ndim(edge) and len(edge) != n:
                    raise ValueError(f"panel {self.name!r}: band {label!r} edge has "
                                     f"{len(edge)} values against {n}")

    def _word(self, words: str) -> None:
        """Fill the words its parts make, in ``words``: the title when not written in full, each
        axis a quantity lies along, each line, reference line and band that knows its words."""
        titled, lines, refs, bands = self._parts
        if not titled:
            object.__setattr__(self, "title", self.quantity.word(words) if self.quantity
                               else self.name)
        if self.quantity is not None:
            object.__setattr__(self, "y_label", self.quantity.axis(words))
        if self.x_quantity is not None:
            object.__setattr__(self, "x_label", self.x_quantity.axis(words))
        object.__setattr__(self, "traces", tuple(
            (_said(label, words), y) for label, (_, y) in zip(lines, self.traces)))
        object.__setattr__(self, "refs", tuple(
            (_said(label, words), v) for label, (_, v) in zip(refs, self.refs)))
        object.__setattr__(self, "bands", tuple(
            (_said(label, words), lo, hi) for label, (_, lo, hi) in zip(bands, self.bands)))

    def in_words(self, words: str) -> "Series":
        """The panel in ``words`` (:data:`WORDS`): itself in names, as built; a copy in symbols.
        Words written in full stay as written either way."""
        if words not in WORDS:
            raise ValueError(f"words {words!r}: one of {list(WORDS)}")
        if words == "names":
            return self
        other = copy.copy(self)
        other._word(words)
        return other


@dataclasses.dataclass(frozen=True)
class Figure:
    """One panel the piece draws itself: a plotly figure built from the record's own fields, for
    what a :class:`Series` cannot say -- a histogram, a heatmap, an image, points on a plane. The
    run file keeps the fields, never the figure: it is drawn when shown, by the code of the day.
    Its title, labels and legend are the piece's own (``CLAUDE.md``, "Figures describe").

    A figure that holds plotly frames PLAYS (from 1.1): the page shows it as plotly's own page
    in a frame on its card, where plotly's play button, slider and 3D turning are plotly's.
    ``script`` is JavaScript run in that page once the plot is made -- plotly's own
    ``post_script``, ``{plot_id}`` in it the plot's element id; a figure with a script is shown
    in such a frame too."""

    name: str        # its key in the chart list and the page's address, kebab-case
    figure: Any      # a ``plotly.graph_objects.Figure``, or the plain dict of one
    group: str = ""  # the heading a listing puts it under
    title: str = ""  # the words a listing and a card show for it; left out, its name
    doc: str = ""
    script: str = "" # JavaScript for the figure's own page; "" for none

    def __post_init__(self) -> None:
        if not self.title:
            object.__setattr__(self, "title", self.name)
        if not isinstance(self.script, str):
            raise TypeError(f"the figure {self.name!r}: its script is text, the JavaScript its "
                            f"page runs; got {type(self.script).__name__}")


def bound_refs(bounds: Any, quantity: str | Quantity,
               unit: str | None = None) -> tuple[tuple[Any, float], ...]:
    """A panel's reference lines for ``quantity``'s ``[lower, upper]`` bounds, each a finite one
    (an infinite bound is no line), named with the quantity and its unit (CLAUDE.md: "A bound
    names the quantity it bounds, with its unit", D7): ``quantity`` its words and ``unit`` its
    unit, or a :class:`Quantity`, which holds its unit and whose words follow the switch (0.25)."""
    held = [(side, float(v)) for side, v in zip(("Lower", "Upper"), np.asarray(bounds, dtype=float))
            if np.isfinite(v)]
    if isinstance(quantity, Quantity):
        if unit is not None:
            raise ValueError(f"quantity {quantity.key!r} holds its unit; bound_refs takes none "
                             f"beside it, {unit!r} given")
        return tuple((_Bound(side, quantity), v) for side, v in held)
    if unit is None:
        raise ValueError(f"bound_refs of {quantity!r} in words: its unit is needed too")
    return tuple((f"{side} bound of {quantity} [{unit}]", v) for side, v in held)


@dataclasses.dataclass(frozen=True)
class Number:
    """The words and unit of one summary number in ``Record.numbers``: written in full
    (``label``, ``unit``), or made from its ``quantity`` and its ``statistic``
    (:data:`STATISTICS`; a share from its ``condition``), by name when built and by symbol on
    asking (:meth:`in_words`). A quantity with no statistic: the number is the quantity."""

    name: str
    label: str = ""
    unit: str = ""          # "" for a dimensionless quantity
    headline: bool = False  # shown first where a listing folds its columns
    doc: str = ""
    group: str = ""         # the heading a listing puts it under
    #: Last among the fields, so that a number declared by position keeps its meaning.
    quantity: Quantity | None = None
    statistic: str = ""
    condition: str = ""     # what a share counts the steps or the time of ("clipped")

    def __post_init__(self) -> None:
        made = bool(self.statistic) or self.quantity is not None
        if made and (self.label or self.unit):
            raise ValueError(f"number {self.name!r} is made from its quantity and statistic and "
                             f"writes its words {self.label!r} or its unit {self.unit!r} too; it "
                             f"says one or the other")
        if not made and not self.label:
            raise ValueError(f"number {self.name!r} has neither words nor a quantity")
        if self.statistic and self.statistic not in STATISTICS:
            raise ValueError(f"number {self.name!r}: statistic {self.statistic!r} is not one of "
                             f"{list(STATISTICS)}")
        share = self.statistic in SHARES
        if share and (not self.condition or self.quantity is not None):
            raise ValueError(f"number {self.name!r} is a share: it counts the steps or the time "
                             f"of a condition, which it names, and names no quantity")
        if self.condition and not share:
            raise ValueError(f"number {self.name!r} names a condition; only a share takes one")
        if self.statistic and not share and self.quantity is None:
            raise ValueError(f"number {self.name!r}: the statistic {self.statistic!r} is of a "
                             f"quantity, which it names")
        if made:
            self._word("names")

    def _word(self, words: str) -> None:
        """Fill its words and unit from its parts, in ``words``: the quantity's word inside the
        statistic's phrase, as written where it opens it; the quantity's unit where the
        statistic keeps it."""
        phrase, keeps_unit = STATISTICS[self.statistic] if self.statistic else ("{quantity}", True)
        q = self.quantity
        word = "" if q is None else q.word(words) if phrase.startswith("{quantity}") \
            else q.inside(words)
        object.__setattr__(self, "label", phrase.format(quantity=word, condition=self.condition))
        object.__setattr__(self, "unit", q.unit if q is not None and keeps_unit else "")

    def in_words(self, words: str) -> "Number":
        """The number in ``words`` (:data:`WORDS`): itself in names, as built; a copy in
        symbols. Words written in full stay as written either way."""
        if words not in WORDS:
            raise ValueError(f"words {words!r}: one of {list(WORDS)}")
        if words == "names" or not (self.statistic or self.quantity is not None):
            return self
        other = copy.copy(self)
        other._word(words)
        return other


def number_words(spec: Mapping[str, Any], words: str) -> tuple[str, str]:
    """A number's words and unit in ``words``, from its declaration as a run file saves it
    (``dataclasses.asdict`` of a :class:`Number`): made again from its parts when it holds them,
    as saved when it does not (a run saved before 0.23)."""
    if not spec.get("statistic") and not spec.get("quantity"):
        return spec["label"], spec.get("unit") or ""
    held = spec.get("quantity")
    worded = Number(spec["name"], quantity=Quantity(**held) if held else None,
                    statistic=spec.get("statistic") or "",
                    condition=spec.get("condition") or "").in_words(words)
    return worded.label, worded.unit


# ---------------------------------------------------------------------------
#  JSON encoding
# ---------------------------------------------------------------------------

def _jsonable(value: Any) -> Any:
    if isinstance(value, Settings):
        # a setting may hold ±inf (an actuator bound with no limit): the same tokens as an array
        return _jsonable(saved(value))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return f if math.isfinite(f) else ("nan" if math.isnan(f) else ("inf" if f > 0 else "-inf"))
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    return value


def _array_back(value: Any) -> np.ndarray:
    def back(v: Any) -> Any:
        if isinstance(v, list):
            return [back(x) for x in v]
        if isinstance(v, str):
            if v not in _NONFINITE:                  # a ValueError, so `load` refuses it in words
                raise ValueError(f"{v!r} is neither a number nor one of {sorted(_NONFINITE)}")
            return _NONFINITE[v]
        return v
    return np.asarray(back(value), dtype=float)


def _plain(hint: Any) -> Any:
    """``hint`` without its ``| None``; a union of several kinds as it is."""
    origin = typing.get_origin(hint)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        return args[0] if len(args) == 1 else hint
    return hint


def _decode(hint: Any, value: Any) -> Any:
    if value is None:
        return None
    hint = _plain(hint)
    if isinstance(hint, type) and issubclass(hint, Settings):
        return from_saved(hint, value)
    if hint is Provenance:
        return Provenance(**{f.name: value.get(f.name) for f in dataclasses.fields(Provenance)})
    if hint is np.ndarray:
        return _array_back(value)
    return value


# ---------------------------------------------------------------------------
#  A file that departs from what its class reads
# ---------------------------------------------------------------------------

class AbsentField(ValueError):
    """A field of a record was used that its file holds no value for the class can read."""


class Absent:
    """Stands where a field's value would be when the record's file holds none its class can
    read. It is no value: every use of it raises :class:`AbsentField` in ``why``'s words, so
    nothing is drawn or computed from what was never read."""

    __slots__ = ("why",)

    def __init__(self, why: str) -> None:
        self.why = why

    def __repr__(self) -> str:
        return f"Absent({self.why!r})"

    def __getattr__(self, name: str) -> Any:
        # reached only for a name the class does not hold. A dunder is a protocol being probed
        # (copy's, numpy's): AttributeError, its plain answer. Any other name is a use.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        raise AbsentField(self.why)

    def _used(self, *_: Any, **__: Any) -> Any:
        raise AbsentField(self.why)


for _used_by in ("len", "iter", "getitem", "contains", "bool", "float", "int", "index", "array",
                 "call", "neg", "pos", "abs", "lt", "le", "gt", "ge",
                 *(f"{side}{op}" for op in ("add", "sub", "mul", "truediv", "floordiv", "mod",
                                            "pow", "matmul") for side in ("", "r"))):
    setattr(Absent, f"__{_used_by}__", Absent._used)


@dataclasses.dataclass(frozen=True)
class Difference:
    """One way a record file departs from what its class reads."""

    place: str               # "result", "provenance" or "settings"
    field: str               # the record's field that holds the place; "" for the result itself
    kind: str                # "lacks": the class reads it and the file holds none; "extra": the reverse
    names: tuple[str, ...]


def differences(cls: type, raw: Mapping[str, Any]) -> tuple[Difference, ...]:
    """Where the content ``raw`` of a record file departs from what ``cls`` reads: in its
    fields, then inside the provenance and the settings it holds. Stated once, here: ``load``
    reads a file by it, and a listing words it."""
    hints = typing.get_type_hints(cls)
    names = [f.name for f in dataclasses.fields(cls)]
    out: list[Difference] = []

    def compare(place: str, field: str, read: Any, held: Any) -> None:
        lacks, extra = sorted(set(read) - set(held)), sorted(set(held) - set(read))
        if lacks:
            out.append(Difference(place, field, "lacks", tuple(lacks)))
        if extra:
            out.append(Difference(place, field, "extra", tuple(extra)))

    compare("result", "", names, [k for k in raw if k not in HEADER_KEYS])
    for name in names:
        hint, held = _plain(hints[name]), raw.get(name)
        if not isinstance(held, dict):
            continue
        if hint is Provenance:
            compare("provenance", name, [f.name for f in dataclasses.fields(Provenance)], held)
        elif isinstance(hint, type) and issubclass(hint, Settings):
            compare("settings", name, setting_names(hint), held)
    return tuple(out)


def _without(field: dataclasses.Field, path: Path) -> Any:
    """What a field the file lacks is read as: the default its class declares for it, else
    no value."""
    if field.default is not dataclasses.MISSING:
        return field.default
    if field.default_factory is not dataclasses.MISSING:
        return field.default_factory()
    return Absent(f"the file {path.name} holds no {field.name!r}")


# ---------------------------------------------------------------------------
#  Record
# ---------------------------------------------------------------------------

class Record:
    """Base of every piece's Record; see the module. Subclasses are frozen dataclasses."""

    component: ClassVar[str] = ""        # the registered piece name (the command word)
    label: ClassVar[str] = ""            # the piece's own words
    produced_by: ClassVar[str] = ""      # the command that writes one

    def series(self) -> tuple[Series, ...]:
        return ()

    def figures(self) -> tuple[Figure, ...]:
        return ()

    def number_specs(self) -> tuple[Number, ...]:
        return ()

    # -- the header a listing reads without rebuilding the body
    def header(self) -> dict[str, Any]:
        """The record's piece, its panels -- the charts ``series()`` declares, then the figures
        ``figures()`` does, in one list of names -- their groups, and its numbers' words. A
        name declared twice is refused: a chart and a figure are opened by the same name."""
        panels = [*self.series(), *self.figures()]
        names = [p.name for p in panels]
        twice = sorted({n for n in names if names.count(n) > 1})
        if twice:
            raise ValueError(f"{type(self).component} declares the panel(s) {twice} more than "
                             f"once; a chart and a figure share one list of names")
        return {COMPONENT_KEY: type(self).component,
                PANELS_KEY: names,
                NUMBER_SPECS_KEY: [dataclasses.asdict(n) for n in self.number_specs()],
                PANEL_GROUPS_KEY: {p.name: p.group for p in panels}}

    def save(self, path: str | os.PathLike[str]) -> Path:
        """Write header then fields, atomically; with them, the files the folder beside
        ``path`` holds (:mod:`runlab.record.files`), when it holds one. Refuses a non-finite
        or undeclared number, and a record read from a file that lacked one of its fields."""
        absent = sorted(f.name for f in dataclasses.fields(self)
                        if isinstance(getattr(self, f.name), Absent))
        if absent:
            raise ValueError(f"{type(self).component} holds no {absent}: a record read from a "
                             f"file that lacked a field is not saved again")
        numbers = getattr(self, "numbers", {})
        bad = sorted(k for k, v in numbers.items() if not math.isfinite(float(v)))
        if bad:
            raise ValueError(f"{type(self).component} numbers {bad} are not finite; a number "
                             f"with no answer is left out of the dict, not saved as a token")
        undeclared = sorted(set(numbers) - {n.name for n in self.number_specs()})
        if undeclared:
            raise ValueError(f"{type(self).component} numbers {undeclared} carry no words "
                             f"(number_specs); every number a listing shows is declared")
        path = Path(path)
        payload = dict(self.header())
        files = listed(path)
        if files:
            payload[FILES_KEY] = files
        payload.update((f.name, _jsonable(getattr(self, f.name)))
                       for f in dataclasses.fields(self))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".partial")
        with open(tmp, "w") as fh:
            json.dump(payload, fh, indent=1, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Record":
        """The record a file holds, read by what the class declares now. A file that departs
        from the class is read all the same, and :func:`differences` names how: an entry the
        class does not read stays in the file and is left unread; a field the file lacks takes
        the default the class declares for it, else an :class:`Absent`; a field whose saved
        value does not decode is an :class:`Absent` in the decoder's words. Refused: a file
        that is not there, and one of another piece.

        The record holds its fields and nothing more: a project rebuilds one from its own
        ``__dict__`` (observed 2026-11-17: DeePC's suite failed on a record that carried how
        its file differed)."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"no {cls.__name__} record at {path}. Run it first:\n"
                                    f"    {cls.produced_by}\nwhich writes that file.")
        with open(path) as fh:
            raw = json.load(fh)
        component = raw.get(COMPONENT_KEY)
        if component != cls.component:
            raise ValueError(f"{path} is a {component!r} record, not {cls.component!r}")
        body = {k: v for k, v in raw.items() if k not in HEADER_KEYS}
        hints = typing.get_type_hints(cls)
        values: dict[str, Any] = {}
        for field in dataclasses.fields(cls):
            if field.name not in body:
                values[field.name] = _without(field, path)
                continue
            try:
                values[field.name] = _decode(hints[field.name], body[field.name])
            except (TypeError, ValueError, AttributeError) as exc:
                values[field.name] = Absent(
                    f"the file {path.name} holds {field.name!r} in a form the current "
                    f"{cls.__name__} does not read ({exc})")
        return cls(**values)


def read_header(path: str | os.PathLike[str]) -> dict[str, Any]:
    """The header and the name of a record file, without importing its piece."""
    try:
        with open(path) as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not a record: not JSON ({exc.msg} at line {exc.lineno})") from None
    if not isinstance(raw, dict) or COMPONENT_KEY not in raw:
        raise ValueError(f"{path} is not a record: it carries no {COMPONENT_KEY!r} header")
    return {k: raw[k] for k in (*HEADER_KEYS, "name") if k in raw}
