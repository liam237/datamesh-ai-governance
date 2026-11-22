"""Mécanisme 1 : EXAMEN UNIQUE sur le jeu 2027 (étape 5b).

Usage : `python -m evaluation.final_exam_mechanism1`

Cette commande ne fait PAS partie du pipeline automatique (`make all`) ni des
tests : l'examen ne doit être ouvert qu'une fois. Elle :
1. lit les réglages figés dans results/metrics/mechanism1_design.json ;
2. refuse de s'exécuter si l'examen a déjà eu lieu (results/metrics/mechanism1_exam.json) ;
3. rejoue l'année 2027 avec le Data Steward simulé et écrit les résultats, plus
   les figures 13 et 14.

Critère principal annoncé avant l'examen (journal de bord) : le coût, avec une
anomalie manquée à 10 lignes examinées (règle 1-10-100). Critères secondaires :
F1 et F2, plus le seuil de rentabilité.
"""

import json
import sys

import pandas as pd

from evaluation.data import ROOT
from evaluation.simulate_steward import report, simulate
from mechanisms.arrival.steward_loop import Settings

OUT = ROOT / "results" / "metrics"
DESIGN, EXAM = OUT / "mechanism1_design.json", OUT / "mechanism1_exam.json"


def figures(rep: dict, title_suffix: str, folder: str = "anomalies", prefix: str = "") -> list:
    import matplotlib.pyplot as plt
    import numpy as np
    from notebooks import viz

    viz.setup()
    m = pd.DataFrame(rep["mois_par_mois"])
    x = np.arange(len(m))
    mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
    labels = [mois[pd.Period(v).month - 1] for v in m["mois"]]
    paths = []

    # Figure 13 : courbe d'apprentissage, rappel mois par mois.
    fig, ax = plt.subplots()
    ax.plot(x, m["expert_rappel"], color=viz.PALETTE[1], marker="o", ms=4)
    ax.plot(x, m["systeme_rappel"], color=viz.PALETTE[0], marker="o", ms=4)
    ax.text(x[-1] + 0.15, m["expert_rappel"].iloc[-1], "Expert seul", color=viz.INK_2, va="center")
    ax.text(x[-1] + 0.15, m["systeme_rappel"].iloc[-1], "Expert + boucle", color=viz.INK_2, va="center")
    ax.set_xticks(x, labels); ax.set_xlim(-0.3, len(m) + 1.6); ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("part des anomalies du mois trouvées")
    ax.set_title(f"Courbe d'apprentissage : rappel mois par mois {title_suffix}")
    paths.append(viz.save(fig, f"{prefix}13_courbe_apprentissage", folder)); plt.close(fig)

    # Figure 14 : coût cumulé (1 par ligne examinée, 10 par anomalie manquée).
    fig, ax = plt.subplots()
    ce, cs = m["expert_cout"].cumsum(), m["systeme_cout"].cumsum()
    ax.plot(x, ce, color=viz.PALETTE[1], marker="o", ms=4)
    ax.plot(x, cs, color=viz.PALETTE[0], marker="o", ms=4)
    ax.text(x[-1] + 0.15, ce.iloc[-1], f"Expert seul : {ce.iloc[-1]:,.0f}".replace(",", " "), color=viz.INK_2, va="center")
    ax.text(x[-1] + 0.15, cs.iloc[-1], f"Expert + boucle : {cs.iloc[-1]:,.0f}".replace(",", " "), color=viz.INK_2, va="center")
    ax.set_xticks(x, labels); ax.set_xlim(-0.3, len(m) + 2.6); ax.set_ylim(0, None)
    ax.set_ylabel("coût cumulé : 1 par ligne examinée,\n10 par anomalie manquée")
    ax.set_title(f"Coût cumulé pour la Finance {title_suffix}")
    paths.append(viz.save(fig, f"{prefix}14_cout_cumule", folder)); plt.close(fig)
    return paths


def main() -> int:
    if EXAM.exists() and "--force" not in sys.argv:
        print(f"L'examen a déjà eu lieu ({EXAM.relative_to(ROOT)}). Il ne se repasse pas.")
        return 1
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    settings = Settings(**design["reglages_figes"])
    rep = report(simulate("examen", settings))
    rep["reglages"] = design["reglages_figes"]
    EXAM.write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    figures(rep, "(jeu d'examen 2027)")
    from evaluation.simulate_steward import to_markdown
    md = to_markdown({"reglages_figes": design["reglages_figes"], "choix_filet": design["choix_filet"],
                      "choix_supervise": design["choix_supervise"], "conception": design["conception"],
                      "developpement": rep}).replace("Jeu de développement (vérification)", "Jeu d'EXAMEN 2027")
    (OUT / "mechanism1_exam.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
