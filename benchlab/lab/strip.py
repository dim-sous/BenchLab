"""The runs in progress, along the bottom: a row per run -- its name and piece, its state as a
pill with the time it has run, a failure's words -- and Stop while it is queued or running, ✕ once
it ended. The mockup's strip (``docs/design.md`` §5), drawn as the run list is: rows as data, a
click a MESSAGE to the page.

A row is built once and then changed in place, and the rows are put back in order only when one
is added or taken off: the clock redraws the rows every second while a run runs, and a button
rebuilt between a press and its release takes no click. (A Panel button per row, added after the
page loaded, drew a Bokeh "reference already known" warning at every click, 2026-11-14.)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import param
from panel.custom import JSComponent

from .skin import STRIP_ROWS


class RunsInProgress(JSComponent):
    """``rows`` in, newest first, each ``{id, name, piece, state, words, clock, error,
    finished}``: ``state`` one of queued, running, done, failed, stopped (its pill's colour),
    ``words`` what the pill says. A click on Stop or ✕ reaches :attr:`on_stop` /
    :attr:`on_dismiss` with the run's id."""

    rows = param.List(default=[], item_type=dict)
    #: the strip's own words (``lab.words``): ``stop``, ``dismiss``, and ``stop_label`` and
    #: ``dismiss_label``, which name a run's button for a screen reader by its ``{name}``
    words = param.Dict(default={})

    on_stop: Optional[Callable[[int], None]] = None
    on_dismiss: Optional[Callable[[int], None]] = None

    _stylesheets = [STRIP_ROWS]
    _esm = """
    export function render({ model }) {
      const root = document.createElement('div'); root.className = 'strip';
      const drawn = new Map();
      const el = (tag, cls, text) => { const e = document.createElement(tag); e.className = cls;
        if (text !== undefined) e.textContent = text; return e; };
      const draw = () => {
        const want = [];
        for (const r of model.rows) {
          let d = drawn.get(r.id);
          if (!d) {
            const row = el('div', 'job'), name = el('span', 'jn');
            name.append(el('span', 'nm', r.name), el('span', 'pc', ' · ' + r.piece));
            const pill = el('span', 'pill'), act = el('button', 'act'), err = el('div', 'err');
            act.addEventListener('click', e => { e.stopPropagation();
              const now = drawn.get(r.id).r;
              model.send_msg(now.finished ? { dismiss: now.id } : { stop: now.id }); });
            row.append(name, pill, act, err);
            d = { row, pill, act, err }; drawn.set(r.id, d);
          }
          d.r = r;
          d.pill.className = 'pill ' + r.state;
          d.pill.textContent = r.clock ? r.words + ' ' + r.clock : r.words;
          const w = model.words;
          d.act.textContent = r.finished ? w.dismiss : w.stop;
          d.act.setAttribute('aria-label', (r.finished ? w.dismiss_label : w.stop_label).split('{name}').join(r.name));
          d.err.textContent = r.error || '';
          d.err.hidden = !r.error;
          want.push(d.row);
        }
        for (const [id, d] of drawn) if (!model.rows.some(r => r.id === id)) drawn.delete(id);
        const now = Array.from(root.children);
        if (now.length !== want.length || want.some((n, i) => now[i] !== n)) root.replaceChildren(...want);
      };
      model.on('rows', draw);
      draw();
      return root;
    }
    """

    def _handle_msg(self, msg: Any) -> None:
        if not isinstance(msg, dict):
            return
        if isinstance(msg.get("stop"), int) and self.on_stop is not None:
            self.on_stop(msg["stop"])
        elif isinstance(msg.get("dismiss"), int) and self.on_dismiss is not None:
            self.on_dismiss(msg["dismiss"])
