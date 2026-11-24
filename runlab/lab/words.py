"""The page's own words.

RunLab names every slot and the fields its word may use, and holds a word for each: its own
words file, ``words.toml`` beside this module. A project may change any of them: its words file
(``WORDS`` in its declaration, :mod:`runlab.project`) lists only the words it wants different,
and every other slot keeps RunLab's. Both files are TOML, one table per part of the page --
``[strip] cap = "up to {n} side by side"`` fills ``strip.cap`` -- and a word writes a field as
``{n}``. A word that counts is two slots, ``….one`` and ``….many``: which reads for a count is
the file's language (:func:`say_n`).

Nothing in a project's file stops the Lab (the developer, 2026-11-15: "If a word is missing or
wrong i will see it in the lab and make the change"). An entry RunLab cannot use -- it names
no slot, is not text, writes a field its slot does not offer, or holds a brace that is no field
-- is left out, the page keeps RunLab's own word, and the Lab says so once, in its terminal
(:func:`left_out`, :mod:`lab.cli`); so does a file it cannot read. A slot's name is therefore
not promised: renamed, a project's entry for it is left out and said. Not slots: words the page
shows but does not write -- a record's, a piece's labels, param's, the runner's and the figure
layer's refusals, shown in their own words -- and words no person using the page can reach (a
programming mistake's).
"""

from __future__ import annotations

import functools
import string
import tomllib
from pathlib import Path
from typing import Any

from runlab.project import words_path

#: RunLab's own words, one for every slot.
OWN = Path(__file__).with_name("words.toml")
#: Every slot, by the part of the page it shows in, and the fields its word may use.
SLOTS: dict[str, tuple[str, ...]] = {
    # the page's top line
    "header.refresh": (), "header.new_run": (), "header.names": (), "header.symbols": (),
    "header.where.one": ("folder", "n"), "header.where.many": ("folder", "n"),
    # the runs: the list on the left
    "runs.heading": (), "runs.filter": (), "runs.all": (), "runs.none": (),
    "runs.count": ("on_disk", "shown"), "runs.count_listed": ("on_disk", "shown", "listed"),
    "runs.empty": ("command",), "runs.none_listed": (),
    "runs.use": (), "runs.delete": (), "runs.delete_label": ("name",),
    "runs.stale.piece": ("held", "piece"),
    "runs.stale.predates.one": ("fields",), "runs.stale.predates.many": ("fields",),
    "runs.stale.gone.one": ("fields",), "runs.stale.gone.many": ("fields",),
    "runs.stale.panels": ("key",), "runs.stale.specs": ("key",), "runs.stale.spec": ("key",),
    # a run that is shown, and how its file departs from what its piece reads now
    "runs.differs.origin_lacks.one": ("fields",), "runs.differs.origin_lacks.many": ("fields",),
    "runs.differs.origin_extra.one": ("fields",), "runs.differs.origin_extra.many": ("fields",),
    "runs.differs.settings_lacks.one": ("fields",),
    "runs.differs.settings_lacks.many": ("fields",),
    "runs.differs.settings_extra.one": ("fields",),
    "runs.differs.settings_extra.many": ("fields",),
    # the compare table
    "compare.heading": (), "compare.settings": (),
    "compare.settings_none": (), "compare.settings_differing": (), "compare.settings_all": (),
    "compare.empty": (), "compare.corner": (), "compare.no_value": (),
    "compare.numbers_group": (), "compare.constants": (),
    "compare.files": (), "compare.file_gone": ("size",),
    "compare.alone.one": ("n",), "compare.alone.many": ("n",),
    "compare.same.one": ("n",), "compare.same.many": ("n",),
    "compare.differ_settings.one": ("n",), "compare.differ_settings.many": ("n",),
    "compare.differ_numbers.one": ("n",), "compare.differ_numbers.many": ("n",),
    # the chart list
    "figures.heading": (), "figures.show_all": (), "figures.hide_all": (),
    "figures.open": ("open", "total"), "figures.empty": (),
    "figures.held_by_none": (), "figures.held_by_some": ("held", "runs"),
    # the cards
    "cards.empty_runs": (), "cards.empty": (), "cards.close": (),
    "cards.number_title": ("number", "setting"), "cards.number_foot": (),
    "cards.x": (), "cards.runs": (), "cards.overlay": (), "cards.split": (), "cards.mean": (),
    "cards.rms": (), "cards.each": (),
    "cards.x_log": (), "cards.y_log": (), "cards.colour_by": (), "cards.by_run": (),
    "cards.by_quantity": (), "cards.dots": (), "cards.lines": (), "cards.chart": (),
    "cards.table": (), "cards.table_digits": (),
    "cards.save": (), "cards.wrote": ("files",), "cards.not_saved": ("words",),
    "cards.one_run": (), "cards.nothing_differs": (), "cards.no_colour": (),
    "cards.colour_pooled": (), "cards.colour_split": (), "cards.nothing_else_differs": (),
    "cards.chart_without.one": ("runs",), "cards.chart_without.many": ("runs",),
    # a card of a figure the piece draws itself
    "cards.own_runs": (), "cards.own_without.one": ("runs",), "cards.own_without.many": ("runs",),
    "cards.rows_split": (), "cards.messages": (), "cards.messages_without.one": ("runs",),
    "cards.messages_without.many": ("runs",),
    # the pictures a Save wrote: the list under the compare table
    "saved.heading": (), "saved.count.one": ("n",), "saved.count.many": ("n",),
    "saved.empty": (), "saved.pictures.one": ("n",), "saved.pictures.many": ("n",),
    "saved.tables.one": ("n",), "saved.tables.many": ("n",),
    "saved.row": ("when", "pictures"), "saved.row_tables": ("when", "pictures", "tables"),
    "saved.delete": (), "saved.delete_label": ("name",),
    # the form
    "form.heading": (), "form.from_defaults": (), "form.from_run": ("run",),
    "form.clear": (), "form.close": (), "form.run": (),
    "form.name": (), "form.sweep": (), "form.sweep_none": (), "form.sweep_values": (),
    "form.code_default": (), "form.default": ("value",), "form.add_row": ("name",),
    "form.range": ("low", "high"),
    "form.group_changed": ("changed", "total"), "form.group_defaults": ("total",),
    "form.sweep_axis": ("setting",), "form.gated": ("setting", "other", "wanted", "value"),
    "form.set": ("n",), "form.taken.one": ("settings",), "form.taken.many": ("settings",),
    "form.sweep_repeats": (), "form.some_rungs": ("setting",),
    "form.overwrites.one": ("names",), "form.overwrites.many": ("names",),
    "form.refused": ("words",),
    "form.bad_name": ("name",),
    "form.busy.one": ("names",), "form.busy.many": ("names",),
    # what Run refuses in a setting (``lab.jobs.refusals``)
    "refuse.whole": ("setting", "text"), "refuse.number": ("setting", "text"),
    "refuse.yes_no": ("setting", "text"), "refuse.choice": ("setting", "choices", "text"),
    "refuse.unread": ("setting", "text"),
    "refuse.texts": ("setting", "text"), "refuse.numbers": ("setting", "text"),
    "refuse.at_least": ("setting", "bound", "text"), "refuse.above": ("setting", "bound", "text"),
    "refuse.at_most": ("setting", "bound", "text"), "refuse.below": ("setting", "bound", "text"),
    # the runs in progress, along the bottom
    "strip.toggle": (), "strip.nothing": (), "strip.cap": ("n",),
    "strip.count.running": ("n",), "strip.count.queued": ("n",), "strip.count.done": ("n",),
    "strip.count.failed": ("n",), "strip.count.stopped": ("n",),
    "strip.state.running": (), "strip.state.queued": (), "strip.state.done": (),
    "strip.state.failed": (), "strip.state.stopped": (),
    "strip.stop": (), "strip.dismiss": (), "strip.stop_label": ("name",),
    "strip.dismiss_label": ("name",),
    "strip.exit": ("code",), "strip.signal": ("signal",), "strip.not_started": ("words",),
    "strip.end_unread": ("words",), "strip.answer_unread": ("words",),
    # what a click says
    "messages.stopping": (), "messages.loaded.one": ("n", "run"), "messages.loaded.many": ("n", "run"),
    "messages.no_longer_declared": ("settings",), "messages.taken_back": ("n",),
    "messages.no_record": ("name",), "messages.reading_failed": ("words",),
    "messages.delete_ask": ("path",),
    "messages.delete_ask_files.one": ("path", "folder", "n"),
    "messages.delete_ask_files.many": ("path", "folder", "n"), "messages.delete_yes": (), "messages.delete_no": (),
    "messages.deleted": ("paths",), "messages.not_deleted": ("words",),
    "messages.delete_no_record": ("name", "folder"), "messages.delete_outside": ("path", "folder"),
    "messages.delete_ask_folder": ("folder",), "messages.delete_not_folder": ("name",),
    "messages.delete_no_folder": ("name", "folder"),
    "messages.delete_holds_other": ("folder", "files"), "messages.save_run_files": ("folder",),
}


def _flat(table: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in table.items():
        if isinstance(value, dict):
            out.update(_flat(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


def _fields(word: str) -> set[str]:
    """The fields a word writes; :class:`ValueError` on a brace that is no field."""
    return {name for _, name, _, _ in string.Formatter().parse(word) if name is not None}


def _unusable(given: dict[str, Any]) -> dict[str, str]:
    """Why RunLab cannot use an entry of a words file, by the slot it names; an entry that is
    not here, it can."""
    out = {}
    for slot, word in given.items():
        if slot not in SLOTS:
            out[slot] = "RunLab names no such slot"
        elif not isinstance(word, str):
            out[slot] = "it is not text"
        else:
            try:
                extra = sorted(_fields(word) - set(SLOTS[slot]))
            except ValueError as exc:
                out[slot] = f"it holds a brace that is no field ({exc}); write {{{{ for {{"
                continue
            if extra:
                out[slot] = (f"it writes {', '.join('{' + e + '}' for e in extra)}, which the "
                             f"slot does not offer (it offers: {', '.join(SLOTS[slot]) or 'none'})")
    return out


def _own() -> dict[str, str]:
    """RunLab's own words, one for every slot. Its file leaving a slot empty, or holding an
    entry :func:`_unusable` names, is a mistake in RunLab and is refused, naming each."""
    with open(OWN, "rb") as f:
        given = _flat(tomllib.load(f))
    problems = [f"{slot}: {why}" for slot, why in _unusable(given).items()]
    missing = sorted(set(SLOTS) - set(given))
    if missing:
        problems.append(f"leaves {len(missing)} slot(s) empty: {', '.join(missing)}")
    if problems:
        raise ValueError(f"RunLab's own words file {OWN} " + "; ".join(problems))
    return {slot: given[slot] for slot in SLOTS}


def read(path: Path) -> tuple[dict[str, str], list[str]]:
    """A project's words file: the words of it RunLab can use, by slot, and each thing it
    leaves out with why -- an entry :func:`_unusable` names, or the whole file when it cannot be
    read. Nothing here is refused (the module says why)."""
    try:
        with open(path, "rb") as f:
            given = _flat(tomllib.load(f))
    except (OSError, tomllib.TOMLDecodeError) as exc:    # left out whole, and said (the docstring)
        return {}, [f"the file ({type(exc).__name__}: {exc})"]
    unusable = _unusable(given)
    return ({slot: word for slot, word in given.items() if slot not in unusable},
            [f"{slot} ({why})" for slot, why in unusable.items()])


def load(path: Path | None = None) -> dict[str, str]:
    """Every slot's word: RunLab's own, and over them the words ``path``, a project's file,
    changes."""
    own = _own()
    return own if path is None else {**own, **read(Path(path))[0]}


def left_out() -> str:
    """One line naming what of the declared project's words file RunLab leaves out, each with
    why; empty when the project names no file or every entry of it is used."""
    path = words_path()
    out = [] if path is None else read(path)[1]
    return (f"the words file {path}: left out, the page keeping RunLab's own words: "
            + "; ".join(out)) if out else ""


@functools.cache
def words() -> dict[str, str]:
    """The page's words for the declared project, read once (:func:`load`)."""
    return load(words_path())


def word(slot: str) -> str:
    """A slot's word as its file wrote it, its fields unfilled: for the page's script code,
    which fills them itself."""
    return words()[slot]


def say(slot: str, **fields: Any) -> str:
    """A slot's word, its fields filled."""
    return words()[slot].format(**fields)


def say_n(slot: str, n: int, **fields: Any) -> str:
    """The word for a count of ``n``: the slot's ``.one`` for 1, its ``.many`` otherwise."""
    return say(f"{slot}.one" if n == 1 else f"{slot}.many", n=n, **fields)
