"""The shore: what a project may use, and the promise that it stays (``README.md``, "What a
project may use"). Every list here is written by hand, never read off the code: a name the code
drops or renames, or a name the declaration starts to require, fails here; a name added passes.
"""

from __future__ import annotations

from pathlib import Path

import param

import benchlab
from benchlab import cli, lab, project, record, testing
from benchlab.record import config

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()
#: The names ``benchlab`` holds for a project's pieces, promised from 0.5, each with the inner
#: module a project took it from before 0.5.
NAMES = {"Settings": config, "with_overrides": config, "Record": record, "Series": record,
         "Number": record, "Provenance": record, "stamp": record, "bound_refs": record}
#: The names a project's declared module holds.
DECLARED = {"NAMES", "get_component", "COMMAND", "TITLE", "ROOT", "LIBRARIES", "WORDS"}
#: What a setting's ``metadata`` may carry.
METADATA = ("group", "unit", "lines", "needs", "replicate", "draws", "record_of", "folded", "rows")


def test_benchlab_holds_every_name_it_promised() -> None:
    missing = [n for n in NAMES if n not in benchlab.__all__ or not hasattr(benchlab, n)]
    assert not missing, f"benchlab no longer holds {missing}"


def test_the_inner_paths_a_project_used_before_0_5_hold_the_same_things() -> None:
    for name, module in NAMES.items():
        assert getattr(module, name) is getattr(benchlab, name), name


def test_the_declaration_requires_no_name_beyond_those_promised() -> None:
    assert project.GROUP == "benchlab"
    assert set(project.DECLARED) <= DECLARED, \
        f"a project must now also declare {sorted(set(project.DECLARED) - DECLARED)}"


def test_the_two_commands_and_the_check_are_where_a_project_names_them() -> None:
    assert callable(cli.main) and callable(lab.main) and callable(testing.check_project)


def test_a_setting_keeps_every_metadata_key_it_may_carry() -> None:
    rows = {"label": "x{}'", "add": "+ State"}

    class Every(benchlab.Settings):
        mode = param.Selector(default="a", objects=["a", "b"],
                              metadata={"group": "G", "lines": {"a": "one", "b": "two"}})
        gain = param.Number(1.0, metadata={"group": "G", "unit": "V", "folded": True,
                                           "needs": {"mode": {"in": ["b"]}}})
        seed = param.Integer(0, metadata={"group": "G", "replicate": True, "draws": "count"})
        count = param.Integer(1, metadata={"group": "G"})
        source = param.String("", metadata={"group": "G", "record_of": "wave"})
        terms = param.List(default=["x"], item_type=str, metadata={"group": "G", "rows": rows})

    by = {f["name"]: f for f in config.fields_of(Every)}
    assert by["mode"]["lines"] == {"a": "one", "b": "two"}
    assert (by["gain"]["group"], by["gain"]["unit"], by["gain"]["folded"]) == ("G", "V", True)
    assert by["gain"]["needs"] == {"mode": {"in": ["b"]}}
    assert (by["seed"]["replicate"], by["seed"]["draws"]) == (True, "count")
    assert by["source"]["record_of"] == "wave" and by["terms"]["rows"] == rows
    assert all(key in by["gain"] for key in METADATA)


def test_the_readme_names_everything_promised() -> None:
    shore = README.split("## What a project may use")[1].split("\n## ")[0]
    promised = [*NAMES, *DECLARED, *METADATA, "Config", "run", "benchlab.cli:main",
                "benchlab.lab:main", "benchlab.testing", "check_project"]
    missing = [word for word in promised if f"`{word}`" not in shore]
    assert not missing, f"the README's list leaves out {missing}"
