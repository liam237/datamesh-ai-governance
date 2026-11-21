"""Vérifie que la structure du dépôt respecte le cahier des charges."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DIRS = [
    "contracts",
    "data_generation",
    "notebooks",
    "mechanisms/arrival",
    "mechanisms/cleaning",
    "mechanisms/publication",
    "mechanisms/consumption",
    "mechanisms/monitoring",
    "baselines",
    "evaluation",
    "pipeline",
    "results/metrics",
    "results/figures",
    "models",
    "tests",
    "docs",
]


@pytest.mark.parametrize("folder", EXPECTED_DIRS)
def test_dossier_present(folder):
    assert (ROOT / folder).is_dir(), f"Dossier manquant : {folder}"


def test_un_seul_dossier_models():
    # Défaut de la v2 : « Models » et « models » coexistaient.
    names = [p.name for p in ROOT.iterdir() if p.is_dir()]
    assert names.count("models") == 1
    assert "Models" not in names


def test_secrets_hors_du_depot():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore.splitlines()
    assert (ROOT / ".env.example").is_file()


def test_commande_unique_executable():
    from pipeline.run_all import main

    assert main() == 0
