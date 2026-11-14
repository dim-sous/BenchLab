"""The made-up project's one piece: a wave u of amplitude A and frequency f over N samples, and
y = u plus Gaussian noise of standard deviation σ, drawn from a seed; the RMS of each. Its Run
group is test machinery for the runs in progress: a wait before it computes; a print to stdout,
left in Python's buffer and holding a byte that is not UTF-8; a crash, or a refusal written over
several lines as Benchlab's own ``Record.load`` writes one."""

from __future__ import annotations

import dataclasses
import sys
import time

import numpy as np
import param

from benchlab.record import Number, Provenance, Series, stamp
from benchlab.record import Record as _Record
from benchlab.record.config import Settings

__all__ = ["Config", "run", "Record"]


class Config(Settings):
    shape = param.Selector(default="sine", objects=["sine", "square"], label="Shape",
                           doc="The wave's shape.", metadata={"group": "Wave"})
    amplitude = param.Number(1.0, bounds=(0.0, None), label="A", doc="The wave's amplitude.",
                             metadata={"group": "Wave"})
    frequency = param.Number(2.0, bounds=(0.0, None), label="f",
                             doc="Cycles over the run.", metadata={"group": "Wave"})
    samples = param.Integer(40, bounds=(2, None), label="N", doc="Samples over the run.",
                            metadata={"group": "Wave"})
    noise = param.Number(0.0, bounds=(0.0, None), label="σ",
                         doc="The noise's standard deviation.", metadata={"group": "Noise"})
    seed = param.Integer(0, label="Seed", doc="The noise's draw.",
                         metadata={"group": "Noise", "replicate": True})
    delay = param.Number(0.0, bounds=(0.0, None), label="Delay",
                         doc="Seconds the run waits before it computes.", metadata={"group": "Run"})
    noisy = param.Boolean(False, label="Noisy", doc="The run prints to stdout first.",
                          metadata={"group": "Run"})
    fail = param.Selector(default="no", objects=["no", "crash", "refuse"], label="Fail",
                          doc="The run crashes, or refuses, instead of computing.",
                          metadata={"group": "Run"})


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

    def series(self) -> tuple[Series, ...]:
        return (Series(name="u", x=self.t, x_label="t", y_label="u", traces=(("u", self.u),),
                       group="Wave"),
                Series(name="y", x=self.t, x_label="t", y_label="y", traces=(("y", self.y),),
                       group="Wave", pooled=("mean", "rms")))

    def number_specs(self) -> tuple[Number, ...]:
        return (Number("rms_u", "RMS of u", group="Wave"),
                Number("rms_y", "RMS of y", headline=True, group="Wave"))


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
    wave = np.sin(2 * np.pi * cfg.frequency * t)
    u = cfg.amplitude * (wave if cfg.shape == "sine" else np.sign(wave))
    y = u + cfg.noise * np.random.default_rng(cfg.seed).standard_normal(cfg.samples)
    return Record(name="default", config=cfg, provenance=stamp(time.perf_counter() - started),
                  t=t, u=u, y=y, numbers={"rms_u": float(np.sqrt(np.mean(u ** 2))),
                                          "rms_y": float(np.sqrt(np.mean(y ** 2)))})
