"""Réexécute les notebooks du dossier notebooks/ et enregistre leurs résultats.

Usage : `make notebooks`, ou `python -m pipeline.run_notebooks`.
Chaque notebook est exécuté de haut en bas dans un noyau neuf : si une cellule
échoue, la commande s'arrête avec une erreur. Les figures sont régénérées dans
results/figures/.
"""

import sys
import warnings
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def run(path: Path, output: Path | None = None) -> None:
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=600, kernel_name="python3",
                   resources={"metadata": {"path": str(path.parent)}}).execute()
    nbformat.write(nb, output or path)


def main() -> int:
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    for path in sorted((ROOT / "notebooks").glob("[0-9][0-9]_*.ipynb")):
        print(f"[exécution] {path.name}", flush=True)
        run(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
