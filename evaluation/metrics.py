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
