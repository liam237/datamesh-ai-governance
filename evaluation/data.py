"""Chargement des données publiées et de la vérité terrain, pour l'évaluation.

Seul le dossier evaluation/ a le droit d'appeler `load_truth`.
"""

from pathlib import Path

import pandas as pd

from data_generation import config as C

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {"conception": C.PATHS.root, "test": C.PATHS.test_root, "examen": C.PATHS.exam_root}
SEEDS = {"conception": C.SEED, "test": C.TEST_SEED, "examen": C.EXAM_SEED}
SUMMARIES = {"conception": "", "test": "_test", "examen": "_exam"}


def ensure(dataset: str) -> Path:
    """Renvoie le dossier du jeu demandé, en le générant s'il n'existe pas encore."""
    root = ROOT / DATASETS[dataset]
    if not (root / "ventes" / "transactions.csv").exists():
        from data_generation.generate import build, write
        write(build(test=dataset == "test", exam=dataset == "examen"), root=str(root),
              summary_path=str(ROOT / "results/metrics" / f"generation_summary{SUMMARIES[dataset]}.json"),
              seed=SEEDS[dataset])
    return root


def load_published(dataset: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = ensure(dataset)
    tx = pd.read_csv(root / "ventes" / "transactions.csv", parse_dates=["date_transaction"])
    clients = pd.read_csv(root / "service_client" / "clients_interne.csv")
    return tx, clients


def load_truth(dataset: str) -> pd.DataFrame:
    return pd.read_csv(ensure(dataset) / "ground_truth" / "transactions.csv").set_index("transaction_id")
