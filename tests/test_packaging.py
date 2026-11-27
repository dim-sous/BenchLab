"""The package as a project installs it. RunLab's own words (``runlab/lab/words.toml``) and the
page's fonts (``runlab/lab/fonts/``) are its files that are not Python, and such a file is left
out of a built package unless ``pyproject.toml`` names it (``[tool.setuptools.package-data]``).
Run from the source folder, the rest of this suite finds them whether or not an installed copy
would; no project's Lab would start without the words, nor show its fonts with no internet
without the fonts.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_built_package_holds_runlabs_own_words_and_fonts_and_no_test(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy(ROOT / name, source / name)
    shutil.copytree(ROOT / "runlab", source / "runlab",
                    ignore=shutil.ignore_patterns("__pycache__"))
    built = subprocess.run(["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist"),
                            str(source)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    [wheel] = (tmp_path / "dist").glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert "runlab/lab/words.toml" in names
    assert "runlab/py.typed" in names, "a project's type checker reads RunLab's hints (PEP 561)"
    [metadata] = [n for n in names if n.endswith(".dist-info/METADATA")]
    assert "License-Expression: MIT" in zipfile.ZipFile(wheel).read(metadata).decode()
    fonts = {f"runlab/lab/fonts/{p.name}" for p in (ROOT / "runlab/lab/fonts").iterdir()}
    assert len(fonts) == 6 and fonts <= set(names), "five fonts and their licence"
    assert {n.split("/")[0] for n in names if "/" in n and ".dist-info/" not in n} == {"runlab"}, \
        "one package: the old name's stand-in left at 1.0"
    assert wheel.name.startswith("runlab-"), "installed as runlab from 1.0"
    assert not [n for n in names if n.startswith("tests/")]
