"""Settings: a piece's Config, each setting a ``param`` parameter. Adapted from BESS's
``devkit/record/config.py`` (itself RCWS's), trimmed to what DeePC's pieces use.

param holds the type, the default, the ``label`` (the words a person reads), the ``doc`` (one
line: what it is, what changing it does), the ``bounds`` (declared only where the code enforces
one) and the ``objects`` of a choice, and refuses a wrong type, a value outside a bound or a pick
outside the choices in its own words. What param has no slot for rides in ``metadata``:

- ``group`` (required): the heading a form puts the setting under;
- ``unit``: the unit a person types it in;
- ``lines``: each choice's own line, ``{choice: one line}``; none here yet;
- ``needs``: what switches the setting on -- ``{other_setting: {"in": [named values]}}``. A value
  set behind a closed gate is refused on construction (:func:`gated`), because the run would
  ignore it and the saved config would claim it;
- ``replicate``: ``True`` for a setting that only re-draws the noise (a seed);
- ``draws``: on a replicate, the setting that counts the draws a run makes from it (run i of
  ``n`` uses ``seed + i``), so a figure pooling runs can tell when two share a draw; none here;
- ``record_of``: on a path setting, the piece whose saved run it names;
- ``folded``: the form shows the setting's group closed until it is opened;
- ``rows``: on a list setting, the form draws one labeled box per item -- ``{"label": "x{}'",
  "add": "+ State"}``, the label numbered from 1, the add button's words.

A setting whose default is ``None`` means "the plant's own": the piece resolves it when it runs
and saves what it resolved. A list setting holds numbers (the Q and R weights; JSON or commas on
the command line) or, declared ``item_type=str``, expressions (JSON on the command line).
``none`` on the command line sets a setting that allows it back to ``None``.

A setting may hold a LIST OF ROWS, a table: a ``param.List`` whose ``item_type`` is a Settings
class (the row), each row a set of settings of its own -- how an ordered list of steps is set
(BESS's ``devkit/record/config.py``; BESS's battery segments). It is a list of
dicts in a run file and as JSON on the command line (``segments=[{...}, ...]``), and one cell of
one row is reached by a dotted path, the row numbered from 0 (``segments.1.power_kw=-30``).

A setting may be of any other kind param offers -- a matrix (``param.Array``), a date, a pair, a
table of param's: param writes it as plain text and reads it back (:func:`other_kind`), so it is typed as
that text (``[[1, 2], [3, 4]]``, ``2026-02-03``), saved as it (:func:`saved`) and loaded as the
real thing. Nothing here names such a kind.

A built Config is immutable; a changed one is a new Config (:func:`with_overrides`).
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import param

__all__ = ["Settings", "fields_of", "gated", "with_overrides", "to_dict", "saved", "from_dict",
           "coerce_value", "parse_override", "other_kind"]

#: The six kinds read and written here; a setting of any other is read and written by param.
_SIX = (param.Integer, param.Number, param.Boolean, param.String, param.Selector, param.List)


class Settings(param.Parameterized):
    """Base of every piece's Config. See the module."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for name, value in vars(cls).items():
            if isinstance(value, param.Parameter):
                if not (value.metadata or {}).get("group"):
                    raise TypeError(f"{cls.__name__}.{name} declares no group; a form has to put "
                                    f"a setting under one (metadata={{'group': ...}})")
                value.constant = True

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        gated(self)


def _parameters(cls: type) -> dict[str, param.Parameter]:
    """The declared parameters, in declaration order, without param's own ``name``."""
    return {n: p for n, p in cls.param.objects(instance=False).items() if n != "name"}


def other_kind(p: param.Parameter) -> bool:
    """Whether ``p`` is of another kind than the six: not built on one of them, or built on one
    and bringing its own writing or reading (a date is built on param's number)."""
    if not isinstance(p, _SIX):
        return True
    definer = next(c for c in type(p).__mro__ if "serialize" in vars(c) or "deserialize" in vars(c))
    return definer is not param.Parameter


def _rows_of(p: param.Parameter) -> type | None:
    """The row class of a list of rows, ``None`` for any other setting."""
    item = getattr(p, "item_type", None) if isinstance(p, param.List) else None
    return item if isinstance(item, type) and issubclass(item, Settings) else None


def _written(p: param.Parameter, value: Any) -> Any:
    """``value`` as the run file holds it: param's own writing for another kind, each row of a
    list of rows as its own settings."""
    if _rows_of(p) and value is not None:
        return [saved(row) for row in value]
    return p.serialize(value) if other_kind(p) and value is not None else value


def _gate_holds(gate: Mapping[str, Any], value: Any) -> bool:
    if set(gate) != {"in"}:
        raise ValueError(f"a gate is {{'in': [named values]}}, got {gate!r}")
    return value in gate["in"]


def gated(cfg: Settings) -> None:
    """Refuse a setting set behind a closed gate; see the module."""
    for name, p in _parameters(type(cfg)).items():
        needs = (p.metadata or {}).get("needs")
        if not needs:
            continue
        closed = [(other, gate) for other, gate in needs.items()
                  if not _gate_holds(gate, getattr(cfg, other))]
        # compared as written: a matrix has no single answer to "is it its default"
        if closed and _written(p, getattr(cfg, name)) != _written(p, p.default):
            gates = "; ".join(f"{other} is one of {gate['in']!r} (it is {getattr(cfg, other)!r})"
                              for other, gate in closed)
            raise ValueError(f"{name}={getattr(cfg, name)!r} is set, but {name} applies only "
                             f"when {gates}; the run would ignore it")


def _type_text(p: param.Parameter) -> str:
    if _rows_of(p):
        return "rows"
    return {param.Integer: "int", param.Number: "float", param.Boolean: "bool",
            param.String: "str", param.Selector: "choice", param.List: "list"}.get(
        type(p), type(p).__name__)


def fields_of(cls: type) -> list[dict[str, Any]]:
    """One dict per setting -- the one reader every surface (the command line, tests, a form)
    uses. A list of rows carries its row's own settings (``element_fields``, read the same way)
    and what a row added to it starts as (``element_default``); both are ``None`` for any other
    setting."""
    out = []
    for name, p in _parameters(cls).items():
        meta = p.metadata or {}
        other = other_kind(p)
        row = _rows_of(p)
        numeric = isinstance(p, param.Number) and not other
        bounds = (getattr(p, "bounds", None) if numeric else None) or (None, None)
        incl = (getattr(p, "inclusive_bounds", None) if numeric else None) or (True, True)
        out.append({
            # another kind's default as the text it is typed as; its bounds are param's to hold
            "name": name, "type": _type_text(p), "default": _written(p, p.default),
            "other": other,
            "element_fields": fields_of(row) if row else None,
            "element_default": saved(row()) if row else None,
            "label": p.label or name, "unit": meta.get("unit", ""), "group": meta["group"],
            "doc": (p.doc or "").strip(), "lines": meta.get("lines"),
            "choices": list(p.objects) if isinstance(p, param.Selector) else None,
            "low": bounds[0], "high": bounds[1], "code_default": p.default is None,
            "low_exclusive": bounds[0] is not None and not incl[0],
            "high_exclusive": bounds[1] is not None and not incl[1],
            "needs": meta.get("needs"), "replicate": bool(meta.get("replicate")),
            "draws": meta.get("draws"), "record_of": meta.get("record_of", ""),
            "folded": bool(meta.get("folded")), "rows": meta.get("rows"),
            "texts": isinstance(p, param.List) and p.item_type is str,
        })
    return out


_TRUE, _FALSE = {"true", "1", "yes", "on"}, {"false", "0", "no", "off"}


def _a_row(p: param.Parameter, held: Any, i: int) -> Mapping[str, Any]:
    """Row ``i`` of a list of rows as the mapping it is, or a refusal naming the setting."""
    if not isinstance(held, Mapping):
        raise ValueError(f"{p.name}: row {i} is {held!r}, not a row {{setting: value, ...}}")
    return held


def _texts(p: param.Parameter, value: Any) -> list[str]:
    """A list of expressions, or a refusal naming the setting."""
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{p.name}: {value!r} is not a list of texts, [\"x2\", \"-x1 + u1\"]")
    return list(value)


def coerce_value(p: param.Parameter, value: Any) -> Any:
    """A command-line text as the setting's own type; a typed value passes through, but a list
    setting's numbers become floats (a config file may write the weight 10 as an integer). A list
    of texts (``item_type=str``) is JSON on the command line. A setting of another kind
    (:func:`other_kind`) takes the text param reads, as JSON when it is JSON, or the value a run
    file holds; a value already of its own type passes through. A list of rows takes its JSON
    text or a list of dicts, each dict a row (:func:`from_dict`); a row already built passes
    through."""
    row = _rows_of(p)
    if row is not None:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"{p.name}: {value!r} is not a list of rows as JSON, "
                                 f"[{{...}}, ...]") from None
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{p.name}: {value!r} is not a list of rows, [{{...}}, ...]")
        rows = []
        for i, r in enumerate(value):
            try:
                rows.append(r if isinstance(r, row)
                            else from_dict(row, _a_row(p, r, i), where=f"{p.name} row {i}"))
            except ValueError as exc:       # a cell's own refusal, with the row it is in
                if str(exc).startswith(f"{p.name}:") or f"{p.name} row {i}" in str(exc):
                    raise
                raise ValueError(f"{p.name} row {i}: {exc}") from exc
        return rows
    if other_kind(p):
        return _read(p, value)
    if isinstance(p, param.List) and p.item_type is str:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"{p.name}: {value!r} is not a JSON list of texts, "
                                 f"[\"x2\", \"-x1 + u1\"]") from None
        return _texts(p, value)
    if isinstance(p, param.List) and isinstance(value, (list, tuple)):
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            raise ValueError(f"{p.name}: {value!r} is not a list of numbers") from None
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.lower() == "none" and p.allow_None:
        return None
    if isinstance(p, param.Boolean):
        if text.lower() in _TRUE:
            return True
        if text.lower() in _FALSE:
            return False
        raise ValueError(f"{p.name}: a bool is one of {sorted(_TRUE | _FALSE)}, not {text!r}")
    try:
        if isinstance(p, param.Integer):
            return int(text)
        if isinstance(p, param.Number):
            return float(text)
        if isinstance(p, param.List):
            held = json.loads(text) if text.startswith("[") else [float(v) for v in text.split(",")]
            if not isinstance(held, list):
                raise ValueError
            return [float(v) for v in held]
    except (ValueError, TypeError, json.JSONDecodeError):
        kind = {param.Integer: "an integer", param.Number: "a number"}.get(
            type(p), "a list of numbers, [1, 2] or 1,2")
        raise ValueError(f"{p.name}: {text!r} is not {kind}") from None
    if isinstance(p, param.Selector):
        by_text = {str(o): o for o in p.objects}
        if text not in by_text:
            raise ValueError(f"{p.name}: {text!r} is not one of {sorted(by_text)}")
        return by_text[text]
    return text


def _read(p: param.Parameter, value: Any) -> Any:
    """A setting of another kind from its text or its saved form, through param's reading."""
    if isinstance(value, str):
        text = value.strip()
        if text.lower() == "none" and p.allow_None:
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = text
    if not isinstance(value, (str, list, dict, int, float)):
        return value
    try:
        return p.deserialize(value)
    except Exception as exc:        # whatever param's reading raises, raised again naming the setting
        raise ValueError(f"{p.name}: {value!r} is not what a {type(p).__name__} setting reads "
                         f"({type(exc).__name__}: {exc})") from exc


def to_dict(cfg: Settings) -> dict[str, Any]:
    """The settings, in declaration order, as the values the piece reads; a list of rows as a
    list of dicts, the rows' own settings as plain values."""
    return {n: [to_dict(r) for r in getattr(cfg, n)] if _rows_of(p) else getattr(cfg, n)
            for n, p in _parameters(type(cfg)).items()}


def saved(cfg: Settings) -> dict[str, Any]:
    """The settings, in declaration order, as a run file holds them: one of another kind as
    param writes it (a matrix as nested lists, a date as text), a list of rows as a list of
    dicts."""
    return {n: _written(p, getattr(cfg, n)) for n, p in _parameters(type(cfg)).items()}


def from_dict(cls: type, raw: Mapping[str, Any], where: str = "") -> Settings:
    """A Config from a mapping; an unknown key is refused, never dropped."""
    params = _parameters(cls)
    unknown = sorted(set(raw) - set(params))
    if unknown:
        raise ValueError(f"unknown setting(s) {unknown}{' in ' + where if where else ''} for "
                         f"{cls.__name__}; valid: {sorted(params)}")
    return cls(**{k: coerce_value(params[k], v) for k, v in raw.items()})


def setting_names(cls: type) -> list[str]:
    """The names of the settings ``cls`` declares, in declaration order."""
    return list(_parameters(cls))


def from_saved(cls: type, raw: Mapping[str, Any]) -> Settings:
    """A Config from the settings a run file holds. An entry ``cls`` has no setting for is left
    out, where :func:`from_dict` refuses it: a settings file is written by hand and a stray key
    in it is a slip, a run file was written by the code of its day and is read as it was saved.
    A setting the file lacks takes its default, as in :func:`from_dict`. The rows of a list of
    rows are read the same way, each by its row class."""
    params = _parameters(cls)
    held = {k: v for k, v in raw.items() if k in params}
    for name, value in held.items():
        row = _rows_of(params[name])
        if row is not None and isinstance(value, list):
            held[name] = [from_saved(row, _a_row(params[name], r, i)) for i, r in enumerate(value)]
    return from_dict(cls, held, where="config")


def with_overrides(cfg: Settings, pairs: Sequence[tuple[str, Any]]) -> Settings:
    """``cfg`` with each ``(setting, value)`` applied, rebuilt ONCE so a gate is checked on the
    final state, not on an intermediate one. A dotted ``setting.row.cell`` sets one cell of one
    row of a list of rows, the rows numbered from 0."""
    cls = type(cfg)
    params = _parameters(cls)
    values = to_dict(cfg)
    for name, value in pairs:
        head, _, rest = name.partition(".")
        if head not in params:
            raise ValueError(f"unknown setting {head!r} on {cls.__name__}; valid: {sorted(params)}")
        if not rest:
            held = coerce_value(params[head], value)
            # a list of rows stays plain until the rebuild, so a cell set after it lands on a dict
            # (BESS, code review 2026-10-27: a row there was spread as if it were a mapping)
            values[head] = [to_dict(r) for r in held] if _rows_of(params[head]) else held
            continue
        row = _rows_of(params[head])
        if row is None:
            raise ValueError(f"{name!r}: {head!r} holds no rows, so nothing is inside it")
        index, _, cell = rest.partition(".")
        rows = values[head]
        if not index.isdigit() or int(index) >= len(rows):
            raise ValueError(f"{name!r}: {head} holds {len(rows)} row(s), numbered from 0; "
                             f"{index!r} is not one of them")
        cells = _parameters(row)
        if cell not in cells:
            raise ValueError(f"{name!r}: a row of {head} holds no {cell!r}; it holds "
                             f"{sorted(cells)}")
        rows[int(index)] = {**rows[int(index)], cell: coerce_value(cells[cell], value)}
    return cls(**{n: coerce_value(params[n], v) if _rows_of(params[n]) else v
                  for n, v in values.items()})


def parse_override(item: str) -> tuple[str, str]:
    """``"setting=value"`` -> ``("setting", "value")``."""
    name, sep, value = item.partition("=")
    if not sep or not name:
        raise ValueError(f"expected SETTING=VALUE, got {item!r}")
    return name.strip(), value
