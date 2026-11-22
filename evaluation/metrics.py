"""Métriques de détection, communes à toutes les évaluations du projet.

Vocabulaire (une « alerte » = une ligne mise en quarantaine) :
- vrai positif (VP)  : alerte sur une vraie anomalie ;
- faux positif (FP)  : alerte sur une ligne correcte (travail inutile pour le Data Steward) ;
- faux négatif (FN)  : anomalie qui passe sans alerte ;
- précision = VP / (VP + FP) : quand le système alerte, a-t-il raison ?
- rappel    = VP / (VP + FN) : parmi les anomalies, combien sont trouvées ?
- F1        = moyenne harmonique de la précision et du rappel.
"""

import pandas as pd


def scores(truth: pd.Series, alert: pd.Series) -> dict:
    """truth et alert : séries booléennes alignées sur le même index."""
    truth, alert = truth.astype(bool), alert.reindex(truth.index).fillna(False).astype(bool)
    vp = int((alert & truth).sum())
    fp = int((alert & ~truth).sum())
    fn = int((~alert & truth).sum())
    vn = int((~alert & ~truth).sum())
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"alertes": vp + fp, "VP": vp, "FP": fp, "FN": fn, "VN": vn,
            "precision": round(precision, 4), "rappel": round(recall, 4), "F1": round(f1, 4)}


def recall_by_family(families: pd.Series, is_anomaly: pd.Series, alert: pd.Series) -> dict:
    """Part des anomalies de chaque famille qui déclenchent une alerte."""
    alert = alert.reindex(families.index).fillna(False).astype(bool)
    anomalies = is_anomaly.astype(bool)
    return {fam: round(float(alert[anomalies & (families == fam)].mean()), 4)
            for fam in sorted(families[anomalies].unique())}


def false_alerts_by_status(status: pd.Series, is_anomaly: pd.Series, alert: pd.Series) -> dict:
    """Où tombent les fausses alertes : sur du « normal » ou du « normal mais inhabituel » ?"""
    alert = alert.reindex(status.index).fillna(False).astype(bool)
    fp = alert & ~is_anomaly.astype(bool)
    return {k: int(v) for k, v in status[fp].value_counts().items()}


# Critère de coût (étape 5b, choix de William). Règle « 1-10-100 » de Labovitz et
# Chang : vérifier une donnée à l'arrivée coûte 1, la corriger plus tard coûte 10,
# laisser l'erreur produire ses effets coûte 100. Ici : chaque ligne examinée par
# le Data Steward coûte 1 ; chaque anomalie manquée coûte MISS_COST (10 par défaut,
# l'hypothèse prudente : l'erreur est rattrapée plus tard, à la correction).
REVIEW_COST, MISS_COST = 1, 10
MISS_COSTS = [1, 10, 100]


def f_beta(precision: float, recall: float, beta: float) -> float:
    """F-beta : beta = 2 compte le rappel deux fois plus que la précision."""
    b2 = beta * beta
    return (1 + b2) * precision * recall / (b2 * precision + recall) if precision + recall else 0.0


def cost(s: dict, miss_cost: float = MISS_COST, review_cost: float = REVIEW_COST) -> float:
    """Coût total d'un système, à partir du résultat de `scores` : lignes examinées + anomalies manquées."""
    return review_cost * s["alertes"] + miss_cost * s["FN"]


def break_even(system: dict, reference: dict) -> float | None:
    """Coût d'une anomalie manquée (en lignes examinées) au-delà duquel `system` coûte moins que `reference`.

    None si le système ne rattrape aucune anomalie de plus que la référence.
    """
    extra_reviews = system["alertes"] - reference["alertes"]
    fewer_missed = reference["FN"] - system["FN"]
    return round(extra_reviews / fewer_missed, 2) if fewer_missed > 0 else None
