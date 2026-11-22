"""Variables (« features ») décrivant chaque vente, pour la détection d'anomalies.

Chaque variable répond à une décision prise pendant l'exploration
(notebooks/01_exploration.ipynb). Toutes sont RELATIVES : elles comparent une
vente à son contexte (sa catégorie, son segment, l'habitude du client, son
canal, l'achat précédent), car l'exploration a montré qu'un même montant peut
être banal dans un contexte et anormal dans un autre.

Toutes sont calculées sans jamais lire la vérité terrain.

Convention : un écart de 0 veut dire « comme d'habitude » ; un écart de +1 veut
dire « dix fois plus que d'habitude » (on travaille en logarithme de base 10) ;
-1 veut dire « dix fois moins ».
"""

import numpy as np
import pandas as pd

EUR_PER_CHF = 1 / 0.94           # taux fixe du monde simulé (data_generation/config.py)
SHRINK_K = 3                     # confiance dans l'habitude d'un client : n / (n + 3)
NO_PREVIOUS_MINUTES = 525_600    # pas d'achat précédent : on fait comme s'il datait d'un an
NO_PREVIOUS_GAP = 1.0            # ... et comme si l'écart de montant valait « dix fois »

FEATURES = {
    "log_montant": "Logarithme du montant en euros (section 4 de l'exploration)",
    "ecart_categorie": "Montant comparé à la médiane de sa catégorie (section 4)",
    "ecart_prix_unitaire": "Prix par article comparé à la médiane de la catégorie (section 6)",
    "ecart_quantite_segment": "Quantité comparée à la médiane du segment (section 6)",
    "ecart_habitude_client": "Montant comparé à l'habitude du client, pondéré par le nombre d'achats (section 8)",
    "rarete_heure_canal": "Rareté de l'heure d'achat pour ce canal (section 7)",
    "log_delai_precedent": "Délai depuis l'achat précédent du client dans la catégorie (section 9)",
    "ecart_montant_precedent": "Écart de montant avec cet achat précédent (section 9)",
    "log_achats_heure_precedente": "Achats du même client dans l'heure précédente, toutes catégories "
                                   "(ajoutée à l'étape 5b, voir le journal de bord)",
}

BURST_WINDOW_MIN = 60            # fenêtre de la variable « rafale » : l'heure précédente


def sales_scope(tx: pd.DataFrame) -> pd.DataFrame:
    """Les lignes concernées : les ventes avec un montant strictement positif.

    Les remboursements ont une distribution à part (section 5 de l'exploration)
    et seront traités séparément ; les ventes à montant vide, nul ou négatif
    violent déjà le contrat et partent en quarantaine sans passer par l'IA.
    """
    return tx[(tx["type_transaction"] == "vente") & (tx["montant"] > 0)].copy()


def _relative_to_group(values: pd.Series, groups: pd.Series) -> pd.Series:
    return values - values.groupby(groups).transform("median")


def _recent_purchases(df: pd.DataFrame, minutes: int) -> np.ndarray:
    """Nombre d'achats du même client dans les `minutes` précédant chaque vente (elle exclue)."""
    out = np.zeros(len(df))
    window = np.timedelta64(minutes, "m")
    pos = pd.DataFrame({"client": df["client_id"].to_numpy(), "t": df["date_transaction"].to_numpy(),
                        "i": np.arange(len(df))}).dropna(subset=["client"])
    for _, g in pos.groupby("client"):
        g = g.sort_values("t", kind="stable")
        t = g["t"].to_numpy()
        out[g["i"].to_numpy()] = np.arange(len(t)) - np.searchsorted(t, t - window, side="left")
    return out


def build_features(tx: pd.DataFrame) -> pd.DataFrame:
    """Renvoie un tableau indexé par transaction_id, une colonne par variable."""
    df = sales_scope(tx)
    eur = df["montant"] * np.where(df["devise"] == "CHF", EUR_PER_CHF, 1.0)
    log_amount = np.log10(eur)
    out = pd.DataFrame(index=df.index)

    out["log_montant"] = log_amount
    out["ecart_categorie"] = _relative_to_group(log_amount, df["categorie"])
    out["ecart_prix_unitaire"] = _relative_to_group(np.log10(eur / df["quantite"]), df["categorie"])
    out["ecart_quantite_segment"] = _relative_to_group(np.log10(df["quantite"]), df["segment"])

    # Habitude du client : écart à la médiane de SES achats, mais pondéré par le
    # nombre d'achats connus. Avec 1 ou 2 achats, l'« habitude » ne veut rien dire,
    # donc l'écart est ramené vers 0 ; avec 20 achats, on lui fait confiance.
    client = df["client_id"].fillna("__inconnu__")
    n = client.map(client.value_counts())
    trust = n / (n + SHRINK_K)
    gap = _relative_to_group(log_amount, client)
    out["ecart_habitude_client"] = np.where(df["client_id"].isna(), 0.0, trust * gap)

    # Rareté de l'heure pour le canal : -log10 de la fréquence observée de cette
    # heure dans ce canal (avec un lissage de Laplace pour les heures jamais vues).
    # Aucune heure d'ouverture n'est écrite en dur : le modèle l'apprend des données.
    hour = df["date_transaction"].dt.hour
    counts = pd.crosstab(df["canal"], hour).reindex(columns=range(24), fill_value=0) + 1
    freq = counts.div(counts.sum(axis=1), axis=0)
    out["rarete_heure_canal"] = -np.log10([freq.at[c, h] for c, h in zip(df["canal"], hour)])

    # Achat précédent du même client dans la même catégorie : délai et écart de montant.
    order = df.sort_values("date_transaction").index
    ordered = df.loc[order]
    key = [ordered["client_id"].fillna("__inconnu__"), ordered["categorie"]]
    delay = ordered["date_transaction"].groupby(key).diff().dt.total_seconds() / 60
    prev_gap = log_amount.loc[order].groupby(key).diff().abs()
    out.loc[order, "log_delai_precedent"] = np.log10(1 + delay.fillna(NO_PREVIOUS_MINUTES))
    out.loc[order, "ecart_montant_precedent"] = prev_gap.fillna(NO_PREVIOUS_GAP)

    # Achats du même client dans l'heure précédente, toutes catégories confondues.
    # Ajoutée à l'étape 5b : sur le jeu 2026, aucune variable ne décrivait plusieurs
    # achats rapprochés dans des catégories différentes. log10(1 + n) : 0 = aucun.
    out["log_achats_heure_precedente"] = np.log10(1 + _recent_purchases(df, BURST_WINDOW_MIN))

    out.index = df["transaction_id"].to_numpy()
    out.index.name = "transaction_id"
    return out[list(FEATURES)]
