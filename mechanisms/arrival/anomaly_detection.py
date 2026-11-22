"""Mécanisme 1 : détection d'anomalies dans les ventes.

Ce module ne lit jamais la vérité terrain. Il propose :
- cinq méthodes NON supervisées, qui apprennent seulement à quoi ressemble une
  vente normale (`fit(X)`), puis notent chaque vente (`score(X)`) ;
- deux modèles SUPERVISÉS de comparaison, qui ont besoin d'étiquettes. Dans la
  réalité, ces étiquettes viendraient des décisions du Data Steward sur les
  lignes mises en quarantaine ; ici, c'est evaluation/ qui les fournit.

Convention commune : plus le score est haut, plus la vente est suspecte.

Les réglages sont ceux par défaut des bibliothèques (ou les valeurs classiques
de la littérature, citées), sans optimisation : on compare des idées à armes
égales. La justification de chaque méthode est dans le journal de bord
(« Justification des choix pour le mécanisme 1 »).
"""

import numpy as np
import pandas as pd
from sklearn.covariance import MinCovDet
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler
from sklearn.svm import OneClassSVM

from mechanisms.arrival.features import FEATURES

# log_montant est exclu (8 variables restent) : corrélé à 0,80 avec ecart_categorie (notebook 02, section 9).
MODEL_FEATURES = [f for f in FEATURES if f != "log_montant"]

OCSVM_MAX_TRAIN = 5_000   # One-Class SVM : coût en n², on l'entraîne sur un échantillon


class RobustZScore:
    """Score z robuste (Iglewicz et Hoaglin, 1993), le plancher statistique.

    Pour chaque variable : z = 0,6745 × (x − médiane) / MAD, où MAD est l'écart
    absolu médian. Le score d'une vente est le plus grand |z| sur ses variables :
    elle est suspecte dès qu'UNE variable est très loin de l'habitude.
    """

    def fit(self, X):
        X = np.asarray(X, dtype=float)
        self.median_ = np.median(X, axis=0)
        mad = np.median(np.abs(X - self.median_), axis=0)
        # Si plus de la moitié des valeurs sont identiques, la MAD vaut 0 : on se
        # rabat sur l'écart absolu moyen (× 1,2533 pour rester comparable).
        meanad = np.mean(np.abs(X - self.median_), axis=0) * 1.2533
        self.scale_ = np.where(mad > 0, mad / 0.6745, meanad)
        self.scale_[self.scale_ == 0] = 1.0
        return self

    def score(self, X):
        return np.max(np.abs((np.asarray(X, dtype=float) - self.median_) / self.scale_), axis=1)


class RobustMahalanobis:
    """Distance de Mahalanobis robuste (estimateur MCD, Rousseeuw et Van Driessen, 1999).

    On estime le centre et la forme (l'ellipse) des ventes normales en ignorant
    la part la plus excentrée des données, puis on mesure la distance de chaque
    vente à ce centre, en tenant compte des corrélations entre variables.
    """

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, X):
        self.scaler_ = RobustScaler().fit(X)
        self.mcd_ = MinCovDet(random_state=self.random_state).fit(self.scaler_.transform(X))
        return self

    def score(self, X):
        return self.mcd_.mahalanobis(self.scaler_.transform(X))


class IForest:
    """Isolation Forest (Liu, Ting et Zhou, 2008) : une anomalie s'isole en peu de coupes."""

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, X):
        self.model_ = IsolationForest(random_state=self.random_state, n_jobs=-1).fit(X)
        return self

    def score(self, X):
        return -self.model_.score_samples(X)


class LOF:
    """Facteur local d'anomalie (Breunig et al., 2000) : densité comparée à celle des voisins.

    novelty=True permet de noter des ventes que le modèle n'a pas vues.
    Les variables sont mises à la même échelle, car LOF repose sur des distances.
    """

    def fit(self, X):
        self.scaler_ = RobustScaler().fit(X)
        self.model_ = LocalOutlierFactor(novelty=True, n_jobs=-1).fit(self.scaler_.transform(X))
        return self

    def score(self, X):
        return -self.model_.score_samples(self.scaler_.transform(X))


class OCSVM:
    """One-Class SVM (Schölkopf et al., 2001) : une frontière souple autour du normal.

    nu = 0,05 : on accepte qu'environ 5 % des ventes d'apprentissage tombent hors
    de la frontière (ordre de grandeur prudent, au-dessus du taux d'anomalies).
    """

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, X):
        X = np.asarray(X, dtype=float)
        if len(X) > OCSVM_MAX_TRAIN:
            rng = np.random.default_rng(self.random_state)
            X = X[rng.choice(len(X), OCSVM_MAX_TRAIN, replace=False)]
        self.scaler_ = RobustScaler().fit(X)
        self.model_ = OneClassSVM(nu=0.05, gamma="scale").fit(self.scaler_.transform(X))
        return self

    def score(self, X):
        return -self.model_.score_samples(self.scaler_.transform(X))


class HistGB:
    """Comparaison supervisée : gradient boosting par histogrammes de scikit-learn.

    class_weight="balanced" : chaque anomalie compte autant que ~40 ventes
    normales, sinon le modèle apprendrait à toujours répondre « normal ».
    """

    supervised = True

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, X, y):
        self.model_ = HistGradientBoostingClassifier(class_weight="balanced",
                                                     random_state=self.random_state).fit(X, y)
        return self

    def score(self, X):
        return self.model_.predict_proba(X)[:, 1]


class XGBoost:
    """Comparaison supervisée : XGBoost (Chen et Guestrin, 2016).

    scale_pos_weight = nombre de normales / nombre d'anomalies : même rôle que
    class_weight="balanced" ci-dessus, pour que les deux soient comparables.
    """

    supervised = True

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, X, y):
        from xgboost import XGBClassifier

        y = np.asarray(y, dtype=int)
        self.model_ = XGBClassifier(scale_pos_weight=(y == 0).sum() / max((y == 1).sum(), 1),
                                    random_state=self.random_state, n_jobs=2,
                                    eval_metric="aucpr").fit(X, y)
        return self

    def score(self, X):
        return self.model_.predict_proba(X)[:, 1]


# Ordre de simplicité : il départage deux méthodes non supervisées équivalentes.
UNSUPERVISED = {
    "score_z_robuste": RobustZScore,
    "mahalanobis_robuste": RobustMahalanobis,
    "isolation_forest": IForest,
    "lof": LOF,
    "one_class_svm": OCSVM,
}
SUPERVISED = {
    "hist_gradient_boosting": HistGB,
    "xgboost": XGBoost,
}
LABELS = {
    "score_z_robuste": "Score z robuste", "mahalanobis_robuste": "Mahalanobis robuste",
    "isolation_forest": "Isolation Forest", "lof": "LOF", "one_class_svm": "One-Class SVM",
    "hist_gradient_boosting": "HistGradientBoosting", "xgboost": "XGBoost",
}


def make(name: str, seed: int = 0):
    cls = {**UNSUPERVISED, **SUPERVISED}[name]
    try:
        return cls(random_state=seed)
    except TypeError:
        return cls()


def is_supervised(name: str) -> bool:
    return name in SUPERVISED


def threshold_for_budget(scores: np.ndarray, budget: float) -> float:
    """Valeur de score au-dessus de laquelle tombe la part `budget` des ventes."""
    return float(np.quantile(scores, 1 - budget))


def alerts(model, X: pd.DataFrame, threshold: float) -> pd.Series:
    return pd.Series(model.score(X[MODEL_FEATURES]) > threshold, index=X.index, name="alerte_ia")
