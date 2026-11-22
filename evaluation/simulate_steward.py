"""Mécanisme 1 : simulation semaine par semaine du Data Steward (étape 5b).

Usage : `python -m evaluation.simulate_steward` (appelé aussi par `make all`).

Ce script RÈGLE le mécanisme sur le jeu de conception, puis le VÉRIFIE sur le
jeu de développement (graine 2026). Il ne touche jamais au jeu d'examen :
l'examen a sa propre commande, evaluation/final_exam_mechanism1.py.

Deux choix, fixés à l'avance dans le journal de bord :
1. le filet : la méthode non supervisée qui apporte le plus en plus de l'expert
   (rappel sur ce que l'expert rate, 10 découpages, Wilcoxon, sinon la plus simple) ;
2. le supervisé : HistGradientBoosting ou XGBoost, selon le F1 du système sur le
   dernier trimestre de la simulation de conception ; écart < 0,01 → HistGradientBoosting.

Le Data Steward est joué ici, dans evaluation/, car il connaît la vérité terrain.
Le mécanisme (mechanisms/arrival/steward_loop.py) ne la voit jamais.
"""

import json
from dataclasses import asdict
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from baselines.rules import run as run_baseline
from evaluation.compare_anomaly_models import ALPHA, cross_validate
from evaluation.data import ROOT, load_published, load_truth
from evaluation.metrics import recall_by_family, scores
from mechanisms.arrival import anomaly_detection as AD
from mechanisms.arrival.features import build_features, sales_scope
from mechanisms.arrival.steward_loop import Settings, StewardLoop

OUT = ROOT / "results" / "metrics"
LAST_QUARTER_START = "2025-10-01"
F1_TIE = 0.01


@lru_cache(maxsize=None)
def prepare(dataset: str):
    """Données d'un jeu, avec des variables calculées SANS regarder l'avenir.

    Pour les ventes de la semaine w, les variables sont calculées avec les seules
    ventes connues à la fin de la semaine w (médianes, habitudes des clients,
    rareté des heures…). C'est ce que verrait un système en production.
    """
    tx, clients = load_published(dataset)
    truth = load_truth(dataset)
    tx = tx.assign(semaine=tx["date_transaction"].dt.to_period("W-SUN"))
    scope_ids = set(sales_scope(tx)["transaction_id"])
    parts = []
    for week in sorted(tx["semaine"].unique()):
        known = tx[tx["date_transaction"] < week.end_time]
        ids = [i for i in tx.loc[tx["semaine"] == week, "transaction_id"] if i in scope_ids]
        parts.append(build_features(known.drop(columns="semaine")).loc[ids])
    X = pd.concat(parts)
    expert = run_baseline("expert", tx.drop(columns="semaine"), clients)["quarantaine"]
    week_of = tx.set_index("transaction_id")["semaine"]
    date_of = tx.set_index("transaction_id")["date_transaction"]
    return X, expert, week_of, date_of, truth


def simulate(dataset: str, settings: Settings) -> pd.DataFrame:
    """Rejoue l'année. Renvoie, pour chaque transaction, si elle a été examinée et par quelle couche."""
    X, expert, week_of, date_of, truth = prepare(dataset)
    loop = StewardLoop(settings)
    weeks = sorted(week_of.unique())
    x_week = pd.Series(week_of.loc[X.index].to_numpy(), index=X.index)
    confirmed = pd.Series(dtype=bool)
    layer = pd.Series("", index=week_of.index, dtype=object)
    for i, week in enumerate(weeks):
        if i % settings.retrain_every == 0:
            recent = x_week.isin(weeks[max(0, i - settings.net_window + 1): i + 1])
            loop.retrain_net(X[recent.to_numpy()])
            if i > 0:
                seen = x_week.isin(weeks[:i])
                loop.retrain_supervised(X[seen.to_numpy()], confirmed)
        ids = week_of.index[(week_of == week).to_numpy()]
        q = expert.reindex(ids).fillna(False)
        Xw = X.loc[X.index.intersection(ids)]
        proposed = loop.propose(Xw, q)
        layer.loc[q.index[q.to_numpy(bool)]] = "quarantaine"
        layer.loc[proposed["supervise"]] = "supervise"
        layer.loc[proposed["filet"]] = "filet"
        reviewed = layer.loc[ids][layer.loc[ids] != ""].index
        # Le Data Steward examine chaque ligne et dit si c'est une vraie anomalie.
        confirmed = pd.concat([confirmed, truth.loc[reviewed, "est_anomalie"].astype(bool)])
    t = truth.loc[week_of.index]
    return pd.DataFrame({"semaine": week_of, "date": date_of, "couche": layer,
                         "examinee": layer != "", "quarantaine_expert": expert.reindex(week_of.index).fillna(False),
                         "est_anomalie": t["est_anomalie"].astype(bool), "famille": t["famille"].fillna(""),
                         "statut": t["statut"]})


def _period(r: pd.DataFrame, alert: str) -> dict:
    return scores(r["est_anomalie"], r[alert])


def report(r: pd.DataFrame) -> dict:
    """Bilans de l'année, du dernier trimestre, et courbe mois par mois."""
    last = r[r["date"] >= LAST_QUARTER_START]
    months = r["date"].dt.to_period("M")
    labels = r[r["examinee"]].sort_values("date")
    monthly = []
    for m in sorted(months.unique()):
        rm = r[months == m]
        sysm, expm = _period(rm, "examinee"), _period(rm, "quarantaine_expert")
        upto = labels[labels["date"] < m.end_time]
        monthly.append({"mois": str(m), "systeme_rappel": sysm["rappel"], "systeme_precision": sysm["precision"],
                        "systeme_F1": sysm["F1"], "expert_rappel": expm["rappel"],
                        "expert_precision": expm["precision"], "expert_F1": expm["F1"],
                        "lignes_examinees_cumul": int(len(upto)),
                        "anomalies_confirmees_cumul": int(upto["est_anomalie"].sum())})
    first_better = next((m["mois"] for m in monthly if m["systeme_F1"] > m["expert_F1"]), None)
    fam = lambda d, col: recall_by_family(d["famille"], d["est_anomalie"], d[col])
    return {
        "annee": {"systeme": _period(r, "examinee"), "expert": _period(r, "quarantaine_expert"),
                  "rappel_par_famille_systeme": fam(r, "examinee"),
                  "rappel_par_famille_expert": fam(r, "quarantaine_expert")},
        "dernier_trimestre": {"systeme": _period(last, "examinee"), "expert": _period(last, "quarantaine_expert"),
                              "rappel_par_famille_systeme": fam(last, "examinee"),
                              "rappel_par_famille_expert": fam(last, "quarantaine_expert")},
        "alertes_par_couche": {k: int(v) for k, v in r.loc[r["examinee"], "couche"].value_counts().items()},
        "vraies_anomalies_par_couche": {k: int(v) for k, v in
                                        r.loc[r["examinee"] & r["est_anomalie"], "couche"].value_counts().items()},
        "premier_mois_ou_le_systeme_depasse_l_expert": first_better,
        "mois_par_mois": monthly,
    }


def choose_net(cv: pd.DataFrame) -> dict:
    """Choix 1 : le filet qui apporte le plus en plus de l'expert."""
    unsup = list(AD.UNSUPERVISED)
    sub = cv[cv["methode"].isin(unsup)]
    med = sub.groupby("methode")["rappel_complement"].median().sort_values(ascending=False)
    first, second = med.index[0], med.index[1]
    a = sub[sub["methode"] == first].sort_values("decoupage")["rappel_complement"].to_numpy()
    b = sub[sub["methode"] == second].sort_values("decoupage")["rappel_complement"].to_numpy()
    p = float(wilcoxon(a, b).pvalue) if np.any(a != b) else 1.0
    winner = first if p < ALPHA else min(first, second, key=unsup.index)
    return {"classement_rappel_complement_median": {k: round(float(v), 4) for k, v in med.items()},
            "premier": first, "deuxieme": second, "wilcoxon_p": round(p, 4), "gagnant": winner}


def design() -> dict:
    # Choix 1 : le filet, sur les 10 découpages du jeu de conception.
    X, expert, *_ , truth = prepare("conception")
    X_all = build_features(load_published("conception")[0])[AD.MODEL_FEATURES]
    y = truth.loc[X_all.index, "est_anomalie"].astype(bool)
    net = choose_net(cross_validate(X_all, y, expert)["tableau"])

    # Choix 2 : le supervisé, sur la simulation du jeu de conception.
    runs = {name: report(simulate("conception", Settings(supervised=name, net=net["gagnant"])))
            for name in AD.SUPERVISED}
    f1 = {n: runs[n]["dernier_trimestre"]["systeme"]["F1"] for n in runs}
    best = max(f1, key=f1.get)
    sup = best if f1[best] - f1["hist_gradient_boosting"] >= F1_TIE else "hist_gradient_boosting"
    settings = Settings(supervised=sup, net=net["gagnant"])

    # Vérification sur le jeu de développement (déjà vu à l'étape 5a).
    dev = report(simulate("test", settings))
    return {"reglages_figes": asdict(settings), "choix_filet": net,
            "choix_supervise": {"F1_dernier_trimestre_conception": f1, "gagnant": sup},
            "conception": runs[sup], "conception_autre_supervise": runs[[n for n in runs if n != sup][0]],
            "developpement": dev}


def to_markdown(res: dict) -> str:
    L = AD.LABELS
    s = res["reglages_figes"]
    lines = ["# Mécanisme 1 : réglage et vérification de la boucle avec le Data Steward", "",
             "Généré par `python -m evaluation.simulate_steward`. Ne pas modifier à la main.", "",
             "## Réglages figés pour l'examen", "",
             f"- Filet : **{L[s['net']]}** (rappel sur ce que l'expert rate, médianes : "
             + ", ".join(f"{L[k]} {v:.3f}" for k, v in res["choix_filet"]["classement_rappel_complement_median"].items())
             + f" ; Wilcoxon premier contre deuxième : p = {res['choix_filet']['wilcoxon_p']:.4f}).",
             f"- Supervisé : **{L[s['supervised']]}** (F1 du dernier trimestre, conception : "
             + ", ".join(f"{L[k]} {v:.3f}" for k, v in res["choix_supervise"]["F1_dernier_trimestre_conception"].items()) + ").",
             f"- Budget : {s['budget']:.0%} des ventes de la semaine, dont {s['net_share']:.0%} pour le filet ; "
             f"réentraînement toutes les {s['retrain_every']} semaines ; supervisé actif dès "
             f"{s['min_positives']} anomalies confirmées.", ""]
    for key, title in [("conception", "Jeu de conception (réglage)"), ("developpement", "Jeu de développement (vérification)")]:
        r = res[key]
        lines += [f"## {title}", "", "| Période | Système | Précision | Rappel | F1 | Lignes examinées |",
                  "|---|---|---|---|---|---|"]
        for per, lab in [("annee", "Année"), ("dernier_trimestre", "Dernier trimestre")]:
            for who, wl in [("expert", "Expert seul"), ("systeme", "Expert + boucle")]:
                m = r[per][who]
                lines.append(f"| {lab} | {wl} | {m['precision']:.3f} | {m['rappel']:.3f} | {m['F1']:.3f} | {m['alertes']} |")
        lines += ["", f"Premier mois où le système dépasse l'expert : {r['premier_mois_ou_le_systeme_depasse_l_expert']}.",
                  f"Alertes par couche : {r['alertes_par_couche']} ; vraies anomalies par couche : "
                  f"{r['vraies_anomalies_par_couche']}.", "",
                  "| Famille (dernier trimestre) | Expert seul | Expert + boucle |", "|---|---|---|"]
        fs, fe = r["dernier_trimestre"]["rappel_par_famille_systeme"], r["dernier_trimestre"]["rappel_par_famille_expert"]
        for f in sorted(fs):
            lines.append(f"| {f} | {fe.get(f, 0):.2f} | {fs[f]:.2f} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    res = design()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mechanism1_design.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float) + "\n",
                                                encoding="utf-8")
    md = to_markdown(res)
    (OUT / "mechanism1_design.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
