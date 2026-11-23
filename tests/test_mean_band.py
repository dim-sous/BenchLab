"""Runs pooled into their mean are weighted by the draws each is a mean of, and drawn inside the
band their panel gives for a mean of all their draws (``Series.averaged``, ``Series.mean_band``).
On the made-up wave's y: the mean of ``draws`` Gaussian draws about u, its band u ± z σ/√n."""

from __future__ import annotations

import dataclasses
import importlib
import json
from statistics import NormalDist

import numpy as np
import pytest

from runlab import Series, cli
from runlab.figure.chart import chart_of, mean_band_of, pool_refusal
from runlab.testing import check_project
from tests.toy import wave

SIGMA = 0.5
Z = NormalDist().inv_cdf(0.975)
#: The module, which the package's own ``draw`` function hides under its name.
draw_module = importlib.import_module("runlab.figure.draw")


def _run(name: str, seed: int, draws: int, **more) -> tuple[str, wave.Record]:
    cfg = wave.Config(noise=SIGMA, seed=seed, draws=draws, **more)
    return name, dataclasses.replace(wave.run(cfg), name=name)


def _noise(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(wave.Config().samples)


#: Three runs that share no draw: seed 1; seeds 2, 3, 4; seeds 5, 6. Six draws in all.
def _three() -> list[tuple[str, wave.Record]]:
    return [_run("a", 1, 1), _run("b", 2, 3), _run("c", 5, 2)]


def test_a_run_of_several_draws_is_their_mean_from_the_seed_on() -> None:
    _, one = _run("one", 7, 1)
    assert np.array_equal(one.y, one.u + SIGMA * _noise(7)), "one draw: the seed's own"
    _, three = _run("three", 7, 3)
    assert np.array_equal(three.y, three.u + SIGMA * np.mean([_noise(7), _noise(8), _noise(9)],
                                                             axis=0))


def test_runs_pool_into_the_mean_of_all_their_draws_inside_its_band() -> None:
    pairs = _three()
    assert pool_refusal(pairs, "y", "mean") == ""
    [axes] = chart_of(pairs, "y", runs="mean").axes
    [line], [band] = axes.lines, axes.bands
    (_, a), (_, b), (_, c) = pairs
    assert line.label == "Mean of 3 runs · y"
    assert np.array_equal(line.y, (1 * a.y + 3 * b.y + 2 * c.y) / 6), "each run by its draws"
    every = a.u + SIGMA * np.mean([_noise(seed) for seed in range(1, 7)], axis=0)
    assert np.allclose(line.y, every, rtol=0, atol=1e-14), "the mean of the six draws themselves"
    half = Z * SIGMA / np.sqrt(6)
    assert band.label == "95% interval of the mean, N = 6"
    assert np.array_equal(band.lo, a.u - half) and np.array_equal(band.hi, a.u + half)


def test_runs_pool_into_their_rms_by_their_draws_with_no_band() -> None:
    pairs = _three()
    [axes] = chart_of(pairs, "y", runs="rms").axes
    (_, a), (_, b), (_, c) = pairs
    assert np.array_equal(axes.lines[0].y, np.sqrt((a.y ** 2 + 3 * b.y ** 2 + 2 * c.y ** 2) / 6))
    assert axes.bands == ()


def test_the_band_of_a_mean_is_drawn_for_pooled_runs_only() -> None:
    pairs = _three()
    assert chart_of(pairs[:1], "y").axes[0].bands == (), "one run alone"
    assert chart_of(pairs, "y").axes[0].bands == (), "overlaid"
    assert all(ax.bands == () for ax in chart_of(pairs, "y", runs="rows").axes), "a row each"


def test_runs_that_share_a_draw_do_not_pool() -> None:
    pairs = [_run("a", 1, 3), _run("b", 3, 1)]
    assert pool_refusal(pairs, "y", "mean") == "runs a and b make the same draw: both use seed 3"
    with pytest.raises(ValueError, match="cannot be pooled by mean: runs a and b make the same"):
        chart_of(pairs, "y", runs="mean")


def test_runs_whose_panels_give_different_bands_do_not_pool_by_their_mean() -> None:
    (_, a), (_, b) = _run("a", 1, 1), _run("b", 2, 1)
    pairs = [("a", a), ("b", dataclasses.replace(b, u=b.u + 1.0))]
    assert pool_refusal(pairs, "y", "mean") == \
        "the runs' charts give different bands for a mean of 2 draws"
    assert pool_refusal(pairs, "y", "rms") == "", "an RMS draws no band"


def test_a_panel_declares_the_band_of_a_mean_only_with_a_mean_and_at_least_one_draw() -> None:
    held = dict(name="p", x=[0.0, 1.0], x_label="t", y_label="y", traces=(("y", [0.0, 1.0]),))
    with pytest.raises(ValueError, match="declares the band of a mean but no 'mean' pooling"):
        Series(**held, pooled=("rms",), mean_band=lambda n: ("band", 0.0, 1.0))
    with pytest.raises(ValueError, match="averages 0 draws; at least 1"):
        Series(**held, pooled=("mean",), averaged=0)
    plain = Series(**held, pooled=("mean",))
    assert plain.averaged == 1 and mean_band_of(plain, 4) == ()


def test_a_band_edge_of_another_length_is_refused_and_the_projects_check_finds_it(
        tmp_path, monkeypatch) -> None:
    path = wave.run(wave.Config(noise=SIGMA)).save(tmp_path / "results" / "wave" / "held.json")
    check_project(runs=[path], sources=[])
    monkeypatch.setattr(wave.Record, "_interval", lambda self, n: ("band", self.u[:-1], 1.0))
    with pytest.raises(AssertionError, match="the chart 'y' does not draw .*its band of a mean "
                                             "of 1 draws has an edge of 39 values against 40"):
        check_project(runs=[path], sources=[])


def test_saved_runs_of_several_draws_pool_into_a_still_with_its_band(tmp_path, monkeypatch) -> None:
    out = tmp_path / "results"
    for name, seed, draws in (("a", 1, 1), ("b", 2, 3)):
        cli.main(["run", "wave", "--set", f"noise={SIGMA}", "--set", f"seed={seed}",
                  "--set", f"draws={draws}", "--name", name, "--out-dir", str(out)])
    records = sorted(str(p) for p in (out / "wave").glob("*.json"))
    assert json.loads((out / "wave" / "b.json").read_text())["config"]["draws"] == 3
    drawn, panels = tmp_path / "drawn", []
    render = draw_module.render
    monkeypatch.setattr(draw_module, "render",
                        lambda panel, *a, **k: panels.append(panel) or render(panel, *a, **k))
    assert cli.main(["draw", *records, "--panel", "y", "--runs", "mean",
                     "--out-dir", str(drawn)]) == 0
    assert (drawn / "y.png").is_file()
    assert json.loads((drawn / "y.png.json").read_text())["traces"] == ["Mean of 2 runs · y"]
    assert [b.label for b in panels[0].axes[0].bands] == ["95% interval of the mean, N = 4"]
