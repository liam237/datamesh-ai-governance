"""Vérifie le calcul des variables du mécanisme 1."""

import numpy as np
import pandas as pd
import pytest

from data_generation.generate import build
from mechanisms.arrival.features import FEATURES, build_features, sales_scope


@pytest.fixture(scope="module")
def tx():
    return build()["ventes/transactions"]


@pytest.fixture(scope="module")
def X(tx):
    return build_features(tx)


def test_une_ligne_par_vente_du_perimetre_et_aucune_valeur_manquante(tx, X):
    assert len(X) == len(sales_scope(tx))
    assert X.index.is_unique
    assert list(X.columns) == list(FEATURES)
    assert not X.isna().any().any()


def test_ecarts_centres_sur_zero(tx, X):
    scope = sales_scope(tx).set_index("transaction_id")
    med = X["ecart_categorie"].groupby(scope.loc[X.index, "categorie"]).median()
    assert np.allclose(med, 0, atol=1e-9)


def test_conversion_des_francs_suisses(tx):
    one = sales_scope(tx).iloc[[0]].copy()
    eur, chf = one.copy(), one.copy()
    eur["devise"], chf["devise"] = "EUR", "CHF"
    chf["montant"] = eur["montant"] * 0.94
    a, b = build_features(eur), build_features(chf)
    assert a["log_montant"].iloc[0] == pytest.approx(b["log_montant"].iloc[0])


def test_doublon_exact_a_un_delai_et_un_ecart_nuls(tx):
    sale = sales_scope(tx).iloc[[0]].copy()
    copy = sale.copy()
    copy["transaction_id"] = "TXN-99999999"
    X = build_features(pd.concat([sale, copy]))
    assert X.loc["TXN-99999999", "log_delai_precedent"] == 0
    assert X.loc["TXN-99999999", "ecart_montant_precedent"] == 0


def test_confiance_reduite_pour_un_client_a_un_seul_achat(tx):
    sale = sales_scope(tx).iloc[[0]].copy()
    sale["client_id"] = "CLT-999999"
    X = build_features(pd.concat([sales_scope(tx), sale]).drop_duplicates("transaction_id", keep="last"))
    assert X.loc[sale["transaction_id"].iloc[0], "ecart_habitude_client"] == pytest.approx(0)


def test_les_variables_ne_lisent_jamais_la_verite_terrain():
    import inspect
    from mechanisms.arrival import features
    assert "ground_truth" not in inspect.getsource(features)


def test_variable_rafale_compte_les_achats_de_l_heure_precedente(tx):
    base = sales_scope(tx).iloc[[0]].copy()
    base["client_id"] = "CLT-888888"
    t0 = base["date_transaction"].iloc[0]
    rows = []
    for i, minutes in enumerate([0, 10, 20, 50, 200]):      # 4 achats en 50 min, puis un tardif
        r = base.copy()
        r["transaction_id"] = f"TXN-8888888{i}"
        r["date_transaction"] = t0 + pd.Timedelta(minutes=minutes)
        rows.append(r)
    X = build_features(pd.concat(rows))
    n = 10 ** X["log_achats_heure_precedente"] - 1
    assert n.round().astype(int).tolist() == [0, 1, 2, 3, 0]
