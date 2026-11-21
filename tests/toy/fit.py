"""The made-up project's third piece: a line w0 + w1 x fitted to N noisy points by gradient
descent on the mean squared error. It holds what the wave and the lag do not: files a run writes
beside its run file -- the weights it ends with (``weights.npy``) and those it held half-way
(``checkpoints/half.npy``, a file in a folder of its own) -- and a setting naming an earlier fit
run whose weights it starts from, read out of that run's folder; and two settings of other kinds than the
six, a matrix (the 2 by 2 ``scale`` each step is multiplied by; the identity leaves the step as
it is) and a calendar date (``day``, only saved). Its Run group is test machinery:
a wait after its files are written, and a crash there."""

from __future__ import annotations

import dataclasses
import datetime
import time

import numpy as np
import param

from runlab import Number, Provenance, Quantity, Series, Settings, files_of, run_files, stamp
from runlab import Record as _Record

__all__ = ["Config", "run", "Record"]


#: The loss chart's two quantities, named once: its words in names are the ones it wrote in full
#: before 0.22 ("Step [-]", "Mean squared error [-]"); its symbols are new.
STEP = Quantity("step", name="Step", symbol="k")
MSE = Quantity("mse", name="Mean squared error", symbol="MSE")

class Config(Settings):
    slope = param.Number(2.0, label="Slope", doc="The slope of the line the points lie on.",
                         metadata={"group": "Points"})
    intercept = param.Number(-1.0, label="Intercept", doc="That line's value at x = 0.",
                             metadata={"group": "Points"})
    points = param.Integer(30, bounds=(2, None), label="N", doc="Points over x in [0, 1].",
                           metadata={"group": "Points"})
    noise = param.Number(0.1, bounds=(0.0, None), label="σ",
                         doc="The standard deviation of the noise on the points.",
                         metadata={"group": "Points"})
    seed = param.Integer(0, label="Seed", doc="The noise's draw.",
                         metadata={"group": "Points", "replicate": True})
    steps = param.Integer(40, bounds=(2, None), label="Steps", doc="Steps of gradient descent.",
                          metadata={"group": "Fit"})
    rate = param.Number(0.5, bounds=(0.0, None), inclusive_bounds=(False, True), label="Rate",
                        doc="The step's length along the gradient.", metadata={"group": "Fit"})
    scale = param.Array(np.eye(2), label="Scale",
                        doc="The 2 by 2 matrix each step along the gradient is multiplied by.",
                        metadata={"group": "Fit"})
    start_from = param.String("", label="Start from",
                              doc="The saved fit run whose weights the fit starts from; "
                                  "empty: from zero.",
                              metadata={"group": "Fit", "record_of": "fit"})
    day = param.CalendarDate(datetime.date(2026, 1, 1), label="Day",
                             doc="The day the points were taken; saved, and nothing else.",
                             metadata={"group": "Points"})
    delay = param.Number(0.0, bounds=(0.0, None), label="Delay",
                         doc="Seconds the run waits once its files are written.",
                         metadata={"group": "Run", "folded": True})
    fail = param.Boolean(False, label="Fail", doc="The run crashes once its files are written.",
                         metadata={"group": "Run", "folded": True})


@dataclasses.dataclass(frozen=True)
class Record(_Record):
    name: str
    config: Config
    provenance: Provenance | None
    step: np.ndarray
    loss: np.ndarray
    numbers: dict

    component = "fit"
    label = "Fit"
    produced_by = "uv run toy run fit"

    def series(self) -> tuple[Series, ...]:
        return (Series(name="loss", x=self.step, x_quantity=STEP, quantity=MSE,
                       traces=(("loss", self.loss),), group="Fit", y_log=True),)

    def number_specs(self) -> tuple[Number, ...]:
        return (Number("w0", "Fitted intercept", group="Fit"),
                Number("w1", "Fitted slope", group="Fit"),
                Number("loss", "Final mean squared error", headline=True, group="Fit"))


def run(cfg: Config) -> Record:
    started = time.perf_counter()
    x = np.linspace(0.0, 1.0, cfg.points)
    y = (cfg.intercept + cfg.slope * x
         + cfg.noise * np.random.default_rng(cfg.seed).standard_normal(cfg.points))
    w = np.load(files_of(cfg.start_from) / "weights.npy") if cfg.start_from else np.zeros(2)
    folder = run_files()
    (folder / "checkpoints").mkdir()
    loss = []
    for k in range(cfg.steps):
        if k == cfg.steps // 2:
            np.save(folder / "checkpoints" / "half.npy", w)
        error = w[0] + w[1] * x - y
        loss.append(float(np.mean(error ** 2)))
        w = w - cfg.rate * 2.0 * cfg.scale @ np.array([np.mean(error), np.mean(error * x)])
    np.save(folder / "weights.npy", w)
    time.sleep(cfg.delay)
    if cfg.fail:
        raise RuntimeError("the fit was told to fail")
    return Record(name="default", config=cfg, provenance=stamp(time.perf_counter() - started),
                  step=np.arange(cfg.steps), loss=np.array(loss),
                  numbers={"w0": float(w[0]), "w1": float(w[1]), "loss": loss[-1]})
