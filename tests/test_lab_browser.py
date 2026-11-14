"""The Lab driven in a real browser (headless Chromium), as a person drives it: the runs in progress
update on the page as the runs move, which only a served page shows (its periodic callback runs
in the browser's session). A run started from the form ends Done and its record joins the list;
a sweep of three, two allowed at once, shows Running and Queued, then Done, and joins the list
too; a long run is stopped from its row while the form is open over the page (Playwright clicks
only what nothing covers). DeePC's ``tests/test_lab_browser.py`` drives the rest of the page
through DeePC's pieces.

The browser is Playwright's Chromium: once per computer, ``uv run playwright install chromium``.
"""

from __future__ import annotations

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


def test_the_runs_in_progress_move_on_the_page_as_the_runs_do(tmp_path, toy_installed,
                                                              monkeypatch) -> None:
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
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
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
            browser.close()
    finally:
        server.stop()
        pn.config.exception_handler = handler             # `serve` sets it process-wide
        jobs.QUEUE.stop_all()
        for done in jobs.QUEUE.runs():
            jobs.QUEUE.dismiss(done.id)
