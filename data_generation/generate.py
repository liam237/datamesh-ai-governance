"""Point d'entrée du générateur : `python -m data_generation.generate`.

Produit deux familles de fichiers, rangés séparément :

- data/ventes/ et data/service_client/ : ce que les domaines PUBLIENT, c'est-à-dire
  ce que les mécanismes ont le droit de lire ;
- data/ground_truth/ : la VÉRITÉ TERRAIN (quelle ligne est anormale, quels
  clients sont en double, quels commentaires contiennent des données
  personnelles, les habitudes cachées des clients). Seul evaluation/ la lit.

Une même graine produit exactement les mêmes fichiers à chaque lancement.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .anomalies import CLASSIQUE, SUBTILE, inject
from .customer_service import (add_client_duplicates, generate_tickets, homonym_pairs,
                               reassign_to_duplicates)
from .sales import generate_sales
from .world import daily_calendar, generate_clients

TRANSACTION_COLUMNS = ["transaction_id", "date_transaction", "client_id", "type_transaction",
                       "categorie", "montant", "quantite", "pays", "devise", "segment", "canal"]
CLIENT_COLUMNS = ["client_id", "prenom", "nom", "email", "telephone", "ville", "pays",
                  "segment", "date_creation"]
HABIT_COLUMNS = ["client_id", "canal_prefere", "activite_annuelle", "multiplicateur_panier"]


def build(seed: int = C.SEED) -> dict[str, pd.DataFrame]:
    """Construit le monde simulé en mémoire et renvoie toutes les tables."""
    rng = np.random.default_rng(seed)

    clients = generate_clients(rng)
    tx = generate_sales(clients, daily_calendar(), rng)
    clients, duplicates = add_client_duplicates(clients, rng)
    tx = reassign_to_duplicates(tx, duplicates, rng)
    tx, labels = inject(tx, rng)

    # Identifiants définitifs, dans l'ordre chronologique.
    tx = tx.sort_values(["date_transaction", "_row"], kind="stable").reset_index(drop=True)
    tx["transaction_id"] = [f"TXN-{i + 1:08d}" for i in range(len(tx))]
    tickets, tickets_truth = generate_tickets(tx, clients, rng)

    truth = _transaction_truth(tx, labels)
    habit_cols = HABIT_COLUMNS + [c for c in clients.columns if c.startswith("pref_")]
    return {
        "ventes/transactions": tx[TRANSACTION_COLUMNS],
        "service_client/clients_interne": clients[CLIENT_COLUMNS],
        "service_client/tickets": tickets,
        "ground_truth/transactions": truth,
        "ground_truth/clients_doublons": duplicates,
        "ground_truth/clients_homonymes": homonym_pairs(clients, duplicates),
        "ground_truth/tickets_pii": tickets_truth,
        "ground_truth/clients_habitudes": clients[habit_cols].dropna(subset=["activite_annuelle"]),
    }


def _transaction_truth(tx: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    truth = tx[["transaction_id", "_row", "type_transaction", "segment", "quantite",
                "_periode", "_derive_prix"]].merge(labels, on="_row", how="left")
    truth["est_anomalie"] = truth["statut"].isin([CLASSIQUE, SUBTILE])

    # Le « normal mais inhabituel » : correct, mais le système ne doit pas s'en
    # alarmer. La période (soldes, Black Friday, Noël) est notée à part, car elle
    # concerne un tiers des ventes : ce n'est pas « inhabituel », c'est saisonnier.
    unusual = np.select(
        [truth["type_transaction"] == "remboursement",
         (truth["segment"] == "Professionnel") & (truth["quantite"] >= 10)],
        ["remboursement", "commande_professionnelle"], default="")
    normal = ~truth["est_anomalie"]
    truth["statut"] = truth["statut"].where(~normal, np.where(unusual != "", "inhabituel_legitime",
                                                              "normal"))
    truth["famille"] = truth["famille"].where(~normal, unusual)
    truth = truth.rename(columns={"_derive_prix": "derive_prix_categorie", "_periode": "periode"})
    return truth[["transaction_id", "statut", "famille", "est_anomalie", "periode",
                  "derive_prix_categorie", "description"]]


def summary(tables: dict[str, pd.DataFrame]) -> dict:
    tx, truth = tables["ventes/transactions"], tables["ground_truth/transactions"]
    pii = tables["ground_truth/tickets_pii"]
    return {
        "graine": C.SEED,
        "periode": f"{C.START} au {C.END}",
        "transactions": int(len(tx)),
        "dont_remboursements": int((tx["type_transaction"] == "remboursement").sum()),
        "clients_fiches": int(len(tables["service_client/clients_interne"])),
        "clients_doublons_injectes": int(len(tables["ground_truth/clients_doublons"])),
        "paires_homonymes": int(len(tables["ground_truth/clients_homonymes"])),
        "tickets": int(len(tables["service_client/tickets"])),
        "tickets_avec_pii": int(pii["contient_pii"].sum()),
        "tickets_avec_piege": int(pii["piege"].sum()),
        "statut_transactions": truth["statut"].value_counts().to_dict(),
        "familles_anomalies": truth.loc[truth["est_anomalie"], "famille"].value_counts().to_dict(),
        "taux_anomalies_pct": round(100 * truth["est_anomalie"].mean(), 2),
        "lignes_touchees_par_la_derive": int(truth["derive_prix_categorie"].sum()),
        "transactions_par_periode": truth["periode"].value_counts().to_dict(),
    }


def write(tables: dict[str, pd.DataFrame], root: str = C.PATHS.root,
          summary_path: str = "results/metrics/generation_summary.json") -> dict:
    for name, df in tables.items():
        path = Path(root) / f"{name}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8")
    info = summary(tables)
    Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_path).write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return info


def main() -> int:
    info = write(build())
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
