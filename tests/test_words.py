"""The page's words as slots (``docs/design.md`` decision 4): Benchlab names every slot and holds no
word; the toy's words file fills every one, and a file that does not is refused, naming each; the
Lab will not start on it. Read off the Lab's own sources: every slot named is said, and every slot
said is named."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from benchlab.lab import cli, words
from tests import toy

LAB = Path(__file__).resolve().parent.parent / "benchlab" / "lab"
TOY_WORDS = Path(toy.__file__).with_name("words.toml")


@pytest.fixture
def words_file(tmp_path, monkeypatch):
    """The toy declaring a words file the test writes: ``write(text)`` returns its path. The
    words read once are forgotten before and after, so no test sees another's."""
    path = tmp_path / "words.toml"

    def write(text: str) -> Path:
        path.write_text(text, encoding="utf-8")
        return path

    monkeypatch.setattr(toy, "WORDS", path)
    words.words.cache_clear()
    yield write
    words.words.cache_clear()


def _toy_text() -> str:
    return TOY_WORDS.read_text(encoding="utf-8")


def test_the_toys_words_fill_every_slot() -> None:
    assert set(words.load(TOY_WORDS)) == set(words.SLOTS)


@pytest.mark.parametrize("edit, refusal", [
    (lambda t: t.replace('refresh = "Refresh"\n', ""), "leaves 1 slot(s) empty: header.refresh"),
    (lambda t: t + '\n[extra]\nnew = "New"\n', "fills slot(s) Benchlab does not name: extra.new"),
    (lambda t: t.replace('cap = "up to {n} side by side"', 'cap = "up to {count} side by side"'),
     "strip.cap writes {count}, which it does not offer (it offers: n)"),
    (lambda t: t.replace('heading = "Runs"', 'heading = "Runs {"'), "runs.heading holds a brace"),
    (lambda t: t.replace('refresh = "Refresh"', "refresh = 3"), "header.refresh is not text"),
])
def test_a_words_file_that_does_not_fill_the_slots_is_refused_naming_each(words_file, edit,
                                                                          refusal) -> None:
    path = words_file(edit(_toy_text()))
    with pytest.raises(ValueError, match="the words file") as caught:
        words.load(path)
    assert refusal in str(caught.value)


def test_the_lab_does_not_start_on_a_words_file_that_leaves_a_slot_empty(words_file) -> None:
    words_file(_toy_text().replace('toggle = "Runs in progress"\n', ""))
    with pytest.raises(SystemExit, match="leaves 1 slot.s. empty: strip.toggle"):
        cli.main(["--no-open", "--port", "0"])


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
