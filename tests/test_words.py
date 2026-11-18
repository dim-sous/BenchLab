"""The page's words: RunLab names every slot and holds a word for each
(``runlab/lab/words.toml``); a project's words file lists only the words it changes. Nothing in
that file stops the Lab: an entry RunLab cannot use is left out, the page keeps RunLab's own
word, and the Lab says so in its terminal. Read off the Lab's own sources: every slot named is
said, and every slot said is named."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from runlab import project
from runlab.lab import cli, words
from runlab.lab.app import Lab
from tests import toy

LAB = Path(__file__).resolve().parent.parent / "runlab" / "lab"


@pytest.fixture
def words_file(tmp_path, monkeypatch):
    """The toy, which names no words file, naming one the test writes: ``write(text)`` returns
    its path. The words read once are forgotten before and after, so no test sees another's."""
    path = tmp_path / "words.toml"

    def write(text: str) -> Path:
        path.write_text(text, encoding="utf-8")
        return path

    monkeypatch.setattr(toy, "WORDS", path, raising=False)
    words.words.cache_clear()
    yield write
    words.words.cache_clear()


def test_runlabs_own_words_fill_every_slot_and_no_other() -> None:
    own = words.load()
    assert list(own) == list(words.SLOTS) and all(isinstance(w, str) and w for w in own.values())


def test_runlabs_own_file_leaving_a_slot_empty_is_refused(tmp_path, monkeypatch) -> None:
    short = tmp_path / "words.toml"
    short.write_text(words.OWN.read_text(encoding="utf-8").replace('refresh = "Refresh"\n', ""),
                     encoding="utf-8")
    monkeypatch.setattr(words, "OWN", short)
    with pytest.raises(ValueError, match=r"leaves 1 slot.s. empty: header.refresh"):
        words.load()


def test_a_project_that_names_no_words_file_keeps_runlabs_own() -> None:
    words.words.cache_clear()
    assert project.words_path() is None and words.words() == words.load()


def test_a_projects_file_changes_the_words_it_lists_and_no_other(words_file) -> None:
    words_file('[header]\nrefresh = "Reload"\n\n[strip]\ncap = "at most {n} at once"\n')
    own, got = words.load(), words.words()
    assert got["header.refresh"] == "Reload" and words.say("strip.cap", n=3) == "at most 3 at once"
    assert list(got) == list(words.SLOTS)
    assert {slot for slot in got if got[slot] != own[slot]} == {"header.refresh", "strip.cap"}


@pytest.mark.parametrize("text, slot, why", [
    ('[extra]\nnew = "New"\n', "extra.new", "extra.new (RunLab names no such slot)"),
    ('[strip]\ncap = "up to {count} side by side"\n', "strip.cap",
     "strip.cap (it writes {count}, which the slot does not offer (it offers: n))"),
    ('[runs]\nheading = "Runs {"\n', "runs.heading", "runs.heading (it holds a brace that is no field"),
    ('[header]\nrefresh = 3\n', "header.refresh", "header.refresh (it is not text)"),
])
def test_an_entry_runlab_cannot_use_is_left_out_and_said(words_file, text, slot, why) -> None:
    path = words_file(text + '\n[form]\nrun = "Go"\n')
    own, got = words.load(), words.words()
    assert list(got) == list(words.SLOTS) and got.get(slot) == own.get(slot), "its own word kept"
    assert got["form.run"] == "Go", "the entry beside it, which RunLab can use, is used"
    said = words.left_out()
    assert said.startswith(f"the words file {path}: left out") and why in said
    assert "form.run" not in said


@pytest.mark.parametrize("text", ['[header\nrefresh = "Reload"\n', None])
def test_a_words_file_that_cannot_be_read_is_left_out_whole_and_said(words_file, text) -> None:
    path = words_file("")
    if text is None:
        path.unlink()                                   # the project names a file that is not there
    else:
        path.write_text(text, encoding="utf-8")         # not TOML: a bracket left open
    assert words.words() == words.load()
    assert words.left_out().startswith(f"the words file {path}: left out") \
        and ": the file (" in words.left_out()


def test_a_words_file_runlab_can_use_whole_says_nothing(words_file) -> None:
    words_file('[header]\nrefresh = "Reload"\n')
    assert words.left_out() == ""


def test_the_lab_starts_on_a_words_file_it_cannot_use_and_says_what_it_left_out(
        words_file, monkeypatch, capsys) -> None:
    """The developer, 2026-11-15: "If a word is missing or wrong i will see it in the lab and make
    the change." The Lab serves; its terminal names the entry left out."""
    words_file('[strip]\ntoggel = "Runs under way"\n')        # a slip of the hand for `toggle`
    served = []
    monkeypatch.setattr(cli, "serve", lambda *a, **k: served.append(a))
    monkeypatch.setattr(cli, "stop_runs_on_sigterm", lambda: None)
    assert cli.main(["--no-open", "--port", "0"]) == 0 and len(served) == 1
    out = capsys.readouterr().out
    assert "lab: the words file" in out and "strip.toggel (RunLab names no such slot)" in out


def test_a_word_a_project_changes_is_the_word_on_the_page(words_file, two_runs) -> None:
    words_file('[header]\nrefresh = "Reload"\n')
    root, out_dir = two_runs
    lab = Lab(root, out_dir, every=lambda cb, ms: None, toast=lambda _w: None)
    lab.page()
    assert lab.refresh.label == "Reload" and lab.new_run_btn.label == words.load()["header.new_run"]


def test_a_cards_controls_wear_the_projects_words(words_file, two_runs) -> None:
    """The row of a card is words like any other: its names, its options, the reason a control
    is greyed (the plan of 2026-11-18, departure 4)."""
    words_file('[cards]\ndots = "Points"\ny_log = "Log ordinate"\none_run = "A single run"\n')
    root, out_dir = two_runs
    lab = Lab(root, out_dir, every=lambda cb, ms: None, toast=lambda _w: None)
    lab.page()
    row = [o for card in lab.cards_box.objects for tools in card.objects[1:2]
           for group in tools.objects for o in group.objects]
    assert "Points" in [o.name for o in row if hasattr(o, "value")]
    said = " ".join(o.object for o in row if not hasattr(o, "value"))
    assert "Log ordinate" in said and 'title="A single run"' in said
    assert "Dots" not in [o.name for o in row if hasattr(o, "value")]


def test_a_count_says_its_one_or_its_many() -> None:
    assert words.say_n("compare.alone", 1) == "1 number; tick another run to compare"
    assert words.say_n("compare.alone", 2) == "2 numbers; tick another run to compare"
    assert words.say_n("compare.alone", 0) == "0 numbers; tick another run to compare"


def _said() -> tuple[set[str], set[str], list[str]]:
    """Off the Lab's sources: every text the code holds; the stems of slots it says by a count
    (``say_n``); and the prefixes it builds slot names from (``f"strip.state.{state}"``)."""
    texts, counted, prefixes = set(), set(), []
    for path in sorted(LAB.glob("*.py")):
        if path.name == "words.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                texts.add(node.value)
            elif isinstance(node, ast.JoinedStr) and node.values \
                    and isinstance(node.values[0], ast.Constant):
                prefixes.append(node.values[0].value)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "say_n" \
                    and node.args and isinstance(node.args[0], ast.Constant):
                counted.add(node.args[0].value)
    return texts, counted, prefixes


def test_every_slot_named_is_said_and_every_slot_said_is_named() -> None:
    texts, counted, prefixes = _said()
    stems = {slot.rsplit(".", 1)[0] for slot in words.SLOTS if slot.endswith((".one", ".many"))}
    unsaid = [slot for slot in words.SLOTS
              if slot not in texts and slot.rsplit(".", 1)[0] not in counted
              and not any(p.endswith(".") and slot.startswith(p) for p in prefixes)]
    assert unsaid == [], "named, never said: a slot no page shows"
    slotlike = {t for t in texts if t.count(".") and t.split(".")[0] in
                {s.split(".")[0] for s in words.SLOTS} and " " not in t and "/" not in t
                and not t.endswith(".")}                   # a prefix a slot is built from
    unnamed = sorted(t for t in slotlike if t not in words.SLOTS and t not in stems)
    assert unnamed == [], "said, never named: a slot no words file can fill"
    assert counted <= stems, sorted(counted - stems)
