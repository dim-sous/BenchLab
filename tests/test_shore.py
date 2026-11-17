"""The shore: what a project may use, and the promise that it stays (``README.md``, "What a
project may use"). Every list here is written by hand, never read off the code: a name the code
drops or renames, or a name the declaration starts to require, fails here; a name added passes.
"""

from __future__ import annotations

from pathlib import Path

import param

import runlab
from runlab import cli, lab, project, record, testing
from runlab.record import config, files

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()
#: The names ``runlab`` holds for a project's pieces, promised from 0.5, each with the inner
#: module that holds it (where a project took it from before 0.5).
NAMES = {"Settings": config, "with_overrides": config, "Record": record, "Series": record,
         "Number": record, "Provenance": record, "stamp": record, "bound_refs": record,
         # from 0.7: a figure a piece draws itself
         "Figure": record}
#: Held from 0.8 and not yet promised: built on the made-up project alone, no project having
#: used them (``docs/plan-branch-R4.md``). They may still change; the README says so.
HELD = {"run_files": files, "files_of": files}
#: The names a project's declared module holds; ``WORDS`` it may leave out (from 0.6).
DECLARED = {"NAMES", "get_component", "COMMAND", "TITLE", "ROOT", "LIBRARIES", "WORDS"}
#: What a setting's ``metadata`` may carry.
METADATA = ("group", "unit", "lines", "needs", "replicate", "draws", "record_of", "folded", "rows")


def test_runlab_holds_every_name_it_promised() -> None:
    missing = [n for n in NAMES if n not in runlab.__all__ or not hasattr(runlab, n)]
    assert not missing, f"runlab no longer holds {missing}"


def test_the_inner_paths_a_project_used_before_0_5_hold_the_same_things() -> None:
    for name, module in NAMES.items():
        assert getattr(module, name) is getattr(runlab, name), name


def test_runlab_holds_nothing_beyond_what_is_promised_or_named_as_not_yet() -> None:
    assert set(runlab.__all__) == {*NAMES, *HELD}
    for name, module in HELD.items():
        assert getattr(module, name) is getattr(runlab, name), name
    shore = README.split("## What a project may use")[1].split("\n## ")[0]
    assert "not yet promised" in shore and all(f"`{name}(" in shore for name in HELD)


def test_the_declaration_requires_no_name_beyond_those_promised() -> None:
    assert project.GROUP == "runlab"
    assert set(project.DECLARED) <= DECLARED, \
        f"a project must now also declare {sorted(set(project.DECLARED) - DECLARED)}"


def test_a_project_need_not_name_a_words_file() -> None:
    assert "WORDS" not in project.DECLARED


def test_the_two_commands_and_the_check_are_where_a_project_names_them() -> None:
    assert callable(cli.main) and callable(lab.main) and callable(testing.check_project)


def test_a_setting_keeps_every_metadata_key_it_may_carry() -> None:
    rows = {"label": "x{}'", "add": "+ State"}

    class Every(runlab.Settings):
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
    promised = [*NAMES, *DECLARED, *METADATA, "Config", "run", "figures()", "runlab.cli:main",
                "runlab.lab:main", "runlab.testing", "check_project"]
    missing = [word for word in promised if f"`{word}`" not in shore]
    assert not missing, f"the README's list leaves out {missing}"
