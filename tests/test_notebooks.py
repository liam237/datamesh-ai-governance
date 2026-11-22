"""Chaque notebook doit s'exécuter de haut en bas, sans erreur.

On l'exécute sur une copie, pour ne pas modifier le notebook versionné.
"""

import shutil
from pathlib import Path

import pytest

from pipeline.run_notebooks import ROOT, run

NOTEBOOKS = sorted((ROOT / "notebooks").glob("[0-9][0-9]_*.ipynb"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_s_execute_sans_erreur(path, tmp_path):
    copy = path.parent / f"_test_{path.name}"
    shutil.copy(path, copy)
    try:
        run(copy, output=tmp_path / path.name)
    finally:
        copy.unlink(missing_ok=True)


def test_le_notebook_d_exploration_ne_lit_pas_la_verite_terrain():
    text = (ROOT / "notebooks" / "01_exploration.ipynb").read_text(encoding="utf-8")
    assert "ground_truth" not in text.replace("`data/ground_truth/`", "")
