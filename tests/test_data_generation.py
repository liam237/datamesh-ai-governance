"""Vérifie que le monde simulé se comporte comme prévu.

Le test le plus important est celui des trois sortes de désordre, face aux règles
de la version INITIALE (1.0.0) du contrat n° 1, celle qui existait avant
l'exploration :
- les données correctes (normales ou inhabituelles) ne violent AUCUNE règle ;
- chaque erreur classique viole AU MOINS UNE règle ;
- aucune anomalie subtile ne viole de règle : c'est là que l'IA devra prouver sa valeur.
"""

import pandas as pd
import pytest

from data_generation import config as C
from data_generation.generate import TRANSACTION_COLUMNS, build

VALID = {
    "type_transaction": {"vente", "remboursement"},
    "categorie": {c.name for c in C.CATEGORIES},
    "pays": set(C.COUNTRIES),
    "segment": set(C.SEGMENTS),
    "canal": set(C.CHANNELS),
}


@pytest.fixture(scope="module")
def world():
    return build()


@pytest.fixture(scope="module")
def tx_truth(world):
    return world["ventes/transactions"].merge(world["ground_truth/transactions"], on="transaction_id")


def contract_violations(tx: pd.DataFrame, clients: pd.DataFrame) -> pd.Series:
    """Règles du contrat n° 1 en version 1.0.0, ligne à ligne (True = au moins une violation).

    La version 1.1.0 ajoute la règle des horaires d'ouverture, qui attrape la
    famille « magasin_hors_horaires » : voir tests/test_contracts.py.
    """
    expected_currency = tx["pays"].map({p: v[1] for p, v in C.COUNTRIES.items()})
    checks = [
        tx["montant"].isna(), tx["client_id"].isna(),
        (tx["type_transaction"] == "vente") & (tx["montant"] <= 0),
        (tx["type_transaction"] == "remboursement") & (tx["montant"] >= 0),
        tx["pays"].isin(VALID["pays"]) & (tx["devise"] != expected_currency),
        tx["quantite"] < 1,
        tx.duplicated(["client_id", "date_transaction", "categorie", "montant"], keep="first"),
        tx["client_id"].notna() & ~tx["client_id"].isin(clients["client_id"]),
    ]
    checks += [~tx[col].isin(values) for col, values in VALID.items()]
    out = checks[0]
    for c in checks[1:]:
        out = out | c
    return out


def test_reproductible_avec_la_meme_graine(world):
    again = build()
    for name, df in world.items():
        pd.testing.assert_frame_equal(df, again[name], obj=name)


def test_une_autre_graine_donne_un_autre_monde(world):
    other = build(seed=7)
    assert not world["ventes/transactions"].equals(other["ventes/transactions"])


def test_donnees_publiees_sans_aucune_etiquette(world):
    forbidden = {"statut", "famille", "est_anomalie", "description", "contient_pii",
                 "activite_annuelle", "multiplicateur_panier", "canal_prefere"}
    for name, df in world.items():
        if name.startswith("ground_truth/"):
            continue
        assert not forbidden & set(df.columns), name
        assert not [c for c in df.columns if c.startswith("_")], name


def test_colonnes_conformes_au_contrat(world):
    assert list(world["ventes/transactions"].columns) == TRANSACTION_COLUMNS


def test_donnees_correctes_ne_violent_aucune_regle(world, tx_truth):
    clean = tx_truth[~tx_truth["est_anomalie"]]
    violations = contract_violations(clean, world["service_client/clients_interne"])
    assert violations.sum() == 0, clean[violations].head()


def test_chaque_erreur_classique_viole_une_regle(world, tx_truth):
    v = contract_violations(tx_truth, world["service_client/clients_interne"])
    classic = tx_truth["statut"] == "erreur_classique"
    missed = tx_truth[classic & ~v]
    assert missed.empty, missed[["famille", "description"]].head()


def test_aucune_anomalie_subtile_ne_viole_de_regle(world, tx_truth):
    v = contract_violations(tx_truth, world["service_client/clients_interne"])
    subtle = tx_truth["statut"] == "anomalie_subtile"
    caught = tx_truth[subtle & v]
    assert caught.empty, caught[["famille", "description"]].head()


def test_proportions_realistes(tx_truth):
    assert 0.015 < tx_truth["est_anomalie"].mean() < 0.04
    refunds = (tx_truth["type_transaction"] == "remboursement").mean()
    assert 0.03 < refunds < 0.08
    assert set(tx_truth.loc[tx_truth["est_anomalie"], "famille"]) == {
        f for f in C.AnomalyRates.__dataclass_fields__}


def test_le_normal_inhabituel_existe(tx_truth):
    families = set(tx_truth.loc[tx_truth["statut"] == "inhabituel_legitime", "famille"])
    assert families == {"remboursement", "commande_professionnelle"}
    assert (tx_truth["periode"] != "normale").mean() > 0.2


def test_magasin_ouvert_pour_les_donnees_correctes(tx_truth):
    shop = tx_truth[(tx_truth["canal"] == "Magasin") & ~tx_truth["est_anomalie"]]
    assert shop["date_transaction"].dt.hour.isin(C.STORE_OPENING_HOURS).all()


def test_derive_limitee_a_la_categorie_au_pays_et_a_la_periode(tx_truth):
    d = tx_truth[tx_truth["derive_prix_categorie"]]
    bug = C.PRICE_BUG
    assert len(d) > 100
    assert set(d["categorie"]) == {bug["categorie"]} and set(d["pays"]) == {bug["pays"]}
    days = d["date_transaction"].dt.date
    assert days.min() >= bug["start"] and days.max() <= bug["end"]


def test_doublons_et_homonymes(world):
    clients = world["service_client/clients_interne"].set_index("client_id")
    dups = world["ground_truth/clients_doublons"]
    homonyms = world["ground_truth/clients_homonymes"]
    assert len(dups) == C.N_CLIENT_DUPLICATES
    assert len(homonyms) >= C.N_FORCED_HOMONYMS
    for a, b in zip(homonyms["client_id_1"], homonyms["client_id_2"]):
        assert clients.at[a, "email"] != clients.at[b, "email"]   # deux personnes distinctes
    identical = sum((clients.loc[o, ["prenom", "nom", "email"]] == clients.loc[d, ["prenom", "nom", "email"]]).all()
                    for o, d in zip(dups["client_id_original"], dups["client_id_doublon"]))
    assert identical == 0, "Un doublon doit différer de l'original par au moins un détail."


def test_tickets_coherents_avec_les_autres_domaines(world):
    tickets = world["service_client/tickets"]
    assert tickets["client_id"].isin(world["service_client/clients_interne"]["client_id"]).all()
    cited = tickets["transaction_id"].dropna()
    assert cited.isin(world["ventes/transactions"]["transaction_id"]).all()


def test_pii_etiquetee_presente_dans_le_texte(world):
    tickets = world["service_client/tickets"].set_index("ticket_id")
    truth = world["ground_truth/tickets_pii"]
    with_pii = truth[truth["contient_pii"]]
    assert {"formatee", "libre"} <= set(with_pii["forme"])
    for tid, values in zip(with_pii["ticket_id"], with_pii["valeurs_pii"]):
        for value in values.split("|"):
            assert value in tickets.at[tid, "commentaire"]


# ---------------------------------------------------------------------------
# Jeu de test indépendant et famille « inconnue » (parade contre la circularité)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_world():
    return build(test=True)


def test_le_jeu_de_conception_ne_contient_pas_la_famille_inconnue(tx_truth):
    assert "anomalie_inconnue" not in set(tx_truth["statut"])


def test_le_jeu_de_test_est_un_autre_monde(world, test_world):
    a, b = world["ventes/transactions"], test_world["ventes/transactions"]
    assert not a[["client_id", "montant"]].head(100).equals(b[["client_id", "montant"]].head(100))


def test_rafales_conformes_a_toutes_les_regles(test_world):
    tx = test_world["ventes/transactions"].merge(test_world["ground_truth/transactions"], on="transaction_id")
    bursts = tx[tx["famille"] == "rafale_achats"]
    assert len(bursts) > 0 and len(bursts) % C.UNKNOWN_BURST_SIZE == 0
    assert contract_violations(bursts, test_world["service_client/clients_interne"]).sum() == 0
    assert bursts["date_transaction"].dt.hour.isin(C.STORE_OPENING_HOURS).all() or \
        not (bursts["canal"] == "Magasin").any()
    for _, b in bursts.groupby("client_id"):
        for _, one in b.groupby(b["date_transaction"].dt.date):
            if len(one) == C.UNKNOWN_BURST_SIZE:
                span = (one["date_transaction"].max() - one["date_transaction"].min()).total_seconds() / 60
                assert span <= C.UNKNOWN_BURST_WINDOW_MIN
                assert one["categorie"].nunique() == C.UNKNOWN_BURST_SIZE


def test_jeu_d_examen_independant_avec_une_nouvelle_famille_inconnue():
    from data_generation.generate import build
    a = build(exam=True)
    truth = a["ground_truth/transactions"]
    fams = set(truth.loc[truth["est_anomalie"], "famille"])
    assert {"rafale_achats", "rejeu_lot"} <= fams
    replay = truth[truth["famille"] == "rejeu_lot"]
    assert (replay["statut"] == "anomalie_inconnue").all() and len(replay) > 0
    b = build(exam=True)
    pd.testing.assert_frame_equal(a["ventes/transactions"], b["ventes/transactions"])
