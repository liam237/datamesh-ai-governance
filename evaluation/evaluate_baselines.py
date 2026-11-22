"""Évalue les deux références simples sur les deux jeux de données.

Usage : `python -m evaluation.evaluate_baselines` (appelé aussi par `make all`).
Écrit results/metrics/baselines.json et results/metrics/baselines.md.
"""

import json

import pandas as pd

from baselines.rules import run
from evaluation.data import ROOT, load_published, load_truth
from evaluation.metrics import false_alerts_by_status, recall_by_family, scores

BASELINES = ["contrat", "expert"]
DATASETS = ["conception", "test"]
OUT = ROOT / "results" / "metrics"


def evaluate() -> dict:
    results = {}
    for dataset in DATASETS:
        tx, clients = load_published(dataset)
        truth = load_truth(dataset)
        for name in BASELINES:
            flags = run(name, tx, clients)
            t = truth.loc[flags.index]
            alert = flags["quarantaine"]
            results[f"{dataset}/{name}"] = {
                "jeu": dataset, "reference": name,
                **scores(t["est_anomalie"], alert),
                "rappel_par_famille": recall_by_family(t["famille"], t["est_anomalie"], alert),
                "fausses_alertes_par_statut": false_alerts_by_status(t["statut"], t["est_anomalie"], alert),
                "alertes_par_regle": {k: int(v) for k, v in
                                      flags.drop(columns=["quarantaine", "motifs"]).sum().items() if v},
            }
    return results


def to_markdown(results: dict) -> str:
    lines = ["# Références simples : résultats", "",
             "Généré par `python -m evaluation.evaluate_baselines`. Ne pas modifier à la main.", "",
             "## Scores globaux", "",
             "| Jeu | Référence | Alertes | Vraies anomalies trouvées | Fausses alertes | Anomalies manquées | Précision | Rappel | F1 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results.values():
        lines.append(f"| {r['jeu']} | {r['reference']} | {r['alertes']} | {r['VP']} | {r['FP']} | {r['FN']} | "
                     f"{r['precision']:.3f} | {r['rappel']:.3f} | {r['F1']:.3f} |")
    families = sorted({f for r in results.values() for f in r["rappel_par_famille"]})
    cols = list(results)
    lines += ["", "## Rappel par famille d'anomalies", "",
              "| Famille | " + " | ".join(c.replace("/", " · ") for c in cols) + " |",
              "|---|" + "---|" * len(cols)]
    for fam in families:
        cells = [f"{results[c]['rappel_par_famille'][fam]:.2f}" if fam in results[c]["rappel_par_famille"] else "—"
                 for c in cols]
        lines.append(f"| {fam} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    results = evaluate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "baselines.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(results)
    (OUT / "baselines.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
