"""Vérifie les références simples (dossier baselines/)."""

import inspect

import pandas as pd
import pytest

from baselines import rules
from baselines.rules import run
from data_generation.generate import build
from evaluation.metrics import scores


@pytest.fixture(scope="module")
def world():
    w = build()
    tx, truth = w["ventes/transactions"], w["ground_truth/transactions"].set_index("transaction_id")
    return tx, w["service_client/clients_interne"], truth


@pytest.mark.parametrize("name", ["contrat", "expert"])
def test_aucune_fausse_alerte_sur_le_jeu_de_conception(world, name):
    tx, clients, truth = world
    flags = run(name, tx, clients)
    assert scores(truth.loc[flags.index, "est_anomalie"], flags["quarantaine"])["FP"] == 0


def test_reference_contrat_attrape_toutes_les_erreurs_classiques_et_aucune_subtile(world):
    tx, clients, truth = world
    q = run("contrat", tx, clients)["quarantaine"]
    t = truth.loc[q.index]
    assert q[t["statut"] == "erreur_classique"].all()
    assert not q[t["statut"] == "anomalie_subtile"].any()


def test_reference_expert_ajoute_les_deux_decouvertes_de_l_exploration(world):
    tx, clients, truth = world
    contract, expert = run("contrat", tx, clients)["quarantaine"], run("expert", tx, clients)["quarantaine"]
    assert (expert | ~contract).all(), "L'expert garde tout ce que le contrat attrape."
    added = truth.loc[expert[expert & ~contract].index, "famille"]
    assert set(added) == {"magasin_hors_horaires", "prix_unitaire_aberrant"}


def test_les_regles_sont_lues_dans_le_contrat(world):
    """Retirer une valeur autorisée dans le contrat change le comportement de la référence."""
    tx, clients, _ = world
    contract = rules.load_contract(rules.CONTRACT_CURRENT)
    canal = next(p for p in contract["schema"][0]["properties"] if p["name"] == "canal")
    canal["quality"][0]["arguments"]["validValues"] = ["Web", "Mobile"]
    flags = rules.contract_flags(tx, clients, contract)
    assert flags["q-canal-valide"].sum() >= (tx["canal"] == "Magasin").sum()


def test_les_references_ne_lisent_jamais_la_verite_terrain():
    assert "ground_truth" not in inspect.getsource(rules)
