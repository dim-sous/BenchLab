"""The made-up project's one piece: a wave u of amplitude A and frequency f over N samples -- a
sine, or a square wave high for its duty share of each cycle -- and y = u plus Gaussian noise of
standard deviation σ, the mean of one or more draws from a seed on; the RMS of each. Its y is the
one chart whose runs pool, so it holds what a pooled chart may declare: how many draws it is a
mean of, and the band of a mean of n draws -- u ± z σ/√n, z the standard normal's 0.975
quantile: the 95 % interval of the mean of n Gaussian draws. The duty opens only with the square
wave and excludes both its bounds, so the form has a gate and an open interval to refuse at; σ
includes both of its, [0, 10]: ends a value may equal. The Run group is folded. Its Run
group is test machinery for the runs in progress: a wait before it computes; a print to stdout,
left in Python's buffer and holding a byte that is not UTF-8; a crash, or a refusal written over
several lines as RunLab's own ``Record.load`` writes one."""

from __future__ import annotations

import dataclasses
import sys
import time
from statistics import NormalDist

import numpy as np
import param

from runlab import Number, Provenance, Series, Settings, stamp
from runlab import Record as _Record

__all__ = ["Config", "run", "Record"]

#: The standard deviations either side of a Gaussian mean that hold it with 95 % probability.
_Z = NormalDist().inv_cdf(0.975)


class Config(Settings):
    shape = param.Selector(default="sine", objects=["sine", "square"], label="Shape",
                           doc="The wave's shape.", metadata={"group": "Wave"})
    duty = param.Number(0.5, bounds=(0.0, 1.0), inclusive_bounds=(False, False), label="Duty",
                        doc="The square wave's share of each cycle spent high.",
                        metadata={"group": "Wave", "needs": {"shape": {"in": ["square"]}}})
    amplitude = param.Number(1.0, bounds=(0.0, None), label="A", doc="The wave's amplitude.",
                             metadata={"group": "Wave"})
    frequency = param.Number(2.0, bounds=(0.0, None), label="f",
                             doc="Cycles over the run.", metadata={"group": "Wave"})
    samples = param.Integer(40, bounds=(2, None), label="N", doc="Samples over the run.",
                            metadata={"group": "Wave"})
    noise = param.Number(0.0, bounds=(0.0, 10.0), label="σ",
                         doc="The noise's standard deviation.", metadata={"group": "Noise"})
    seed = param.Integer(0, label="Seed", doc="The noise's draw; of several, the first.",
                         metadata={"group": "Noise", "replicate": True, "draws": "draws"})
    draws = param.Integer(1, bounds=(1, None), label="Draws",
                          doc="How many draws of the noise y is the mean of, from the seed on.",
                          metadata={"group": "Noise"})
    delay = param.Number(0.0, bounds=(0.0, None), label="Delay",
                         doc="Seconds the run waits before it computes.",
                         metadata={"group": "Run", "folded": True})
    noisy = param.Boolean(False, label="Noisy", doc="The run prints to stdout first.",
                          metadata={"group": "Run", "folded": True})
    fail = param.Selector(default="no", objects=["no", "crash", "refuse"], label="Fail",
                          doc="The run crashes, or refuses, instead of computing.",
                          metadata={"group": "Run", "folded": True})


@dataclasses.dataclass(frozen=True)
class Record(_Record):
    name: str
    config: Config
    provenance: Provenance | None
    t: np.ndarray
    u: np.ndarray
    y: np.ndarray
    numbers: dict

    component = "wave"
    label = "Wave"
    produced_by = "uv run toy run wave"
    provides = ("u",)

    def series(self) -> tuple[Series, ...]:
        return (Series(name="u", x=self.t, x_label="t", y_label="u", traces=(("u", self.u),),
                       group="Wave", doc="The wave, before its noise."),
                Series(name="y", x=self.t, x_label="t", y_label="y", traces=(("y", self.y),),
                       group="Wave", pooled=("mean", "rms"), averaged=self.config.draws,
                       mean_band=self._interval))

    def _interval(self, n: int) -> tuple[str, np.ndarray, np.ndarray]:
        """The 95 % interval of y's mean over ``n`` draws, about u."""
        half = _Z * self.config.noise / np.sqrt(n)
        return f"95% interval of the mean, N = {n}", self.u - half, self.u + half

    def number_specs(self) -> tuple[Number, ...]:
        return (Number("rms_u", "RMS of u", group="Wave"),
                Number("rms_y", "RMS of y", headline=True, group="Wave",
                       doc="The RMS of the wave with its noise."))


def run(cfg: Config) -> Record:
    started = time.perf_counter()
    if cfg.noisy:
        print("the wave says hello on stdout")
        sys.stdout.buffer.write(b"and a byte UTF-8 has no word for: \xff\n")
        sys.stdout.buffer.flush()                  # below the print, which is left buffered
    time.sleep(cfg.delay)
    if cfg.fail == "crash":
        raise RuntimeError("the wave was told to fail")
    if cfg.fail == "refuse":
        raise FileNotFoundError("no Record record at results/wave/gone.json. Run it first:\n"
                                "    uv run toy run wave\nwhich writes that file.")
    t = np.linspace(0.0, 1.0, cfg.samples)
    u = cfg.amplitude * (np.sin(2 * np.pi * cfg.frequency * t) if cfg.shape == "sine" else
                         np.where((cfg.frequency * t) % 1.0 < cfg.duty, 1.0, -1.0))
    y = u + cfg.noise * np.mean([np.random.default_rng(cfg.seed + i).standard_normal(cfg.samples)
                                 for i in range(cfg.draws)], axis=0)
    return Record(name="default", config=cfg, provenance=stamp(time.perf_counter() - started),
                  t=t, u=u, y=y, numbers={"rms_u": float(np.sqrt(np.mean(u ** 2))),
                                          "rms_y": float(np.sqrt(np.mean(y ** 2)))})
