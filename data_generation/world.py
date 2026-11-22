"""Le monde « normal » : les clients avec leurs habitudes, et le calendrier.

Chaque client a des habitudes stables (pays, segment, catégories préférées,
panier habituel, canal préféré). Les transactions découlent de ces habitudes :
c'est ce qui rend l'inhabituel légitime naturel (un professionnel qui commande
beaucoup, un pic d'achats pendant les soldes) et l'anomalie détectable par
contraste avec l'historique du client.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config as C

FIRST_NAMES = [
    "Julie", "Thomas", "Camille", "Nicolas", "Léa", "Lucas", "Manon", "Hugo", "Chloé",
    "Louis", "Emma", "Antoine", "Sarah", "Maxime", "Inès", "Alexandre", "Laura", "Paul",
    "Hélène", "Julien", "Claire", "Mathieu", "Élodie", "Pierre", "Sophie", "Karim",
    "Amina", "Yanis", "Fatou", "Moussa", "Nadia", "Samuel", "Anaïs", "Kevin", "Marie",
    "Jean", "Lina", "Adam", "Zoé", "Théo", "Clara", "Victor", "Jade", "Raphaël",
    "Aïcha", "Mehdi", "Elsa", "Noah", "Lucie", "Gabriel", "Maëlle", "Arthur", "Rose",
    "Ibrahim", "Salomé", "Bastien", "Océane", "Florian", "Mélanie", "Cédric",
]
LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand",
    "Leroy", "Moreau", "Simon", "Laurent", "Lefèvre", "Michel", "Garcia", "David",
    "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "André", "Lefebvre",
    "Mercier", "Dupont", "Lambert", "Bonnet", "François", "Martinez", "Legrand",
    "Garnier", "Faure", "Rousseau", "Blanc", "Guérin", "Muller", "Henry", "Roussel",
    "Nicolas", "Perrin", "Morin", "Mathieu", "Clément", "Gauthier", "Dumont", "Lopez",
    "Fontaine", "Chevalier", "Robin", "Diallo", "Traoré", "Nguyen", "Benali", "Kamga",
    "Ngono", "Fernandes", "Schmidt", "Peeters", "Janssens", "Rossi", "Weber",
    "Haddad", "Mbappé", "Lemaire", "Barbier", "Brun", "Colin", "Arnaud", "Giraud",
]
EMAIL_DOMAINS = ["exemple.fr", "courriel-demo.fr", "mail-test.eu", "boite-fictive.com"]


def _ascii(text: str) -> str:
    table = str.maketrans("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ", "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return text.translate(table)


def make_email(first: str, last: str, rng: np.random.Generator) -> str:
    domain = EMAIL_DOMAINS[rng.integers(len(EMAIL_DOMAINS))]
    suffix = "" if rng.random() < 0.6 else str(rng.integers(1, 99))
    sep = "." if rng.random() < 0.7 else "_"
    return f"{_ascii(first).lower()}{sep}{_ascii(last).lower().replace(' ', '')}{suffix}@{domain}"


def make_phone(rng: np.random.Generator) -> str:
    digits = rng.integers(0, 10, size=8)
    prefix = "06" if rng.random() < 0.6 else "07"
    groups = [prefix] + ["".join(map(str, digits[i:i + 2])) for i in range(0, 8, 2)]
    return " ".join(groups)


def _unique(emails: list[str]) -> list[str]:
    """Une adresse e-mail n'appartient qu'à une personne : on numérote les collisions."""
    seen: dict[str, int] = {}
    out = []
    for e in emails:
        local, domain = e.split("@")
        n = seen.get(e, 0)
        seen[e] = n + 1
        out.append(e if n == 0 else f"{local}.{n + 1}@{domain}")
    return out


def generate_clients(rng: np.random.Generator) -> pd.DataFrame:
    """Référentiel interne du Service client : personnes réelles du monde simulé.

    Contient des données personnelles (nom, e-mail, téléphone) : il reste dans le
    domaine Service client et n'est jamais publié tel quel à la Finance.
    """
    n = C.N_CLIENTS
    countries = list(C.COUNTRIES)
    country_w = np.array([C.COUNTRIES[c][0] for c in countries])
    segments = list(C.SEGMENTS)
    segment_w = np.array([C.SEGMENTS[s][0] for s in segments])
    cat_names = [c.name for c in C.CATEGORIES]

    pays = rng.choice(countries, size=n, p=country_w / country_w.sum())
    segment = rng.choice(segments, size=n, p=segment_w / segment_w.sum())
    # Chaque personne reçoit une combinaison prénom + nom distincte (tirage sans
    # remise parmi toutes les combinaisons possibles) : les homonymes ne viennent
    # donc que de l'étape suivante, en nombre contrôlé.
    combos = rng.choice(len(FIRST_NAMES) * len(LAST_NAMES), size=n, replace=False)
    first = np.array(FIRST_NAMES, dtype=object)[combos // len(LAST_NAMES)]
    last = np.array(LAST_NAMES, dtype=object)[combos % len(LAST_NAMES)]

    # Homonymes : deux personnes DIFFÉRENTES qui portent le même nom (par
    # exemple deux « Julie Martin » dans deux villes différentes).
    donors = rng.choice(n, size=C.N_FORCED_HOMONYMS, replace=False)
    takers = rng.choice(np.setdiff1d(np.arange(n), donors), size=C.N_FORCED_HOMONYMS,
                        replace=False)
    first[takers] = first[donors]
    last[takers] = last[donors]

    ville = np.array([C.COUNTRIES[p][2][rng.integers(len(C.COUNTRIES[p][2]))] for p in pays])
    creation_offsets = rng.integers(0, 6 * 365, size=n)
    date_creation = [C.START - timedelta(days=int(d)) for d in creation_offsets]

    # Habitudes : fréquence d'achat, catégories préférées, panier, canal.
    freq_mult = np.array([C.SEGMENTS[s][1] for s in segment])
    activity = rng.lognormal(mean=np.log(C.MEAN_PURCHASES_PER_CLIENT) - 0.32, sigma=0.8,
                             size=n) * freq_mult
    cat_prefs = rng.dirichlet(alpha=np.full(len(cat_names), 0.6), size=n)
    basket = rng.lognormal(mean=0.0, sigma=0.35, size=n)  # client plutôt dépensier ou non
    channel = rng.choice(C.CHANNELS, size=n, p=C.CHANNEL_WEIGHTS)

    clients = pd.DataFrame({
        "client_id": [f"CLT-{i + 1:06d}" for i in range(n)],
        "prenom": first,
        "nom": last,
        "email": _unique([make_email(f, l, rng) for f, l in zip(first, last)]),
        "telephone": [make_phone(rng) for _ in range(n)],
        "ville": ville,
        "pays": pays,
        "segment": segment,
        "date_creation": date_creation,
        "canal_prefere": channel,
        "activite_annuelle": activity.round(2),
        "multiplicateur_panier": basket.round(3),
    })
    for j, cat in enumerate(cat_names):
        clients[f"pref_{cat}"] = cat_prefs[:, j].round(4)
    return clients


def daily_calendar() -> pd.DataFrame:
    """Un jour par ligne, avec son facteur de volume et son facteur de prix."""
    days = pd.date_range(C.START, C.END, freq="D")
    cal = pd.DataFrame({"jour": days.date})
    cal["periode"] = "normale"
    cal["facteur_volume"] = 1.0
    cal["facteur_prix"] = 1.0
    for p in C.PERIODS:
        mask = (cal["jour"] >= p.start) & (cal["jour"] <= p.end)
        cal.loc[mask, "periode"] = p.name
        cal.loc[mask, "facteur_volume"] = p.volume_factor
        cal.loc[mask, "facteur_prix"] = p.price_factor
    weekend = pd.to_datetime(cal["jour"]).dt.dayofweek >= 5
    cal.loc[weekend, "facteur_volume"] *= C.WEEKEND_FACTOR
    return cal


def is_in(day: date, start: date, end: date) -> bool:
    return start <= day <= end
