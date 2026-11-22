"""Domaine Ventes : génération des transactions « normales ».

Normales ne veut pas dire banales : on y trouve des remboursements (montants
négatifs légitimes), de grosses commandes de professionnels et des pics de
soldes. Ce sont des cas inhabituels mais corrects, que le système ne doit PAS
signaler.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import config as C

CAT_BY_NAME = {c.name: c for c in C.CATEGORIES}
CAT_NAMES = [c.name for c in C.CATEGORIES]

# Répartition horaire des achats en ligne : creux la nuit, pic le soir.
WEB_HOUR_WEIGHTS = np.array([0.4, 0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.2, 2.4,
                             2.8, 2.6, 2.2, 2.0, 2.0, 2.4, 3.0, 3.6, 4.0, 3.6, 2.4, 1.2])
STORE_HOURS = np.array(list(C.STORE_OPENING_HOURS))
STORE_HOUR_WEIGHTS = np.array([1.0, 1.4, 1.8, 2.0, 1.6, 1.6, 1.8, 2.0, 2.2, 2.0, 1.4])


def _draw_hour(channel: str, rng: np.random.Generator) -> int:
    if channel == "Magasin":
        return int(rng.choice(STORE_HOURS, p=STORE_HOUR_WEIGHTS / STORE_HOUR_WEIGHTS.sum()))
    return int(rng.choice(24, p=WEB_HOUR_WEIGHTS / WEB_HOUR_WEIGHTS.sum()))


def _draw_quantity(segment: str, rng: np.random.Generator) -> int:
    mean_qty = C.SEGMENTS[segment][2]
    if segment == "Professionnel":
        return int(max(1, round(rng.lognormal(np.log(mean_qty), 0.6))))
    return int(1 + rng.poisson(mean_qty - 1))


def generate_sales(clients: pd.DataFrame, calendar: pd.DataFrame,
                   rng: np.random.Generator) -> pd.DataFrame:
    """Génère les ventes, puis les remboursements qui en découlent."""
    day_p = calendar["facteur_volume"].to_numpy()
    day_p = day_p / day_p.sum()
    days = calendar["jour"].to_numpy()
    price_factor = dict(zip(calendar["jour"], calendar["facteur_prix"]))
    period = dict(zip(calendar["jour"], calendar["periode"]))
    pref_cols = [f"pref_{c}" for c in CAT_NAMES]

    rows = []
    for client in clients.itertuples(index=False):
        n_purchases = rng.poisson(client.activite_annuelle)
        if n_purchases == 0:
            continue
        prefs = np.array([getattr(client, col) for col in pref_cols])
        prefs = prefs / prefs.sum()
        currency = C.COUNTRIES[client.pays][1]
        for day_idx in rng.choice(len(days), size=n_purchases, p=day_p):
            day = days[day_idx]
            cat = CAT_BY_NAME[CAT_NAMES[rng.choice(len(CAT_NAMES), p=prefs)]]
            channel = client.canal_prefere if rng.random() < 0.7 else \
                C.CHANNELS[rng.choice(3, p=C.CHANNEL_WEIGHTS)]
            qty = _draw_quantity(client.segment, rng)
            unit_price = (cat.median_unit_price_eur * rng.lognormal(0.0, cat.price_sigma)
                          * client.multiplicateur_panier * price_factor[day])
            amount = unit_price * qty
            if currency == "CHF":
                amount *= C.EUR_TO_CHF
            ts = datetime(day.year, day.month, day.day, _draw_hour(channel, rng),
                          int(rng.integers(60)), int(rng.integers(60)))
            rows.append({
                "date_transaction": ts, "client_id": client.client_id,
                "type_transaction": "vente", "categorie": cat.name,
                "montant": round(max(amount, 0.5), 2), "quantite": qty,
                "pays": client.pays, "devise": currency, "segment": client.segment,
                "canal": channel, "_periode": period[day],
            })

    sales = pd.DataFrame(rows)
    sales["_vente_origine"] = pd.NA
    sales = _apply_price_bug(sales)
    refunds = _generate_refunds(sales, rng)
    return pd.concat([sales, refunds], ignore_index=True)


def _apply_price_bug(sales: pd.DataFrame) -> pd.DataFrame:
    """Dérive : +12 % sur une catégorie, dans un pays, pendant trois semaines."""
    bug = C.PRICE_BUG
    d = sales["date_transaction"].dt.date
    mask = ((sales["categorie"] == bug["categorie"]) & (sales["pays"] == bug["pays"])
            & (d >= bug["start"]) & (d <= bug["end"]))
    sales.loc[mask, "montant"] = (sales.loc[mask, "montant"] * bug["factor"]).round(2)
    sales["_derive_prix"] = mask
    return sales


def _generate_refunds(sales: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Un remboursement reprend la vente d'origine, avec un montant négatif."""
    rate = sales["categorie"].map(lambda c: CAT_BY_NAME[c].refund_rate).to_numpy()
    picked = sales[rng.random(len(sales)) < rate]
    refunds = []
    for idx, sale in picked.iterrows():
        day = (sale["date_transaction"] + timedelta(days=int(rng.integers(2, 31)))).date()
        when = datetime(day.year, day.month, day.day, _draw_hour(sale["canal"], rng),
                        int(rng.integers(60)), int(rng.integers(60)))
        if day > C.END:
            continue
        full = rng.random() < 0.85
        share = 1.0 if full else rng.uniform(0.3, 0.7)
        qty = sale["quantite"] if full else max(1, int(round(sale["quantite"] * share)))
        refund = sale.copy()
        refund["date_transaction"] = when
        refund["type_transaction"] = "remboursement"
        refund["montant"] = -round(sale["montant"] * share, 2)
        refund["quantite"] = qty
        refund["_vente_origine"] = idx
        refund["_derive_prix"] = False
        refunds.append(refund)
    return pd.DataFrame(refunds)
