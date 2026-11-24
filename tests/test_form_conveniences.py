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
