"""The Lab driven in a real browser (headless Chromium), as a person drives it: the runs in progress
update on the page as the runs move, which only a served page shows (its periodic callback runs
in the browser's session). A run started from the form ends Done and its record joins the list;
a sweep of three, two allowed at once, shows Running and Queued, then Done, and joins the list
too; a long run is stopped from its row while the form is open over the page (Playwright clicks
only what nothing covers). Nothing the page draws wears a hover but a greyed control, and a
value its setting refuses is said under it when Run is pressed. DeePC's
``tests/test_lab_browser.py`` drives the rest of the page through DeePC's pieces.

The browser is Playwright's Chromium: once per computer, ``uv run playwright install chromium``.
"""

from __future__ import annotations

import contextlib
import socket
import time
import urllib.request

import panel as pn
import pytest
from playwright import sync_api as playwright

from benchlab import cli
from benchlab.lab import jobs
from benchlab.lab.app import serve
from benchlab.runner import planned

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
def _served(tmp_path, query: str = ""):
    """The Lab served over two toy runs, ``first`` and ``second``, and a browser page on it
    (``query`` its address's, e.g. ``?shown=first``): ``(page, errors, root, out_dir)``."""
    root, out_dir = str(tmp_path), "results"
    for name in ("first", "second"):
        cli.main(["run", "wave", "--name", name, "--out-dir", str(tmp_path / out_dir)])
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
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"page: {e}"))
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
