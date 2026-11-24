"""What the form shows beyond what is typed (1.11): an empty setting's number looked up off
another's (``default_from``), the values a picked saved run sets in place of the ones set here
(``replaces``), a registered option opened as the settings it stands for (``stands_for``), and a
table's rows by their names (``row_words``). On settings built here, as a project declares them
(the other project's tracker, fit and flight)."""

from __future__ import annotations

import json

import param

from runlab import Settings
from runlab.lab.app import _Table
from runlab.lab.form import Form
from runlab.record.config import fields_of

CRUISE = {"fighter": 250.0, "drone": 50.0}


class _Switch(Settings):
    mode = param.String("cv", metadata={"group": "g"})
    ca = param.Number(None, allow_None=True, metadata={"group": "g"})


class _Flight(Settings):
    flight = param.Selector(default="built", objects=["built", "weave"], label="flight",
                            metadata={"group": "g",
                                      "stands_for": lambda: {"weave": {"flight": "built",
                                                                       "turn_g": 4.0}}})
    vehicle = param.Selector(default="fighter", objects=list(CRUISE), metadata={"group": "g"})
    speed = param.Number(None, allow_None=True, label="speed",
                         metadata={"group": "g", "default_from": ("vehicle", CRUISE)})
    told = param.Number(None, allow_None=True, metadata={"group": "g",
                                                         "default_from": ("speed", None)})
    turn_g = param.Number(0.0, metadata={"group": "g"})
    fit = param.String("", metadata={"group": "g", "record_of": "fit", "replaces": "flies"})
    gain = param.Number(1.0, metadata={"group": "g"})
    transition = param.List([], item_type=_Switch,
                            metadata={"group": "g", "by_name": "mode",
                                      "row_words": {"cv": {"label": "constant velocity"}}})


def _form() -> Form:
    return Form({"name": "flight", "fields": fields_of(_Flight)})


def test_the_declarations_are_reported_read_now() -> None:
    f = {x["name"]: x for x in fields_of(_Flight)}
    assert f["speed"]["default_from"] == {"field": "vehicle", "values": CRUISE}
    assert f["told"]["default_from"] == {"field": "speed", "values": None}
    assert f["flight"]["stands_for"] == {"weave": {"flight": "built", "turn_g": 4.0}}
    assert f["fit"]["replaces"] == "flies"
    assert f["transition"]["row_words"] == {"cv": {"label": "constant velocity"}}


def test_an_empty_setting_shows_the_number_it_looks_up_and_follows_the_other() -> None:
    form = _form()
    speed, told = form.by_name["speed"], form.by_name["told"]
    assert form.shown_default(speed) == "250"
    form.type_or_pick("vehicle", "drone")
    assert form.shown_default(speed) == "50", "it follows the vehicle picked"
    form.type_or_pick("speed", "80")
    assert form.shown_default(told) == "80", "the other setting's own value"


def test_a_picked_run_shows_the_values_it_sets_in_place_of_the_ones_set_here(tmp_path) -> None:
    from runlab.lab import app as app_module
    run = tmp_path / "results" / "fit" / "a-fit.json"
    run.parent.mkdir(parents=True)
    run.write_text(json.dumps({"component": "fit", "flies": [["gain", 2.5]]}))
    form = _form()

    class _Lab:
        root = str(tmp_path)
    _Lab.form = form
    app_module.Lab._replaced_by(_Lab, form.by_name["fit"], "results/fit/a-fit.json")
    assert form.shown_default(form.by_name["gain"]) == "2.5 (from a-fit)"
    app_module.Lab._replaced_by(_Lab, form.by_name["fit"], "")
    assert form.shown_default(form.by_name["gain"]) == "1"


def test_use_opens_a_registered_option_at_the_settings_it_stands_for() -> None:
    form = _form()
    form.use({"flight": "weave", "vehicle": "fighter"})
    assert form.set == {"turn_g": "4"}, "the flight built here, its turn as the weave's"


def test_a_table_of_named_rows_labels_each_by_its_words() -> None:
    f = next(x for x in fields_of(_Flight) if x["name"] == "transition")
    table = _Table(f, on_edit=lambda text: None)
    table.value = json.dumps([{"mode": "cv", "ca": 0.1}, {"mode": "ca", "ca": None}])
    assert [table._row_label(i, r) for i, r in enumerate(table._rows)] == [
        "constant velocity", "ca"]


# --- 1.14: a table looked up, and a part's looked-up setting --------------------------------

_BY_FORM = {"slow": [{"mode": "cv", "ca": 0.1}, {"mode": "ct", "ca": 0.2}],
            "fast": [{"mode": "cv", "ca": 0.5}]}


class _Bank(Settings):
    form = param.Selector(default="slow", objects=list(_BY_FORM), metadata={"group": "g"})
    rows = param.List([], item_type=_Switch,
                      metadata={"group": "g", "by_name": "mode",
                                "default_from": ("form", lambda: _BY_FORM),
                                "row_words": {"cv": {"label": "constant velocity"}}})
    once = param.List([], item_type=_Switch,
                      metadata={"group": "g", "by_name": "mode",
                                "default_from": (None, {"": [{"mode": "cv", "ca": 0.9}]})})


def test_a_looked_up_table_shows_the_rows_registered_now_and_holds_only_what_is_set() -> None:
    """1.14, carried from RCWS's tracker and fit: a list of rows called by name whose rows are
    registered against another setting's value -- or once, against none -- shows each
    registered row, every cell empty with its registered value as the placeholder; a cell set
    here makes the value hold that row with that cell alone; another value of the other
    setting shows its own rows, keeping what was set."""
    form = Form({"name": "bank", "fields": fields_of(_Bank)})
    f = form.by_name["rows"]
    assert form.shown_default(f) == "[]", "a table is no placeholder of its own"
    edits = []
    table = _Table(f, on_edit=edits.append, registered=lambda: form.registered_rows(f))
    table.value = ""
    labels = [o.object for row in table.view.objects[1:] for o in row.objects[:1]]
    assert ["constant velocity" in a for a in labels] == [True, False] and "ct" in labels[1]
    assert [c.placeholder for c in table._cells] == ["0.1", "0.2"]
    assert all(c.value == "" for c in table._cells)
    assert not table._buttons, "which rows there are is what is registered"
    table._cells[1].value_input = "0.3"
    assert json.loads(edits[-1]) == [{"mode": "ct", "ca": 0.3}]
    form.set["rows"] = edits[-1]
    form.type_or_pick("form", "fast")
    table.refresh()
    assert [c.placeholder for c in table._cells] == ["0.5", ""], \
        "the fast form's one row, then the row set here that it does not register"
    assert table._cells[1].value == "0.3"
    table._cells[1].value_input = "0.4"
    assert json.loads(edits[-1]) == [{"mode": "ct", "ca": 0.4}]
    table._cells[1].value_input = ""
    assert json.loads(edits[-1]) == [], "a cell emptied runs as registered"
    once = form.by_name["once"]
    table = _Table(once, on_edit=edits.append, registered=lambda: form.registered_rows(once))
    assert [c.placeholder for c in table._cells] == ["0.9"]


def test_a_parts_looked_up_setting_follows_its_sibling_in_the_part() -> None:
    """1.14: inside a part, the setting an empty one is looked up off is the part's own."""
    class _Holder(Settings):
        flight = param.ClassSelector(class_=_Flight, default=_Flight(), metadata={"group": "h"})

    form = Form({"name": "holder", "fields": fields_of(_Holder)})
    f = form.by_name["flight.speed"]
    assert f["default_from"]["field"] == "flight.vehicle"
    assert form.shown_default(f) == "250"
    form.type_or_pick("flight.vehicle", "drone")
    assert form.shown_default(f) == "50"


def test_a_rows_choice_worded_by_a_function_is_drawn() -> None:
    """1.14, found driving the other project's flight form: a row's choice whose lines are a
    function (read off a registry) is read at declaration, as ``stands_for`` and ``row_words``
    are; the table drew it as a mapping and the piece's form failed to open."""
    class _Segment(Settings):
        until = param.Selector(default="time", objects=["time", "speed"],
                               metadata={"group": "g",
                                         "lines": lambda: {"time": "time in the segment"}})

    class _Plan(Settings):
        segments = param.List([_Segment()], item_type=_Segment, metadata={"group": "g"})

    f = next(x for x in fields_of(_Plan) if x["name"] == "segments")
    assert f["element_fields"][0]["lines"] == {"time": "time in the segment"}
    table = _Table(f, on_edit=lambda text: None)
    assert "time in the segment" in table._cells[0].options
