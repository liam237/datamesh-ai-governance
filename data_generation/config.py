"""Paramètres du monde simulé.

Tous les chiffres « réalistes » du générateur sont réunis ici, pour qu'on puisse
les lire, les discuter et les justifier au même endroit. Ce sont des hypothèses
de simulation, pas des statistiques réelles.
"""

from dataclasses import dataclass, field
from datetime import date

SEED = 42            # jeu de CONCEPTION : exploration, choix des variables, réglages
TEST_SEED = 2026     # jeu de DÉVELOPPEMENT (ex-« test ») : déjà vu à l'étape 5a
EXAM_SEED = 2027     # jeu d'EXAMEN : sous scellé, une seule exécution à la fin (étape 5b)

# --- Taille du monde -------------------------------------------------------
N_CLIENTS = 3_000
START = date(2025, 1, 1)
END = date(2025, 12, 31)          # une année complète : soldes, Black Friday, Noël
MEAN_PURCHASES_PER_CLIENT = 10    # moyenne annuelle (loi log-normale autour)

# --- Géographie : pays, poids, devise, villes ------------------------------
COUNTRIES = {
    # code: (poids, devise, villes)
    "FR": (0.60, "EUR", ["Paris", "Lyon", "Marseille", "Toulouse", "Lille", "Nantes",
                         "Bordeaux", "Orléans", "Tours", "Rennes", "Strasbourg", "Nice"]),
    "BE": (0.12, "EUR", ["Bruxelles", "Liège", "Namur", "Charleroi", "Anvers"]),
    "CH": (0.10, "CHF", ["Genève", "Lausanne", "Zurich", "Berne", "Neuchâtel"]),
    "DE": (0.10, "EUR", ["Berlin", "Munich", "Hambourg", "Cologne", "Francfort"]),
    "ES": (0.08, "EUR", ["Madrid", "Barcelone", "Valence", "Séville", "Bilbao"]),
}
EUR_TO_CHF = 0.94                 # taux fixe, approximation 2025

# --- Segments de clientèle -------------------------------------------------
SEGMENTS = {
    # nom: (poids, multiplicateur de fréquence d'achat, quantité moyenne)
    "Particulier": (0.80, 1.0, 1.2),
    "Premium": (0.08, 2.0, 1.5),
    "Professionnel": (0.12, 1.5, 15.0),
}

CHANNELS = ["Web", "Mobile", "Magasin"]
CHANNEL_WEIGHTS = [0.50, 0.30, 0.20]
STORE_OPENING_HOURS = range(9, 20)  # un magasin est ouvert de 9 h à 19 h 59


@dataclass(frozen=True)
class Category:
    name: str
    median_unit_price_eur: float   # prix unitaire médian
    price_sigma: float             # dispersion log-normale des prix
    refund_rate: float             # part des ventes remboursées


CATEGORIES = [
    Category("Électronique", 180.0, 0.70, 0.05),
    Category("Mode", 45.0, 0.55, 0.12),
    Category("Maison", 70.0, 0.60, 0.05),
    Category("Sport", 55.0, 0.55, 0.06),
    Category("Alimentation", 25.0, 0.45, 0.01),
]


@dataclass(frozen=True)
class Period:
    name: str
    start: date
    end: date
    volume_factor: float           # multiplicateur du nombre d'achats
    price_factor: float            # multiplicateur des prix (remises)


# Dates approximatives des temps forts du commerce en 2025.
PERIODS = [
    Period("soldes_hiver", date(2025, 1, 8), date(2025, 2, 4), 1.6, 0.75),
    Period("soldes_ete", date(2025, 6, 25), date(2025, 7, 22), 1.6, 0.75),
    Period("black_friday", date(2025, 11, 24), date(2025, 12, 1), 2.2, 0.80),
    Period("noel", date(2025, 12, 2), date(2025, 12, 24), 1.8, 1.00),
]
WEEKEND_FACTOR = 1.2


@dataclass(frozen=True)
class AnomalyRates:
    """Part des transactions touchées par chaque famille d'anomalies."""

    # Erreurs classiques : une règle simple tirée du contrat les attrape.
    montant_nul_ou_negatif: float = 0.003
    devise_incoherente: float = 0.003
    valeur_hors_referentiel: float = 0.002
    valeur_manquante: float = 0.003
    doublon_exact: float = 0.004
    # Anomalies subtiles : aucune règle du contrat ne les attrape.
    pic_client: float = 0.003
    prix_unitaire_aberrant: float = 0.003
    magasin_hors_horaires: float = 0.002
    doublon_approche: float = 0.002


ANOMALY_RATES = AnomalyRates()

# Famille « inconnue », injectée UNIQUEMENT dans le jeu de test. Elle a été
# conçue après le choix des variables (notebook 02), et aucune variable n'a été
# pensée pour elle : elle sert à vérifier si le système généralise au-delà de
# ce qu'on lui a appris à chercher (parade contre la circularité).
# Rafale d'achats : 4 achats en moins de 30 minutes, dans 4 catégories
# différentes, à des montants banals (schéma typique d'une carte volée).
UNKNOWN_BURST_RATE = 0.002       # part des ventes concernées
UNKNOWN_BURST_SIZE = 4
UNKNOWN_BURST_WINDOW_MIN = 30

# Dérive : un bug de prix fait monter de 12 % tous les prix d'une catégorie,
# en France, pendant trois semaines. Invisible ligne à ligne : c'est le
# mécanisme 2 (dérives) qui doit la repérer, pas le mécanisme 1.
PRICE_BUG = {"categorie": "Maison", "pays": "FR", "start": date(2025, 9, 8),
             "end": date(2025, 9, 28), "factor": 1.12}

# --- Service client -------------------------------------------------------
TICKET_RATE = 0.08                 # tickets ouverts par transaction de vente
N_CLIENT_DUPLICATES = 60           # clients saisis deux fois
N_FORCED_HOMONYMS = 40             # paires de personnes différentes au même nom
PII_FORMATTED_RATE = 0.07          # e-mail, téléphone, IBAN, n° de sécurité sociale
PII_FREE_RATE = 0.05               # nom ou adresse sans format reconnaissable
TRAP_RATE = 0.10                   # textes qui ressemblent à de la PII sans en être


@dataclass(frozen=True)
class Paths:
    root: str = "data"
    test_root: str = "data_test"
    exam_root: str = "data_exam"
    ventes: str = "data/ventes"
    service_client: str = "data/service_client"
    ground_truth: str = "data/ground_truth"
    extra: dict = field(default_factory=dict)


PATHS = Paths()
