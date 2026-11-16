"""The Lab driven in a real browser (headless Chromium), as a person drives it: the runs in progress
update on the page as the runs move, which only a served page shows (its periodic callback runs
in the browser's session). A run started from the form ends Done and its record joins the list;
a sweep of three, two allowed at once, shows Running and Queued, then Done, and joins the list
too; a long run is stopped from its row while the form is open over the page (Playwright clicks
only what nothing covers). Nothing the page draws wears a hover but a greyed control, and a
value its setting refuses is said under it when Run is pressed.

The Python-driven page tests (``test_lab_view.py``) set a widget's values one at a time; a
browser does not. On 2026-10-27 BESS's suite passed (189) while the real page lost a value pasted
into a box or typed with Tab right after it: one browser message carried both of the box's
values, a watcher over both got two events from it, and the run kept its default while the box
showed the value. So these also hold, on the page as served (DeePC's
``tests/test_lab_browser.py``, moved here onto the made-up project in branch R1): what is typed
or pasted into the form is what the run uses, read off the record it saves; every chart's points
in the browser are exactly its record's numbers; driving the page raises no error in the browser;
at half a laptop screen and at full width, nothing runs off the page and no words on a chart sit
on top of each other; a list setting shows a labelled row per item and takes every key.

The browser is Playwright's Chromium: once per computer, ``uv run playwright install chromium``.
"""

from __future__ import annotations

import contextlib
import json
import socket
import time
import urllib.request
from pathlib import Path

import numpy as np
import panel as pn
import pytest
from playwright import sync_api as playwright

from benchlab import cli
from benchlab.lab import jobs
from benchlab.lab.app import serve
from benchlab.runner import planned
from tests.toy import wave

#: The words the page shows, leaf by leaf, through its shadow roots (DeePC's ``_TEXT``).
_TEXT = """() => {
  const out = [];
  const walk = root => { root.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
    root.querySelectorAll('span,b,button,td,th,pre').forEach(e => {
      const t = (e.innerText || '').trim(); if (t && !e.children.length) out.push(t); }); };
  walk(document);
  return out;
}"""


def _shows(page, *words: str, timeout: float = 45.0) -> list[str]:
    """Wait until every one of ``words`` is in some leaf the page shows; those leaves."""
    deadline = time.time() + timeout
    while True:
        text = page.evaluate(_TEXT)
        if all(any(w in t for t in text) for w in words) or time.time() > deadline:
            assert all(any(w in t for t in text) for w in words), (words, text)
            return text
        page.wait_for_timeout(300)


@contextlib.contextmanager
def _served(tmp_path, query: str = "", *, width: int = 1440, second: tuple[str, ...] = (),
            lag: bool = False):
    """The Lab served over two toy runs, ``first`` and ``second`` (the defaults, but for the
    settings ``second`` names for it) -- and, with ``lag``, a run ``one`` of the lag on ``first``
    -- and a browser page ``width`` wide on it (``query`` its address's, e.g. ``?shown=first``):
    ``(page, errors, root, out_dir)``, the errors those the page raises and those it logs to its
    console."""
    root, out_dir = str(tmp_path), "results"
    for name, sets in (("first", ()), ("second", second)):
        cli.main(["run", "wave", "--name", name, "--out-dir", str(tmp_path / out_dir),
                  *(w for item in sets for w in ("--set", item))])
    if lag:
        cli.main(["run", "lag", "--name", "one", "--out-dir", str(tmp_path / out_dir),
                  "--set", f"wave_run={tmp_path / out_dir / 'wave' / 'first.json'}"])
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    handler = pn.config.exception_handler
    server = serve(port, root, out_dir, show=False, threaded=True)
    deadline = time.time() + 30
    while True:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read()
            break
        except OSError:
            if time.time() > deadline:
                raise
            time.sleep(0.2)
    try:
        with playwright.sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:  # noqa: BLE001 -- no browser here: say how to get one
                pytest.fail(f"no Chromium for Playwright here ({str(exc).splitlines()[0]}); "
                            f"install it once: uv run playwright install chromium")
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"page: {e}"))
            page.on("console",
                    lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
            page.goto(f"http://127.0.0.1:{port}/{query}", wait_until="networkidle")
            yield page, errors, root, out_dir
            browser.close()
    finally:
        server.stop()
        pn.config.exception_handler = handler             # `serve` sets it process-wide
        jobs.QUEUE.stop_all()
        for done in jobs.QUEUE.runs():
            jobs.QUEUE.dismiss(done.id)


def test_the_runs_in_progress_move_on_the_page_as_the_runs_do(tmp_path, toy_installed,
                                                              monkeypatch) -> None:
    with _served(tmp_path) as (page, errors, root, out_dir):
        _shows(page, "Nothing running", "2 on disk")
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(800)
        page.get_by_role("button", name="Run", exact=True).click()
        _shows(page, "1 done", "3 on disk")                # the form's run, ended and listed
        monkeypatch.setattr(jobs.QUEUE, "at_once", 2)
        jobs.QUEUE.submit("wave", planned("sw", ["delay=2"], ["seed=1,2,3"]), root=root,
                          out_dir=out_dir)
        _shows(page, "2 running · 1 queued")
        _shows(page, "4 done", "6 on disk")                 # the sweep, ended and listed
        page.locator("button", has_text="New run").click()  # the form over the page
        page.wait_for_timeout(800)
        [run] = jobs.QUEUE.submit("wave", planned("long", ["delay=60"]), root=root,
                                  out_dir=out_dir)
        _shows(page, "1 running")
        page.get_by_role("button", name="Stop long", exact=True).click()
        _shows(page, "1 stopped")
        assert run.state == "stopped" and not errors, errors


#: Every element under the page's shadow roots that carries a hover: a ``title``, or plotly's own
#: ``data-title`` (a toolbar button's name, which its stylesheet shows on hover) -- as ``[which
#: attribute, its words, the element's style, its class]``.
_TITLED = """() => {
  const out = [];
  const walk = root => root.querySelectorAll('*').forEach(el => {
    for (const attr of ['title', 'data-title'])
      if (el.hasAttribute && el.hasAttribute(attr))
        out.push([attr, el.getAttribute(attr), el.getAttribute('style') || '',
                  typeof el.className === 'string' ? el.className : '']);
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""


def test_nothing_wears_a_hover_but_a_greyed_control_and_run_refuses_under_a_setting(
        tmp_path, toy_installed) -> None:
    """``docs/design.md`` decision 5, in the browser: with both runs shown, a chart card, a
    number card, the form open and a run in the strip, the only hovers left are greyed controls'
    reasons (their style is :data:`benchlab.lab.skin.GREYED`) and the chart toolbar's own button
    names, which the mockup kept. Then A = -1 and Run: refused under A, the form still open,
    nothing more queued."""
    from benchlab.lab import skin
    with _served(tmp_path, "?shown=first,second&open=u") as (page, errors, root, out_dir):
        _shows(page, "2 on disk")
        jobs.QUEUE.submit("wave", planned("long", ["delay=60"]), root=root, out_dir=out_dir)
        _shows(page, "1 running")                                 # its Stop in the strip
        page.locator("td", has_text="RMS of y").first.click()      # a number card
        _shows(page, "All | Mean | RMS")                         # its greyed controls
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(1200)
        hovers = page.evaluate(_TITLED)
        titles = [h for h in hovers if h[0] == "title"]
        assert titles, "no greyed control found: the walk sees nothing"
        assert all(style == skin.GREYED for _, _, style, _ in titles), \
            [h for h in titles if h[2] != skin.GREYED]
        assert all("modebar-btn" in cls for attr, _, _, cls in hovers if attr == "data-title"), \
            [h for h in hovers if h[0] == "data-title" and "modebar-btn" not in h[3]]
        page.locator(".run", has_text="first").first.hover()     # its actions show on hover
        assert page.get_by_role("button", name="Delete first", exact=True).is_visible(), \
            "the run list's ✕, named for a screen reader"
        page.locator('input[placeholder="1"]').fill("-1")         # A, whose default is 1
        page.wait_for_timeout(500)
        page.get_by_role("button", name="Run", exact=True).click()
        _shows(page, "A must be at least 0, got -1")
        assert [r.name for r in jobs.QUEUE.runs()] == ["long"], "nothing more queued"
        assert page.get_by_role("button", name="Run", exact=True).is_visible(), "the form open"
        assert not errors, errors


# --- DeePC's browser tests, on the made-up project (branch R1) ------------------------------

#: Every chart in the page's shadow roots, as plotly holds it: each trace's name, x and y, and
#: the figure's meta (what panel it is).
_PLOTS = """() => {
  const out = [];
  const walk = root => root.querySelectorAll('*').forEach(el => {
    if (el.classList && el.classList.contains('js-plotly-plot') && el.data)
      out.push({meta: el.layout.meta, traces: el.data.map(t => ({name: t.name, x: t.x, y: t.y,
                                                                    fill: t.fill || ''}))});
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""
#: On every chart, the boxes of the words plotly draws -- the legend, the annotations, the axis
#: titles -- as [chart, what, left, top, right, bottom].
_WORD_BOXES = """() => {
  const out = [];
  const walk = root => root.querySelectorAll('*').forEach(el => {
    if (el.classList && el.classList.contains('js-plotly-plot')) {
      const sel = ['.legend', '.annotation', '.g-xtitle', '[class^="g-y"][class$="title"]'];
      sel.forEach(s => el.querySelectorAll(s).forEach(w => { const r = w.getBoundingClientRect();
        if (r.width && r.height) out.push([el.layout.meta.panel, s, r.left, r.top, r.right, r.bottom]); }));
    }
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""
#: Every element under the page's shadow roots whose right edge is past the window's.
_PAST_THE_EDGE = """() => {
  const out = [], w = window.innerWidth;
  const walk = root => root.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > w + 1 && getComputedStyle(el).visibility !== 'hidden')
      out.push((el.className && el.className.baseVal === undefined ? el.className : el.tagName) + ' ' + Math.round(r.right));
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""


def _charts(page, n: int, timeout: float = 30.0) -> list[dict]:
    """The page's charts once ``n`` are drawn, or those drawn when ``timeout`` runs out. (Read
    1.5 s after the network went idle, they were none in two runs of DeePC's whole suite,
    2026-11-14; the log kept of one shows plotly had not yet reported a chart's size.)"""
    deadline = time.time() + timeout
    while len(plots := page.evaluate(_PLOTS)) < n and time.time() < deadline:
        page.wait_for_timeout(200)
    return plots


def test_what_is_pasted_or_typed_with_tab_at_once_is_what_the_run_uses(tmp_path,
                                                                       toy_installed) -> None:
    with _served(tmp_path) as (page, errors, root, out_dir):
        record = Path(root) / out_dir / "wave" / "wave-1.json"     # the name offered
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(900)
        page.locator('input[placeholder="2"]').click()             # f, whose default is 2
        page.keyboard.insert_text("3")                             # a paste
        page.keyboard.press("Tab")                                 # and Tab, at once
        page.wait_for_timeout(900)
        page.locator('input[placeholder="40"]').click()            # N, whose default is 40
        page.keyboard.type("25", delay=0)                          # keys and Tab, at once
        page.keyboard.press("Tab")
        page.wait_for_timeout(900)
        page.get_by_role("button", name="Run", exact=True).click()
        deadline = time.time() + 60
        while not record.exists() and time.time() < deadline:
            page.wait_for_timeout(300)
        config = json.loads(record.read_text())["config"]
        assert config["frequency"] == 3 and config["samples"] == 25, config
        assert not errors, errors


def test_every_chart_in_the_browser_is_exactly_its_records_numbers(tmp_path) -> None:
    with _served(tmp_path, "?shown=second,first&open=u,y",
                 second=("amplitude=2", "noise=0.1")) as (page, errors, root, out_dir):
        plots = _charts(page, 2)
        assert sorted(p["meta"]["panel"] for p in plots) == ["u", "y"]
        records = {name: wave.Record.load(Path(root) / out_dir / "wave" / f"{name}.json")
                   for name in ("first", "second")}
        checked = 0
        for plot in plots:
            for trace in plot["traces"]:
                # a long name is broken onto lines at its separators, each kept on its line
                run, _, label = trace["name"].replace("<br>", " ").partition(" — ")
                if trace["fill"] or run not in records:
                    continue                    # a band, a reference, a line every run holds
                series = next(s for s in records[run].series() if s.name == plot["meta"]["panel"])
                if not label:                   # a run left with one trace of its own: its name
                    [(label, _)] = series.traces
                y = dict(series.traces)[label]
                assert np.array_equal(np.asarray(trace["x"], float), np.asarray(series.x, float))
                assert np.array_equal(np.asarray(trace["y"], float), np.asarray(y, float)), \
                    f"{plot['meta']['panel']} {trace['name']}"
                checked += 1
        assert checked == 2 * 2, "each run's own line on the two charts"
        assert not errors, errors


def test_driving_every_kind_of_card_raises_nothing_in_the_browser(tmp_path) -> None:
    with _served(tmp_path, "?shown=second,first&open=u",
                 second=("amplitude=2",)) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("td", has_text="RMS of y").first.click()      # a number card
        page.wait_for_timeout(1500)
        # a chart card's one control is its runs (the developer's cut, 2026-11-11)
        for words in ("Split", "Overlay"):
            page.locator("button", has_text=words).first.click()
            page.wait_for_timeout(900)
        for gone in ("Save", "Table", "Dots", "Log x", "Quantity"):
            assert not page.locator("button", has_text=gone).count(), f"{gone} is not on a card"
        page.locator("button", has_text="Differing").click()
        page.wait_for_timeout(900)
        assert any("vs A" in t for t in page.evaluate(_TEXT)), "the number card is on the page"
        assert not errors, errors


def _overlapping(boxes: list[list]) -> list[str]:
    out = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] != b[0]:
                continue
            if min(a[4], b[4]) - max(a[2], b[2]) > 1 and min(a[5], b[5]) - max(a[3], b[3]) > 1:
                out.append(f"{a[0]}: {a[1]} on {b[1]}")
    return out


@pytest.mark.parametrize("width", [1000, 1440])
def test_at_half_a_screen_and_at_full_width_nothing_runs_off_or_overprints(tmp_path, width) -> None:
    with _served(tmp_path, "?shown=second,first&open=u,y", width=width,
                 second=("amplitude=2",)) as (page, errors, _root, _out_dir):
        _charts(page, 2)
        page.locator("button", has_text="Split").first.click()       # the stacked layout
        page.wait_for_timeout(1500)
        assert page.evaluate("document.documentElement.scrollWidth") <= width, \
            "the page scrolls sideways"
        past = page.evaluate(_PAST_THE_EDGE)
        assert not past, f"past the window's right edge at {width} px: {past[:8]}"
        assert not _overlapping(page.evaluate(_WORD_BOXES)), _overlapping(page.evaluate(_WORD_BOXES))
        assert not errors, errors


def test_a_list_setting_shows_a_labelled_row_per_item_and_adds_one(tmp_path) -> None:
    """The developer, 2026-11-11, of DeePC's System form: rows for each equation, labelled, with
    add and remove. Switching the piece may log a plotly page error of its own (found in DeePC,
    2026-11-11); the form must add none."""
    with _served(tmp_path) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("select").first.select_option(label="Lag")
        page.wait_for_timeout(2500)
        switched = len(errors)
        page.locator("button", has_text="New run").first.click()
        page.wait_for_timeout(1500)
        assert [t for t in page.evaluate(_TEXT) if t.endswith(" =")] == [
            "Limit 1 =", "Limit 2 =", "Trace 1 ="]
        page.locator("button", has_text="+ Trace").first.click()
        page.wait_for_timeout(1500)
        assert "Trace 2 =" in page.evaluate(_TEXT)
        box = next(b for b in page.locator("input[type=text]").all() if b.input_value() == "y")
        box.click()
        page.keyboard.press("End")
        page.keyboard.type(" and u", delay=40)                  # key by key, as a person types
        page.wait_for_timeout(1500)
        assert box.input_value() == "y and u", "every key reached the box (code review)"
        assert not errors[switched:], errors[switched:]


def test_a_figure_the_piece_draws_itself_is_drawn_in_the_browser_as_the_piece_drew_it(
        tmp_path) -> None:
    """Branch R3: the lag's pole, a plotly figure of the piece's own, opened from the chart list;
    plotly in the browser holds the piece's own point and the page raises nothing for it."""
    with _served(tmp_path, lag=True) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("select").first.select_option(label="Lag")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.locator("button", has_text="Frequency").first.click()   # its group, in the index
        page.wait_for_timeout(600)
        page.locator("button", has_text="Pole").first.click()
        plots = {p["meta"]["panel"]: p for p in _charts(page, 2)}
        assert sorted(plots) == ["output", "pole"]
        [trace] = plots["pole"]["traces"]
        assert trace["x"] == [-20] and trace["y"] == [0], "the pole of the default τ = 0.05"
        assert "Pole" in page.evaluate(_TEXT), "the card's title"
        assert not errors[switched:], errors[switched:]
