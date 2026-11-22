"""Références simples : des règles, sans IA, auxquelles on compare les mécanismes.

Deux références :

- « contrat » : les règles du contrat n° 1 dans sa version INITIALE (1.0.0),
  telle qu'elle existait avant l'exploration des données ;
- « expert »  : les règles du contrat ACTUEL (1.1.0, avec les horaires
  d'ouverture), plus la règle qu'un analyste attentif aurait écrite après
  l'exploration (quantité anormale pour un particulier).

Les règles ne sont pas recopiées à la main : elles sont LUES dans le fichier
YAML du contrat (format ODCS) et appliquées ligne par ligne. Si le contrat
change, la référence change avec lui.

Chaque règle produit une colonne vraie/fausse par transaction ; une transaction
part en quarantaine dès qu'une règle au moins la signale. Aucune de ces règles
ne lit la vérité terrain.
"""

import re
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_INITIAL = ROOT / "contracts" / "history" / "ventes_vers_finance_v1.0.0.yaml"
CONTRACT_CURRENT = ROOT / "contracts" / "ventes_vers_finance.yaml"
EXPERT_MAX_QTY_NON_PRO = 5     # exploration, section 6 : jamais plus de 5 articles chez un particulier


def load_contract(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def contract_flags(tx: pd.DataFrame, clients: pd.DataFrame, contract: dict) -> pd.DataFrame:
    """Applique ligne par ligne les règles exécutables du contrat n° 1.

    Les règles de type « custom » sont ignorées ici : elles sont confiées aux
    mécanismes d'IA. Les règles qui portent sur l'ensemble du lot (nombre de
    lignes) ne produisent pas de signalement ligne par ligne.
    """
    obj = next(o for o in contract["schema"] if o["name"] == "transactions")
    flags = pd.DataFrame(index=tx.index)

    for prop in obj["properties"]:
        col = prop["name"]
        if prop.get("required"):
            flags[f"requis:{col}"] = tx[col].isna()
        options = prop.get("logicalTypeOptions", {})
        if "pattern" in options:
            flags[f"format:{col}"] = tx[col].notna() & ~tx[col].astype(str).str.fullmatch(options["pattern"])
        if "minimum" in options:
            flags[f"minimum:{col}"] = tx[col] < options["minimum"]
        for rule in prop.get("quality", []):
            if rule.get("metric") == "nullValues":
                flags[rule["id"]] = tx[col].isna()
            elif rule.get("metric") == "invalidValues":
                flags[rule["id"]] = tx[col].notna() & ~tx[col].isin(rule["arguments"]["validValues"])
            elif rule.get("type") == "sql":
                flags[rule["id"]] = _sql_flags(tx, clients, rule["query"])

    for rule in obj.get("quality", []):
        if rule.get("metric") == "duplicateValues":
            flags[rule["id"]] = tx.duplicated(rule["arguments"]["properties"], keep="first")
        elif rule.get("type") == "sql":
            flags[rule["id"]] = _sql_flags(tx, clients, rule["query"])
    return flags


def _sql_flags(tx: pd.DataFrame, clients: pd.DataFrame, query: str) -> pd.Series:
    """Transforme une requête « SELECT COUNT(*) ... » du contrat en liste de lignes fautives."""
    alias = re.search(r"FROM \{object\}\s+(\w+)\b(?!\s*WHERE)", query)
    column = f"{alias.group(1)}.transaction_id" if alias and alias.group(1).upper() not in {"WHERE", "LEFT"} \
        else "transaction_id"
    rows_query = query.replace("SELECT COUNT(*)", f"SELECT {column}", 1).replace("{object}", "ventes_transactions")
    con = duckdb.connect()
    con.register("ventes_transactions", tx)
    con.register("service_client_clients", clients)
    bad = set(con.execute(rows_query).df().iloc[:, 0])
    con.close()
    return tx["transaction_id"].isin(bad)


def expert_flags(tx: pd.DataFrame) -> pd.DataFrame:
    """Règle ajoutée par un analyste après l'exploration (hors contrat)."""
    return pd.DataFrame({
        "expert:quantite_particulier": (tx["segment"] != "Professionnel") & (tx["quantite"] > EXPERT_MAX_QTY_NON_PRO),
    }, index=tx.index)


def run(name: str, tx: pd.DataFrame, clients: pd.DataFrame) -> pd.DataFrame:
    """Applique la référence « contrat » ou « expert ».

    Renvoie un tableau indexé par transaction_id : une colonne par règle, plus
    `quarantaine` (au moins une règle signale la ligne) et `motifs` (lesquelles).
    """
    if name == "contrat":
        flags = contract_flags(tx, clients, load_contract(CONTRACT_INITIAL))
    elif name == "expert":
        flags = pd.concat([contract_flags(tx, clients, load_contract(CONTRACT_CURRENT)), expert_flags(tx)], axis=1)
    else:
        raise ValueError(f"Référence inconnue : {name!r} (attendu : « contrat » ou « expert »)")
    flags = flags.fillna(False).astype(bool)
    flags["quarantaine"] = flags.any(axis=1)
    flags["motifs"] = flags.drop(columns="quarantaine").apply(lambda r: "|".join(r.index[r]), axis=1)
    flags.index = tx["transaction_id"].to_numpy()
    flags.index.name = "transaction_id"
    return flags
