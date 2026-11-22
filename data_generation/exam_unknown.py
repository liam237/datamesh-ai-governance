"""Famille inconnue du jeu d'EXAMEN (graine 2027) : un rejeu de lot.

Écrite le 22 novembre 2026, APRÈS le gel des variables du mécanisme 1
(commit 440fe26), pour que les variables n'aient pas pu être conçues pour elle.

L'incident simulé est un incident de pipeline, pas une fraude : le fichier
quotidien d'un système source (un pays × un canal) est renvoyé une seconde
fois le lendemain, et la date d'intégration remplace la date de vente. Toutes
les ventes du lot réapparaissent donc avec de nouveaux identifiants, à la même
heure, exactement 24 heures plus tard. Chaque ligne prise seule est banale ; le
contrat ne les voit pas comme des doublons, puisque leur date diffère.
"""

import numpy as np
import pandas as pd

from . import config as C
from .anomalies import INCONNUE

FAMILY = "rejeu_lot"
N_INCIDENTS = 3
COUNTRIES = ["FR", "BE"]


def inject_replay(tx: pd.DataFrame, labels: pd.DataFrame, rng: np.random.Generator
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    tx = tx.copy()
    sales = tx[(tx["type_transaction"] == "vente") & (tx["montant"] > 0)
               & tx["pays"].isin(COUNTRIES)]
    day = sales["date_transaction"].dt.normalize()
    last_day = pd.Timestamp(C.END).normalize()
    batches = sales[day < last_day].groupby([day, "pays", "canal"]).groups
    keys = list(batches)
    chosen = [keys[i] for i in rng.choice(len(keys), size=N_INCIDENTS, replace=False)]
    rows, new_labels = [], []
    next_row = int(tx["_row"].max()) + 1
    for (d, country, channel) in chosen:
        batch = tx.loc[batches[(d, country, channel)]]
        for _, r in batch.iterrows():
            copy = r.to_dict()
            copy["date_transaction"] = r["date_transaction"] + pd.Timedelta(days=1)
            copy["_row"], copy["_vente_origine"] = next_row, pd.NA
            rows.append(copy)
            new_labels.append({"_row": next_row, "statut": INCONNUE, "famille": FAMILY,
                               "description": f"rejeu du lot {country} / {channel} du {d.date()} "
                                              f"le lendemain"})
            next_row += 1
    tx = pd.concat([tx, pd.DataFrame(rows)], ignore_index=True)
    return tx, pd.concat([labels, pd.DataFrame(new_labels)], ignore_index=True)
