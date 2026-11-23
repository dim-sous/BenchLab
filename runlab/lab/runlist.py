"""The lists on the left: a piece's runs -- one row each, a dot that ticks it shown, ``use`` and
a delete -- and the folders of pictures a Save wrote, each a row with a delete. RCWS's lists
(``lab/runlist.py``, 822b0cf): a run's row is its name alone, the dot in the colour its lines
wear while it is shown; what sets a run apart is the compare table's to say."""

from __future__ import annotations

from typing import Any, Callable, Optional

import param
from panel.custom import JSComponent

from .skin import LIST

#: The row's actions.
_ROW = """
    const el = (tag, cls, text) => { const e = document.createElement(tag); e.className = cls;
      if (text !== undefined) e.textContent = text; return e; };
    const action = (cls, words, msg) => { const b = el('button', 'act ' + cls, words);
      b.addEventListener('click', e => { e.stopPropagation(); model.send_msg(msg); });
      return b; };
"""


class RunList(JSComponent):
    """``rows`` in (``name``, ``stale`` and ``notes`` -- :func:`lab.view.run_rows`: a stale run's
    reason written under its name, and under a readable one a line for each way its file departs
    from what its piece reads now -- and ``colour``, the colour a shown run's lines wear), ``shown``
    out: the ticked names in the order they were ticked, toggled by a click on a readable row.
    A click on ``use`` or ``✕`` reaches :attr:`on_use` / :attr:`on_delete` with the run's name
    as a MESSAGE, not a parameter, so the same run asked twice reaches it twice."""

    rows = param.List(default=[], item_type=dict)
    shown = param.List(default=[], item_type=str)
    empty = param.String(default="", doc="what the list says when it lists no run")
    #: the list's own words (``lab.words``): ``use``, ``delete``, and ``delete_label``, which
    #: names a run's delete for a screen reader by its ``{name}``
    words = param.Dict(default={})

    on_use: Optional[Callable[[str], None]] = None
    #: A click on ``re-fly`` (from 1.12), offered on a readable run whose file departs from what
    #: its piece reads now: the run's name, as a message.
    on_refly: Optional[Callable[[str], None]] = None
    on_delete: Optional[Callable[[str], None]] = None

    _stylesheets = [LIST]
    _esm = """
    export function render({ model }) {
      const root = document.createElement('div'); root.className = 'list';""" + _ROW + """
      const draw = () => {
        root.replaceChildren();
        if (!model.rows.length) { root.append(el('div', 'empty', model.empty)); return; }
        for (const r of model.rows) {
          const shown = model.shown.includes(r.name);
          const row = el('div', 'run' + (r.stale ? ' stale' : '') + (shown ? ' shown' : ''));
          const dot = el('span', 'dot');
          if (shown && r.colour) { dot.style.background = r.colour; dot.style.borderColor = r.colour; }
          const main = el('div', 'main');
          main.append(el('div', 'name', r.name));
          if (r.stale) main.append(el('div', 'why', r.stale));
          for (const note of (r.notes || [])) main.append(el('div', 'note', note));
          row.append(dot, main);
          if (!r.stale) {
            row.append(action('use', model.words.use, { use: r.name }));
            if ((r.notes || []).length && model.words.refly)
              main.append(action('refly', model.words.refly, { refly: r.name }));
            row.addEventListener('click', () => {
              const s = model.shown.slice(); const i = s.indexOf(r.name);
              if (i >= 0) s.splice(i, 1); else s.push(r.name);
              model.shown = s; });
          } else {
            row.append(el('span', ''));
          }
          const del = action('del', model.words.delete, { delete: r.name });
          del.setAttribute('aria-label', model.words.delete_label.split('{name}').join(r.name));
          row.append(del);
          root.append(row);
        }
      };
      for (const p of ['rows', 'shown', 'empty']) model.on(p, draw);
      draw();
      return root;
    }
    """

    def _handle_msg(self, msg: Any) -> None:
        if not isinstance(msg, dict):
            return
        if isinstance(msg.get("use"), str) and self.on_use is not None:
            self.on_use(msg["use"])
        if isinstance(msg.get("refly"), str) and self.on_refly is not None:
            self.on_refly(msg["refly"])
        elif isinstance(msg.get("delete"), str) and self.on_delete is not None:
            self.on_delete(msg["delete"])


class SavedList(JSComponent):
    """``rows`` in (``name``, ``when`` -- its date and what it holds -- and ``pictures``, their
    names): the folders of saved pictures, each a flat row with a delete that reaches
    :attr:`on_delete` with the folder's name as a message. BESS's ``StillList``, the pictures'
    names written under the folder's instead of on its hover: this page wears no hover but a
    greyed control's."""

    rows = param.List(default=[], item_type=dict)
    empty = param.String(default="")
    #: the list's own words (``lab.words``): ``delete``, and ``delete_label``, which names a
    #: folder's delete for a screen reader by its ``{name}``
    words = param.Dict(default={})

    on_delete: Optional[Callable[[str], None]] = None

    _stylesheets = [LIST]
    _esm = """
    export function render({ model }) {
      const root = document.createElement('div'); root.className = 'list';""" + _ROW + """
      const draw = () => {
        root.replaceChildren();
        if (!model.rows.length) { root.append(el('div', 'empty', model.empty)); return; }
        for (const r of model.rows) {
          const row = el('div', 'run flat');
          const main = el('div', 'main');
          main.append(el('div', 'name', r.name), el('div', 'when', r.when),
                      el('div', 'note', r.pictures));
          const del = action('del', model.words.delete, { delete: r.name });
          del.setAttribute('aria-label', model.words.delete_label.split('{name}').join(r.name));
          row.append(main, del);
          root.append(row);
        }
      };
      for (const p of ['rows', 'empty']) model.on(p, draw);
      draw();
      return root;
    }
    """

    def _handle_msg(self, msg: Any) -> None:
        if isinstance(msg, dict) and isinstance(msg.get("delete"), str) and self.on_delete:
            self.on_delete(msg["delete"])

