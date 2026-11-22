"""Vérifie le mécanisme 1 (mechanisms/arrival/anomaly_detection.py) et son protocole."""

import inspect

import numpy as np
import pandas as pd
import pytest

from evaluation import compare_anomaly_models as C
from mechanisms.arrival import anomaly_detection as AD


@pytest.fixture(scope="module")
def toy():
    """1 000 points normaux autour de 0 et 10 points très éloignés."""
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(1010, len(AD.MODEL_FEATURES))), columns=AD.MODEL_FEATURES)
    X.iloc[1000:] += 8
    y = np.r_[np.zeros(1000, dtype=int), np.ones(10, dtype=int)]
    return X, y


def test_le_mecanisme_ne_lit_jamais_la_verite_terrain():
    src = inspect.getsource(AD)
    assert "ground_truth" not in src and "load_truth" not in src


def test_log_montant_exclu_du_modele():
    assert "log_montant" not in AD.MODEL_FEATURES and len(AD.MODEL_FEATURES) == 7


@pytest.mark.parametrize("name", [*AD.UNSUPERVISED, *AD.SUPERVISED])
def test_chaque_methode_place_les_points_eloignes_en_tete(toy, name):
    X, y = toy
    model = AD.make(name, 0)
    model.fit(X, y) if AD.is_supervised(name) else model.fit(X)
    s = model.score(X)
    assert s.shape == (len(X),)
    assert np.mean(s[y == 1]) > np.quantile(s[y == 0], 0.95)


def test_les_non_supervisees_n_acceptent_pas_d_etiquettes():
    for name in AD.UNSUPERVISED:
        assert list(inspect.signature(AD.make(name).fit).parameters) == ["X"]


def test_seuil_complementaire_respecte_le_budget():
    s = np.arange(1000, dtype=float)
    eligible = np.ones(1000, dtype=bool); eligible[-50:] = False   # 50 déjà en quarantaine
    thr = C._complement_threshold(s, eligible, 0.01)
    assert ((s > thr) & eligible).sum() == 9 and ((s >= thr) & eligible).sum() == 10


def test_regle_de_choix_ignore_les_supervises_et_departage_par_simplicite():
    rows = []
    for split in range(10):
        rows += [{"methode": "xgboost", "decoupage": split, "auc_pr": 0.9},
                 {"methode": "isolation_forest", "decoupage": split, "auc_pr": 0.30 + 0.001 * (split % 2)},
                 {"methode": "score_z_robuste", "decoupage": split, "auc_pr": 0.30 + 0.001 * ((split + 1) % 2)},
                 {"methode": "lof", "decoupage": split, "auc_pr": 0.1},
                 {"methode": "one_class_svm", "decoupage": split, "auc_pr": 0.1},
                 {"methode": "mahalanobis_robuste", "decoupage": split, "auc_pr": 0.1}]
    choice = C.choose(pd.DataFrame(rows))
    assert not choice["ecart_significatif"]
    assert choice["gagnant"] == "score_z_robuste"
