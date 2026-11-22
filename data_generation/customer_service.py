"""Domaine Service client : doublons de clients et tickets en texte libre.

Deux pièges, chacun étiqueté pour l'évaluation :

- des CLIENTS SAISIS DEUX FOIS (faute de frappe, initiale du prénom, accents
  perdus), à distinguer des HOMONYMES, personnes différentes portant le même nom ;
- des COMMENTAIRES qui contiennent des données personnelles, avec un format
  reconnaissable (e-mail, téléphone, IBAN, n° de sécurité sociale) ou sans
  format (« rappeler Mme Dupont chez elle »), et des pièges qui y ressemblent
  sans en être (une référence produit, une ville de point relais).
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from . import config as C
from .world import FIRST_NAMES, _ascii, make_email, make_phone

# ------------------------------------------------------------------ doublons


def _typo(word: str, rng) -> str:
    if len(word) < 4:
        return word + word[-1]
    i = int(rng.integers(1, len(word) - 1))
    swapped = word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if rng.random() < 0.5 and swapped != word:  # deux lettres inversées (si elles diffèrent)
        return swapped
    return word[:i] + word[i + 1:]               # une lettre oubliée


def add_client_duplicates(clients: pd.DataFrame, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Crée des fiches en double d'un même client réel, avec des variations."""
    originals = clients.sample(n=C.N_CLIENT_DUPLICATES, random_state=int(rng.integers(1e9)))
    start_id = len(clients) + 1
    dups, truth = [], []
    kinds = ["faute_de_frappe", "initiale_prenom", "sans_accents", "email_different"]
    for k, (_, orig) in enumerate(originals.iterrows()):
        d = orig.copy()
        kind = kinds[k % len(kinds)]
        if kind == "faute_de_frappe":
            d["nom"] = _typo(orig["nom"], rng)
        elif kind == "initiale_prenom":
            d["prenom"] = orig["prenom"][0] + "."
        elif kind == "sans_accents":
            d["prenom"], d["nom"] = _ascii(orig["prenom"]), _ascii(orig["nom"]).upper()
        else:                                     # nouvelle adresse, jamais vue
            used = set(clients["email"])
            while d["email"] in used:
                d["email"] = make_email(orig["prenom"], orig["nom"], rng) \
                    .replace("@", f".{int(rng.integers(100, 999))}@")
        if rng.random() < 0.3:
            d["telephone"] = None                 # fiche incomplète
        d["client_id"] = f"CLT-{start_id + k:06d}"
        d["date_creation"] = C.START + timedelta(days=int(rng.integers(0, 300)))
        dups.append(d)
        truth.append({"client_id_original": orig["client_id"], "client_id_doublon": d["client_id"],
                      "variation": kind})
    return pd.concat([clients, pd.DataFrame(dups)], ignore_index=True), pd.DataFrame(truth)


def homonym_pairs(clients: pd.DataFrame, duplicates: pd.DataFrame) -> pd.DataFrame:
    """Toutes les paires de personnes DIFFÉRENTES portant exactement le même nom."""
    dup_ids = set(duplicates["client_id_doublon"])
    real = clients[~clients["client_id"].isin(dup_ids)]
    pairs = []
    for _, group in real.groupby(["prenom", "nom"]):
        ids = sorted(group["client_id"])
        pairs += [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]]
    return pd.DataFrame(pairs, columns=["client_id_1", "client_id_2"])


def reassign_to_duplicates(tx: pd.DataFrame, duplicates: pd.DataFrame, rng) -> pd.DataFrame:
    """Une partie des achats d'un client passe sous sa fiche en double, comme en vrai.

    On tire au sort des VENTES ; leurs remboursements les suivent sur la même
    fiche. Appelé avant l'injection des anomalies, pour qu'une copie en double
    porte toujours le même client que la vente qu'elle recopie.
    """
    tx = tx.copy()
    for orig, dup in zip(duplicates["client_id_original"], duplicates["client_id_doublon"]):
        sales = tx.index[(tx["client_id"] == orig) & (tx["type_transaction"] == "vente")]
        moved = sales[rng.random(len(sales)) < 0.3]
        follows = tx.index[tx["_vente_origine"].isin(moved)]
        tx.loc[moved.union(follows), "client_id"] = dup
    return tx

# ------------------------------------------------------------------ tickets


MOTIFS = ["livraison", "retour", "remboursement", "produit_defectueux", "information", "autre"]
MOTIF_WEIGHTS = [0.30, 0.20, 0.0, 0.15, 0.25, 0.10]   # « remboursement » vient des remboursements

TEMPLATES = {
    "livraison": ["Colis non reçu, le transporteur indique une livraison effectuée. Enquête ouverte.",
                  "Retard de livraison de {n} jours, client mécontent. Relance transporteur faite.",
                  "Colis endommagé à la réception, photos demandées."],
    "retour": ["Article ne convient pas, retour accepté sous 14 jours.",
               "Taille trop petite, échange proposé.",
               "Retour reçu en entrepôt, contrôle qualité en cours."],
    "remboursement": ["Remboursement validé pour la commande {txn}.",
                      "Geste commercial accordé suite au retour, remboursement en cours.",
                      "Remboursement partiel accepté, article conservé par le client."],
    "produit_defectueux": ["Produit ne s'allume plus après {n} jours d'utilisation.",
                           "Défaut constaté à l'ouverture, remplacement proposé.",
                           "Pièce manquante dans le carton, envoi en cours."],
    "information": ["Demande d'information sur la garantie.",
                    "Question sur les délais de livraison vers la Suisse.",
                    "Souhaite connaître la disponibilité en magasin."],
    "autre": ["Client souhaite modifier son adresse de facturation.",
              "Demande de suppression de son compte, transmise au service concerné.",
              "Réclamation sur l'accueil en magasin, transmise au responsable."],
}
TRAPS = ["Commande {txn} de {n} articles vérifiée.",
         "Référence produit 0612-4457-8 en rupture.",
         "Colis de 2,5 kg remis au point relais de {ville}.",
         "Montant remboursé : {montant} €.",
         "Ticket transféré au service Martin Logistique.",
         "Garantie de 24 mois, facture n° 2025-118-4473."]


def make_iban(rng) -> str:
    """IBAN français fictif, avec une clé de contrôle valide (norme ISO 13616)."""
    bban = "".join(str(d) for d in rng.integers(0, 10, size=23))
    rearranged = bban + "152700"                  # F=15, R=27, puis « 00 »
    check = 98 - int(rearranged) % 97
    iban = f"FR{check:02d}{bban}"
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def make_nir(rng) -> str:
    """Numéro de sécurité sociale fictif, avec une clé valide (97 - n mod 97)."""
    body = (f"{rng.integers(1, 3)}{rng.integers(60, 100):02d}{rng.integers(1, 13):02d}"
            f"{rng.integers(1, 96):02d}{rng.integers(1, 1000):03d}{rng.integers(1, 1000):03d}")
    key = 97 - int(body) % 97
    return f"{body[0]} {body[1:3]} {body[3:5]} {body[5:7]} {body[7:10]} {body[10:13]} {key:02d}"


def _formatted_pii(client, rng) -> tuple[str, str, str]:
    kind = ["email", "telephone", "iban", "numero_securite_sociale"][rng.integers(4)]
    if kind == "email":
        value = client["email"]
        return f"Client joignable à {value} pour le suivi.", kind, value
    if kind == "telephone":
        value = client["telephone"] or make_phone(rng)
        return f"Rappeler au {value} après 18 h.", kind, value
    if kind == "iban":
        value = make_iban(rng)
        return f"IBAN communiqué pour le virement : {value}.", kind, value
    value = make_nir(rng)
    return f"N° de sécurité sociale indiqué par erreur : {value}.", kind, value


def _free_pii(client, rng) -> tuple[str, str, str]:
    choice = int(rng.integers(4))
    if choice == 0:
        value = client["nom"]
        return f"Rappeler Mme {value} chez elle en fin de journée.", "nom_personne", value
    if choice == 1:
        value = f"{client['prenom']} {client['nom']}"
        return f"{value} a appelé deux fois ce matin.", "nom_personne", value
    if choice == 2:
        value = f"{rng.integers(1, 120)} rue des {rng.choice(['Lilas', 'Tilleuls', 'Acacias'])}"
        return f"Livrer chez la voisine au {value}.", "adresse", value
    value = str(rng.choice(FIRST_NAMES))
    return f"Sa fille {value} passera récupérer le colis.", "nom_personne", value


def generate_tickets(tx: pd.DataFrame, clients: pd.DataFrame, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_id = clients.set_index("client_id")
    sales = tx[(tx["type_transaction"] == "vente") & tx["client_id"].notna()]
    refunds = tx[tx["type_transaction"] == "remboursement"]

    picked = sales.sample(frac=C.TICKET_RATE, random_state=int(rng.integers(1e9)))
    jobs = [(row, str(rng.choice(MOTIFS, p=MOTIF_WEIGHTS)),
             row["date_transaction"] + timedelta(days=int(rng.integers(1, 21))), row)
            for _, row in picked.iterrows()]
    # 70 % des remboursements font suite à un ticket, qui cite la vente d'origine.
    for _, ref in refunds[rng.random(len(refunds)) < 0.7].iterrows():
        origin = tx.loc[tx["_row"] == ref["_vente_origine"]]
        cited = origin.iloc[0] if len(origin) else ref
        jobs.append((ref, "remboursement", ref["date_transaction"] - timedelta(days=int(rng.integers(0, 3))),
                     cited))

    tickets, truth = [], []
    for k, (row, motif, when, cited) in enumerate(sorted(jobs, key=lambda j: j[2])):
        client = by_id.loc[row["client_id"]]
        text = str(rng.choice(TEMPLATES[motif])).format(
            n=rng.integers(2, 15), txn=cited["transaction_id"])
        found = []
        u = rng.random()
        if u < C.PII_FORMATTED_RATE:
            found.append(("formatee",) + _formatted_pii(client, rng))
        elif u < C.PII_FORMATTED_RATE + C.PII_FREE_RATE:
            found.append(("libre",) + _free_pii(client, rng))
        sentences = [text] + [f[1] for f in found]
        trap = rng.random() < C.TRAP_RATE
        if trap:
            sentences.append(str(rng.choice(TRAPS)).format(
                txn=cited["transaction_id"], n=rng.integers(2, 6),
                ville=rng.choice(C.COUNTRIES["FR"][2]), montant=f"{abs(cited['montant'] or 0):.2f}"
                .replace(".", ",")))
        ticket_id = f"TCK-{k + 1:08d}"
        tickets.append({
            "ticket_id": ticket_id, "client_id": row["client_id"],
            "transaction_id": cited["transaction_id"] if motif in ("remboursement", "retour",
                                                                   "produit_defectueux", "livraison") else None,
            "date_ticket": when, "motif": motif,
            "commentaire": " ".join(sentences) if rng.random() > 0.03 else None,
        })
        if tickets[-1]["commentaire"] is None:   # commentaire vide : rien à détecter
            found, trap = [], False
        truth.append({
            "ticket_id": ticket_id, "contient_pii": bool(found),
            "forme": found[0][0] if found else "aucune",
            "types_pii": "|".join(f[2] for f in found), "valeurs_pii": "|".join(f[3] for f in found),
            "piege": trap,
        })
    return pd.DataFrame(tickets), pd.DataFrame(truth)
