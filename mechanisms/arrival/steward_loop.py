"""Mécanisme 1, version finale : trois couches qui apprennent des décisions du Data Steward.

Décidé à l'étape 5b (journal de bord, « Décision B + C »). Chaque semaine :

1. les RÈGLES de l'expert mettent en quarantaine ce qu'elles reconnaissent ;
2. le modèle SUPERVISÉ, appris sur les décisions passées du Data Steward,
   propose les ventes qui ressemblent à des anomalies déjà confirmées ;
3. le FILET non supervisé propose ce qui est rare, pour faire remonter ce que
   personne n'a encore vu (sans lui, le supervisé n'apprendrait jamais une
   famille qu'aucune règle ne signale : c'est le biais de sélection).

Le Data Steward examine la quarantaine, plus un budget d'alertes égal à une part
fixe des ventes de la semaine. Ce module ne lit jamais la vérité terrain : les
étiquettes lui sont données par celui qui joue le Data Steward (evaluation/).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from mechanisms.arrival import anomaly_detection as AD


@dataclass
class Settings:
    supervised: str = "hist_gradient_boosting"
    net: str = "isolation_forest"
    budget: float = 0.01          # part des ventes de la semaine examinées en plus de la quarantaine
    net_share: float = 0.25       # part de ce budget réservée au filet, une fois le supervisé actif
    retrain_every: int = 4        # semaines entre deux réentraînements
    net_window: int = 12          # semaines de ventes sur lesquelles le filet apprend le « normal »
    min_positives: int = 20       # étiquettes « vraie anomalie » nécessaires pour activer le supervisé
    sup_min_score: float | None = None  # si fixé : le supervisé n'envoie que les ventes au-dessus de ce score
    seed: int = 0


@dataclass
class StewardLoop:
    settings: Settings = field(default_factory=Settings)

    def __post_init__(self):
        self.net_model = None
        self.sup_model = None

    @property
    def supervised_active(self) -> bool:
        return self.sup_model is not None

    def retrain_net(self, X_recent: pd.DataFrame) -> None:
        """Le filet réapprend le « normal » sur les ventes récentes, sans étiquette."""
        self.net_model = AD.make(self.settings.net, self.settings.seed).fit(X_recent[AD.MODEL_FEATURES])

    def retrain_supervised(self, X_seen: pd.DataFrame, confirmed: pd.Series) -> None:
        """Le supervisé réapprend sur toutes les ventes passées.

        confirmed : True pour une anomalie confirmée par le Data Steward, False
        sinon. Une vente jamais examinée compte comme normale, ce qui est faux
        pour les anomalies que personne n'a vues : c'est le bruit réaliste de
        l'apprentissage à partir des décisions humaines.
        """
        y = confirmed.reindex(X_seen.index).fillna(False).astype(int).to_numpy()
        if y.sum() < self.settings.min_positives:
            return
        self.sup_model = AD.make(self.settings.supervised, self.settings.seed).fit(
            X_seen[AD.MODEL_FEATURES], y)

    def propose(self, X_week: pd.DataFrame, quarantined: pd.Series) -> dict[str, pd.Index]:
        """Les ventes de la semaine envoyées au Data Steward en plus de la quarantaine.

        Chaque couche envoie ses k ventes les plus suspectes ; k est fixé par le
        budget, si bien qu'aucun seuil de score n'est à régler.
        """
        s = self.settings
        candidates = X_week.index[~quarantined.reindex(X_week.index).fillna(False).to_numpy(bool)]
        k_total = int(round(s.budget * len(X_week)))
        k_sup = int(round(k_total * (1 - s.net_share))) if self.supervised_active else 0
        out = {"supervise": pd.Index([]), "filet": pd.Index([])}
        if k_sup and len(candidates):
            score = pd.Series(self.sup_model.score(X_week.loc[candidates, AD.MODEL_FEATURES]), index=candidates)
            if s.sup_min_score is not None:
                score = score[score >= s.sup_min_score]
            out["supervise"] = score.nlargest(k_sup).index
            candidates = candidates.difference(out["supervise"])
        k_net = k_total - k_sup
        if k_net and len(candidates) and self.net_model is not None:
            score = pd.Series(self.net_model.score(X_week.loc[candidates, AD.MODEL_FEATURES]), index=candidates)
            out["filet"] = score.nlargest(k_net).index
        return out
