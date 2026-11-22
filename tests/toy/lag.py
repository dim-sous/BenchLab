"""The made-up project's second piece: a first-order lag, τ ẏ = -y + K u, driven by the u of a
saved wave run and sampled at the wave's own step under a zero-order hold -- exactly,
y[k+1] = a y[k] + (1 - a) K u[k] with a = exp(-Δt/τ), or by forward Euler, a = 1 - Δt/τ.

It holds what the wave does not, each for a test that needs one: a setting naming another piece's
saved run; two defaults the code resolves (K: none is 1; the hold: none is exact); a list of
numbers (the limits y is drawn against, as references named by what they bound) and a list of
text (the traces the output chart draws), a row each in the form; a list of rows, a table (the
steps and ramps added to the input, each row a time, a shape and a size; none by default, so a
run at the defaults is the wave's u alone); a unit; constants a run used beyond its Config; the
lag's Bode magnitude and phase, on logarithmic axes; and a figure it draws itself, its pole on
the complex plane, which lines against an abscissa cannot say."""

from __future__ import annotations

import dataclasses
import time

import numpy as np
import param

from runlab import Figure, Number, Provenance, Quantity, Series, Settings, bound_refs, stamp
from runlab import Record as _Record

from . import wave

__all__ = ["Config", "run", "Record"]

_TRACES = ("u", "y")


#: The lag's output, named once for its bound lines: by its symbol alone, so its words are the ones
#: it wrote in full before 0.25 ("Lower bound of y [-]").
Y = Quantity("y", symbol="y")


class Step(Settings):
    """One row of the input's additions: from ``at`` on, a step of ``size`` or a ramp of slope
    ``size`` is added to the wave's u."""

    at = param.Number(0.5, bounds=(0.0, None), label="From",
                      doc="The time the addition starts.", metadata={"group": "Source", "unit": "s"})
    shape = param.Selector(default="step", objects=["step", "ramp"], label="Shape",
                           doc="A step of the size, or a ramp of that slope.",
                           metadata={"group": "Source",
                                     "lines": {"step": "step [-]", "ramp": "ramp [1/s]"}})
    size = param.Number(1.0, label="Size", doc="The step's height, or the ramp's slope.",
                        metadata={"group": "Source"})


class Config(Settings):
    wave_run = param.String("results/wave/default.json", label="Wave run",
                            doc="The saved wave run whose u drives the lag.",
                            metadata={"group": "Source", "record_of": "wave"})
    steps = param.List([], item_type=Step, label="Additions",
                       doc="What is added to the wave's u, in order: each row a step or a ramp "
                           "from its time on.", metadata={"group": "Source"})
    gain = param.Number(None, allow_None=True, label="K", doc="The lag's gain; none: 1.",
                        metadata={"group": "Lag"})
    tau = param.Number(0.05, bounds=(0.0, None), inclusive_bounds=(False, True), label="τ",
                       doc="The lag's time constant.", metadata={"group": "Lag", "unit": "s"})
    hold = param.Selector(default=None, objects=["exact", "euler"], allow_None=True, label="Hold",
                          doc="How the lag is sampled; none: exact.", metadata={"group": "Lag"})
    limits = param.List([-1.0, 1.0], item_type=float, label="Limits",
                        doc="The lower and the upper bound y is drawn against.",
                        metadata={"group": "Output", "rows": {"label": "Limit {}", "add": "+ Limit"}})
    keep = param.List(["y"], item_type=str, label="Traces",
                      doc="The traces the output chart draws, each u or y.",
                      metadata={"group": "Output", "rows": {"label": "Trace {}", "add": "+ Trace"}})


@dataclasses.dataclass(frozen=True)
class Record(_Record):
    name: str
    config: Config
    provenance: Provenance | None
    t: np.ndarray
    u: np.ndarray
    y: np.ndarray
    omega: np.ndarray
    magnitude: np.ndarray
    phase: np.ndarray
    constants: dict
    numbers: dict

    component = "lag"
    label = "Lag"
    produced_by = "uv run toy run lag"

    def series(self) -> tuple[Series, ...]:
        held = {"u": self.u, "y": self.y}
        return (Series(name="output", x=self.t, x_label="t [s]", y_label="y [-]",
                       traces=tuple((k, held[k]) for k in self.config.keep),
                       refs=bound_refs(self.config.limits, Y), group="Time"),
                Series(name="bode-magnitude", x=self.omega, x_label="ω [rad/s]", y_label="|G| [-]",
                       traces=(("|G|", self.magnitude),), group="Frequency", x_log=True,
                       y_log=True),
                Series(name="bode-phase", x=self.omega, x_label="ω [rad/s]", y_label="∠G [deg]",
                       traces=(("∠G", self.phase),), group="Frequency", x_log=True,
                       doc="The lag's phase, from 0 down to -90 degrees."))

    def figures(self) -> tuple[Figure, ...]:
        pole = -1.0 / self.config.tau
        return (Figure(name="pole", group="Frequency", title="Pole", figure={
            "data": [{"type": "scatter", "mode": "markers", "x": [pole], "y": [0.0],
                      "marker": {"symbol": "x", "size": 11}}],
            "layout": {"xaxis": {"title": {"text": "Re [rad/s]"}},
                       "yaxis": {"title": {"text": "Im [rad/s]"}, "scaleanchor": "x"}}}),)

    def number_specs(self) -> tuple[Number, ...]:
        return (Number("peak_y", "Peak of y", headline=True, group="Time"),
                Number("corner", "Corner frequency", unit="rad/s", group="Frequency"))


def run(cfg: Config) -> Record:
    started = time.perf_counter()
    unknown = [k for k in cfg.keep if k not in _TRACES]
    if unknown:
        raise ValueError(f"the lag keeps the traces {' and '.join(_TRACES)}; it holds no "
                         f"{', '.join(unknown)}")
    source = wave.Record.load(cfg.wave_run)
    gain = 1.0 if cfg.gain is None else cfg.gain
    hold = cfg.hold or "exact"
    step = float(source.t[1] - source.t[0])
    a = float(np.exp(-step / cfg.tau)) if hold == "exact" else 1.0 - step / cfg.tau
    u = source.u
    for row in cfg.steps:
        since = np.clip(source.t - row.at, 0.0, None)
        u = u + row.size * (since if row.shape == "ramp" else (source.t >= row.at).astype(float))
    y = np.zeros_like(u)
    for k in range(len(y) - 1):
        y[k + 1] = a * y[k] + (1.0 - a) * gain * u[k]
    omega = np.logspace(-2.0, 2.0, 41) / cfg.tau
    return Record(name="default", config=cfg, provenance=stamp(time.perf_counter() - started),
                  t=source.t, u=u, y=y, omega=omega,
                  magnitude=abs(gain) / np.sqrt(1.0 + (omega * cfg.tau) ** 2),
                  phase=-np.degrees(np.arctan(omega * cfg.tau)),
                  constants={"gain": gain, "hold": hold, "step_s": step},
                  numbers={"peak_y": float(np.max(np.abs(y))), "corner": 1.0 / cfg.tau})
