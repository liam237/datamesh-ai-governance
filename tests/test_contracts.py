"""Vérifie les contrats de données.

Deux niveaux de contrôle :
1. conformité au schéma officiel ODCS v3.1.0 (fichier contracts/schema/) ;
2. règles propres au projet (identifiants uniques, requêtes SQL bien formées,
   renvoi des règles « custom » vers un mécanisme existant du cadre).
"""

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
SCHEMA_FILE = CONTRACTS_DIR / "schema" / "odcs-json-schema-v3.1.0.json"
CONTRACT_FILES = sorted(CONTRACTS_DIR.glob("*.yaml"))
OPERATORS = {
    "mustBe", "mustNotBe", "mustBeGreaterThan", "mustBeGreaterOrEqualTo",
    "mustBeLessThan", "mustBeLessOrEqualTo", "mustBeBetween", "mustNotBeBetween",
}
CUSTOM_ENGINE = "datamesh-ai-governance"


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def all_quality_rules(contract):
    """Toutes les règles de qualité, au niveau des objets et des colonnes."""
    for obj in contract.get("schema", []):
        for rule in obj.get("quality", []):
            yield obj["name"], None, rule
        for prop in obj.get("properties", []):
            for rule in prop.get("quality", []):
                yield obj["name"], prop["name"], rule


def test_deux_contrats_presents():
    names = {p.name for p in CONTRACT_FILES}
    assert names == {"ventes_vers_finance.yaml", "service_client_vers_finance.yaml"}


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_conforme_au_schema_officiel_odcs(path):
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    jsonschema.validate(load(path), schema)


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_un_proprietaire_identifie(path):
    members = load(path)["team"]["members"]
    owners = [m for m in members if m.get("role") == "owner"]
    assert len(owners) == 1, "Un contrat a exactement un propriétaire (le A du RACI)."


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_identifiants_de_regles_uniques(path):
    ids = [rule["id"] for _, _, rule in all_quality_rules(load(path))]
    assert len(ids) == len(set(ids)), "Deux règles portent le même identifiant."


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_chaque_regle_a_une_dimension_et_une_gravite(path):
    for obj, prop, rule in all_quality_rules(load(path)):
        assert rule.get("dimension"), f"{obj}.{prop} {rule['id']} : dimension manquante"
        assert rule.get("severity") in {"error", "warning"}, rule["id"]


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_regles_sql_bien_formees(path):
    for _, _, rule in all_quality_rules(load(path)):
        if rule.get("type") != "sql":
            continue
        assert "{object}" in rule["query"], rule["id"]
        assert rule["query"].strip().upper().startswith("SELECT COUNT(*)"), rule["id"]
        used = OPERATORS & rule.keys()
        assert len(used) == 1, f"{rule['id']} : une seule comparaison attendue"


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_regles_custom_renvoient_a_un_mecanisme(path):
    for _, _, rule in all_quality_rules(load(path)):
        if rule.get("type") != "custom":
            continue
        assert rule["engine"] == CUSTOM_ENGINE
        match = re.match(r"^mecanisme_(\d+)_", rule["implementation"])
        assert match and 1 <= int(match.group(1)) <= 10, rule["id"]


def test_minimisation_rgpd_du_referentiel_clients():
    """La Finance ne reçoit ni nom, ni e-mail, ni téléphone des clients."""
    contract = load(CONTRACTS_DIR / "service_client_vers_finance.yaml")
    clients = next(o for o in contract["schema"] if o["name"] == "clients")
    columns = {p["name"] for p in clients["properties"]}
    assert not columns & {"nom", "prenom", "nom_complet", "email", "telephone", "iban"}


def test_remboursement_autorise_montant_negatif():
    """Le contrat distingue vente et remboursement au lieu d'interdire tout montant négatif."""
    contract = load(CONTRACTS_DIR / "ventes_vers_finance.yaml")
    ids = {rule["id"] for _, _, rule in all_quality_rules(contract)}
    assert {"q-vente-positive", "q-remboursement-negatif"} <= ids


# ---------------------------------------------------------------------------
# Exécution réelle des règles SQL des contrats sur les données générées (DuckDB)
# ---------------------------------------------------------------------------

HISTORY_FILES = sorted((CONTRACTS_DIR / "history").glob("*.yaml"))


@pytest.mark.parametrize("path", HISTORY_FILES, ids=lambda p: p.name)
def test_versions_archivees_conformes_au_schema_officiel(path):
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    jsonschema.validate(load(path), schema)


def test_versions_successives_du_contrat_ventes():
    old = load(CONTRACTS_DIR / "history" / "ventes_vers_finance_v1.0.0.yaml")
    new = load(CONTRACTS_DIR / "ventes_vers_finance.yaml")
    assert (old["version"], new["version"]) == ("1.0.0", "1.1.0")
    added = {r["id"] for _, _, r in all_quality_rules(new)} - {r["id"] for _, _, r in all_quality_rules(old)}
    assert added == {"q-magasin-horaires"}


@pytest.fixture(scope="module")
def duck():
    """Une base DuckDB en mémoire avec les tables publiées et le sous-ensemble correct."""
    import duckdb
    from data_generation.generate import build

    world = build()
    tx = world["ventes/transactions"]
    truth = world["ground_truth/transactions"]
    tickets = world["service_client/tickets"]
    con = duckdb.connect()
    con.register("ventes_transactions", tx)
    con.register("service_client_clients", world["service_client/clients_interne"])
    con.register("service_client_tickets", tickets)
    con.register("clean_transactions", tx[tx["transaction_id"].isin(truth.loc[~truth["est_anomalie"], "transaction_id"])])
    return con, truth


def sql_rules(path):
    return [(obj["physicalName"], rule) for obj, _, rule in
            ((o, None, r) for o in load(path)["schema"]
             for r in o.get("quality", []) + [q for p in o.get("properties", []) for q in p.get("quality", [])])
            if rule.get("type") == "sql"]


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_regles_sql_sans_fausse_alerte_sur_les_donnees_correctes(duck, path):
    con, _ = duck
    for table, rule in sql_rules(path):
        target = "clean_transactions" if table == "ventes_transactions" else table
        count = con.execute(rule["query"].replace("{object}", target)).fetchone()[0]
        assert count == 0, f"{rule['id']} : {count} fausse(s) alerte(s)"


def test_regle_horaires_attrape_exactement_les_ventes_de_nuit(duck):
    con, truth = duck
    rule = next(r for _, r in sql_rules(CONTRACTS_DIR / "ventes_vers_finance.yaml") if r["id"] == "q-magasin-horaires")
    query = rule["query"].replace("SELECT COUNT(*)", "SELECT transaction_id").replace("{object}", "ventes_transactions")
    caught = set(con.execute(query).df()["transaction_id"])
    expected = set(truth.loc[truth["famille"] == "magasin_hors_horaires", "transaction_id"])
    assert caught == expected
