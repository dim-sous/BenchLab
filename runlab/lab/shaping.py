"""The ways a Lab card shapes what it draws, each declared once: what it holds on the card, its
words, its kind, its group, what it offers, why a card cannot use it (or one of its options) right
now, and the keyword it hands the figure layer. A card's controls are these, in this order
(:data:`SHAPINGS`); its chart is drawn from what they hold (:func:`draw_keywords`), and a new way
of shaping a chart is one entry here (RCWS ``feat/unequal-state-mixing``, ``lab/shaping.py``).

The controls stand in groups by what they act on -- the axes (X, Log x, Log y), the runs (Colour
by, Runs), the drawing (Dots | Lines), the view (Chart | Table) -- every one on every chart and
number card (BESS's ``lab/shaping.py``; the developer's answers of 2026-11-17, which put back
what the cut of 2026-11-11 took). A control a card cannot use is greyed with the reason on its
hover: the figure layer's refusal in its own words where it is one
(``figure.chart.pool_refusal``, ``figure.render.log_refusal``). A logarithmic axis the chart
declares itself is never greyed: only switching on one it does not declare is. A card of a
figure the piece draws itself (kind ``own``) carries the chart card's Runs alone, greyed whole:
such a figure is drawn once per run, and only the piece could merge two.

No Panel here, so what a card offers is tested without a page.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .words import say

__all__ = ["Card", "Context", "Shaping", "SHAPINGS", "offered", "draw_keywords"]


@dataclass
class Card:
    """One open card: a ``chart`` (a panel the records declare) or a ``numbers`` card (a summary
    number against a setting, ``x``). ``x_log``, ``y_log`` and ``points`` are ``None`` while
    they follow what the chart declares; ``runs`` and ``x`` are ``""`` for the card's default;
    ``by`` is ``None`` for every setting that tells the runs apart. ``saved`` is what its last
    Save wrote, or why it wrote nothing (``save_failed``)."""
    id: int
    kind: str
    chart: str = ""
    number: str = ""
    x: str = ""
    x_log: bool | None = None
    y_log: bool | None = None
    colour_by: str = "run"
    by: tuple[str, ...] | None = None
    runs: str = ""
    points: bool | None = None
    cold_start: bool = False
    table: bool = False
    saved: str = ""
    save_failed: bool = False


@dataclass(frozen=True)
class Context:
    """What a card's controls are read off: its kind (``chart``, ``numbers``, or ``own`` for a
    chart card whose panel is a figure the piece draws itself) and how many runs it draws; the
    bottom axis's options (words -> value); on a chart card why each statistic cannot pool its
    runs (``{"mean": why, "rms": why}``, ``""`` where it can); what the chart declares over the
    bottom axis the card is on (its logarithmic axes, its dots); on a numbers card the settings
    that tell the runs apart (words -> setting) and whether a colour holds two runs at one
    value; and, once the chart is built, why it cannot take a logarithmic bottom axis or
    ordinate."""
    kind: str
    runs: int = 1
    axes: dict[str, str] = field(default_factory=dict)
    pool: dict[str, str] = field(default_factory=dict)
    declared_x_log: bool = False
    declared_y_log: bool = False
    declared_points: bool = False
    declared_split: bool = False
    declared_rows: bool = False
    declared_cold_start: bool = False
    declared_colours: bool = False
    telling: dict[str, str] = field(default_factory=dict)
    pools: bool = False
    x_log_refusal: str = ""
    y_log_refusal: str = ""


def _fine(card: Card, ctx: Context) -> str:
    return ""


@dataclass(frozen=True)
class Shaping:
    """One way of shaping a card. ``kind``: ``list`` (a drop-down), ``switch`` (on or off),
    ``one`` (one of a few, side by side, an option greyed alone where it cannot be picked) or
    ``several`` (any of a few). ``options(card, ctx)`` are ``(words, value, why greyed)``;
    ``shown`` what it holds for a card; ``keywords`` what it hands the figure layer;
    ``unusable`` why the whole control is greyed, ``""`` when it is not; ``kinds`` the cards it
    stands on."""
    field: str
    slot: str                                     # its words' slot (lab.words), "" for none
    kind: str
    group: int
    shown: Callable[[Card, Context], Any]
    keywords: Callable[[Card, Context], dict[str, Any]]
    options: Callable[[Card, Context], list[tuple[str, Any, str]]] = lambda card, ctx: []
    kinds: tuple[str, ...] = ("chart", "numbers")
    unusable: Callable[[Card, Context], str] = _fine


# -- the chart card's runs: one plot, a row each, or pooled where the chart declares a statistic

def _chart_runs(card: Card, ctx: Context) -> str:
    value = card.runs or ("rows" if ctx.declared_split and ctx.runs > 1 else "one")
    if value == "rows" and ctx.declared_rows:
        return "one"
    return "one" if value in ("mean", "rms") and ctx.pool.get(value) else value


def _chart_runs_options(card: Card, ctx: Context) -> list[tuple[str, Any, str]]:
    return [(say("cards.overlay"), "one", ""),
            (say("cards.split"), "rows", say("cards.rows_split") if ctx.declared_rows else ""),
            (say("cards.mean"), "mean", ctx.pool.get("mean", "")),
            (say("cards.rms"), "rms", ctx.pool.get("rms", ""))]


def _one_run(card: Card, ctx: Context) -> str:
    if ctx.kind == "own":
        return say("cards.own_runs")
    return say("cards.one_run") if ctx.runs < 2 else ""


def _colour_unusable(card: Card, ctx: Context) -> str:
    if ctx.declared_colours:
        return say("cards.colour_declared")
    if ctx.runs < 2:
        return say("cards.one_run")
    runs = _chart_runs(card, ctx)
    if runs in ("mean", "rms"):
        return say("cards.colour_pooled")
    if runs == "rows":
        return say("cards.colour_split")
    return ""


# -- the numbers card's runs: each a point, or a colour's runs at one value pooled

def _numbers_runs(card: Card, ctx: Context) -> str:
    return (card.runs or "each") if ctx.pools else "each"


def _by(card: Card, ctx: Context) -> tuple[str, ...]:
    """The settings a numbers card's colours stand for: every one that tells the runs apart
    until some are picked, then those of the picked that still do."""
    offered = tuple(ctx.telling.values())
    return offered if card.by is None else tuple(b for b in card.by if b in offered)


# -- the axes: logarithmic as the chart declares until switched; a declared one never greyed

def _x_log_shown(card: Card, ctx: Context) -> bool:
    return ctx.declared_x_log if card.x_log is None else bool(card.x_log)


def _x_log_unusable(card: Card, ctx: Context) -> str:
    return "" if _x_log_shown(card, ctx) or ctx.declared_x_log else ctx.x_log_refusal


def _y_log_shown(card: Card, ctx: Context) -> bool:
    return ctx.declared_y_log if card.y_log is None else bool(card.y_log)


def _y_log_unusable(card: Card, ctx: Context) -> str:
    return "" if _y_log_shown(card, ctx) or ctx.declared_y_log else ctx.y_log_refusal


def _points_shown(card: Card, ctx: Context) -> bool:
    return ctx.declared_points if card.points is None else bool(card.points)


#: Every way of shaping a card, in the order a card shows them.
SHAPINGS: tuple[Shaping, ...] = (
    Shaping("x", "cards.x", "list", 1, kinds=("chart",),
            options=lambda card, ctx: [(w, v, "") for w, v in ctx.axes.items()],
            shown=lambda card, ctx: card.x or "own",
            keywords=lambda card, ctx: {"x": card.x or "own"}),
    Shaping("x", "cards.x", "list", 1, kinds=("numbers",),
            options=lambda card, ctx: [(w, v, "") for w, v in ctx.axes.items()],
            unusable=lambda card, ctx: "" if ctx.axes else say("cards.nothing_differs"),
            shown=lambda card, ctx: card.x,
            keywords=lambda card, ctx: {"vs": card.x}),
    Shaping("x_log", "cards.x_log", "switch", 1, unusable=_x_log_unusable, shown=_x_log_shown,
            keywords=lambda card, ctx: {"x_log": _x_log_shown(card, ctx)}),
    Shaping("y_log", "cards.y_log", "switch", 1, unusable=_y_log_unusable, shown=_y_log_shown,
            keywords=lambda card, ctx: {"y_log": _y_log_shown(card, ctx)}),
    Shaping("colour_by", "cards.colour_by", "one", 2, kinds=("chart",),
            options=lambda card, ctx: [(say("cards.by_run"), "run", ""),
                                       (say("cards.by_quantity"), "quantity", "")],
            unusable=_colour_unusable, shown=lambda card, ctx: card.colour_by,
            keywords=lambda card, ctx: ({"colour_by": card.colour_by}
                                        if not _colour_unusable(card, ctx) else {})),
    # Its colours travel even when greyed: none named is one colour over every run.
    Shaping("by", "cards.colour_by", "several", 2, kinds=("numbers",),
            options=lambda card, ctx: [(w, v, "") for w, v in ctx.telling.items()],
            unusable=lambda card, ctx: "" if ctx.telling else say("cards.nothing_else_differs"),
            shown=_by, keywords=lambda card, ctx: {"by": _by(card, ctx)}),
    Shaping("runs", "cards.runs", "one", 2, kinds=("chart", "own"), options=_chart_runs_options,
            unusable=_one_run, shown=_chart_runs,
            keywords=lambda card, ctx: {"runs": _chart_runs(card, ctx)}),
    Shaping("runs", "cards.runs", "one", 2, kinds=("numbers",),
            options=lambda card, ctx: [(say("cards.each"), "each", ""),
                                       (say("cards.mean"), "mean", ""),
                                       (say("cards.rms"), "rms", "")],
            unusable=lambda card, ctx: "" if ctx.pools else say("cards.no_colour"),
            shown=_numbers_runs,
            keywords=lambda card, ctx: {"runs": _numbers_runs(card, ctx)}),
    Shaping("points", "", "one", 3,
            options=lambda card, ctx: [(say("cards.dots"), True, ""),
                                       (say("cards.lines"), False, "")],
            shown=_points_shown,
            keywords=lambda card, ctx: {"points": _points_shown(card, ctx)}),
    # A chart that declares where its run's cold start ends is drawn past it, unless this is on
    # (from 1.9; RCWS's card switch)
    Shaping("cold_start", "cards.cold_start", "switch", 3, kinds=("chart",),
            unusable=lambda card, ctx: "" if ctx.declared_cold_start else say("cards.no_cold_start"),
            shown=lambda card, ctx: card.cold_start,
            keywords=lambda card, ctx: ({"cold_start": card.cold_start}
                                        if ctx.declared_cold_start else {})),
    # The view hands the figure layer nothing: the table is read off the chart it draws.
    Shaping("table", "", "one", 4,
            options=lambda card, ctx: [(say("cards.chart"), False, ""),
                                       (say("cards.table"), True, "")],
            shown=lambda card, ctx: card.table,
            keywords=lambda card, ctx: {}),
)


def offered(card: Card, ctx: Context) -> list[tuple[Shaping, str]]:
    """``(shaping, why it is greyed or "")`` for every way the card shapes what it draws, in
    order -- every one, on every card of its kind."""
    return [(s, s.unusable(card, ctx)) for s in SHAPINGS if ctx.kind in s.kinds]


def draw_keywords(card: Card, ctx: Context) -> dict[str, Any]:
    """What the card draws, as the figure layer's keywords (``figure.chart.chart_of`` for a
    chart card, ``sweep_of`` for a numbers card)."""
    out: dict[str, Any] = {}
    for s, _ in offered(card, ctx):
        out.update(s.keywords(card, ctx))
    return out
