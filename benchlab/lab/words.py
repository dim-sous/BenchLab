"""The page's own words, as slots the declared project fills (``docs/design.md`` decision 4).

Benchlab names every slot and the fields its word may use, and holds no word: the project's words
file (``WORDS`` in its declaration, :mod:`benchlab.project`) fills each one. The file is TOML, one
table per part of the page -- ``[strip] cap = "up to {n} side by side"`` fills ``strip.cap`` -- and
a word writes a field as ``{n}``. A word that counts is two slots, ``….one`` and ``….many``:
which reads for a count is the project's language, not Benchlab's (:func:`say_n`).

A file that leaves a slot empty, fills one Benchlab does not name, gives a word a field its slot
does not offer, or holds a brace that is no field is refused, naming each; the Lab does not start
(:mod:`lab.cli`). Not slots: words the page shows but does not write -- a record's, a piece's
labels, param's, the runner's and the figure layer's refusals, shown in their own words -- and
words no person using the page can reach (a programming mistake's).
"""

from __future__ import annotations

import functools
import string
import tomllib
from pathlib import Path
from typing import Any

from benchlab.project import words_path

#: Every slot, by the part of the page it shows in, and the fields its word may use.
SLOTS: dict[str, tuple[str, ...]] = {
    # the page's top line
    "header.refresh": (), "header.new_run": (),
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
    # the compare table
    "compare.heading": (), "compare.settings": (),
    "compare.settings_none": (), "compare.settings_differing": (), "compare.settings_all": (),
    "compare.empty": (), "compare.corner": (), "compare.no_value": (),
    "compare.numbers_group": (), "compare.constants": (),
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
    "cards.one_run": (), "cards.nothing_differs": (), "cards.no_colour": (),
    # the form
    "form.heading": (), "form.from_defaults": (), "form.from_run": ("run",),
    "form.clear": (), "form.close": (), "form.run": (),
    "form.name": (), "form.sweep": (), "form.sweep_none": (), "form.sweep_values": (),
    "form.code_default": (), "form.default": ("value",),
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
    "messages.delete_ask": ("path",), "messages.delete_yes": (), "messages.delete_no": (),
    "messages.deleted": ("paths",), "messages.not_deleted": ("words",),
    "messages.delete_no_record": ("name", "folder"), "messages.delete_outside": ("path", "folder"),
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


def load(path: Path) -> dict[str, str]:
    """The words ``path`` gives every slot. Refused, in words naming each, when a slot is left
    empty, a slot Benchlab does not name is filled, a word is not text, writes a field its slot
    does not offer, or holds a brace that is no field."""
    with open(path, "rb") as f:
        given = _flat(tomllib.load(f))
    problems = []
    missing = sorted(set(SLOTS) - set(given))
    if missing:
        problems.append(f"leaves {len(missing)} slot(s) empty: {', '.join(missing)}")
    unknown = sorted(set(given) - set(SLOTS))
    if unknown:
        problems.append(f"fills slot(s) Benchlab does not name: {', '.join(unknown)}")
    for slot in sorted(set(given) & set(SLOTS)):
        word = given[slot]
        if not isinstance(word, str):
            problems.append(f"{slot} is not text")
            continue
        try:
            extra = sorted(_fields(word) - set(SLOTS[slot]))
        except ValueError as exc:
            problems.append(f"{slot} holds a brace that is no field ({exc}); write {{{{ for {{")
            continue
        if extra:
            offered = ", ".join(SLOTS[slot]) or "none"
            problems.append(f"{slot} writes {', '.join('{' + e + '}' for e in extra)}, which it "
                            f"does not offer (it offers: {offered})")
    if problems:
        raise ValueError(f"the words file {path} " + "; ".join(problems))
    return {slot: given[slot] for slot in SLOTS}


@functools.cache
def words() -> dict[str, str]:
    """The declared project's words, read once and checked (:func:`load`)."""
    return load(words_path())


def word(slot: str) -> str:
    """A slot's word as the project wrote it, its fields unfilled: for the page's script code,
    which fills them itself."""
    return words()[slot]


def say(slot: str, **fields: Any) -> str:
    """A slot's word, its fields filled."""
    return words()[slot].format(**fields)


def say_n(slot: str, n: int, **fields: Any) -> str:
    """The word for a count of ``n``: the slot's ``.one`` for 1, its ``.many`` otherwise."""
    return say(f"{slot}.one" if n == 1 else f"{slot}.many", n=n, **fields)
