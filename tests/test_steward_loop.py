"""Vérifie la boucle du mécanisme 1 avec le Data Steward (mechanisms/arrival/steward_loop.py)."""

import inspect

import numpy as np
import pandas as pd

from mechanisms.arrival import anomaly_detection as AD
from mechanisms.arrival import steward_loop
from mechanisms.arrival.steward_loop import Settings, StewardLoop


def _week(n=1000, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, len(AD.MODEL_FEATURES))), columns=AD.MODEL_FEATURES,
                     index=[f"TXN-{i:08d}" for i in range(n)])
    X.iloc[:15] += 6
    return X


def test_la_boucle_ne_lit_jamais_la_verite_terrain():
    src = inspect.getsource(steward_loop)
    assert "ground_truth" not in src and "load_truth" not in src


def test_le_filet_seul_utilise_tout_le_budget_tant_que_le_supervise_est_inactif():
    X = _week()
    loop = StewardLoop(Settings(budget=0.01))
    loop.retrain_net(X)
    out = loop.propose(X, pd.Series(False, index=X.index))
    assert len(out["supervise"]) == 0 and len(out["filet"]) == 10


def test_le_supervise_attend_assez_d_anomalies_confirmees():
    X = _week()
    loop = StewardLoop(Settings(min_positives=20))
    loop.retrain_supervised(X, pd.Series(X.index.isin(X.index[:15]), index=X.index))
    assert not loop.supervised_active
    loop.retrain_supervised(X, pd.Series(X.index.isin(X.index[:25]), index=X.index))
    assert loop.supervised_active


def test_partage_du_budget_et_lignes_deja_en_quarantaine_exclues():
    X = _week()
    loop = StewardLoop(Settings(budget=0.02, net_share=0.25))
    loop.retrain_net(X)
    loop.retrain_supervised(X, pd.Series(X.index.isin(X.index[:30]), index=X.index))
    q = pd.Series(X.index.isin(X.index[:5]), index=X.index)
    out = loop.propose(X, q)
    assert len(out["supervise"]) == 15 and len(out["filet"]) == 5
    sent = out["supervise"].union(out["filet"])
    assert not sent.isin(X.index[:5]).any() and not out["supervise"].isin(out["filet"]).any()
