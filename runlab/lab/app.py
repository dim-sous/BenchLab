"""The Lab's page on Panel -- one :class:`Lab` per browser session, one screen.

The piece's runs on the left (a list to tick, filter and delete from, and the ticked runs
compared column by column), their cards on the right -- each the
figure layer's own drawing of what the records declare: a panel over the shown runs, or a summary
number against the setting that varies -- a draggable split between the two, the form over the
Config's groups in a drawer that opens from "New run" or a run's "use", and the runs in progress
along the bottom. Rows come from :mod:`lab.view`, a card's controls from
:mod:`lab.shaping`, what a control offers from :mod:`lab.form`, the runs from
:mod:`lab.jobs`, everything listed from :mod:`lab.state`, every chart from :mod:`figure.chart`
and :func:`figure.twin.figure_of`, the look from :mod:`lab.skin`. Served on 127.0.0.1 by
:func:`serve`.

Everything on the page is derived from what is on disk, what is ticked and what each card's
controls hold, on every event, in :meth:`Lab.render`; the one memo is the loaded records, keyed
by their file's mtime. The page computes nothing and restates one rule: a typed value its setting
cannot read, or one outside the bounds it declares, is refused when Run is pressed, in the Lab's
own words (:func:`lab.jobs.refusals`; ``tests/test_runner.py``
holds it to param's verdict). Otherwise a greyed control is its field's own gate or the figure
layer's refusal, a refusal is the words of what refused it, a chart is the figure layer's. A click that raises, or a page that cannot be built, shows its error on the
page.
"""

from __future__ import annotations

import copy
import dataclasses
import functools
import html
import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import panel as pn

from runlab.cli import folder_of
from runlab.figure.chart import (INDEX_LABEL, chart_of, distinct, pool_refusal, series_of,
                                 sweep_of, telling)
from runlab.figure.draw import draw, draw_sweep
from runlab.figure.own import own_figure
from runlab.figure.render import log_refusal, table_of
from runlab.figure.style import series_color
from runlab.figure.twin import figure_of
from runlab.project import title
from runlab.record import capital
from runlab.runner import planned

from . import jobs, shaping, skin, state, view
from .compare import CompareTable
from .form import Form, as_text, interval, term
from .runlist import RunList, SavedList
from .strip import RunsInProgress
from .words import say, say_n, word
from .split import DEFAULT_PX, Split

_POLL_MS = 700
#: A run's states, in the order the strip's head counts them: the mockup's (running, waiting,
#: then what ended). Each says itself through ``strip.state.<state>`` and ``strip.count.<state>``.
_STATES = (jobs.RUNNING, jobs.QUEUED, jobs.DONE, jobs.FAILED, jobs.STOPPED)
_PLOT_CONFIG = {"displaylogo": False, "responsive": True, "displayModeBar": "hover",
                "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toImage"]}
_SANS = skin.SANS.replace('"', "'")
_MONO = f"font-family:{skin.MONO.replace(chr(34), chr(39))}"
_DIM = f"color:{skin.INK3}"
_RED = f"color:{skin.SIGNAL}"
_H2 = (f"font:600 12px {_SANS};letter-spacing:.05em;text-transform:uppercase;"
       f"color:{skin.INK2}")
_LABEL = f"{_DIM};font-size:12px;line-height:24px;display:inline-block"
#: A card's controls' margin (RCWS): with Panel's own (5, 10), 20 px between two buttons, and a
#: number card's controls over 160 runs took two lines of a 1050 px card.
_TOOL_MARGIN = (2, 3)
#: The most a table in a card's place takes of the page's height before it scrolls (BESS).
_TABLE_PX = 420
#: The width of the column a chart group's words stand in, before its charts: the form's label
#: track (RCWS: in 100 px the longest group name took three lines).
_GROUP_PX = skin.LABEL_PX
#: The columns the chart list's index of groups is read down (RCWS).
_INDEX_COLUMNS = 3
#: The compare table's settings choice: each choice's slot, and what it asks for (``view.SETTINGS``).
_SETTINGS = {"compare.settings_none": "none", "compare.settings_differing": "differ",
             "compare.settings_all": "all"}
#: What the compare table groups its numbers by: each choice's slot, and its ``view.BY``.
_NUMBERS_BY = {"compare.numbers_heading": "heading", "compare.numbers_quantity": "quantity",
               "compare.numbers_statistic": "statistic"}


def _shown_in_page(exc: BaseException) -> None:
    """A callback that raises says so on the page and in the Lab's console. Not a fallback."""
    traceback.print_exc()
    if pn.state.notifications is not None:
        pn.state.notifications.error(f"{type(exc).__name__}: {exc}", duration=0)


def _toast(words: str) -> None:
    if pn.state.notifications is not None:
        pn.state.notifications.info(words, duration=3200)


def _every(callback: Callable[[], None], period_ms: int) -> Any:
    return pn.state.add_periodic_callback(callback, period=period_ms)


def _html(text: str, *, title: str = "", style: str = "", **kw: Any) -> pn.pane.HTML:
    t = f' title="{html.escape(title, quote=True)}"' if title else ""
    s = f' style="{style}"' if style else ""
    kw.setdefault("margin", (2, 5))      # a grid cell passes 0: there the gaps are the grid's
    return pn.pane.HTML(f"<span{t}{s}>{text}</span>", **kw)


def _h2(words: str) -> pn.pane.HTML:
    return _html(html.escape(words), style=_H2)


def _widget(cls: Any, **kw: Any) -> Any:
    """A Panel widget wearing the Lab's stylesheet."""
    return cls(stylesheets=[skin.WIDGET], **kw)


def _tool(cls: Any, **kw: Any) -> Any:
    """A control on a card: the Lab's stylesheet, compact."""
    kw.setdefault("margin", _TOOL_MARGIN)
    return cls(stylesheets=[skin.WIDGET, skin.TOOL], **kw)


class _Rows:
    """A list setting declaring ``rows`` drawn as labelled rows: one box per item, labelled by
    its index (``x1' =``), ✕ to take it out, a button to add one. It holds the list as the form
    holds every setting, as the text ``--set`` takes (JSON); ``""`` is the declared default.
    Every edit by hand calls ``on_edit`` with that text; a value written to it does not. Greying
    and the changed mark reach the drawn boxes in place: redrawing them while one is typed in
    would take the box away from under the keyboard."""

    def __init__(self, f: dict[str, Any], on_edit: Callable[[str], None]) -> None:
        self.f, self._on_edit = f, on_edit
        self.view = pn.Column(sizing_mode="stretch_width", margin=0)
        self._disabled, self._stylesheets = False, [skin.WIDGET]
        self._boxes: list[Any] = []
        self._buttons: list[Any] = []
        self._items: list[str] = [as_text(v) for v in f["default"] or []]
        self._draw()

    @property
    def value(self) -> str:
        return self._text()

    @value.setter
    def value(self, text: str) -> None:
        self._items = [as_text(v) for v in (json.loads(text) if text else self.f["default"] or [])]
        self._draw()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, off: bool) -> None:
        self._disabled = off
        for widget in self._boxes + self._buttons:
            widget.disabled = off

    @property
    def stylesheets(self) -> list[Any]:
        return self._stylesheets

    @stylesheets.setter
    def stylesheets(self, sheets: list[Any]) -> None:
        self._stylesheets = list(sheets)
        for box in self._boxes:
            box.stylesheets = self._stylesheets

    def _text(self) -> str:
        """The rows as JSON. A list of numbers (θ) writes each row that reads as a number as
        one, so its default reads as unset, and any other row as the text typed, which Run
        refuses under the setting (:func:`lab.jobs.refusals`): never a row split or dropped on
        the way."""
        if self.f.get("texts"):
            return json.dumps(self._items, ensure_ascii=False)
        def number(text: str) -> Any:
            try:
                return float(text)
            except ValueError:
                return text
        return json.dumps([number(v) for v in self._items], ensure_ascii=False)

    def _draw(self) -> None:
        label, add = self.f["rows"]["label"], self.f["rows"]["add"]
        rows, self._boxes, self._buttons = [], [], []
        for i, item in enumerate(self._items):
            box = pn.widgets.TextInput(value=item, margin=0, sizing_mode="stretch_width",
                                       disabled=self._disabled, stylesheets=self._stylesheets)
            box.param.watch(lambda e, i=i: self._typed(i, e.new), "value_input")
            drop = _widget(pn.widgets.Button, label="✕", width=30, margin=(0, 0, 0, 6),
                           disabled=self._disabled)
            drop.on_click(lambda _e, i=i: self._drop(i))
            self._boxes.append(box)
            self._buttons.append(drop)
            rows.append(pn.Row(_html(html.escape(label.format(i + 1) + " ="), margin=0,
                                     style=f"{_MONO};font-size:12.5px;display:block;width:64px"),
                               box, drop, sizing_mode="stretch_width", margin=(0, 0, 4, 0)))
        more = _widget(pn.widgets.Button, label=add, width=120, margin=(2, 0, 0, 64),
                       disabled=self._disabled)
        more.on_click(lambda _e: self._add())
        self._buttons.append(more)
        self.view.objects = rows + [more]

    def _typed(self, i: int, text: str) -> None:
        self._items[i] = text
        self._on_edit(self._text())

    def _drop(self, i: int) -> None:
        del self._items[i]
        self._draw()
        self._on_edit(self._text())

    def _add(self) -> None:
        self._items.append("")
        self._draw()
        self._on_edit(self._text())


class _Table:
    """A list of rows drawn as a table (BESS's ``lab/app.py``, ``_draw_rows``): a line of its
    columns' words, then a line per row -- its number, as a path names it
    (``segments.1.power_kw``), a box or a pick per cell, ✕ to take the row out -- and a button
    that adds a row, a copy of the last. It holds the rows as the form holds every setting, as
    the text ``--set`` takes (JSON); ``""`` is the declared default. Every edit by hand calls
    ``on_edit`` with that text; a value written to it does not. Typing in a cell changes the
    text and not the table, so the box keeps its cursor; adding or taking out a row draws the
    table again."""

    #: A box's and a pick's width: a pick shows its options' own lines (BESS, 2026-10-27: at a
    #: box's width "time in the segment [min]" was cut to "time in the").
    BOX, PICK = 110, 250

    def __init__(self, f: dict[str, Any], on_edit: Callable[[str], None]) -> None:
        self.f, self._on_edit = f, on_edit
        self.view = pn.Column(sizing_mode="stretch_width", margin=0)
        self._disabled, self._stylesheets = False, [skin.WIDGET]
        self._cells: list[Any] = []
        self._buttons: list[Any] = []
        self._rows: list[dict[str, Any]] = copy.deepcopy(f["default"] or [])
        self._draw()

    @property
    def value(self) -> str:
        return as_text(self._rows)

    @value.setter
    def value(self, text: str) -> None:
        self._rows = json.loads(text) if text else copy.deepcopy(self.f["default"] or [])
        self._draw()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, off: bool) -> None:
        self._disabled = off
        for widget in self._cells + self._buttons:
            widget.disabled = off

    @property
    def stylesheets(self) -> list[Any]:
        return self._stylesheets

    @stylesheets.setter
    def stylesheets(self, sheets: list[Any]) -> None:
        self._stylesheets = list(sheets)
        for cell in self._cells:
            cell.stylesheets = self._stylesheets

    def _row_default(self, i: int) -> dict[str, Any]:
        """What row ``i`` runs as when a cell of it is emptied: the declared list's own row
        ``i``, else what a row added to the list starts as (BESS, code review 2026-10-27: the
        second default leg, a charge, emptied to the added row's discharge)."""
        default = self.f["default"] or []
        return default[i] if i < len(default) else self.f["element_default"]

    def _width(self, sub: dict[str, Any]) -> int:
        return self.PICK if sub.get("choices") else self.BOX

    def _draw(self) -> None:
        subs = self.f["element_fields"]
        head = pn.Row(_html("", width=28, margin=(0, 4)),
                      *[_html(html.escape(term(s)), width=self._width(s), margin=(0, 4),
                              style=f"{_DIM};font-size:12px") for s in subs], margin=0)
        lines: list[Any] = [head]
        self._cells, self._buttons = [], []
        for i, row in enumerate(self._rows):
            cells = []
            for sub in subs:
                held = as_text(row.get(sub["name"]))
                if sub.get("choices"):
                    words = sub.get("lines") or {}
                    cell = pn.widgets.Select(
                        width=self._width(sub), margin=(2, 4), value=held,
                        options={words.get(c, as_text(c)): as_text(c) for c in sub["choices"]},
                        disabled=self._disabled, stylesheets=self._stylesheets)
                    cell.param.watch(lambda e, i=i, sub=sub: self._typed(i, sub, e.new), "value")
                else:
                    cell = pn.widgets.TextInput(
                        width=self._width(sub), margin=(2, 4), value=held,
                        placeholder=as_text(self._row_default(i)[sub["name"]]),
                        disabled=self._disabled, stylesheets=self._stylesheets)
                    cell.param.watch(lambda e, i=i, sub=sub: self._typed(i, sub, e.new),
                                     "value_input")
                cells.append(cell)
            drop = _widget(pn.widgets.Button, label="✕", width=30, margin=(2, 0, 0, 6),
                           disabled=self._disabled)
            drop.on_click(lambda _e, i=i: self._drop(i))
            self._cells += cells
            self._buttons.append(drop)
            lines.append(pn.Row(_html(str(i), width=28, margin=(0, 4),
                                      style=f"{_MONO};{_DIM};font-size:12.5px;"
                                            f"line-height:{skin.BOX_PX}px"),
                                *cells, drop, margin=0))
        add = say("form.add_row", name=self.f["label"])
        more = _widget(pn.widgets.Button, label=add, width=_width(add), margin=(4, 0, 0, 36),
                       disabled=self._disabled)
        more.on_click(lambda _e: self._add())
        self._buttons.append(more)
        self.view.objects = lines + [more]

    def _typed(self, i: int, sub: dict[str, Any], text: str) -> None:
        """One cell of row ``i``: a choice as picked, a number as typed (any other text is kept
        as typed, and Run refuses it under the setting), an emptied cell back at its row's
        default."""
        name, text = sub["name"], (text or "").strip()
        if text == "":
            self._rows[i][name] = self._row_default(i)[name]
        elif sub.get("choices"):
            self._rows[i][name] = next((c for c in sub["choices"] if as_text(c) == text), text)
        elif sub["type"] in ("float", "int"):
            try:
                self._rows[i][name] = float(text) if sub["type"] == "float" else int(text)
            except ValueError:
                self._rows[i][name] = text
        else:
            self._rows[i][name] = text
        self._on_edit(self.value)

    def _drop(self, i: int) -> None:
        del self._rows[i]
        self._draw()
        self._on_edit(self.value)

    def _add(self) -> None:
        self._rows.append(copy.deepcopy(self._rows[-1] if self._rows
                                        else self.f["element_default"]))
        self._draw()
        self._on_edit(self.value)


def _width(words: str) -> int:
    """A button as wide as its words, at the card's 12 px (RCWS)."""
    return 20 + 13 * len(words) // 2


def _six(value: Any) -> str:
    """A number at six significant digits, as a table in a card's place writes it."""
    if isinstance(value, float):
        return f"{value:.6g}"
    return "" if value is None else str(value)


def _when(mtime: float) -> str:
    """A file's last change as a run's date reads in the lists: ``2026-11-18 07:10``, UTC."""
    return datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="minutes")[:16] \
        .replace("T", " ")


def _span_on(span: Optional[tuple[list[Any], bool]], x_log: bool) -> Optional[list[Any]]:
    """The span a zoom left -- its two ends as the chart library reported them, and whether the
    chart reporting them was logarithmic, on which the library's ends are powers of ten -- as
    the ends to set on a chart that is logarithmic (``x_log``) or not. ``None``: nothing to
    set, because no span is kept or a logarithmic axis cannot show one that reaches zero."""
    if span is None:
        return None
    ends, was_log = span
    if was_log == x_log:
        return list(ends)
    if was_log:
        return [10.0 ** float(e) for e in ends]
    if min(float(e) for e in ends) <= 0.0:
        return None
    return [math.log10(float(e)) for e in ends]


def _tab(name: str, value: bool) -> pn.widgets.Toggle:
    """A chart's toggle, across the cell that holds it, in the controls' look (RCWS)."""
    return pn.widgets.Toggle(label=name, value=value, margin=0, sizing_mode="stretch_width",
                             css_classes=["tab"], stylesheets=[skin.WIDGET, skin.TOOL])


def _tab_cell(toggle: pn.widgets.Toggle, note: str) -> pn.Column:
    """A chart's toggle with its note under it: at least as wide as its name in the type the
    toggles are set in, and growing with the others on its line until the line is full (RCWS:
    cells as wide as the longest name left most of each line empty)."""
    said = ([_html(html.escape(note), style=f"{_DIM};font-size:11px", margin=(1, 0, 0, 6))]
            if note else [])
    return pn.Column(toggle, *said, margin=(3, 3), width=_tab_width(toggle.label),
                     sizing_mode="fixed", styles={"flex": "1 1 auto", "max-width": "none"})


def _tab_width(title: str) -> int:
    """A chart toggle's cell's width: at least as wide as its title."""
    return 22 + 8 * len(title)


def _declared(record: Any) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]:
    """What a record can draw, as its class declares it now: the names of its charts, then of
    the figures it draws itself, with each one's group and its title by name and by symbol (a
    figure of its own has one title)."""
    panels = [*record.series(), *record.figures()]
    return ([p.name for p in panels], {p.name: p.group for p in panels},
            {p.name: p.title for p in panels},
            {p.name: p.in_words("symbols").title if hasattr(p, "in_words") else p.title
             for p in panels})


def _colour(i: int) -> str:
    """The colour the i-th shown run's lines wear on one plot (``figure.style.series_color``)."""
    return series_color(i)


class Lab:
    """The page's state for one browser session. ``queue``, ``every`` and ``toast`` are
    injectable so the page can be driven in Python (the tests do); the queue is the Lab's own,
    shared by every session, unless one is given."""

    def __init__(self, root: str, out_dir: str, *,
                 queue: Optional[jobs.Queue] = None,
                 every: Callable[[Callable[[], None], int], Any] = _every,
                 toast: Callable[[str], None] = _toast) -> None:
        self.root, self.out_dir = root, out_dir
        self.queue = queue if queue is not None else jobs.QUEUE
        self.every, self.toast = every, toast
        self.pieces = state.pieces()
        self.piece = self.pieces[0]
        self.form = Form(self.piece)
        self.records: list[dict[str, Any]] = []
        #: what the strip last drew (the queue's version); the runs this page has seen Done, so
        #: each is listed and ticked once (one Done before the page opened, never); and the runs
        #: it knew, so one cleared before this page saw it Done still gets its record listed
        self._seen = -1
        self._done: set[int] = {r.id for r in self.queue.runs() if r.state == jobs.DONE}
        self._known: set[int] = {r.id for r in self.queue.runs()}
        self._controls: dict[str, Any] = {}
        self._labels: dict[str, pn.pane.HTML] = {}
        #: the line under each setting: what Run refused in it, else why it is greyed
        self._notes: dict[str, pn.pane.HTML] = {}
        #: what the last Run refused, by setting, and in the sweep row: each said under its
        #: place until that place is edited, the form cleared or loaded, or a Run queues
        self._refused: dict[str, str] = {}
        self._sweep_refused = ""
        self._group_notes: dict[str, pn.pane.HTML] = {}
        #: the folded groups opened, by name; kept across redraws of one piece's form
        self._unfolded: set[str] = set()
        #: each folded group's head, by group, so Run can open the group a refusal is said in
        self._folds: dict[str, pn.widgets.Toggle] = {}
        self._filling = False
        self._from: Optional[str] = None            # the run the form was last loaded from
        self.shown: list[str] = []                  # the runs the cards and the table show
        self.cards: list[shaping.Card] = []
        #: the folders of pictures a Save wrote for this piece, newest first (``state.folders``)
        self.folders: list[dict[str, Any]] = []
        self._seq = 0
        self._asked_open: list[str] = []            # what the address asked to open
        self.settings_shown = "none"
        #: What the compare table groups its numbers by (``view.BY``): the switch under Settings,
        #: kept in the address.
        self.numbers_by = "heading"
        #: path -> (mtime, record): a loaded record is read once per version of its file
        #: per file: the version read, the record (``None`` when refused, with the words why) and
        #: what it draws -- its charts and their groups, read once with it (``_drawable``)
        self._loaded: dict[str, tuple[float, Any, str, Optional[tuple]]] = {}
        #: card id -> the runs its chart draws, in the order shown
        self.drawn: dict[int, list[str]] = {}
        #: Each open chart's pane with the words of its bottom axis; and, per bottom axis, the
        #: range a zoom left on it (``None`` once reset): every chart over it is shown at it.
        self._panes: dict[int, tuple[pn.pane.Plotly, str, bool]] = {}
        #: What each card keeps from one drawing of the cards to the next, by its id and the part
        #: (its box, top line, title, Save, close, plot; a figure of a piece's own also by the
        #: run's name), so the browser updates each where it stands. Drawn anew on every drawing,
        #: a plot the browser was still drawing was destroyed under it: plotly's "_guiEditing"
        #: error, 4 of 48 saves under load (2026-11-21, 0.23.0); and a button drawn anew inside a
        #: kept box was sent back by the browser in full when clicked (Bokeh's "reference already
        #: known" warning, the second Save of the every-card drive, 2026-11-21).
        self._kept: dict[tuple, Any] = {}
        #: What each card's Save draws, as the card was last drawn.
        self._save_args: dict[int, tuple] = {}
        self._ranges: dict[str, Optional[tuple[list[Any], bool]]] = {}
        self._answer: Optional[Callable[[], None]] = None   # what the dialog's yes does
        #: How the charts word a quantity, by name or by symbol (``record.WORDS``): the switch in
        #: the header, kept in the address.
        self.wording = "names"
        self._read_url()

        # -- header
        self.piece_select = _widget(pn.widgets.Select, width=170,
                                    options={p["label"]: p["name"] for p in self.pieces},
                                    value=self.piece["name"])
        self.piece_select.param.watch(lambda e: self._on_piece(e.new), "value")
        self.where = _html("")
        self.new_run_btn = _widget(pn.widgets.Button, label=say("header.new_run"), color="primary",
                                   width=92)
        self.new_run_btn.on_click(lambda _e: self.open_drawer())
        self.refresh = _widget(pn.widgets.Button, label=say("header.refresh"), width=72)
        self.refresh.on_click(lambda _e: self.reload())
        self.wording_choice = _tool(pn.widgets.RadioButtonGroup,
                                    options={say("header.names"): "names",
                                             say("header.symbols"): "symbols"},
                                    value=self.wording)
        self.wording_choice.param.watch(lambda e: self._on_wording(e.new), "value")

        # -- the left pane: the runs, the shown ones compared
        self.runs_count = _html("", style=_DIM, stylesheets=[skin.BAR_FILL])
        self.run_filter = _tool(pn.widgets.TextInput, placeholder=say("runs.filter"),
                                sizing_mode="stretch_width")
        self.run_filter.param.watch(lambda _e: self._draw_list(), "value_input")
        self.all_btn = _tool(pn.widgets.Button, label=say("runs.all"), width=_width(say("runs.all")))
        self.all_btn.on_click(lambda _e: self.tick_listed())
        self.none_btn = _tool(pn.widgets.Button, label=say("runs.none"),
                              width=_width(say("runs.none")))
        self.none_btn.on_click(lambda _e: self.untick_listed())
        self.run_list = RunList(rows=[], shown=[], sizing_mode="stretch_width", styles=skin.RUNS,
                                words={"use": say("runs.use"), "delete": say("runs.delete"),
                                       "delete_label": word("runs.delete_label")})
        self.run_list.on_use = self.open_drawer
        self.run_list.on_delete = self._ask_delete_run
        self.run_list.param.watch(lambda e: self._on_shown(list(e.new)), "shown")
        self.compare_count = _html("", style=_DIM, stylesheets=[skin.BAR_FILL])
        self.settings_choice = _tool(pn.widgets.RadioButtonGroup,
                                     options={say(slot): v for slot, v in _SETTINGS.items()},
                                     value="none")
        self.settings_choice.param.watch(lambda e: self._on_settings(e.new), "value")
        self.numbers_choice = _tool(pn.widgets.RadioButtonGroup,
                                    options={say(slot): v for slot, v in _NUMBERS_BY.items()},
                                    value=self.numbers_by)
        self.numbers_choice.param.watch(lambda e: self._on_numbers_by(e.new), "value")
        # shown only while a shown run's numbers name a quantity or a statistic (_draw_compare)
        self.numbers_row = pn.Row(_html(html.escape(say("compare.numbers")), style=_LABEL),
                                  self.numbers_choice, stylesheets=[skin.BAR],
                                  sizing_mode="stretch_width", visible=False)
        self.compare_table = CompareTable(sizing_mode="stretch_width",
                                          empty=say("compare.empty"),
                                          corner=say("compare.corner"),
                                          styles={"background": skin.PAPER,
                                                  "border-radius": "6px", "overflow": "auto"})
        self.compare_table.on_number = self.open_number
        self.saved_count = _html("", style=_DIM, stylesheets=[skin.BAR_FILL])
        self.saved_list = SavedList(rows=[], sizing_mode="stretch_width",
                                    empty=say("saved.empty"),
                                    words={"delete": say("saved.delete"),
                                           "delete_label": word("saved.delete_label")})
        self.saved_list.on_delete = self._ask_delete_folder

        # -- the right pane: the cards
        self.open_count = _html("", style=_DIM)
        self.tabs = pn.Column(sizing_mode="stretch_width", margin=0)
        self._chart_toggles: dict[str, pn.widgets.Toggle] = {}
        self._chart_cells: dict[str, pn.Column] = {}     # each toggle's cell, sized to its title
        self._index_toggles: dict[str, pn.widgets.Toggle] = {}
        self._lines: dict[str, Any] = {}
        #: what the list was last built from (:meth:`_draw_tabs`); the groups the index shows,
        #: and the cards whose group was shown when they opened
        self._tabs_hold: Optional[tuple] = None
        self._groups_shown: set[str] = set()
        self._groups_met: set[int] = set()
        self.show_all = _tool(pn.widgets.Button, label=say("figures.show_all"),
                              width=_width(say("figures.show_all")))
        self.show_all.on_click(lambda _e: self._show_groups(True))
        self.hide_all = _tool(pn.widgets.Button, label=say("figures.hide_all"),
                              width=_width(say("figures.hide_all")))
        self.hide_all.on_click(lambda _e: self._show_groups(False))
        self.cards_box = pn.Column(sizing_mode="stretch_width")

        # -- deleting asks first, in a dialog of its own: nothing else can be clicked meanwhile
        self.question = pn.pane.HTML("")
        self.yes = _widget(pn.widgets.Button, label=say("messages.delete_yes"), color="danger",
                           width=72)
        self.yes.on_click(lambda _e: self._on_yes())
        self.no = _widget(pn.widgets.Button, label=say("messages.delete_no"), width=72)
        self.no.on_click(lambda _e: self._on_no())
        self.asking = pn.Modal(self.question, pn.Row(self.no, self.yes), show_close_button=False)

        # -- the drawer: the form
        self.form_box = pn.Column(sizing_mode="stretch_width")
        self.from_words = _html("", style=_DIM)
        self.form_note = _html("")
        self.sweep_field = _widget(pn.widgets.Select, width=170)
        self.sweep_values = _widget(pn.widgets.TextInput, width=150,
                                    placeholder=say("form.sweep_values"))
        self.sweep_field.param.watch(lambda e: self._on_sweep(field=e.new), "value")
        # A text box is read on `value_input` alone, every keystroke: a browser message that
        # carries both of a box's values at once (a paste, a key and Tab together) reached one
        # watcher over both as two events, and the box showed a value the run did not use
        # (2026-10-27, headless Chromium; RCWS watches `value_input` alone).
        self.sweep_values.param.watch(lambda e: self._on_sweep(values=e.new), "value_input")
        self.run_name = _widget(pn.widgets.TextInput, width=200)
        self.run_name.param.watch(lambda e: self._on_name(e.new), "value_input")
        #: On a line of its own under the bar, not in it: in the bar a long overwrite list pushed
        #: Run off the drawer, and made to give way there it was cut to two letters (2026-10-06).
        self.name_note = _html("", style=_DIM)
        #: what Run refused in the sweep row, under it
        self.sweep_note = _html("", visible=False)
        self.run_btn = _widget(pn.widgets.Button, label=say("form.run"), color="primary", width=70)
        self.run_btn.on_click(lambda _e: self._run())
        self.clear_btn = _widget(pn.widgets.Button, label=say("form.clear"), width=62)
        self.clear_btn.on_click(lambda _e: self._clear())
        self.close_btn = _widget(pn.widgets.Button, label=say("form.close"), width=64)
        self.close_btn.on_click(lambda _e: self.close_drawer())
        self.banner = pn.pane.HTML("", visible=False, styles={"color": skin.SIGNAL})
        self.drawer = pn.Column(
            pn.Row(_html(f"<b style='font-size:15px'>{html.escape(say('form.heading'))}</b>"),
                   self.from_words,
                   pn.layout.HSpacer(), self.clear_btn, self.close_btn,
                   styles=skin.DRAWER_HEAD, stylesheets=[skin.BAR],
                   sizing_mode="stretch_width"),
            pn.Column(self.form_box, styles=skin.DRAWER_BODY, sizing_mode="stretch_both",
                      scroll=True),
            pn.Column(pn.Row(_html(html.escape(say("form.name")), style=_DIM), self.run_name,
                             _html(html.escape(say("form.sweep")), style=_DIM), self.sweep_field,
                             self.sweep_values,
                             pn.layout.HSpacer(), self.run_btn, stylesheets=[skin.BAR],
                             sizing_mode="stretch_width"),
                      self.sweep_note, self.name_note, self.banner, self.form_note,
                      styles=skin.DRAWER_FOOT, sizing_mode="stretch_width"),
            visible=False, styles=skin.DRAWER, width=skin.DRAWER_PX)

        # -- runs in progress, along the bottom where the terminal was (decision 3)
        self.strip_btn = _widget(pn.widgets.Button, label=f"▸ {say('strip.toggle')}", width=150,
                                 css_classes=["quiet"])
        self.strip_btn.on_click(lambda _e: self._open_strip(not self.strip_list.visible))
        self.strip_summary = _html(html.escape(say("strip.nothing")), style=_DIM,
                                   stylesheets=[skin.BAR_FILL])
        self.strip_cap = _html(html.escape(say("strip.cap", n=self.queue.at_once)), style=_DIM)
        self.strip_rows = RunsInProgress(rows=[], sizing_mode="stretch_width",
                                         words={"stop": say("strip.stop"),
                                                "dismiss": say("strip.dismiss"),
                                                "stop_label": word("strip.stop_label"),
                                                "dismiss_label": word("strip.dismiss_label")})
        self.strip_rows.on_stop = self._stop
        self.strip_rows.on_dismiss = self._dismiss
        self.strip_list = pn.Column(self.strip_rows, scroll=True, height=skin.STRIP_LIST_PX,
                                    visible=False, styles=skin.STRIP_LIST,
                                    sizing_mode="stretch_width")
        self.strip = pn.Column(
            pn.Row(self.strip_btn, self.strip_summary, self.strip_cap, styles=skin.STRIP_BAR,
                   stylesheets=[skin.BAR], sizing_mode="stretch_width"),
            self.strip_list, styles=skin.STRIP, sizing_mode="stretch_width")

        self._fit_drawer()
        self._draw_form()
        self.reload()
        self._poll()
        self.every(self._poll, _POLL_MS)

    # ------------------------------------------------------------------ reading
    def reload(self) -> None:
        """Re-read the records on disk and redraw everything that shows them."""
        self.records = state.records(self.root, self.out_dir)
        self.folders = state.folders(self.root, self.out_dir, self.piece["name"])
        self._offer_saved()
        # the piece's own: with two pieces, every piece's count stood beside one piece's folder
        n = len(self.runs())
        where = say_n("header.where", n, folder=f"{self.out_dir}/{self.piece['name']}")
        self.where.object = (f"<span style='{_MONO};font-size:12px;{_DIM}'>"
                             f"{html.escape(where)}</span>")
        readable = [r for r in self.runs() if not r["stale"]]
        names = {r["name"] for r in readable}
        kept = [name for name in self.shown if name in names]
        if not kept and readable:
            # the newest that can be read: a row the list greys has no tick to take it off with
            kept = [readable[0]["name"]]
        self.shown = kept
        declared = [row["name"] for row in view.chart_rows(self._shown_drawable(), [])]
        for name in self._asked_open:
            if name in declared and name not in self.open_charts:
                self._open(name)
        self._asked_open = []
        if not self.cards and declared:
            self._open(declared[0])                 # so the page is never empty
        self._draw_names()
        self.render()

    def runs(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r["piece"] == self.piece["name"]]

    def shown_runs(self) -> list[dict[str, Any]]:
        """The ticked runs, in the order they were ticked."""
        by_name = {r["name"]: r for r in self.runs()}
        return [by_name[n] for n in self.shown if n in by_name]

    @property
    def open_charts(self) -> list[str]:
        """The panels open as cards, in the order they were opened."""
        return [c.chart for c in self.cards if c.kind == "chart"]

    def _record_of(self, run: dict[str, Any]) -> tuple[Any, str]:
        """The record behind a row, read once per version of its file -- a refusal too, else a
        run the class refuses was read again at every redraw (code review, 2026-10-27); else
        ``(None, why)`` in the loading's own words. A record whose charts read a field its file
        holds no value for is such a refusal, in the field's words (``record.AbsentField``):
        what it can draw is asked here, once."""
        hit = self._loaded.get(run["path"])
        if hit is not None and hit[0] == run["mtime"]:
            return hit[1], hit[2]
        try:
            record, why = state.load(run), ""
            drawn = _declared(record)
        except (ValueError, OSError) as exc:
            record, why, drawn = None, str(exc), None
        self._loaded[run["path"]] = (run["mtime"], record, why, drawn)
        return record, why

    def render(self) -> None:
        """Everything that shows the runs, from disk, the ticks and the cards, in one pass."""
        self._draw_list()
        self._draw_compare()
        self._draw_saved()
        self._draw_tabs()
        self._draw_cards()
        self._draw_url()

    # ------------------------------------------------------------------ the runs
    def _listed(self) -> list[dict[str, Any]]:
        return view.matching(self.runs(), self.run_filter.value_input or "")

    def _draw_list(self) -> None:
        listed = self._listed()
        colour = {name: _colour(i) for i, name in enumerate(self.shown)}
        self.run_list.rows = [{"name": r["name"], "stale": r["stale"], "notes": r["notes"],
                               "colour": colour.get(r["name"], "")}
                              for r in view.run_rows(listed)]
        self.run_list.empty = (say("runs.none_listed") if self.runs()
                               else say("runs.empty", command=self.piece["produced_by"]))
        if list(self.run_list.shown) != self.shown:
            self.run_list.shown = list(self.shown)
        n = len(self.runs())
        count = (say("runs.count_listed", on_disk=n, shown=len(self.shown), listed=len(listed))
                 if len(listed) != n else say("runs.count", on_disk=n, shown=len(self.shown)))
        self.runs_count.object = f"<span style='{_DIM}'>{html.escape(count)}</span>"

    def _on_shown(self, names: list[str]) -> None:
        if names == self.shown:
            return
        readable = {r["name"] for r in self.runs() if not r["stale"]}
        self.shown = [n for n in names if n in readable]
        self.render()

    def tick_listed(self) -> None:
        """Tick every run the filter lists that can be read, in the order listed."""
        for r in self._listed():
            if not r["stale"] and r["name"] not in self.shown:
                self.shown.append(r["name"])
        self.render()

    def untick_listed(self) -> None:
        """Untick every run the filter lists; a run it does not list keeps its tick."""
        listed = {r["name"] for r in self._listed()}
        self.shown = [n for n in self.shown if n not in listed]
        self.render()

    def _on_wording(self, value: str) -> None:
        """The switch: every open chart and number card, the chart list and the compare table in
        the other words, kept in the address."""
        self.wording = value
        self._draw_tabs()
        self._draw_cards()
        self._draw_compare()
        self._draw_url()

    def _on_settings(self, value: str) -> None:
        self.settings_shown = value
        self._draw_compare()

    def _on_numbers_by(self, value: str) -> None:
        """The table's numbers by heading, by quantity or by statistic, kept in the address."""
        self.numbers_by = value
        self._draw_compare()
        self._draw_url()

    def _draw_compare(self) -> None:
        runs = self.shown_runs()
        constants = []
        for run in runs:
            record, _why = self._record_of(run)
            constants.append(getattr(record, "constants", None) if record is not None else None)
        declared = self._numbers_declared()
        rows = view.compare_rows(runs, self.form.fields, settings=self.settings_shown,
                                 constants=constants, declared=declared,
                                 words=self.wording, by=self.numbers_by)
        specs = [*(declared or []), *(spec for run in runs for spec in run["number_specs"])]
        self.numbers_row.visible = any(s.get("quantity") or s.get("statistic") for s in specs)
        self.compare_count.object = (f"<span style='{_DIM}'>"
                                     f"{html.escape(view.compare_count(rows, runs, self.form.fields))}"
                                     f"</span>")
        opened = {c.number for c in self.cards if c.kind == "numbers"}
        self.compare_table.param.update(
            heads=[r["name"] for r in runs],
            rows=[{**row, "open": row["kind"] == "number" and row["key"] in opened}
                  for row in rows])

    # ------------------------------------------------------------------ deleting
    def _ask_delete_run(self, name: str) -> None:
        path = f"{self.out_dir}/{self.piece['name']}/{name}"
        files = next((len(r["files"]) for r in self.runs() if r["name"] == name), 0)
        self._ask(say_n("messages.delete_ask_files", files, path=f"{path}.json",
                        folder=f"{path}.files/") if files
                  else say("messages.delete_ask", path=f"{path}.json"),
                  functools.partial(self._delete, records=[name]))

    def _ask(self, question: str, then: Callable[[], None]) -> None:
        self.question.object = f"<p style='font-size:14px'>{html.escape(question)}</p>"
        self._answer = then
        self.asking.show()

    def _on_yes(self) -> None:
        """Do what was asked, once: a second click that reaches here after the first has
        answered finds nothing left to do."""
        then, self._answer = self._answer, None
        self.asking.hide()
        if then is not None:
            then()

    def _on_no(self) -> None:
        self._answer = None
        self.asking.hide()

    def _ask_delete_folder(self, name: str) -> None:
        self._ask(say("messages.delete_ask_folder",
                      folder=f"{self.out_dir}/{self.piece['name']}/{name}/"),
                  functools.partial(self._delete, folders=[name]))

    def _draw_saved(self) -> None:
        """The folders of pictures a Save wrote, each with its date, what it holds and its
        pictures' names (BESS's ``_draw_saved``)."""
        n = len(self.folders)
        self.saved_count.object = (f"<span style='{_DIM}'>"
                                   f"{html.escape(say_n('saved.count', n))}</span>" if n else "")
        rows = []
        for f in self.folders:
            fields = {"when": _when(f["mtime"]),
                      "pictures": say_n("saved.pictures", len(f["pictures"]))}
            held = (say("saved.row_tables", tables=say_n("saved.tables", f["tables"]), **fields)
                    if f["tables"] else say("saved.row", **fields))
            rows.append({"name": f["name"], "when": held, "pictures": ", ".join(f["pictures"])})
        self.saved_list.rows = rows

    def _delete(self, records: tuple = (), folders: tuple = ()) -> None:
        try:
            gone = jobs.delete(self.piece["name"], records, folders, root=self.root,
                               out_dir=self.out_dir)
        except ValueError as exc:
            self.toast(say("messages.not_deleted", words=exc))
            return
        print("lab: deleted " + " ".join(gone))
        self.shown = [n for n in self.shown if n not in records]
        self.toast(say("messages.deleted", paths=" ".join(gone)))
        self.reload()

    # ------------------------------------------------------------------ the chart list
    def _numbers_declared(self) -> list[dict[str, Any]] | None:
        """The numbers the first shown run's record declares, read off it through its class --
        so a file written before its numbers were grouped is compared in its class's groups;
        ``None`` (the files' own headers) when it does not load."""
        runs = self.shown_runs()
        record = self._record_of(runs[0])[0] if runs else None
        if record is None:
            return None
        return [dataclasses.asdict(n) for n in record.number_specs()]

    def _drawable(self, run: dict[str, Any]) -> dict[str, Any]:
        """``run`` with the charts it can draw and their groups as its record's class declares
        them now, read through the class (:meth:`_record_of`, once per version of its file). Read
        off the file, a chart change left every saved run's list behind: the list offered charts
        the code no longer drew and none it now did (RCWS #257). A run that does not load keeps
        its file's list; its card says why."""
        record = self._record_of(run)[0]
        if record is None:
            return run
        hit = self._loaded.get(run["path"])
        if hit is not None and hit[1] is record:
            panels, groups, titles, symbols = hit[3]          # read once with the record
        else:
            panels, groups, titles, symbols = _declared(record)
        return {**run, "panels": panels, "panel_groups": groups, "panel_titles": titles,
                "panel_symbols": symbols}

    def _shown_drawable(self) -> list[dict[str, Any]]:
        return [self._drawable(run) for run in self.shown_runs()]

    def _draw_tabs(self) -> None:
        """The charts the shown runs declare, each a toggle, in the groups and the order their
        records' class declares them: an index of the groups by name, then each group on lines
        of its own, its words before it, while its name in the index shows it. This list
        re-sorts nothing.

        The toggles are built again only when what the list holds changes -- its charts, their
        groups and notes, whether a run is shown; anything else, their titles among it, sets the
        toggles already there. Built again on every click, a click landing while the page drew
        the new ones was lost: 2 of 5 charts clicked 80 ms apart in headless Chromium
        (2026-10-27; RCWS #256, 4 of 5). Built again on the Names / Symbols switch, a Save
        pressed as the switch drew raised plotly's "_guiEditing" error in the browser, 3 of 8
        tries (2026-11-21); set in place, none of 6."""
        rows = view.chart_rows(self._shown_drawable(), self.open_charts, words=self.wording)
        holds = tuple((r["name"], r["group"], r["sub"]) for r in rows)
        if holds != self._tabs_hold:
            self._tabs_hold = holds
            self._build_tabs(rows)
        self._set_tabs(rows)

    def _build_tabs(self, rows: list[dict[str, Any]]) -> None:
        """The list's toggles, the index and each group's line, built and put on the page. Each
        toggle as wide as its name with its note under it, growing with the others on its line
        until the line is full; each group on lines of its own, its words in a column before it
        (RCWS ``_build_tabs``, the developer's: groups flowing on from one another mixed on a
        line)."""
        self._chart_toggles, self._chart_cells, self._lines, self._index_toggles = {}, {}, {}, {}
        cells: dict[str, list[Any]] = {}
        for group, in_group in view.grouped(rows):
            for row in in_group:
                toggle = _tab(row["title"], row["open"])
                toggle.param.watch(lambda e, n=row["name"]: self._on_chart(n, e.new), "value")
                self._chart_toggles[row["name"]] = toggle
                self._chart_cells[row["name"]] = cell = _tab_cell(toggle, row["sub"])
                cells.setdefault(group, []).append(cell)
        named = [group for group in cells if group]
        self.show_all.visible = self.hide_all.visible = bool(named)
        if not rows:
            items: list[Any] = [_html(html.escape(say("figures.empty")), style=_DIM)]
        elif not named:
            items = [pn.FlexBox(*cells.get("", []), align_items="flex-start", margin=0,
                                gap="0 2px", sizing_mode="stretch_width")]
        else:
            for group, in_line in cells.items():
                self._lines[group] = pn.FlexBox(
                    _html(html.escape(group), style=_LABEL, width=_GROUP_PX, margin=(3, 4, 0, 2)),
                    pn.FlexBox(*in_line, align_items="flex-start", margin=0, gap="0 2px",
                               styles={"flex": "1 1 0", "min-width": "0"}),
                    flex_wrap="nowrap", align_items="flex-start", margin=0,
                    sizing_mode="stretch_width")
            items = [self._index(named), *self._lines.values()]
        self.tabs.objects = items

    def _set_tabs(self, rows: list[dict[str, Any]]) -> None:
        """What the list's toggles say: which charts are open, which groups the index shows, and
        how many charts are open of how many. A toggle set to what its card already is changes
        nothing (:meth:`_on_chart`, :meth:`_on_group` return)."""
        for row in rows:
            toggle = self._chart_toggles[row["name"]]
            if toggle.label != row["title"]:          # the switch: other words, the same list
                toggle.label = row["title"]
                self._chart_cells[row["name"]].width = _tab_width(row["title"])
            toggle.value = row["open"]
        if self._index_toggles:
            shown = self._groups_on_show(rows)
            for group, toggle in self._index_toggles.items():
                on = group in shown
                toggle.param.update(value=on, label=f"{'▾' if on else '▸'} {group}")
            for group, line in self._lines.items():
                line.visible = not group or group in shown
        self.open_count.object = (f"<span style='{_DIM}'>"
                                  f"{html.escape(say('figures.open', open=len(self.open_charts), total=len(rows)))}"
                                  f"</span>")

    def _groups_on_show(self, rows: list[dict[str, Any]]) -> set[str]:
        """The groups the list shows below its index: the ones the developer showed, and the
        group of every chart opened since the list was last drawn -- by its toggle, by the
        address, or as the first chart a page opens on. Hiding a group closes nothing."""
        group_of = {row["name"]: row["group"] for row in rows}
        for card in self.cards:
            if card.kind == "chart" and card.id not in self._groups_met and card.chart in group_of:
                self._groups_met.add(card.id)
                self._groups_shown.add(group_of[card.chart])
        return self._groups_shown

    def _index(self, named: list[str]) -> pn.FlexBox:
        """The list's groups by name, read down :data:`_INDEX_COLUMNS` columns, each name a
        toggle that shows its group's lines below -- "▾" while it does, "▸" while not
        (:meth:`_set_tabs`). RCWS #255: 45 charts in 15 groups, every group shown, put the first
        chart below the bottom of a 1700 x 1100 window."""
        per_column = -(-len(named) // _INDEX_COLUMNS)

        def entry(group: str) -> pn.widgets.Toggle:
            toggle = pn.widgets.Toggle(label=f"▸ {group}", value=False, margin=0,
                                       sizing_mode="stretch_width", css_classes=["index"],
                                       stylesheets=[skin.WIDGET, skin.INDEX])
            toggle.param.watch(lambda e, g=group: self._on_group(g, e.new), "value")
            self._index_toggles[group] = toggle
            return toggle

        columns = [pn.Column(*(entry(g) for g in named[c * per_column:(c + 1) * per_column]),
                             margin=0, styles={"flex": "1 1 0", "min-width": "0"})
                   for c in range(_INDEX_COLUMNS)]
        return pn.FlexBox(*columns, flex_wrap="nowrap", align_items="flex-start", gap="0 16px",
                          margin=(0, 2, 6, 2), sizing_mode="stretch_width", styles=skin.INDEX_BOX)

    def _on_group(self, group: str, show: bool) -> None:
        if show == (group in self._groups_shown):
            return
        if show:
            self._groups_shown.add(group)
        else:
            self._groups_shown.discard(group)
        self._draw_tabs()

    def _show_groups(self, every: bool) -> None:
        """show all / hide all: every group the list holds on show below its index, or none."""
        self._groups_shown.clear()
        if every:
            self._groups_shown.update(group for group in self._lines if group)
        self._draw_tabs()

    def group_toggles(self) -> dict[str, pn.widgets.Toggle]:
        """The index's toggles on screen, by group."""
        return dict(self._index_toggles)

    def toggles(self) -> dict[str, pn.widgets.Toggle]:
        """The chart toggles on screen, by panel -- a hidden group's among them."""
        return dict(self._chart_toggles)

    def _open(self, chart: str) -> shaping.Card:
        self._seq += 1
        card = shaping.Card(self._seq, "chart", chart=chart)
        self.cards.append(card)
        return card

    def _on_chart(self, panel: str, open_it: bool) -> None:
        opened = next((c for c in self.cards if c.kind == "chart" and c.chart == panel), None)
        if open_it and opened is None:
            self._open(panel)
        elif not open_it and opened is not None:
            self.cards.remove(opened)
        else:
            return
        self._draw_tabs()
        self._draw_cards()
        self._draw_url()

    def open_number(self, number: str) -> None:
        """A number of the compare table, as a card of its own over the shown runs; asked
        again, the card closes."""
        opened = next((c for c in self.cards if c.kind == "numbers" and c.number == number), None)
        if opened is not None:
            self.cards.remove(opened)
        else:
            self._seq += 1
            self.cards.insert(0, shaping.Card(self._seq, "numbers", number=number))
        self._draw_compare()
        self._draw_cards()

    # ------------------------------------------------------------------ the cards
    def _pairs(self, names: Optional[list[str]] = None) -> tuple[list[tuple[str, Any]], list[str]]:
        """``(name, record)`` for every shown run that loads, and, for every one that does not,
        why -- in the loader's own words."""
        pairs, words = [], []
        for run in self.shown_runs():
            record, why = self._record_of(run)
            if record is None:
                words.append(f"{run['name']}: {why}")
            else:
                pairs.append((run["name"], record))
        return pairs, words

    def _draw_cards(self) -> None:
        """One card per open chart and number: the numbers first, then the charts in the order
        the records declare them."""
        runs = self.shown_runs()
        self.drawn, self._panes = {}, {}
        live = {card.id for card in self.cards}
        self._kept = {key: part for key, part in self._kept.items() if key[0] in live}
        self._save_args = {key: held for key, held in self._save_args.items() if key in live}
        if not runs:
            self.cards_box.objects = [_html(html.escape(say("cards.empty_runs")), style=_DIM)]
            return
        if not self.cards:
            self.cards_box.objects = [_html(html.escape(say("cards.empty")), style=_DIM)]
            return
        declared = [row["name"] for row in view.chart_rows([self._drawable(r) for r in runs],
                                                            self.open_charts)]
        place = {name: i for i, name in enumerate(declared)}
        numbers = [c for c in self.cards if c.kind == "numbers"]
        charts = sorted((c for c in self.cards if c.kind == "chart"),
                        key=lambda c: (place.get(c.chart, len(place)), c.id))
        self.cards_box.objects = [self._card_view(card) for card in numbers + charts]

    def _card_view(self, card: shaping.Card) -> pn.Column:
        pairs, refused = self._pairs()
        if card.kind == "numbers":
            return self._numbers_view(card, pairs, refused)
        if any(f.name == card.chart for _, record in pairs for f in record.figures()):
            return self._own_view(card, pairs, refused)
        return self._chart_view(card, pairs, refused)

    def _frame(self, card: shaping.Card, title: str, tools: list[Any], body: Any,
               foot: str, warn: bool, save: Optional[Any] = None) -> pn.Column:
        """A card: its title, Save and close at the line's end; then its controls, one row of
        groups, a whole group wrapping onto the next line when the card is too narrow for it;
        then what it draws; then a foot -- why it could not draw, else what its last Save
        wrote or why that wrote nothing. No hover: the title is the chart's or the number's
        own words."""
        close, new = self._keep((card.id, "close"), lambda: _widget(
            pn.widgets.Button, label=say("cards.close"), width=34))
        if new:
            close.on_click(lambda _e: self._close(card))
        # the panel's name rides on the title as data-panel: the tests found a card by its
        # title's text, which found none once a title showed words, not the name (2026-10-27)
        heading = self._keep((card.id, "title"), lambda: _html("", stylesheets=[skin.BAR_FILL]))[0]
        heading.object = (f"<span><b data-panel='{html.escape(card.chart or card.number)}' "
                          f"style='{_MONO};font-size:15px'>{html.escape(title)}</b></span>")
        top = self._keep((card.id, "top"), lambda: pn.FlexBox(
            flex_wrap="nowrap", align_items="center", margin=0, stylesheets=[skin.BAR],
            sizing_mode="stretch_width"))[0]
        top.objects = [heading, *([save] if save is not None else []), close]
        items: list[Any] = [top]
        if tools:
            items.append(pn.FlexBox(*tools, flex_wrap="wrap", align_items="center", margin=0,
                                    gap="4px 8px", stylesheets=[skin.BAR],
                                    sizing_mode="stretch_width"))
        items.append(body)
        words, red = (foot, warn) if foot else (card.saved, card.save_failed)
        if words:
            items.append(_html(html.escape(words),
                               style=f"font-size:12.5px;{_RED if red else _DIM}"))
        return self._box((card.id, "box"), items, styles=skin.CARD)

    def _keep(self, key: tuple, make: Callable[[], Any]) -> tuple[Any, bool]:
        """The part kept under ``key`` (a card's id first), made by ``make`` the first time; and
        whether it is new."""
        part = self._kept.get(key)
        if part is not None:
            return part, False
        part = self._kept[key] = make()
        return part, True

    def _box(self, key: tuple, items: list[Any], **kw: Any) -> pn.Column:
        """The box kept under ``key``, holding ``items``: the same box from one drawing to the
        next, so what it holds that stays the same stays in the browser too."""
        box = self._keep(key, lambda: pn.Column(sizing_mode="stretch_width", **kw))[0]
        box.objects = items
        return box

    def _plot(self, key: tuple, fig: dict[str, Any]) -> tuple[pn.pane.Plotly, bool]:
        """The plot kept under ``key``, showing ``fig``, and whether it is new: one kept is given
        the figure where it stands."""
        pane, new = self._keep(key, lambda: pn.pane.Plotly(
            fig, config=_PLOT_CONFIG, sizing_mode="stretch_width", height=fig["layout"]["height"]))
        if not new:
            pane.param.update(object=fig, height=fig["layout"]["height"])
        return pane, new

    def _toolbar(self, card: shaping.Card, ctx: shaping.Context) -> list[Any]:
        """The card's controls, one per way it shapes what it draws, in the groups and the order
        :data:`lab.shaping.SHAPINGS` declares, each group one box that stays whole -- every
        control on every card, greyed with the reason on its hover where it cannot be used
        right now. A greyed control is its words and nothing to click, the reason its hover:
        a disabled Panel widget would show none."""
        groups: dict[int, list[Any]] = {}
        for s, why in shaping.offered(card, ctx):
            value, options = s.shown(card, ctx), s.options(card, ctx)
            cell: list[Any] = []
            words = say(s.slot) if s.slot else ""
            if words and s.kind != "switch":
                cell.append(_html(html.escape(words), style=_LABEL, margin=(0, 2, 0, 4)))
            if why:
                said = ([words] if s.kind == "switch"
                        else [next((w for w, v, _ in options if v == value), "")] if s.kind == "list"
                        else [" | ".join(w for w, _, _ in options)])
                # a control with nothing of its own to grey (no setting to colour by) greys
                # its label, so the reason still has a hover to stand on
                if not any(said):
                    said, cell = [words], []
                cell += [_html(html.escape(w), title=capital(why), style=skin.GREYED,
                               margin=_TOOL_MARGIN)
                         for w in said if w]
            elif s.kind == "switch":
                toggle = _tool(pn.widgets.Toggle, label=words, value=bool(value),
                               width=_width(words))
                toggle.param.watch(functools.partial(self._on_shaping, card, s.field), "value")
                cell.append(toggle)
            elif s.kind == "list":
                shows = next((w for w, v, _ in options if v == value), "")
                select = _tool(pn.widgets.Select, options={w: v for w, v, _ in options},
                               value=value if value in [v for _, v, _ in options] else None,
                               width=max(80, min(200, 40 + 8 * len(shows))))
                select.param.watch(functools.partial(self._on_shaping, card, s.field), "value")
                cell.append(select)
            elif s.kind == "one":
                for words, option, greyed in options:
                    if greyed:
                        cell.append(_html(html.escape(words), title=capital(greyed),
                                          style=skin.GREYED,
                                          margin=_TOOL_MARGIN))
                        continue
                    toggle = _tool(pn.widgets.Toggle, label=words, value=option == value,
                                   width=_width(words))
                    toggle.param.watch(functools.partial(self._on_one, card, s.field, option),
                                       "value")
                    cell.append(toggle)
            elif s.kind == "several":
                for words, option, _ in options:
                    toggle = _tool(pn.widgets.Toggle, label=words, value=option in value,
                                   width=_width(words))
                    toggle.param.watch(functools.partial(self._on_several, card, s.field,
                                                         option, tuple(value)), "value")
                    cell.append(toggle)
            else:
                raise ValueError(f"a card control of kind {s.kind!r}: lab.shaping declares "
                                 f"'list', 'switch', 'one' and 'several'")
            groups.setdefault(s.group, []).extend(cell)
        # Each group as wide as its controls and kept whole: a FlexBox stretches across what
        # holds it by default, which put each group on a line of its own (seen 2026-10-27 at
        # 1440 px; RCWS `_cell`).
        return [pn.FlexBox(*groups[g], flex_wrap="nowrap", align_items="center", margin=0,
                           sizing_mode=None, styles=skin.GROUP if i else {},
                           stylesheets=[skin.BAR])
                for i, g in enumerate(sorted(groups))]

    def _on_shaping(self, card: shaping.Card, name: str, event: Any) -> None:
        setattr(card, name, event.new)
        self._draw_cards()

    def _on_one(self, card: shaping.Card, name: str, option: Any, event: Any) -> None:
        """One of a few: pressed, the card takes it; pressed off, nothing changes (one of them
        is always held)."""
        if event.new:
            setattr(card, name, option)
        self._draw_cards()

    def _on_several(self, card: shaping.Card, name: str, option: Any, held: tuple,
                    event: Any) -> None:
        """Any of a few: pressed, the card holds it with the others; pressed off, without it."""
        chosen = tuple(v for v in held if v != option) + ((option,) if event.new else ())
        setattr(card, name, chosen)
        self._draw_cards()

    def _chart_context(self, card: shaping.Card, pairs: list[tuple[str, Any]]) -> shaping.Context:
        """What the chart card's controls are read off: the figure layer's own answers, over
        the shown runs that declare the chart."""
        held = [(n, r) for n, r in pairs if series_of(r, card.chart) is not None]
        if not held:
            return shaping.Context("chart", runs=0)
        first = series_of(held[0][1], card.chart).in_words(self.wording)
        pool = {how: pool_refusal(held, card.chart, how) for how in ("mean", "rms")}
        axes = {first.x_label: "own"}
        axes.setdefault(INDEX_LABEL, "index")
        # over the sample index the chart declares no logarithm: its own was of its abscissa
        own = (card.x or "own") == "own"
        ctx = shaping.Context("chart", runs=len(held), axes=axes, pool=pool,
                              declared_x_log=first.x_log and own, declared_y_log=first.y_log)
        base = {**shaping.draw_keywords(card, ctx), "x_log": False, "y_log": False}
        try:
            plain = chart_of(held, card.chart, **base)
        except ValueError:
            # not hidden: the view builds the chart again and writes the refusal under the card
            return ctx
        return dataclasses.replace(ctx, x_log_refusal=log_refusal(plain, "x"),
                                   y_log_refusal=log_refusal(plain, "y"))

    def _chart_view(self, card: shaping.Card, pairs: list[tuple[str, Any]],
                    refused: list[str]) -> pn.Column:
        """A panel over the shown runs that declare it, drawn by the figure layer from what the
        card's controls hold. The foot names every shown run the card leaves out: one that does
        not load, in the loader's words, and one that declares no such panel (the developer's
        design of 2026-11-13: "a chart card that says which run it leaves out")."""
        ctx = self._chart_context(card, pairs)
        held = [(n, r) for n, r in pairs if series_of(r, card.chart) is not None]
        without = [n for n, r in pairs if series_of(r, card.chart) is None]
        declared = next((series_of(r, card.chart) for _, r in held), None)
        body: Any = pn.pane.HTML("")
        save = None
        words = list(refused)
        if without and held:
            words.append(say_n("cards.chart_without", len(without), runs=", ".join(without)))
        foot, warn = " · ".join(words), bool(words)
        if ctx.runs:
            # the words only when they are symbols: a picture saved in names, and its note, are
            # what they were before the switch
            keywords = {**shaping.draw_keywords(card, ctx),
                        **({"words": self.wording} if self.wording != "names" else {})}
            # a zoom is kept by the bottom axis's words in names, so the switch keeps it
            axis = declared.x_label if (card.x or "own") == "own" else INDEX_LABEL
            try:
                panel = chart_of(held, card.chart, **keywords)
            except ValueError as exc:
                foot, warn = capital(str(exc)), True
            else:
                body = self._body(card, panel, axis=axis)
                self.drawn[card.id] = [n for n, _ in held]
                save = self._save_button(card, [n for n, _ in held], keywords,
                                         panels=(card.chart,), axis=axis,
                                         x_log=panel.x_log)
        # a card no shown run draws has nothing to shape: no controls, where an X with no
        # axis to offer would be an empty list
        return self._frame(card, declared.in_words(self.wording).title if declared else card.chart,
                           self._toolbar(card, ctx) if ctx.runs else [], body, foot, warn, save)

    def _own_view(self, card: shaping.Card, pairs: list[tuple[str, Any]],
                  refused: list[str]) -> pn.Column:
        """A figure the piece draws itself, once per shown run that declares it, each under its
        run's name where there is more than one: the page cannot merge what only the piece can
        read (the developer, 2026-11-17). A shown run that declares no
        such figure is named in the foot. The card's control is every chart card's, greyed."""
        held = [(name, own_figure(record, card.chart)) for name, record in pairs]
        drawn = [(name, fig) for name, fig in held if fig is not None]
        without = [name for name, fig in held if fig is None]
        title = next((f.title for _, record in pairs for f in record.figures()
                      if f.name == card.chart), card.chart)
        rows: list[Any] = []
        for name, fig in drawn:
            if len(pairs) > 1:
                dot = _colour(self.shown.index(name)) if name in self.shown else ""
                rows.append(_html(f"<span style='color:{dot}'>●</span> "
                                  f"<span data-run='{html.escape(name)}'>{html.escape(name)}</span>",
                                  style=_LABEL, margin=(6, 0, 0, 4)))
            rows.append(self._plot((card.id, "plot", name), fig)[0])
        body: Any = self._box((card.id, "own"), rows, margin=0) if rows else pn.pane.HTML("")
        words = list(refused)
        if without:
            words.append(say_n("cards.own_without", len(without), runs=", ".join(without)))
        self.drawn[card.id] = [name for name, _ in drawn]
        ctx = shaping.Context("own", runs=len(drawn))
        return self._frame(card, title, self._toolbar(card, ctx), body, " · ".join(words),
                           bool(words))

    def _numbers_context(self, card: shaping.Card,
                         pairs: list[tuple[str, Any]]) -> shaping.Context:
        fields = {f["name"]: f for f in self.form.fields}
        vary = distinct(pairs) if len(pairs) > 1 else []
        if card.x not in vary:
            card.x = vary[0] if vary else ""
        axes = {view.term(fields[v]): v for v in vary}
        ctx = shaping.Context("numbers", runs=len(pairs), axes=axes, declared_points=True)
        if not card.x:
            return ctx
        tell = {fields[v]["label"]: v for v in telling(pairs, card.x)}
        ctx = dataclasses.replace(ctx, telling=tell)
        each = {**shaping.draw_keywords(card, ctx), "runs": "each", "x_log": False,
                "y_log": False}
        try:
            plain = sweep_of(pairs, card.number, **each)
        except ValueError:
            return ctx
        pools = any(len(set(line.x)) < len(line.x) for line in plain.axes[0].lines)
        return dataclasses.replace(ctx, pools=pools, x_log_refusal=log_refusal(plain, "x"),
                                   y_log_refusal=log_refusal(plain, "y"))

    def _numbers_view(self, card: shaping.Card, pairs: list[tuple[str, Any]],
                      refused: list[str]) -> pn.Column:
        """A summary number against the setting that varies, every shown run a point, drawn by
        the figure layer from what the card's controls hold."""
        ctx = self._numbers_context(card, pairs)
        spec = next((n for _, r in pairs for n in r.number_specs() if n.name == card.number), None)
        title = spec.in_words(self.wording).label if spec else card.number
        fields = {f["name"]: f for f in self.form.fields}
        if card.x:
            title = say("cards.number_title", number=title, setting=fields[card.x]["label"])
        body: Any = pn.pane.HTML("")
        save = None
        foot, warn = " · ".join(refused), bool(refused)
        if not card.x:
            foot, warn = say("cards.number_foot"), True
        else:
            # the words only when they are symbols, as a chart card's (a picture saved in names
            # and its note are as before)
            keywords = {**shaping.draw_keywords(card, ctx),
                        **({"words": self.wording} if self.wording != "names" else {})}
            try:
                panel = sweep_of(pairs, card.number, **keywords)
            except ValueError as exc:
                foot, warn = capital(str(exc)), True
            else:
                body = self._body(card, panel)
                self.drawn[card.id] = [n for n, _ in pairs]
                save = self._save_button(card, [n for n, _ in pairs], keywords,
                                         number=card.number)
        return self._frame(card, title, self._toolbar(card, ctx), body, foot, warn, save)

    def _body(self, card: shaping.Card, panel: Any, axis: str = "") -> Any:
        """What a card shows: the figure layer's chart, as its live twin, or -- its table
        picked -- the numbers on it, read off the same panel (``figure.render.table_of``), at
        six significant digits (BESS's ``_body``). A chart is drawn at the span a zoom left on
        its bottom axis, and its own zooms are heard (:meth:`_on_zoom`); a number card's bottom
        axis is a setting, so it is neither, and a table has no axis to zoom."""
        if card.table:
            table = table_of(panel)
            head = "".join(f"<th>{html.escape(str(h))}</th>" for h in table.header)
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(_six(v))}</td>" for v in row)
                           + "</tr>" for row in table.rows)
            beside = "".join(f"<div>{html.escape(w)}: {', '.join(_six(v) for v in vals)}</div>"
                             for w, vals in table.beside)
            note = f"<div class='dim'>{html.escape(say('cards.table_digits'))}</div>"
            return pn.pane.HTML(
                f"<div class='numbers' style='max-height:{_TABLE_PX}px'><table><thead><tr>{head}"
                f"</tr></thead><tbody>{rows}</tbody></table></div>"
                f"<div class='beside'>{beside}{note}</div>",
                stylesheets=[skin.NUMBERS], sizing_mode="stretch_width")
        # a number card draws no legend: the hover names each point's run (RCWS)
        fig = figure_of(panel, legend=card.kind != "numbers")
        linked = card.kind == "chart"
        key = axis or panel.x_label          # the words a zoom on this chart is kept by
        ends = _span_on(self._ranges.get(key), panel.x_log) if linked else None
        if ends:
            fig["layout"]["xaxis"] = {**fig["layout"]["xaxis"], "range": ends,
                                      "autorange": False}
        pane, new = self._plot((card.id, "plot"), fig)
        if linked:
            if new:
                pane.param.watch(lambda e, key=card.id: self._on_zoom(key, e.new), "relayout_data")
            self._panes[card.id] = (pane, key, panel.x_log)
        return pane

    # ------------------------------------------------------------------ save: the card, as shown
    def _save_button(self, card: shaping.Card, names: list[str], keywords: dict[str, Any], *,
                     panels: tuple = (), number: str = "", axis: str = "",
                     x_log: bool = False) -> Any:
        """Save, for a card that draws: ``names`` the runs it draws and ``keywords`` what its
        controls hold, as the card was just drawn from them. ``axis``, the words of a chart's
        bottom axis: the span the page is on for it is read when Save is pressed, because a
        zoom reaches the chart without building the card again (BESS's ``_save_button``)."""
        self._save_args[card.id] = (names, keywords, panels, number, axis, x_log)
        save, new = self._keep((card.id, "save"), lambda: _widget(
            pn.widgets.Button, label=say("cards.save"), width=_width(say("cards.save")) + 16))
        if new:
            save.on_click(lambda _e: self._save(card, *self._save_args[card.id]))
        return save

    def _save(self, card: shaping.Card, names: list[str], keywords: dict[str, Any],
              panels: tuple, number: str, axis: str, x_log: bool) -> None:
        """Write the card's picture as it is shown, and with its table picked its numbers too,
        into the folder beside the runs that is named after them -- where the command's
        ``draw`` writes (``cli.folder_of``). The figure layer writes it, from the keywords the
        card's chart was built from, in this process: nothing is started and no command is
        read (the developer's answer of 2026-11-18; BESS's page starts its ``draw`` command).
        What it wrote, or why it wrote nothing, stands under the card."""
        shaped = dict(keywords)
        ends = _span_on(self._ranges.get(axis), x_log) if axis else None
        if ends:
            # the span in the axis's own units: plotly holds a logarithmic axis's as powers of ten
            shaped["x_range"] = tuple(10.0 ** float(e) if x_log else float(e) for e in ends)
        piece = self.piece["name"]
        where = os.path.join(self.out_dir, piece, folder_of(names))
        loaded = dict(self._pairs()[0])
        try:
            gone = [name for name in names if name not in loaded]
            if gone:
                raise ValueError(say("messages.no_record", name=", ".join(gone)))
            if where.endswith(state.RUN_FILES):
                raise ValueError(say("messages.save_run_files", folder=f"{where}/"))
            pairs = [(name, loaded[name]) for name in names]
            folder = os.path.join(self.root, where)
            paths = (draw_sweep(pairs, folder, number, table=card.table, **shaped) if number
                     else draw(pairs, folder, panels=list(panels), table=card.table, **shaped))
        except (ValueError, OSError) as exc:
            card.saved, card.save_failed = say("cards.not_saved", words=exc), True
        else:
            wrote = " ".join(os.path.relpath(str(path), self.root) for path in paths)
            print(f"lab: wrote {wrote}")
            card.saved, card.save_failed = say("cards.wrote", files=wrote), False
        self.folders = state.folders(self.root, self.out_dir, piece)
        self._draw_saved()
        self._draw_cards()

    def _on_zoom(self, key: int, data: Any) -> None:
        """A zoom on one chart reaches every open chart over the same bottom axis, and a reset
        too; the span is kept for a chart drawn afterwards. A chart already on that span is
        not pushed, so a push cannot echo back (BESS's ``lab/app.py``, ``_on_relayout``). The
        span is kept as the chart reported it, with whether that chart was logarithmic: a card
        switches its own axis, so two charts over one axis may differ, and each is set the span
        in its own terms (:func:`_span_on`). A logarithmic chart shows the whole of its axis
        when the span reaches zero or below, and a reset made on it then reads as the echo of
        that and is not passed on."""
        if not isinstance(data, dict) or key not in self._panes:
            return
        _, label, x_log = self._panes[key]
        if "xaxis.range[0]" in data and "xaxis.range[1]" in data:
            span: Optional[tuple[list[Any], bool]] = (
                [data["xaxis.range[0]"], data["xaxis.range[1]"]], x_log)
        elif data.get("xaxis.autorange"):
            span = None
        else:
            return
        if _span_on(self._ranges.get(label), x_log) == (span[0] if span else None):
            return                                 # the echo of a push, or nothing new
        self._ranges[label] = span
        for other, (pane, other_label, other_log) in self._panes.items():
            if other == key or other_label != label:
                continue
            fig = pane.object
            xaxis = dict(fig["layout"].get("xaxis", {}))
            ends = _span_on(span, other_log)
            if ends is None:
                xaxis.pop("range", None)
                xaxis["autorange"] = True
            else:
                xaxis["range"], xaxis["autorange"] = ends, False
            pane.object = {**fig, "layout": {**fig["layout"], "xaxis": xaxis}}

    def _close(self, card: shaping.Card) -> None:
        if card in self.cards:
            self.cards.remove(card)
        self._draw_tabs()
        self._draw_cards()
        self._draw_compare()
        self._draw_url()

    # ------------------------------------------------------------------ the url
    def _read_url(self) -> None:
        """``?shown=a,b&open=soc`` on the way in: a hand-off is a link."""
        location = pn.state.location
        if location is None:
            return
        query = location.query_params or {}
        self.shown = [n for n in str(query.get("shown", "")).split(",") if n]
        self._asked_open = [p for p in str(query.get("open", "")).split(",") if p]
        self.wording = "symbols" if query.get("words") == "symbols" else "names"
        self.numbers_by = str(query.get("by")) if query.get("by") in view.BY else "heading"

    def _draw_url(self) -> None:
        location = pn.state.location
        if location is None:
            return
        try:
            location.update_query(shown=",".join(self.shown), open=",".join(self.open_charts),
                                  words=self.wording, by=self.numbers_by)
        except Exception as exc:  # noqa: BLE001         # the address bar is a convenience
            print(f"lab: the address could not be updated: {exc!r}", file=sys.stderr)

    # ------------------------------------------------------------------ the form
    def open_drawer(self, from_run: Optional[str] = None) -> None:
        """Open the form; from a run's ``use``, loaded with that run's settings."""
        if from_run is not None:
            self._use(from_run)
        said = say("form.from_run", run=self._from) if self._from else say("form.from_defaults")
        self.from_words.object = f"<span style='{_DIM}'>{html.escape(said)}</span>"
        self.drawer.visible = True

    def close_drawer(self) -> None:
        self.drawer.visible = False

    def _draw_form(self) -> None:
        self._controls.clear(); self._labels.clear(); self._notes.clear(); self._folds.clear()
        self._group_notes.clear()
        self._refused, self._sweep_refused = {}, ""
        groups: dict[str, list[Any]] = {}
        blocks: dict[str, list[Any]] = {}       # the row fields, full width under the grid
        for f in self.form.fields:
            cells = groups.setdefault(f["group"], [])
            if f.get("rows") or f.get("element_fields"):
                blocks.setdefault(f["group"], []).append(self._rows_block(f))
            else:
                cells.extend(self._field_cells(f))
        sections = []
        for g, cells in groups.items():
            note = _html("", style=_DIM)
            self._group_notes[g] = note
            grid = ([pn.GridBox(*cells, ncols=6, stylesheets=[skin.FORM_GRID],
                                sizing_mode="stretch_width")] if cells else [])
            body = pn.Column(*grid, *blocks.get(g, []), sizing_mode="stretch_width", margin=0)
            head: Any = _h2(g)
            if all(f.get("folded") for f in self.form.fields if f["group"] == g):
                body.visible = g in self._unfolded
                head = pn.widgets.Toggle(label=f"{'▾' if body.visible else '▸'} {g}",
                                         value=body.visible, margin=0, css_classes=["index"],
                                         stylesheets=[skin.WIDGET, skin.INDEX])
                head.param.watch(lambda e, g=g, body=body, head=head:
                                 self._on_fold(g, body, head, e.new), "value")
                self._folds[g] = head
            sections.append(pn.Column(pn.Row(head, note, stylesheets=[skin.BAR],
                                             sizing_mode="stretch_width"),
                                      body, sizing_mode="stretch_width", margin=(6, 0)))
        self.form_box.objects = sections
        self.sweep_field.options = {say("form.sweep_none"): "",
                                    **{words: n for n, words in self.form.axes()}}
        self._apply_gates()

    def _on_fold(self, group: str, body: pn.Column, head: Any, show: bool) -> None:
        """A folded group opened or closed: its settings shown or not, the arrow saying which."""
        (self._unfolded.add if show else self._unfolded.discard)(group)
        body.visible = show
        head.label = f"{'▾' if show else '▸'} {group}"

    def _offer_saved(self) -> None:
        """Each piece's readable saved runs, as the paths a setting naming one offers, from the
        records just read; each such pick refilled, holding what it held."""
        saved: dict[str, list[str]] = {}
        for r in self.records:
            if not r["stale"]:
                saved.setdefault(r["piece"], []).append(
                    f"{self.out_dir}/{r['piece']}/{r['name']}.json")
        self.form.saved = saved
        for f in self.form.fields:
            control = self._controls.get(f["name"])
            if not f.get("record_of") or control is None:
                continue
            self._filling = True
            try:
                control.options = {o["words"]: o["value"] for o in self.form.options(f) or []}
                control.value = self.form.set.get(f["name"], "")
            finally:
                self._filling = False

    def _rows_block(self, f: dict[str, Any]) -> Any:
        """A row field: its label, then its rows (a box per item, :class:`_Rows`; a table for a
        list of rows, :class:`_Table`), then its note."""
        name = f["name"]
        label = _html("", margin=0)
        self._labels[name] = label
        editor = (_Table if f.get("element_fields") else _Rows)(
            f, on_edit=lambda text, n=name: self._on_type(n, text))
        editor.value = self.form.set.get(name, "")
        self._controls[name] = editor
        return pn.Column(label, editor.view, self._note(name), sizing_mode="stretch_width",
                         margin=(0, 0, 8, 0))

    def _field_cells(self, f: dict[str, Any]) -> list[Any]:
        """A field as the THREE cells of a six-track grid: label, box with the range it declares
        and its note under it, unit (or nothing). The cells go into the grid themselves rather
        than into a row of their own, because a row is its own flex box and two rows share no
        geometry -- which is what left the boxes 196px apart across the sections, measured
        2026-10-05. Every cell is margin-free: the spacing is the grid's gaps, so the tracks are what they say they are."""
        name = f["name"]
        label = _html("", margin=0)
        self._labels[name] = label
        options = self.form.options(f)
        after: Any = pn.Spacer(height=0)             # the third track is never left unfilled
        if f.get("unit"):
            after = _html(html.escape(f["unit"]), margin=0,
                          style=f"{_MONO};font-size:11px;{_DIM};line-height:{skin.BOX_PX}px")
        if options is None:
            control = _widget(pn.widgets.TextInput, margin=0, sizing_mode="stretch_width",
                              placeholder=self.form.shown_default(f),
                              value=self.form.set.get(name, ""))
            control.param.watch(lambda e, n=name: self._on_type(n, e.new), "value_input")
        else:
            control = _widget(pn.widgets.Select, margin=0, sizing_mode="stretch_width",
                              options={o["words"]: o["value"] for o in options},
                              value=self.form.set.get(name, ""))
            control.param.watch(lambda e, n=name: self._on_pick(n, e.new), "value")
        self._controls[name] = control
        # the range under the box, not beside the unit: units of 11 characters already fill the
        # 48 px unit track, and one with its range ran to 19 (two projects, 2026-11-19)
        under = [_html(html.escape(interval(f)), margin=0, style=f"{_MONO};font-size:11px;{_DIM}")
                 ] if interval(f) else []
        return [label, pn.Column(control, *under, self._note(name), margin=0,
                                 sizing_mode="stretch_width"), after]

    def _note(self, name: str) -> pn.pane.HTML:
        """The line under a setting, hidden while it has nothing to say."""
        note = _html("", margin=0, visible=False)
        self._notes[name] = note
        return note

    def _apply_gates(self) -> None:
        """Every control's state is its field's own gate or the sweep row's axis, nothing else."""
        changed: dict[str, int] = {}
        for f in self.form.fields:
            name = f["name"]
            off, reason = self.form.state_of(f)
            control, label = self._controls[name], self._labels[name]
            control.disabled = off
            control.stylesheets = [skin.WIDGET, skin.CHANGED] if name in self.form.set \
                else [skin.WIDGET]
            style = (f"display:flex;align-items:center;min-height:{skin.BOX_PX}px;"
                     f"text-align:left;font-size:12.5px;"
                     f"color:{skin.INK if name in self.form.set else skin.INK2};"
                     + ("opacity:.45" if off else ""))
            label.object = (f"<span style=\"{style}\">"
                            f"{html.escape(f['label'])}</span>")      # the unit sits by the box
            refused = self._refused.get(name, "")
            note = self._notes[name]
            note.object = (f"<span style='{_RED if refused else _DIM};font-size:12px'>"
                           f"{html.escape(refused or reason)}</span>")
            note.visible = bool(refused or reason)
            changed[f["group"]] = changed.get(f["group"], 0) + (name in self.form.set)
        for g, note in self._group_notes.items():
            total = sum(1 for f in self.form.fields if f["group"] == g)
            moved = changed.get(g, 0)
            note.object = (f"<span style='color:{skin.ACCENT if moved else skin.INK3};"
                           f"font-size:12px'>"
                           + html.escape(say("form.group_changed", changed=moved, total=total)
                                         if moved else say("form.group_defaults", total=total))
                           + "</span>")
        note_words, warns = self.form.note()
        self.form_note.object = (f"<span style='{_RED if warns else _DIM}'>"
                                 f"{html.escape(note_words)}</span>")
        self.sweep_note.object = f"<span style='{_RED}'>{html.escape(self._sweep_refused)}</span>"
        self.sweep_note.visible = bool(self._sweep_refused)
        self._draw_typed()

    def _fill_controls(self) -> None:
        """Push the form's values into the widgets without the watchers reading it as typing; a
        saved run's pick is offered again first, so the path it now holds is one it offers.
        What a Run refused in the values these replace is said no more."""
        self._refused, self._sweep_refused = {}, ""
        self._offer_saved()
        self._filling = True
        try:
            for name, control in self._controls.items():
                self._write(control, self.form.set.get(name, ""))
            self.sweep_field.value = self.form.sweep_field
            self._write(self.sweep_values, self.form.sweep_values)
            self._write(self.run_name, self.form.name)
        finally:
            self._filling = False
        self._apply_gates()
        self._draw_names()

    @staticmethod
    def _write(control: Any, text: str) -> None:
        """Put ``text`` in a control and in every parameter a watcher reads, so what the box
        shows and what the run would use cannot drift apart."""
        control.value = text
        if hasattr(control, "param") and "value_input" in control.param:
            control.value_input = text

    def _taken(self) -> list[dict[str, Any]]:
        """The names a new run of this piece cannot take quietly: its records on disk, and the
        runs of it queued or running."""
        busy = self.queue.in_progress(self.piece["name"], self.root, self.out_dir)
        return self.runs() + [{"piece": self.piece["name"], "name": n} for n in sorted(busy)]

    def _draw_names(self) -> None:
        self.run_name.placeholder = self.form.free_name(self._taken())
        note = self.form.name_note(self.runs())
        self.name_note.object = f"<span style='{_RED if note else _DIM}'>{html.escape(note)}</span>"
        self._draw_typed()

    def _draw_typed(self) -> None:
        """Why Run would be refused, live, in the words of what refuses it; nothing when it
        would not. What the settings themselves refuse, Run says under each (:meth:`_run`)."""
        try:
            self._planned()
        except ValueError as exc:
            self._say(say("form.refused", words=exc))
            return
        self._say("")

    def _planned(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """The runs Run would queue -- the record name and the setting pairs of each, a sweep's
        named as the command line names them -- every word checked; refused in words."""
        overrides, sweeps = self.form.launch_words()
        name = self.form.name.strip() or self.form.free_name(self._taken())
        runs = jobs.checked(self.piece["name"], planned(name, overrides, sweeps))
        self.queue.check_free(self.piece["name"], [n for n, _ in runs], root=self.root,
                              out_dir=self.out_dir)
        return runs

    # ------------------------------------------------------------------ typing
    def _on_type(self, name: str, text: str) -> None:
        if self._filling:
            return
        self._refused.pop(name, None)
        taken = self.form.type_or_pick(name, text)
        self._taken_back(taken)
        self._apply_gates()

    def _on_pick(self, name: str, value: str) -> None:
        if self._filling:
            return
        self._refused.pop(name, None)
        taken = self.form.type_or_pick(name, value)
        self._taken_back(taken)
        self._apply_gates()

    def _on_sweep(self, *, field: Optional[str] = None, values: Optional[str] = None) -> None:
        if self._filling:
            return
        self._sweep_refused = ""
        taken = self.form.sweep(self.form.sweep_field if field is None else field,
                                self.form.sweep_values if values is None else values)
        self._taken_back(taken)
        self._apply_gates()
        self._draw_names()                      # a sweep renames what the run would write

    def _taken_back(self, names: list[str]) -> None:
        """A box behind a gate that just shut is shown empty, not holding a value Run would refuse,
        nor what Run refused in it."""
        if not names:
            return
        for n in names:
            self._refused.pop(n, None)
        self._filling = True
        try:
            for n in names:
                self._write(self._controls[n], "")
        finally:
            self._filling = False

    def _on_name(self, text: str) -> None:
        if self._filling:
            return
        self.form.name = text
        self._draw_names()

    def _use(self, run_name: str) -> None:
        run = next((r for r in self.runs() if r["name"] == run_name), None)
        if run is None:
            self._say(say("messages.no_record", name=repr(run_name)))
            return
        n, dropped = self.form.use(run["config"])
        self._from = run_name
        self._fill_controls()
        words = say_n("messages.loaded", n, run=run_name)
        if dropped:
            words += "; " + say("messages.no_longer_declared", settings=", ".join(dropped))
        if self.form.taken:
            words += "; " + say("messages.taken_back", n=len(self.form.taken))
        self.toast(words)

    def _clear(self) -> None:
        self.form.clear()
        self._from = None
        self.from_words.object = f"<span style='{_DIM}'>{html.escape(say('form.from_defaults'))}</span>"
        self._fill_controls()

    def _on_piece(self, name: str) -> None:
        self.piece = next(p for p in self.pieces if p["name"] == name)
        self.form = Form(self.piece)
        # every one of these is keyed by a bare run name, which belongs to the piece it came from
        self.shown, self.cards, self._loaded, self._from = [], [], {}, None
        self._groups_shown, self._groups_met, self._tabs_hold = set(), set(), None
        self._unfolded, self._ranges = set(), {}
        self._draw_form()
        # the name and sweep boxes outlive a form: unwritten, they kept the last piece's words,
        # which the next Run no longer used (2026-11-14, found driving 2b's hand-off)
        self._clear()
        self.reload()

    # ------------------------------------------------------------------ running
    def _say(self, words: str) -> None:
        self.banner.object = f"<b>{html.escape(words)}</b>"
        self.banner.visible = bool(words)

    def _run(self) -> None:
        """Queue the form's runs, a sweep's side by side; Run never waits for the last one. A
        value its setting refuses -- out of its range, or not what it reads -- is said under
        the setting, or under the sweep row, and nothing is queued."""
        self._refused, self._sweep_refused = jobs.refusals(
            self.piece["name"], self.form.set, self.form.swept(), self.form.rungs())
        if self._refused or self._sweep_refused:
            # a refusal in a folded group was said on no line the page showed: Run changed
            # nothing on screen (2b review, 2026-11-14)
            for group in {self.form.by_name[n]["group"] for n in self._refused}:
                if group in self._folds:
                    self._folds[group].value = True
            self._apply_gates()
            return
        try:
            runs = self.queue.submit(self.piece["name"], self._planned(), root=self.root,
                                     out_dir=self.out_dir)
        except ValueError as exc:
            self._say(say("form.refused", words=exc))
            return
        self._say("")
        for run in runs:                            # the side-door command that makes the same
            print(f"lab: {run.line}")
        self._draw_names()                          # the names offered skip the runs just queued
        self.close_drawer()
        self._open_strip(True)
        self._poll()

    def _poll(self) -> None:
        """Every 700 ms: redraw the strip when a run moved; when runs ended, list what they wrote.

        Its own failures are shown here: Panel's periodic callback has no exception hook, so an
        error raised inside it would otherwise reach only the server's log.
        """
        try:
            self._tick()
        except Exception as exc:  # noqa: BLE001 -- shown on the page, the docstring says why
            _shown_in_page(exc)
            self._say(say("messages.reading_failed", words=exc))

    def _tick(self) -> None:
        runs = self.queue.runs()
        running = any(r.state == jobs.RUNNING for r in runs)
        if self.queue.version == self._seen and not running:
            return
        self._seen = self.queue.version
        self._draw_strip(runs)                      # first: a reload that fails cannot freeze it
        ids = {r.id for r in runs}
        done = [r for r in runs if r.state == jobs.DONE and r.id not in self._done]
        cleared = self._known - ids                 # perhaps in another tab, before this one saw
        self._done.update(r.id for r in done)       # it Done
        self._known = ids
        for run in done:                            # show what just ran, if it is this piece's
            if run.piece == self.piece["name"] and run.name not in self.shown:
                self.shown.append(run.name)
        if done or cleared:
            self.reload()

    # ------------------------------------------------------------------ runs in progress
    def _open_strip(self, open_it: bool) -> None:
        self.strip_list.visible = open_it
        self.strip_btn.label = f"{'▾' if open_it else '▸'} {say('strip.toggle')}"
        self._fit_drawer()

    def _fit_drawer(self) -> None:
        """The form's drawer ends where the strip begins, so a run can be stopped, and its state
        read, while the next one is set up (the header's Stop it replaced was never covered)."""
        strip = skin.STRIP_PX + (skin.STRIP_LIST_PX if self.strip_list.visible else 0)
        self.drawer.styles = {**skin.DRAWER,
                              "height": f"calc(100vh - {skin.HEADER_PX + strip}px)"}

    def _draw_strip(self, runs: list[jobs.Run]) -> None:
        """The head's count of each state, and the rows, newest first, as the strip draws them."""
        now = time.monotonic()
        counts = [say(f"strip.count.{state}", n=n) for state in _STATES
                  if (n := sum(r.state == state for r in runs))]
        self.strip_summary.object = (f"<span style='{_DIM}'>"
                                     f"{html.escape(' · '.join(counts) or say('strip.nothing'))}"
                                     f"</span>")
        labels = {p["name"]: p["label"] for p in self.pieces}
        self.strip_rows.rows = [
            {"id": r.id, "name": r.name, "piece": labels.get(r.piece, r.piece), "state": r.state,
             "words": say(f"strip.state.{r.state}"), "clock": self._clock(r, now), "error": r.error,
             "finished": r.finished}
            for r in reversed(runs)]

    @staticmethod
    def _clock(run: jobs.Run, now: float) -> str:
        """The time a run has run, ``m:ss``, once it started."""
        if run.started is None:
            return ""
        seconds = int(run.elapsed(now))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _stop(self, run_id: int) -> None:
        if self.queue.stop(run_id):
            self.toast(say("messages.stopping"))
        self._poll()

    def _dismiss(self, run_id: int) -> None:
        self.queue.dismiss(run_id)
        self._poll()

    # ------------------------------------------------------------------ the page
    def page(self) -> pn.Column:
        header = pn.Row(
            _html(f"<b style='font-size:15px;letter-spacing:.01em'>"
                  f"{html.escape(title())}</b>"),
            self.piece_select,
            pn.layout.HSpacer(), self.wording_choice, self.where, self.refresh, self.new_run_btn,
            styles=skin.TOP, stylesheets=[skin.BAR], sizing_mode="stretch_width")
        left = pn.Column(
            pn.Row(_h2(say("runs.heading")), self.runs_count, stylesheets=[skin.BAR],
                   sizing_mode="stretch_width"),
            pn.Row(self.run_filter, self.all_btn, self.none_btn, stylesheets=[skin.BAR],
                   sizing_mode="stretch_width"),
            self.run_list,
            pn.Row(_h2(say("compare.heading")), self.compare_count, stylesheets=[skin.BAR],
                   sizing_mode="stretch_width", margin=(14, 0, 0, 0)),
            pn.Row(_html(html.escape(say("compare.settings")), style=_LABEL), self.settings_choice,
                   stylesheets=[skin.BAR], sizing_mode="stretch_width"),
            self.numbers_row,
            self.compare_table,
            pn.Row(_h2(say("saved.heading")), self.saved_count, stylesheets=[skin.BAR],
                   sizing_mode="stretch_width", margin=(14, 0, 0, 0)),
            self.saved_list,
            styles=skin.LEFT, scroll=True, sizing_mode="stretch_width")
        right = pn.Column(
            pn.Row(_h2(say("figures.heading")), self.open_count, self.show_all, self.hide_all,
                   pn.layout.HSpacer(),
                   stylesheets=[skin.BAR], sizing_mode="stretch_width"),
            self.tabs,
            self.cards_box,
            styles=skin.PANE, scroll=True, sizing_mode="stretch_width")
        self.split = Split(left=left, right=right, left_px=DEFAULT_PX, styles=skin.BODY,
                           sizing_mode="stretch_width")
        # both ways: the drawer's body stretches both ways, and Panel widened the page to match
        # with a warning on every load (RCWS); declared, it is what the page already was
        return pn.Column(header, self.split, self.drawer, self.strip, self.asking,
                         sizing_mode="stretch_both", margin=0)


def page(root: str, out_dir: str) -> pn.viewable.Viewable:
    """The page for one session, or -- when it cannot be built -- the traceback, on the page."""
    try:
        return Lab(root, out_dir).page()            # its runs are the Lab's: a closed tab
                                                     # leaves them going
    except Exception:  # noqa: BLE001 -- the traceback, on the page (the docstring)
        text = traceback.format_exc()
        print(text, file=sys.stderr)
        return pn.pane.HTML(f"<h3>the Lab could not build its page</h3><pre>{html.escape(text)}</pre>")


def serve(port: int, root: str, out_dir: str, *, show: bool = True, threaded: bool = False) -> Any:
    """Serve on 127.0.0.1 until ctrl-c (or return the server when ``threaded``)."""
    pn.extension("plotly", notifications=True, exception_handler=_shown_in_page)
    for css in (skin.FONTS, skin.PAGE):
        if css not in pn.config.raw_css:
            pn.config.raw_css.append(css)
    # Import every registered piece before the address answers rather than inside the first
    # page load: a piece can be slow to import and the Lab needs all of their field
    # declarations. Each session reads them again, out of `sys.modules`.
    state.pieces()
    return pn.serve({"/": lambda: page(root, out_dir)}, port=port, address="127.0.0.1",
                    websocket_origin=[f"127.0.0.1:{port}", f"localhost:{port}"], show=show,
                    title=title(), threaded=threaded,
                    static_dirs={skin.FONTS_ROUTE: str(skin.FONTS_DIR)})
