"""The package as a project installs it. Benchlab's own words (``benchlab/lab/words.toml``) are
its one file that is not Python, and such a file is left out of a built package unless
``pyproject.toml`` names it (``[tool.setuptools.package-data]``). Run from the source folder, the
rest of this suite finds the file whether or not an installed copy would; no project's Lab would
start without it.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_built_package_holds_benchlabs_own_words_and_no_test(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy(ROOT / name, source / name)
    shutil.copytree(ROOT / "benchlab", source / "benchlab",
                    ignore=shutil.ignore_patterns("__pycache__"))
    built = subprocess.run(["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist"),
                            str(source)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    [wheel] = (tmp_path / "dist").glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert "benchlab/lab/words.toml" in names
    assert not [n for n in names if n.startswith("tests/")]
