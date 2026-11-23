"""A piece's own figures, as the page takes them.

The figure layer draws nothing here. A record's ``figures()`` are the piece's drawings, plotly
figures built from the record's own fields; this module hands one over as the plain dict the
page's Plotly pane serialises, with the card's look laid UNDER it as a plotly template -- the
paper, the type, the grid and zero lines, the margins, the colours in the charts' order -- so it
sits on its card as the layer's own charts do. A template fills only what a figure leaves unset:
whatever the piece set is kept, and its title, labels and legend are its own. A piece that
chose a template of its own keeps it.

A figure that holds frames, or carries a script, is handed over a second way as well
(:func:`own_page`): as the page plotly itself writes for it, which the Lab's page shows in a
frame. Observed 2026-11-22 (Panel 1.9.4): a figure with frames in the page's Plotly pane showed
its play button and its slider, held no frames, and did not move.

Observed 2026-11-17, driving DeePC's pole map: under plotly's stock template, which its classes
give every figure and the page's pane gives a plain dict, the grid and the zero lines are white,
drawn for that template's grey-blue plot; on the card's paper they did not show.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runlab.figure.style import FONT, GRID, INK, INK_SECONDARY, MONO, NEUTRAL, SURFACE, series_color
from runlab.figure.twin import ONE_PX

__all__ = ["own_figure", "own_page", "library_dir", "TEMPLATE"]

_AXIS = {"gridcolor": GRID, "linecolor": GRID, "zerolinecolor": NEUTRAL, "zerolinewidth": 1,
         "title": {"font": {"size": 12, "color": INK}, "standoff": 8}, "tickfont": {"size": 11}}
#: The card's look, as the layer's own charts wear it (:mod:`figure.twin`).
TEMPLATE: dict[str, Any] = {"layout": {
    "paper_bgcolor": SURFACE, "plot_bgcolor": SURFACE,
    "font": {"family": FONT, "size": 12, "color": INK_SECONDARY},
    "margin": {"l": 64, "r": 14, "t": 16, "b": 44},
    "colorway": [series_color(i) for i in range(8)],
    "hoverlabel": {"bgcolor": SURFACE, "bordercolor": GRID,
                   "font": {"family": MONO, "size": 11, "color": INK}},
    "xaxis": _AXIS, "yaxis": _AXIS}}


def _stock(figure: Any) -> bool:
    """Whether a figure built with plotly's classes wears plotly's stock template, which they
    give every figure whose piece chose none."""
    import plotly.io as pio                 # the figure is plotly's own: plotly is there

    return figure.layout.template == pio.templates[pio.templates.default]


def _plain(figure: Any) -> dict[str, Any]:
    """A plotly figure as a plain dict, its layout a dict of its own to write on, holding a
    template only where the piece chose one: a ``plotly.graph_objects.Figure`` through its own
    ``to_plotly_json``, a dict as it is."""
    built = hasattr(figure, "to_plotly_json")
    raw = figure.to_plotly_json() if built else figure
    if not isinstance(raw, dict) or "data" not in raw:
        raise TypeError(f"a figure is a plotly figure or the dict of one, holding its data; "
                        f"got {type(figure).__name__}")
    layout = dict(raw.get("layout") or {})
    if built and _stock(figure):
        layout.pop("template", None)
    return {**raw, "layout": layout}


def own_figure(record: Any, name: str) -> dict[str, Any] | None:
    """The figure ``name`` that ``record`` draws itself, as the page's pane takes it; ``None``
    when the record declares none of that name. Its layout's ``meta`` names the panel, as the
    layer's own charts' does; its height is the charts' where the piece set none."""
    for figure in record.figures():
        if figure.name == name:
            drawn = _plain(figure.figure)
            layout = drawn["layout"]
            layout.setdefault("template", TEMPLATE)
            layout.setdefault("height", ONE_PX)
            layout["meta"] = {**(layout.get("meta") or {}), "panel": name}
            return drawn
    return None


def own_page(record: Any, name: str, library: str) -> str | None:
    """The figure ``name`` that ``record`` draws itself, as a page of its own -- the one plotly
    writes (``plotly.io.to_html``), its plot the whole of the page, plotly's library read from
    the address ``library`` -- when the figure plays (it holds frames) or carries a script;
    ``None`` for any other figure, and for a name the record declares no figure of. Nothing
    plays until its play button is pressed. The script runs once the plot is made. The plot's
    element is always ``figure``: plotly's own choice is a new random id each time, and the
    same figure would then be a different page at every drawing (observed 2026-11-23: a frame
    given such a page again loaded it again, which starts a figure left playing over)."""
    declared = next((f for f in record.figures() if f.name == name), None)
    if declared is None:
        return None
    drawn = own_figure(record, name)
    if not drawn.get("frames") and not declared.script:
        return None
    import plotly.io as pio                 # the figure is plotly's own: plotly is there

    return pio.to_html(drawn, include_plotlyjs=library, full_html=True, auto_play=False,
                       post_script=declared.script or None, default_height="100%", div_id="figure",
                       config={"displaylogo": False, "responsive": True})


def library_dir() -> Path:
    """The folder of the installed ``plotly`` package that holds plotly's own library
    (``plotly.min.js``), which a playing figure's page reads."""
    import plotly

    return Path(plotly.__file__).parent / "package_data"
