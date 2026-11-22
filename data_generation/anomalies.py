"""Injection des anomalies dans les transactions, avec leur étiquette.

Deux grandes familles, pour pouvoir comparer honnêtement règles et IA :

- les ERREURS CLASSIQUES violent une règle écrite dans le contrat : une règle
  simple doit les attraper toutes ;
- les ANOMALIES SUBTILES respectent toutes les règles du contrat : seule une
  méthode qui compare une ligne à son contexte (l'historique du client, la
  catégorie, le canal) peut les repérer.

Chaque ligne touchée reçoit une étiquette (famille, difficulté, description).
Les étiquettes sont renvoyées à part : elles ne doivent jamais se retrouver dans
les données publiées.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from . import config as C

CLASSIQUE, SUBTILE = "erreur_classique", "anomalie_subtile"


def _pick(candidates: pd.Index, rate: float, n_sales: int, rng) -> pd.Index:
    k = min(len(candidates), int(round(rate * n_sales)))
    return pd.Index(rng.choice(candidates, size=k, replace=False)) if k else pd.Index([])


def inject(tx: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renvoie (transactions modifiées, étiquettes indexées par la clé interne _row)."""
    tx = tx.copy()
    tx["_row"] = np.arange(len(tx))
    labels: list[dict] = []
    touched: set[int] = set()
    r = C.ANOMALY_RATES
    n_sales = int((tx["type_transaction"] == "vente").sum())

    def free_sales() -> pd.Index:
        ok = (tx["type_transaction"] == "vente") & ~tx["_row"].isin(touched) & ~tx["_derive_prix"]
        return tx.index[ok]

    def label(idx, famille, difficulte, description):
        for i in idx:
            touched.add(int(tx.at[i, "_row"]))
            labels.append({"_row": int(tx.at[i, "_row"]), "statut": difficulte,
                           "famille": famille, "description": description(i)})

    # ---------------- Erreurs classiques ----------------
    idx = _pick(free_sales(), r.montant_nul_ou_negatif, n_sales, rng)
    before = tx.loc[idx, "montant"].copy()
    zero = rng.random(len(idx)) < 0.5
    tx.loc[idx[zero], "montant"] = 0.0
    tx.loc[idx[~zero], "montant"] = -tx.loc[idx[~zero], "montant"]
    label(idx, "montant_nul_ou_negatif", CLASSIQUE,
          lambda i: f"vente à {tx.at[i, 'montant']} au lieu de {before[i]}")

    idx = _pick(free_sales(), r.devise_incoherente, n_sales, rng)
    for i in idx:
        old = tx.at[i, "devise"]
        tx.at[i, "devise"] = "EUR" if tx.at[i, "pays"] == "CH" else rng.choice(["CHF", "USD"])
        labels_desc = f"devise {tx.at[i, 'devise']} pour le pays {tx.at[i, 'pays']} (attendu {old})"
        label([i], "devise_incoherente", CLASSIQUE, lambda _i, d=labels_desc: d)

    idx = _pick(free_sales(), r.valeur_hors_referentiel, n_sales, rng)
    variants = [("categorie", ["electronique", "Électroniques", "Jouets", "MODE"]),
                ("canal", ["Téléphone", "web", "Marketplace"]),
                ("pays", ["FRA", "IT", "fr"])]
    for i in idx:
        col, values = variants[rng.integers(len(variants))]
        old = tx.at[i, col]
        tx.at[i, col] = values[rng.integers(len(values))]
        desc = f"{col} « {tx.at[i, col]} » hors référentiel (attendu {old})"
        label([i], "valeur_hors_referentiel", CLASSIQUE, lambda _i, d=desc: d)

    idx = _pick(free_sales(), r.valeur_manquante, n_sales, rng)
    for i in idx:
        col = "montant" if rng.random() < 0.6 else "client_id"
        tx.at[i, col] = np.nan if col == "montant" else None
        label([i], "valeur_manquante", CLASSIQUE, lambda _i, c=col: f"{c} manquant")

    # Doublon exact : SEULE LA COPIE est une anomalie, l'original est légitime.
    idx = _pick(free_sales(), r.doublon_exact, n_sales, rng)
    touched.update(int(x) for x in tx.loc[idx, "_row"])   # l'original ne doit plus bouger
    copies = tx.loc[idx].copy()
    copies["_row"] = np.arange(len(tx), len(tx) + len(copies))
    tx = pd.concat([tx, copies], ignore_index=True)
    for src_row, new_i in zip(tx.loc[idx, "_row"], tx.index[-len(copies):] if len(copies) else []):
        label([new_i], "doublon_exact", CLASSIQUE,
              lambda _i, s=src_row: f"copie exacte de la ligne interne {s}")

    # ---------------- Anomalies subtiles ----------------
    # Pic client : dix fois le panier habituel DU CLIENT, mais un montant qui
    # reste banal pour la catégorie (sous son 99e centile) : aucun seuil global
    # ne le voit, seule la comparaison avec l'historique du client le révèle.
    sales_ok = tx[(tx["type_transaction"] == "vente") & tx["montant"].gt(0)]
    p99 = sales_ok.groupby("categorie")["montant"].quantile(0.99)
    client_median = sales_ok.groupby("client_id")["montant"].median()
    client_count = sales_ok.groupby("client_id").size()
    regulars = client_count[client_count >= 6].index
    cand = free_sales()
    cand = cand[tx.loc[cand, "client_id"].isin(regulars)
                & (tx.loc[cand, "segment"] == "Particulier")]
    new_amount = tx.loc[cand, "client_id"].map(client_median) * 10
    cand = cand[new_amount.to_numpy() < tx.loc[cand, "categorie"].map(p99).to_numpy()]
    idx = _pick(cand, r.pic_client, n_sales, rng)
    for i in idx:
        old = tx.at[i, "montant"]
        tx.at[i, "montant"] = round(client_median[tx.at[i, "client_id"]] * 10, 2)
        desc = (f"montant {tx.at[i, 'montant']} = 10 x la médiane du client "
                f"(au lieu de {old}), sous le 99e centile de la catégorie")
        label([i], "pic_client", SUBTILE, lambda _i, d=desc: d)

    # Prix unitaire aberrant : erreur de saisie de quantité. Le total ne change
    # pas, mais le prix par article devient absurdement bas.
    cand = free_sales()
    cand = cand[(tx.loc[cand, "quantite"] == 1) & (tx.loc[cand, "segment"] != "Professionnel")]
    idx = _pick(cand, r.prix_unitaire_aberrant, n_sales, rng)
    for i in idx:
        tx.at[i, "quantite"] = int(rng.integers(8, 21))
        desc = f"quantité {tx.at[i, 'quantite']} pour un montant d'un seul article"
        label([i], "prix_unitaire_aberrant", SUBTILE, lambda _i, d=desc: d)

    # Magasin hors horaires : une vente « en magasin » à 3 h du matin. Le
    # contrat ne parle pas des horaires d'ouverture : aucune règle ne le voit.
    cand = free_sales()
    idx = _pick(cand, r.magasin_hors_horaires, n_sales, rng)
    for i in idx:
        ts = tx.at[i, "date_transaction"]
        tx.at[i, "canal"] = "Magasin"
        tx.at[i, "date_transaction"] = ts.replace(hour=int(rng.integers(1, 6)))
        desc = f"vente en magasin à {tx.at[i, 'date_transaction']:%H:%M}"
        label([i], "magasin_hors_horaires", SUBTILE, lambda _i, d=desc: d)

    # Doublon approché : la même vente renvoyée quelques minutes plus tard,
    # avec un arrondi différent. Le contrôle de doublon exact la laisse passer.
    idx = _pick(free_sales(), r.doublon_approche, n_sales, rng)
    touched.update(int(x) for x in tx.loc[idx, "_row"])
    copies = tx.loc[idx].copy()
    copies["date_transaction"] = [t + timedelta(minutes=int(rng.integers(1, 21)))
                                  for t in copies["date_transaction"]]
    copies["montant"] = (copies["montant"] + rng.choice([-1, 1], len(copies))
                         * rng.uniform(0.01, 1.0, len(copies))).round(2)
    copies["_row"] = np.arange(len(tx), len(tx) + len(copies))
    src_rows = tx.loc[idx, "_row"].to_list()
    tx = pd.concat([tx, copies], ignore_index=True)
    for src_row, new_i in zip(src_rows, tx.index[-len(copies):] if len(copies) else []):
        label([new_i], "doublon_approche", SUBTILE,
              lambda _i, s=src_row: f"quasi-copie de la ligne interne {s}")

    return tx, pd.DataFrame(labels)
