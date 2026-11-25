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
on top of each other; a list setting shows a labelled row per item and takes every key. The page
needs no internet: every request beyond this computer is refused and counted an error, and its
fonts load from RunLab's own files.

The browser is Playwright's Chromium: once per computer, ``uv run playwright install chromium``.
"""

from __future__ import annotations

import contextlib
import json
import re
import socket
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import panel as pn
import pytest
from playwright import sync_api as playwright

from runlab import cli
from runlab.lab import jobs
from runlab.lab.app import serve
from runlab.runner import planned
from tests.stand_ins import settled
from tests.toy import lag, wave

#: The words the page shows, leaf by leaf, through its shadow roots (DeePC's ``_TEXT``).
_TEXT = """() => {
  const out = [];
  const walk = root => { root.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
    root.querySelectorAll('span,b,button,td,th,pre').forEach(e => {
      const t = (e.innerText || '').trim(); if (t && !e.children.length) out.push(t); }); };
  walk(document);
  return out;
}"""


def _run(page):
    """The form's Run. A chart card over several runs carries a button of the same word, the
    Run of its Colour by, so the form's is found by its dress: the page's primary button."""
    return page.locator("button.bk-btn-primary", has_text=re.compile(r"^Run$"))


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
            lag: bool = False, fit: bool = False):
    """The Lab served over two toy runs, ``first`` and ``second`` (the defaults, but for the
    settings ``second`` names for it) -- and, with ``lag``, a run ``one`` of the lag on ``first``;
    with ``fit``, a run ``a`` of the fit -- and a browser page ``width`` wide on it (``query`` its address's, e.g. ``?shown=first``):
    ``(page, errors, root, out_dir)``, the errors those the page raises, those it logs to its
    console, and each request it makes beyond this computer, which is refused: the page needs no
    internet."""
    root, out_dir = str(tmp_path), "results"
    for name, sets in (("first", ()), ("second", second)):
        cli.main(["run", "wave", "--name", name, "--out-dir", str(tmp_path / out_dir),
                  *(w for item in sets for w in ("--set", item))])
    if lag:
        cli.main(["run", "lag", "--name", "one", "--out-dir", str(tmp_path / out_dir),
                  "--set", f"wave_run={tmp_path / out_dir / 'wave' / 'first.json'}"])
    if fit:
        cli.main(["run", "fit", "--name", "a", "--out-dir", str(tmp_path / out_dir)])
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

            def beyond(route) -> None:
                if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost"):
                    route.continue_()
                else:
                    errors.append(f"asked beyond this computer: {route.request.url}")
                    route.abort()
            page.route("**/*", beyond)
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
        _run(page).click()
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
    """No hovers, in the browser: with both runs shown, a chart card, a
    number card, the form open and a run in the strip, the only hovers left are greyed controls'
    reasons (their style is :data:`runlab.lab.skin.GREYED`) and the chart toolbar's own button
    names, which the mockup kept. Then A = -1 and Run: refused under A, the form still open,
    nothing more queued."""
    from runlab.lab import skin
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
        # A, whose default is 1: the first of the two boxes that show a 1 (Draws is the other)
        page.locator('input[placeholder="1"]').first.fill("-1")
        page.wait_for_timeout(500)
        _run(page).click()
        _shows(page, "A must be at least 0, got -1")
        assert [r.name for r in jobs.QUEUE.runs()] == ["long"], "nothing more queued"
        assert _run(page).is_visible(), "the form open"
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
        _run(page).click()
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


def test_a_zoom_drawn_with_the_mouse_on_one_chart_moves_the_other(tmp_path) -> None:
    """The one path the page's own tests cannot walk: from the mouse, through plotly and the
    page's code, to the other chart; and a double click back to the whole of both."""
    with _served(tmp_path, "?shown=first&open=u,y") as (page, errors, root, out_dir):
        assert len(_charts(page, 2)) == 2
        plots = page.locator(".js-plotly-plot")
        # sorted: a chart zoomed with the mouse held the same six labels in another order than
        # the chart the zoom was set on (Chromium 157 in a cloud session, 2026-11-18: `0.4`
        # first on the one, `0.3` first on the other, both charts on 0.3 to 0.55)
        ticks = lambda i: sorted(plots.nth(i).locator(".xtick text").all_text_contents())

        def settled(what, said: str) -> None:
            deadline = time.time() + 20
            while not what() and time.time() < deadline:
                page.wait_for_timeout(200)
            assert what(), (said, ticks(0), ticks(1))

        whole = ticks(1)
        assert ticks(0) == whole
        box = plots.first.locator(".nsewdrag").first.bounding_box()
        y = box["y"] + box["height"] / 2
        page.mouse.move(box["x"] + box["width"] * 0.30, y)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.45, y, steps=8)
        page.mouse.move(box["x"] + box["width"] * 0.60, y, steps=8)
        page.mouse.up()
        settled(lambda: ticks(0) != whole and ticks(1) == ticks(0), "the other chart follows")
        page.mouse.dblclick(box["x"] + box["width"] / 2, y)
        settled(lambda: ticks(0) == whole and ticks(1) == whole, "a reset reaches it too")
        assert not errors, errors


def test_driving_every_kind_of_card_raises_nothing_in_the_browser(tmp_path) -> None:
    with _served(tmp_path, "?shown=second,first&open=u",
                 second=("amplitude=2",)) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("td", has_text="RMS of y").first.click()      # a number card
        page.wait_for_timeout(1500)
        button = lambda words: page.get_by_role("button", name=words, exact=True)
        # every control of a card, pressed once on each card that carries it (the developer's
        # answers of 2026-11-17): the path from the click to the page's code and back
        for words in ("Split", "Overlay", "Quantity"):
            assert button(words).count() == 1, f"{words} is the chart card's alone"
            button(words).click()
            page.wait_for_timeout(900)
        for words in ("Dots", "Lines", "Table", "Chart"):
            assert button(words).count() == 2, f"{words} is on the number card and on the chart card"
            for i in range(2):
                button(words).nth(i).click()
                page.wait_for_timeout(900)
                if words == "Table":
                    assert page.locator(".numbers th").count(), "the table stands in the card"
        assert not page.locator(".numbers").count(), "both cards are back on their charts"
        assert len(_charts(page, 2)) == 2
        # the wave runs from t = 0 and below zero, so its Log x and Log y are greyed; the number
        # card's amplitudes are 1 and 2
        assert button("Log x").count() == button("Log y").count() == 1
        for _ in range(2):
            button("Log x").click()
            page.wait_for_timeout(900)
        axis = page.locator("select", has=page.locator("option", has_text="Sample index"))
        axis.select_option(label="Sample index [-]")
        page.wait_for_timeout(900)
        assert "Sample index [-]" in page.locator(".xtitle").all_text_contents(), \
            "the chart card's bottom axis"
        # Save on each card, the folder it wrote listed, and deleted after its question
        assert button("Save").count() == 2, "on the number card and on the chart card"
        for i in range(2):
            button("Save").nth(i).click()
            page.wait_for_timeout(2500)              # the first loads the drawing library
        said = page.evaluate(_TEXT)
        assert sum("Wrote results/wave/second+first/" in t for t in said) == 2, said
        saved = page.locator(".run.flat")
        assert saved.locator(".name").all_text_contents() == ["second+first"], \
            "listed under Saved pictures"
        assert "2 pictures" in saved.locator(".when").first.text_content()
        saved.first.hover()                          # a row's delete shows under the mouse
        page.get_by_role("button", name="Delete the saved pictures second+first",
                         exact=True).click()
        page.get_by_text("Delete the pictures in results/wave/second+first/?").wait_for()
        button("Delete").click()
        page.wait_for_timeout(1500)
        assert not page.locator(".run.flat").count(), "gone from the list"
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


def test_a_piece_whose_rows_start_greyed_opens_on_a_pick(tmp_path, monkeypatch) -> None:
    """1.17: a click on a piece whose form held a table greyed at its defaults left the page on
    the piece before (a project's page, 2026-11-25): the pick's one batch held changes to boxes
    the browser was never sent, and it dropped the batch whole, raising "reference ... isn't
    known". Here the lag's Limits rows are shut at its defaults; picked, the page shows the lag's
    one run."""
    limits = lag.Config.param["limits"]
    monkeypatch.setattr(limits, "metadata",
                        {**limits.metadata, "needs": {"drive": {"in": ["built"]}}})
    with _served(tmp_path, lag=True) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("select").first.select_option(label="Lag")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        assert not [e for e in errors if "isn't known" in e], errors


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


def test_a_figure_that_plays_plays_in_the_browser_and_its_script_runs(tmp_path) -> None:
    """1.1: the fit's descent, a figure of the piece's own that holds frames, opened from the
    chart list. It is plotly's own page in a frame on the card: its script ran there, the point
    stands at the first step, and its Play button moves it to the last. The library that page
    reads came from this computer, and the page raises nothing for it."""
    with _served(tmp_path, fit=True) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.locator("button", has_text="Descent").first.click()
        page.wait_for_timeout(2500)
        framed = [f for f in page.frames if "/runlab-frames/" in f.url]
        assert len(framed) == 1, [f.url for f in page.frames]
        [frame] = framed
        frame.wait_for_function("document.getElementById('figure') "
                                "&& document.getElementById('figure').data")
        now = "document.getElementById('figure').data[1].x[0]"
        assert frame.evaluate("document.getElementById('figure').dataset.scripted") == "yes"
        assert frame.evaluate(now) == 0, "nothing plays until asked"
        steps = frame.evaluate("document.getElementById('figure').data[0].x.length")
        assert steps > 10
        frame.locator("text=Play").first.click()
        frame.wait_for_function(f"{now} === {steps - 1}", timeout=15000)
        assert "Descent" in page.evaluate(_TEXT), "the card's title"
        assert not errors[switched:], errors[switched:]


def test_a_runs_messages_show_on_their_card_in_the_browser(tmp_path) -> None:
    """1.3: the fit's messages, opened from the chart list, read on the page as the run says
    them, and the page raises nothing for them."""
    with _served(tmp_path, fit=True) as (page, errors, _root, _out_dir):
        _shows(page, "2 on disk")
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.locator("button", has_text="Messages").first.click()
        _shows(page, "the descent")
        assert any(t.startswith("stopped after 40 steps at a loss of ")
                   for t in page.evaluate(_TEXT))
        assert not errors[switched:], errors[switched:]


def test_a_runs_files_show_in_the_compare_table_and_go_with_the_run(tmp_path, toy_installed) -> None:
    """Branch R4: a fit run started from the form lists the files it wrote, by size; a second,
    started from the first through the form's pick of a saved run, ran on its weights; a run
    stopped from its row leaves no folder; a run deleted from the list takes its folder, the
    question naming it."""
    with _served(tmp_path) as (page, errors, root, out_dir):
        folder = Path(root) / out_dir / "fit"
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "0 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(800)
        _run(page).click()
        _shows(page, "1 done", "1 on disk", "FILES", "weights.npy", "144 B")
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(800)
        # Start from: the list that offers the saved fit (a card's bottom axis is a list too)
        page.locator("select", has=page.locator("option", has_text="fit-1")) \
            .select_option(label="fit-1")
        page.wait_for_timeout(500)
        _run(page).click()
        _shows(page, "2 done", "2 on disk")
        second = json.loads((folder / "fit-2.json").read_text())
        assert second["config"]["start_from"] == "results/fit/fit-1.json"
        assert second["loss"][0] < 0.01, "it started from the first run's weights, not from zero"
        page.locator("button", has_text="All").first.click()
        _shows(page, "2 shown")
        assert page.evaluate(_TEXT).count("144 B") == 4, "two files, under each of two runs"
        [run] = jobs.QUEUE.submit("fit", planned("long", ["delay=60"]), root=root, out_dir=out_dir)
        _shows(page, "1 running")
        settled((folder / "long.files.partial" / "weights.npy").is_file, lambda: "no weights yet")
        page.get_by_role("button", name="Stop long", exact=True).click()
        _shows(page, "1 stopped")
        settled(lambda: not (folder / "long.files.partial").exists(), lambda: "its folder is left")
        page.locator(".run", has_text="fit-1").first.hover()
        page.get_by_role("button", name="Delete fit-1", exact=True).click()
        page.get_by_text("Delete results/fit/fit-1.json and results/fit/fit-1.files/, the 2 files "
                         "its run wrote?").wait_for()
        page.get_by_role("button", name="Delete", exact=True).click()
        _shows(page, "1 on disk")
        assert sorted(p.name for p in folder.iterdir()) == ["fit-2.files", "fit-2.json"]
        assert run.state == "stopped" and not errors[switched:], errors[switched:]


def test_a_matrix_and_a_date_are_typed_refused_run_compared_and_loaded_back(tmp_path,
                                                                           toy_installed) -> None:
    """Branch R5: the fit's Scale (a matrix) and Day (a calendar date), settings of other kinds
    than the six. A text neither reads is refused under each when Run is pressed and nothing is
    queued; ones they read run, and the run file holds them; the compare table words the matrix
    as typed, its shape kept; a run's settings loaded back into the form are that text."""
    scale, day = 'input[placeholder="[[1.0, 0.0], [0.0, 1.0]]"]', 'input[placeholder="2026-01-01"]'
    with _served(tmp_path) as (page, errors, root, out_dir):
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "0 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(800)
        _run(page).click()
        _shows(page, "1 done", "1 on disk")
        page.locator("button", has_text="New run").click()
        page.wait_for_timeout(800)
        page.locator(scale).fill("[[1, 0], [0")
        page.locator(day).fill("tomorrow")
        page.wait_for_timeout(500)
        _run(page).click()
        _shows(page, "Scale cannot read [[1, 0], [0", "Day cannot read tomorrow")
        assert [r.name for r in jobs.QUEUE.runs()] == ["fit-1"], "nothing more queued"
        page.locator(scale).fill("[[1, 0], [0, 0.5]]")
        page.locator(day).fill("2026-02-03")
        page.wait_for_timeout(500)
        _run(page).click()
        _shows(page, "2 done", "2 on disk")
        held = json.loads((Path(root) / out_dir / "fit" / "fit-2.json").read_text())["config"]
        assert (held["scale"], held["day"]) == ([[1.0, 0.0], [0.0, 0.5]], "2026-02-03")
        page.locator("button", has_text="All").first.click()
        _shows(page, "2 shown")
        page.locator("button", has_text="Differing").first.click()
        _shows(page, "[[1.0, 0.0], [0.0, 1.0]]", "[[1.0, 0.0], [0.0, 0.5]]", "2026-02-03")
        page.locator(".run", has_text="fit-2").first.hover()
        page.get_by_role("button", name="Use", exact=True).first.click()
        page.wait_for_timeout(1200)
        assert page.locator(scale).input_value() == "[[1.0, 0.0], [0.0, 0.5]]"
        assert page.locator(day).input_value() == "2026-02-03"
        assert not errors[switched:], errors[switched:]


#: Load each face named (a CSS font, ``"500 16px 'IBM Plex Mono'"``) as the page would; the faces
#: loaded, as ``"<family> <weight> <status>"``.
_LOAD = """async named => {
  const out = [];
  for (const font of named) (await document.fonts.load(font)).forEach(
    f => out.push(`${f.family} ${f.weight} ${f.status}`));
  return out;
}"""


def test_the_page_carries_its_own_fonts_and_asks_nothing_beyond_this_computer(tmp_path) -> None:
    """Every request beyond this computer is refused (``_served``), and the page's two typefaces
    at its five weights still load: RunLab's own files, served beside the page."""
    with _served(tmp_path, "?shown=first,second&open=u,y") as (page, errors, root, out_dir):
        faces = [("IBM Plex Sans", 400), ("IBM Plex Sans", 500), ("IBM Plex Sans", 600),
                 ("IBM Plex Mono", 400), ("IBM Plex Mono", 500)]
        loaded = page.evaluate(_LOAD, [f"{weight} 16px '{family}'" for family, weight in faces])
        assert loaded == [f"{family} {weight} loaded" for family, weight in faces]
        assert not errors, errors


#: Every chart's two axis titles, as plotly in the browser holds them.
_AXES = """() => {
  const out = [];
  const walk = root => root.querySelectorAll('*').forEach(el => {
    if (el.classList && el.classList.contains('js-plotly-plot') && el.layout)
      out.push([el.layout.xaxis.title.text, el.layout.yaxis.title.text]);
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""


def test_the_switch_words_a_chart_in_the_browser_keeps_its_choice_and_saves_in_it(tmp_path) -> None:
    """0.22: the made-up fit's loss chart, made from quantities. The header's Symbols turns its
    axes, in plotly in the browser, to the symbols; the address keeps the choice; Save writes
    the picture in symbols, its note saying so."""
    cli.main(["run", "fit", "--name", "a", "--out-dir", str(tmp_path / "results")])
    with _served(tmp_path) as (page, errors, root, out_dir):
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.get_by_role("button", name="All", exact=True).first.click()
        _shows(page, "Mean squared error")
        if not page.evaluate(_AXES):
            page.locator("button:visible", has_text=re.compile(r"^\s*Mean squared error\s*$")) \
                .first.click()
        deadline = time.time() + 30
        while page.evaluate(_AXES) != [["Step [-]", "Mean squared error [-]"]]:
            assert time.time() < deadline, page.evaluate(_AXES)
            page.wait_for_timeout(300)
        page.get_by_role("button", name="Symbols", exact=True).click()
        while page.evaluate(_AXES) != [["k [-]", "MSE [-]"]]:
            assert time.time() < deadline + 30, page.evaluate(_AXES)
            page.wait_for_timeout(300)
        assert "MSE" in page.evaluate(_TEXT), "the chart list's title and the card's"
        assert "words=symbols" in page.url
        page.get_by_role("button", name="Save", exact=True).first.click()
        notes: list[Path] = []
        while not notes:
            assert time.time() < deadline + 60, "no picture saved"
            page.wait_for_timeout(300)
            notes = list((Path(root) / out_dir / "fit").rglob("*.png.json"))
        [note] = notes
        assert json.loads(note.read_text())["shaping"]["words"] == "symbols"
        assert not errors[switched:], errors[switched:]


#: Mark every chart's plot element (``True``), or read the marks back (``False``): an element the
#: page drew anew carries none.
_MARK = """(set) => {
  const out = [];
  const walk = root => root.querySelectorAll('*').forEach(el => {
    if (el.classList && el.classList.contains('js-plotly-plot')) {
      if (set) el.dataset.kept = 'yes';
      out.push(el.dataset.kept || '');
    }
    if (el.shadowRoot) walk(el.shadowRoot);
  });
  walk(document);
  return out;
}"""


def test_a_charts_plot_is_updated_where_it_stands_through_the_switch_save_and_a_control(
        tmp_path) -> None:
    """0.24: a card drawn again keeps its plot's element in the browser and gives it the new
    figure. Drawn anew on every drawing, a plot the browser was still drawing was destroyed
    under it: plotly's "_guiEditing" error, 4 of 48 saves under load on 0.23.0."""
    cli.main(["run", "fit", "--name", "a", "--out-dir", str(tmp_path / "results")])
    with _served(tmp_path) as (page, errors, root, out_dir):
        page.locator("select").first.select_option(label="Fit")
        _shows(page, "1 on disk")
        page.wait_for_timeout(1500)
        switched = len(errors)
        page.get_by_role("button", name="All", exact=True).first.click()
        deadline = time.time() + 30
        while page.evaluate(_AXES) != [["Step [-]", "Mean squared error [-]"]]:
            assert time.time() < deadline, page.evaluate(_AXES)
            page.wait_for_timeout(200)
        assert page.evaluate(_MARK, True) == ["yes"]
        page.get_by_role("button", name="Symbols", exact=True).click()
        while page.evaluate(_AXES) != [["k [-]", "MSE [-]"]]:
            assert time.time() < deadline + 30, page.evaluate(_AXES)
            page.wait_for_timeout(200)
        assert page.evaluate(_MARK, False) == ["yes"], "the same element, with the new words"
        page.get_by_role("button", name="Save", exact=True).first.click()
        notes: list[Path] = []
        while not notes:
            assert time.time() < deadline + 60, "no picture saved"
            page.wait_for_timeout(200)
            notes = list((Path(root) / out_dir / "fit").rglob("*.png.json"))
        page.wait_for_timeout(1000)
        assert page.evaluate(_MARK, False) == ["yes"], "Save drew the cards again, the plot kept"
        page.get_by_role("button", name="Dots", exact=True).first.click()
        page.wait_for_timeout(1500)
        assert page.evaluate(_MARK, False) == ["yes"], "a control drew the card again, kept"
        assert not errors[switched:], errors[switched:]
