"""The form, the run list and the compare table as plain data (DeePC's ``tests/test_lab_form.py``
and the half of its ``tests/test_lab.py`` that reads the run list, moved here onto the made-up
project in branch R1): what a control offers and says, which settings a gate shuts, the sweep row,
the runs the form queues, and the records read off their files -- read off the pieces' own
declarations, never restated here."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import pytest

from runlab.cli import folder_of
from runlab.lab import jobs, state, view
from runlab.lab.form import Form, as_text, term
from runlab.lab.words import say
from runlab.project import get_component, piece_names
from runlab.record.config import coerce_value, fields_of


@pytest.fixture
def piece() -> dict:
    return state.pieces()[0]


@pytest.fixture
def lag() -> dict:
    return next(p for p in state.pieces() if p["name"] == "lag")


def _runs(*names: str) -> list[dict]:
    return [{"piece": "wave", "name": n, "config": {}, "provenance": {}, "stale": ""}
            for n in names]


# --- the form ------------------------------------------------------------------------------

def test_the_lab_opens_on_the_first_piece_registered(piece) -> None:
    assert piece["name"] == piece_names()[0] == "wave"


def test_a_gate_that_shuts_takes_the_value_behind_it_back_with_the_reason(piece) -> None:
    form = Form(piece)
    assert form.type_or_pick("shape", "square") == []
    assert form.type_or_pick("duty", "0.3") == [] and form.set == {"shape": "square", "duty": "0.3"}
    assert form.type_or_pick("shape", "sine") == ["duty"]
    assert form.set == {}
    w, gate = form.label("duty"), form.label("shape")
    off, words = form.state_of(form.by_name["duty"])
    assert off and words == f"{w} applies only when {gate} is square; it is sine"
    # taken back, and SAID: a typed value that vanishes silently is one the run would ignore
    assert form.note() == (f"0 set — {w} taken back: the run would ignore it", True)


def test_a_gate_is_read_against_the_sweep_rungs_not_the_axis_default(piece) -> None:
    form = Form(piece)
    assert form.sweep("shape", "square,sine") == []
    assert form.type_or_pick("duty", "0.3") == []                 # some rungs open it: kept
    assert form.state_of(form.by_name["duty"]) == (False, ""), "not greyed: the note warns, below"
    assert form.note() == (f"1 set — {form.label('duty')} is set, and only some sweep values "
                           f"open it", True)
    assert form.sweep("shape", "sine") == ["duty"]                # no rung opens it: taken back
    assert form.state_of(form.by_name["duty"])[0]
    form.sweep("shape", "square, sine, sine")
    words, warns = form.note()
    assert warns and "repeats a value — Run refuses it" in words


def test_the_sweep_axis_is_swept_once_and_not_also_set(piece) -> None:
    form = Form(piece)
    form.type_or_pick("amplitude", "10")
    form.type_or_pick("samples", "20")
    assert form.sweep("amplitude", "1,5") == ["amplitude"]
    label = form.by_name["amplitude"]["label"]
    assert form.state_of(form.by_name["amplitude"]) == (
        True, f"{label} is the sweep axis; its values come from the sweep row")
    assert form.launch_words() == (["samples=20"], ["amplitude=1,5"])
    assert form.sweep("amplitude", "") == [] and form.swept() == ""
    assert form.launch_words() == (["samples=20"], [])
    # the values go as they were typed: what is an acceptable list is the runner's rule
    form.sweep("amplitude", " 1 , 5 ")
    assert form.launch_words()[1] == ["amplitude=1 , 5"]


def test_a_pick_list_offers_the_default_first(piece) -> None:
    form = Form(piece)
    by = form.by_name
    assert [(o["value"], o["words"]) for o in form.options(by["shape"])] == [
        ("", "sine (default)"), ("square", "square")]
    assert [(o["value"], o["words"]) for o in form.options(by["noisy"])] == [
        ("", "false (default)"), ("true", "true")]
    assert form.options(by["amplitude"]) is None


def test_a_default_the_code_resolves_is_said_so_not_left_blank(piece, lag) -> None:
    """``None`` in the Config is the code's own value, resolved by the run; an empty placeholder
    and a pick worded " (default)" said nothing about it."""
    form = Form(lag)
    by = form.by_name
    assert by["gain"]["code_default"] and form.shown_default(by["gain"]) == say("form.code_default")
    assert [(o["value"], o["words"]) for o in form.options(by["hold"])] == [
        ("", say("form.code_default")), ("exact", "exact"), ("euler", "euler")]
    assert Form(piece).shown_default(Form(piece).by_name["samples"]) == "40"


def test_a_saved_run_setting_offers_that_pieces_runs_by_name(lag) -> None:
    """RCWS's ``record_of``: the wave run is picked from the wave piece's saved runs, each worded
    by its name; the run it holds stays offered."""
    form = Form(lag)
    f = form.by_name["wave_run"]
    assert f["record_of"] == "wave"
    assert form.options(f) == [{"value": "", "words": "default (default)"}]
    form.saved = {"wave": ["results/wave/noisy.json", "results/wave/default.json"],
                  "lag": ["results/lag/x.json"]}
    assert [(o["value"], o["words"]) for o in form.options(f)] == [
        ("", "default (default)"), ("results/wave/noisy.json", "noisy")]
    form.type_or_pick("wave_run", "elsewhere/gone.json")
    assert [o["words"] for o in form.options(f)] == ["default (default)", "noisy", "gone"]
    assert form.launch_words() == (["wave_run=elsewhere/gone.json"], [])
    assert "wave_run" not in dict(form.axes()), "a path cannot name a sweep's records"


def test_a_list_of_numbers_goes_as_the_runner_reads_it_and_is_no_sweep_axis(lag) -> None:
    """A run's own list loads into its box as the JSON ``--set`` reads back, and the sweep row
    does not offer a list, because the sweep splits its values on commas."""
    form = Form(lag)
    form.use({"limits": [10.0, 10.0, 1.0]})
    assert form.launch_words() == (["limits=[10.0, 10.0, 1.0]"], [])
    limits = get_component("lag").Config.param["limits"]
    assert coerce_value(limits, form.set["limits"]) == [10.0, 10.0, 1.0]
    assert {"limits", "keep"}.isdisjoint(dict(form.axes()))


def test_a_control_wears_its_label_and_its_unit(lag) -> None:
    by = Form(lag).by_name
    assert term(by["tau"]) == "τ [s]" and term(by["hold"]) == "Hold"


def test_a_name_says_when_run_overwrites_a_record(piece) -> None:
    form = Form(piece)
    assert form.free_name(_runs("wave-1", "wave-2", "other")) == "wave-3"
    assert form.free_name([]) == "wave-1"
    form.name = "other"
    assert form.name_note(_runs("other")) == "other exists — Run overwrites it"
    assert form.name_note(_runs("else")) == ""

    # a sweep writes one record per rung, named as the runner names them
    held = _runs("wave-1-amplitude-2", "wave-1-amplitude-5")
    fresh = Form(piece)
    assert fresh.free_name(held) == "wave-2"
    fresh.sweep("amplitude", "2,5")
    assert fresh.would_write("wave-1") == ["wave-1-amplitude-2", "wave-1-amplitude-5"]
    assert fresh.name_note(held) == ""                 # the offered name is free: nothing to warn
    fresh.name = "wave-1"
    assert fresh.name_note(held) == ("wave-1-amplitude-2, wave-1-amplitude-5 exist "
                                     "— Run overwrites them")


def test_a_value_is_written_the_way_set_reads_it_back() -> None:
    assert [as_text(v) for v in (None, True, False, 2, 2.0, 0.25, 1e-06, "hold")] == [
        "", "true", "false", "2", "2", "0.25", "1e-06", "hold"]


def test_typing_the_default_leaves_the_field_unset(piece) -> None:
    form = Form(piece)
    assert form.type_or_pick("samples", "40") == [] and form.set == {}
    form.type_or_pick("samples", " 7 ")
    assert form.set == {"samples": "7"} and form.effective("samples") == "7"
    assert form.effective("shape") == "sine"


def test_use_loads_what_a_run_held_away_from_the_defaults_and_clear_empties(lag) -> None:
    form = Form(lag)
    form.type_or_pick("tau", "10")
    form.name, form.sweep_field, form.sweep_values = "x", "gain", "1,2"
    n, dropped = form.use({"wave_run": "results/wave/noisy.json", "tau": 50.0, "gain": None,
                           "limits": [-1.0, 1.0], "ancient": 7})
    assert n == 2 and form.set == {"wave_run": "results/wave/noisy.json", "tau": "50"}
    assert dropped == ["ancient"]        # named, not silently loaded as if it still were one
    assert form.name == "" and form.swept() == ""
    form.clear()
    assert form.set == {} and form.launch_words() == ([], [])


# --- the run list, read off its files ------------------------------------------------------

@pytest.fixture
def own_runs(two_runs) -> tuple[str, str]:
    return two_runs


def test_the_pieces_are_the_registry_with_their_own_declarations() -> None:
    pieces = state.pieces()
    assert [p["name"] for p in pieces] == list(piece_names())
    for p in pieces:
        component = get_component(p["name"])
        assert p["fields"] == fields_of(component.Config)
        assert p["label"] == component.Record.label and p["produced_by"]
        assert all(f["group"] and f["label"] for f in p["fields"])


def test_an_empty_out_dir_is_an_empty_list_not_an_error(tmp_path: Path) -> None:
    assert state.records(str(tmp_path), "results") == []


def test_records_are_read_off_their_files_newest_first(two_runs) -> None:
    root, out_dir = two_runs
    rows = state.records(root, out_dir)
    assert [r["name"] for r in rows] == ["second", "first"]
    for r in rows:
        assert set(r) == set(state.RECORD_KEYS)
        assert r["piece"] == "wave" and r["stale"] == "" and r["panels"] == ["u", "y"]
        assert {n["name"] for n in r["number_specs"]} == set(r["numbers"])
        assert r["provenance"]["git_sha"]
        json.dumps(r)                                    # plain data, nothing exotic
    assert rows[0]["config"]["amplitude"] == 2 and rows[1]["config"]["amplitude"] == 1


def test_a_record_is_re_read_only_when_its_file_changes(two_runs) -> None:
    root, out_dir = two_runs
    before = next(r for r in state.records(root, out_dir) if r["name"] == "second")
    assert state.records(root, out_dir)[0] is before
    path = Path(before["path"])
    os.utime(path, (time.time() + 5, time.time() + 5))
    after = next(r for r in state.records(root, out_dir) if r["name"] == "second")
    assert after is not before and after["name"] == before["name"]


@pytest.mark.parametrize("body,words", [('{"a": 1}', "carries no 'component' header"),
                                         ("not json at all", "not JSON")])
def test_a_json_that_is_not_a_record_is_listed_with_the_refusal_as_its_words(
        tmp_path: Path, body: str, words: str) -> None:
    """A kept settings file or a stray sidecar must not take the page down: the row carries
    ``read_header``'s refusal and the rest of the folder still lists."""
    folder = tmp_path / "results" / "wave"
    folder.mkdir(parents=True)
    (folder / "stray.json").write_text(body)
    rows = state.records(str(tmp_path), "results")
    assert len(rows) == 1 and rows[0]["name"] == "stray"
    assert words in rows[0]["stale"] and rows[0]["config"] == {} and rows[0]["panels"] == []


def test_a_record_the_class_has_moved_past_is_listed_and_marked(two_runs, tmp_path: Path) -> None:
    root, out_dir = two_runs
    raw = json.loads((Path(root) / out_dir / "wave" / "first.json").read_text())
    raw.pop("y")
    raw["mood"] = [1, 2]
    folder = tmp_path / "elsewhere" / "results" / "wave"
    folder.mkdir(parents=True)
    (folder / "old.json").write_text(json.dumps(raw))
    [row] = state.records(str(tmp_path / "elsewhere"), "results")
    assert "predates the field y" in row["stale"] and "holds gone field mood" in row["stale"]


def test_delete_takes_only_what_it_names_and_refuses_anything_else(own_runs) -> None:
    root, out_dir = own_runs
    folder = Path(root) / out_dir / "wave"
    with pytest.raises(ValueError, match="no record 'absent'"):
        jobs.delete("wave", records=["absent"], root=root, out_dir=out_dir)
    with pytest.raises(ValueError, match="cannot name a record"):
        jobs.delete("wave", records=["../second"], root=root, out_dir=out_dir)
    assert (folder / "second.json").exists()
    gone = jobs.delete("wave", records=["first"], root=root, out_dir=out_dir)
    assert gone == [os.path.join(out_dir, "wave", "first.json")]
    assert not (folder / "first.json").exists() and (folder / "second.json").exists()


def test_a_draw_of_many_runs_writes_a_folder_a_filesystem_takes() -> None:
    assert folder_of(["a", "b"]) == "a+b"
    names = [f"default-amplitude-{20 + i}-run-{i}" for i in range(20)]
    many = folder_of(names)
    assert len(many.encode()) <= 255 and many.startswith(names[0] + "+19-more-")
    assert many != folder_of(names[:-1] + ["other"]), "two sets of runs, two folders"


def test_a_shown_record_is_loaded_through_its_own_class_in_its_own_words(own_runs) -> None:
    """Loading is reading: the class decodes the file and refuses one it cannot, in words."""
    root, out_dir = own_runs
    run = next(r for r in state.records(root, out_dir) if r["name"] == "first")
    record = state.load(run)
    assert type(record) is get_component("wave").Record
    assert [s.name for s in record.series()] == run["panels"]
    broken = Path(root) / out_dir / "wave" / "broken.json"
    shutil.copy(run["path"], broken)
    broken.write_text(broken.read_text().replace('"t": [', '"tim": [', 1))
    with pytest.raises(ValueError, match="does not match the current Record"):
        state.load(dict(run, path=str(broken)))


# --- the rail, the chart list and the compare table ----------------------------------------

def test_a_chart_takes_the_first_group_a_run_names_for_it() -> None:
    """A run whose file predates groups names none, and must not blank the chart's group for the
    runs that do (BESS code review, 2026-10-27)."""
    runs = [{"name": "old", "panels": ["p"], "panel_groups": {}},
            {"name": "new", "panels": ["p"], "panel_groups": {"p": "Solver"}}]
    assert [row["group"] for row in view.chart_rows(runs, [])] == ["Solver"]


def test_a_rail_row_is_the_runs_name_and_why_it_cannot_be_read() -> None:
    """RCWS's row: the name alone, a stale run's reason under it; what sets a run apart is the
    compare table's to say."""
    runs = [{"piece": "wave", "name": "a", "config": {"amplitude": 5.0},
             "provenance": {"date": "2026-10-04T18:02:11+00:00", "git_sha": "0ff4c32abc",
                            "git_dirty": True},
             "stale": ""},
            {"piece": "wave", "name": "c", "config": {}, "provenance": {},
             "stale": "predates the field y"}]
    assert view.run_rows(runs) == [{"name": "a", "stale": ""},
                                   {"name": "c", "stale": "predates the field y"}]
    assert view.when(runs[0]) == "2026-10-04 18:02 · 0ff4c32" and view.when(runs[1]) == ""
    assert view.text(None) == "—" and view.text(0.123456) == "0.1235" and view.text(True) == "true"


_SPECS = [{"name": "rms_y", "label": "RMS of y", "unit": "V", "headline": True,
           "doc": "The RMS of the wave with its noise", "group": "Outputs"},
          {"name": "run_time_s", "label": "Run time", "unit": "s", "headline": False,
           "doc": "Wall-clock time of the run", "group": "Timing"}]


def _run(name: str, numbers: dict, config: dict, panels=("u", "y"), specs=None) -> dict:
    """A listed record row, as ``state.records`` hands one over."""
    return {"piece": "wave", "name": name, "config": config, "numbers": numbers,
            "panels": list(panels), "number_specs": list(specs if specs is not None else _SPECS),
            "provenance": {}, "stale": "", "mtime": 0.0, "path": f"{name}.json"}


def test_the_chart_list_is_the_panels_the_shown_runs_declare_in_their_own_order() -> None:
    both = [_run("a", {}, {}), _run("b", {}, {}, panels=("u", "y", "spectrum"))]
    rows = view.chart_rows(both, ["y"])
    assert [(r["name"], r["open"], r["sub"]) for r in rows] == [
        ("u", False, ""), ("y", True, ""), ("spectrum", False, "1 of 2 runs")]
    assert view.chart_rows([], []) == []


def test_the_compare_table_puts_the_numbers_first_and_the_settings_by_group(piece) -> None:
    runs = [_run("a", {"rms_y": 0.00267, "run_time_s": 3.0},
                 {"amplitude": 1.0, "samples": 40, "shape": "sine"}),
            _run("b", {"rms_y": 0.00412}, {"amplitude": 5.0, "samples": 40, "shape": "sine"})]
    rows = view.compare_rows(runs, piece["fields"], settings="all")

    assert rows[0] == {"kind": "head", "group": "Outputs", "key": "", "term": "Outputs",
                       "values": [], "differs": False}
    numbers = [r for r in rows if r["kind"] == "number"]
    assert [r["key"] for r in numbers] == ["rms_y", "run_time_s"], "a row opens its card"
    assert [r["term"] for r in numbers] == ["RMS of y [V]", "Run time [s]"]
    assert numbers[0]["values"] == ["0.00267", "0.00412"] and numbers[0]["differs"]
    assert numbers[1]["values"] == ["3", "—"], "a number a run does not carry is an em dash"

    heads = [r["term"] for r in rows if r["kind"] == "head"]
    assert heads == ["Outputs", "Timing"] + list(dict.fromkeys(f["group"] for f in piece["fields"]))
    assert [r["kind"] for r in view.compare_rows(runs, piece["fields"])].count("setting") == 0, \
        "the numbers alone until the settings are asked for"
    old = [dict(r, number_specs=[{k: v for k, v in s.items() if k != "group"} for s in _SPECS])
           for r in runs]
    assert view.compare_rows(old, piece["fields"])[0]["term"] == "Numbers", \
        "a file written before groups lists its numbers under one heading"
    by_term = {r["term"]: r for r in rows if r["kind"] == "setting"}
    fields = {f["name"]: f for f in piece["fields"]}
    amplitude = by_term[term(fields["amplitude"])]
    assert amplitude["values"] == ["1", "5"] and amplitude["differs"]
    shape = by_term[term(fields["shape"])]
    assert not shape["differs"] and shape["values"] == ["sine", "sine"]
    assert by_term[term(fields["frequency"])]["values"] == ["—", "—"], \
        "a setting a run's file does not hold is an em dash"


def test_only_the_settings_that_differ_keeps_every_number_and_drops_the_rest(piece) -> None:
    runs = [_run("a", {"rms_y": 1.0}, {"amplitude": 1.0, "shape": "sine"}),
            _run("b", {"rms_y": 2.0}, {"amplitude": 5.0, "shape": "sine"})]
    rows = view.compare_rows(runs, piece["fields"], settings="differ")
    settings = [r for r in rows if r["kind"] == "setting"]
    assert [r["values"] for r in settings] == [["1", "5"]]
    assert [r["kind"] for r in rows].count("number") == 2, "numbers are what runs are compared on"
    assert view.compare_count(rows, runs, piece["fields"]) == "1 setting · 1 number differ"
    hidden = view.compare_rows(runs, piece["fields"])
    assert view.compare_count(hidden, runs, piece["fields"]) == "1 setting · 1 number differ", \
        "a setting that differs is counted whether or not the table shows it"
    with pytest.raises(ValueError, match="settings is one of"):
        view.compare_rows(runs, piece["fields"], settings="some")


def test_the_count_says_what_differs_and_never_compares_one_run_with_itself(piece) -> None:
    one = [_run("a", {"rms_y": 1.0}, {})]
    alone = view.compare_rows(one, piece["fields"])
    assert view.compare_count(alone, one, piece["fields"]) == "2 numbers; tick another run to compare"
    pair = [_run("a", {"rms_y": 1.0}, {"shape": "sine"}), _run("b", {"rms_y": 1.0}, {"shape": "sine"})]
    same = view.compare_rows(pair, piece["fields"])
    assert view.compare_count(same, pair, piece["fields"]) == "2 numbers, none of them differs"
    assert view.varying([_run("a", {}, {"shape": "sine"}), _run("b", {}, {"shape": "square"})],
                        piece["fields"]) == ["shape"]


def test_a_row_differs_on_the_saved_values_not_on_the_words_they_are_shown_by(piece) -> None:
    """Four digits hide the sixth, and this table is where a refactor's numbers are checked."""
    runs = [_run("a", {"rms_y": 0.00267124}, {}), _run("b", {"rms_y": 0.00267139}, {})]
    rows = view.compare_rows(runs, piece["fields"])
    row = next(r for r in rows if r["kind"] == "number")
    assert row["values"] == ["0.002671", "0.002671"] and row["differs"]
    assert view.compare_count(rows, runs, piece["fields"]) == "0 settings · 1 number differ"


def test_a_chart_already_open_keeps_a_row_even_when_no_shown_run_draws_it() -> None:
    rows = view.chart_rows([_run("a", {}, {}, panels=("u",))], ["u", "y"])
    assert [(r["name"], r["open"], r["sub"]) for r in rows] == [
        ("u", True, ""), ("y", True, "No shown run draws it")]


def test_the_chart_list_is_in_the_groups_the_records_declare() -> None:
    a = dict(_run("a", {}, {}, panels=("u", "y", "spectrum")),
             panel_groups={"u": "Inputs", "y": "Outputs", "spectrum": "Outputs"})
    rows = view.chart_rows([a], [])
    assert [(g, [r["name"] for r in rs]) for g, rs in view.grouped(rows)] == [
        ("Inputs", ["u"]), ("Outputs", ["y", "spectrum"])]
    assert [r["group"] for r in view.chart_rows([_run("old", {}, {})], [])] == ["", ""], \
        "a file written before groups lists ungrouped"


def test_the_run_filter_keeps_the_runs_holding_every_word_anywhere() -> None:
    runs = [_run(n, {}, {}) for n in ("sweep-amplitude-1", "sweep-amplitude-50", "default", "p100")]
    assert [r["name"] for r in view.matching(runs, "amplitude 50")] == ["sweep-amplitude-50"]
    assert [r["name"] for r in view.matching(runs, "  ")] == [r["name"] for r in runs]
    assert view.matching(runs, "amplitude nope") == []
