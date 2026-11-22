"""Mécanisme 1 : comparaison des méthodes de détection d'anomalies.

Usage : `python -m evaluation.compare_anomaly_models` (appelé aussi par `make all`).

Applique le protocole fixé AVANT les résultats (journal de bord, « Protocole du
mécanisme 1 ») :
1. 10 découpages 70 / 30 stratifiés du jeu de conception, communs à toutes les méthodes ;
2. mesures sur les 30 % : AUC-PR (critère principal), AUC-ROC, rappel au budget,
   rappel sur ce que l'expert rate ;
3. choix du gagnant parmi les non supervisées, Wilcoxon contre la deuxième ;
4. examen unique sur le jeu de test, seuils figés sur le jeu de conception.

Écrit results/metrics/anomaly_models.json et .md, et deux figures dans
results/figures/anomalies/.
"""

import json

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit

from baselines.rules import run as run_baseline
from evaluation.data import ROOT, load_published, load_truth
from evaluation.metrics import false_alerts_by_status, recall_by_family, scores
from mechanisms.arrival import anomaly_detection as AD
from mechanisms.arrival.features import build_features

N_SPLITS, TEST_SIZE = 10, 0.30
BUDGET = 0.01                                   # 1 % des ventes examinées en plus par le Data Steward
BUDGETS = [0.0025, 0.005, 0.01, 0.02, 0.05]     # sensibilité : ce budget est une hypothèse
ALPHA = 0.05
OUT = ROOT / "results" / "metrics"


def _load(dataset: str):
    tx, clients = load_published(dataset)
    truth = load_truth(dataset)
    X = build_features(tx)[AD.MODEL_FEATURES]
    expert = run_baseline("expert", tx, clients)["quarantaine"]
    return tx, truth, X, expert


def _top_k(scores_: np.ndarray, eligible: np.ndarray, k: int) -> np.ndarray:
    """Les k ventes les plus suspectes parmi celles que l'expert n'a pas déjà mises en quarantaine."""
    s = np.where(eligible, scores_, -np.inf)
    out = np.zeros(len(s), dtype=bool)
    if k > 0:
        out[np.argsort(-s, kind="stable")[:k]] = True
    return out & eligible


def _complement_threshold(scores_: np.ndarray, eligible: np.ndarray, budget: float) -> float:
    """Score minimal des alertes en plus de l'expert, pour un budget donné (part de toutes les ventes)."""
    k = int(round(budget * len(scores_)))
    s = np.sort(scores_[eligible])[::-1]
    return float(s[min(k, len(s)) - 1]) if k else float("inf")


def _fit(name, seed, X, y):
    model = AD.make(name, seed)
    return model.fit(X, y) if AD.is_supervised(name) else model.fit(X)


def cross_validate(X: pd.DataFrame, y: pd.Series, expert: pd.Series) -> dict:
    """Étapes 2 à 5 du protocole, sur le jeu de conception."""
    splitter = StratifiedShuffleSplit(n_splits=N_SPLITS, test_size=TEST_SIZE, random_state=0)
    names = [*AD.UNSUPERVISED, *AD.SUPERVISED]
    rows = []
    for split, (tr, ho) in enumerate(splitter.split(X, y)):
        Xtr, Xho, ytr, yho = X.iloc[tr], X.iloc[ho], y.iloc[tr].to_numpy(), y.iloc[ho].to_numpy()
        eligible = ~expert.reindex(X.index[ho]).fillna(False).to_numpy(bool)
        missed = yho & eligible                      # anomalies que l'expert laisse passer
        for name in names:
            s = _fit(name, split, Xtr, ytr).score(Xho)
            k = int(round(BUDGET * len(s)))
            top = np.zeros(len(s), dtype=bool)
            top[np.argsort(-s, kind="stable")[:k]] = True
            comp = _top_k(s, eligible, k)
            row = {"methode": name, "decoupage": split,
                   "auc_pr": average_precision_score(yho, s), "auc_roc": roc_auc_score(yho, s),
                   "rappel_budget": float(top[yho].mean()),
                   "rappel_complement": float(comp[missed].mean()),
                   "precision_complement": float(yho[comp].mean()) if comp.any() else 0.0}
            for b in BUDGETS:
                row[f"rappel_complement_{b}"] = float(_top_k(s, eligible, int(round(b * len(s))))[missed].mean())
            rows.append(row)
    return {"tableau": pd.DataFrame(rows)}


def choose(cv: pd.DataFrame) -> dict:
    """Étape 6 : règle de choix fixée à l'avance."""
    unsup = list(AD.UNSUPERVISED)
    med = cv[cv["methode"].isin(unsup)].groupby("methode")["auc_pr"].median().sort_values(ascending=False)
    first, second = med.index[0], med.index[1]
    a = cv[cv["methode"] == first].sort_values("decoupage")["auc_pr"].to_numpy()
    b = cv[cv["methode"] == second].sort_values("decoupage")["auc_pr"].to_numpy()
    p = float(wilcoxon(a, b).pvalue)
    winner = first if p < ALPHA else min(first, second, key=unsup.index)
    return {"classement_auc_pr_mediane": {k: round(float(v), 4) for k, v in med.items()},
            "premier": first, "deuxieme": second, "wilcoxon_p": round(p, 4),
            "ecart_significatif": p < ALPHA, "gagnant": winner}


def examine(Xc, yc, expert_c, Xt, truth_t, tx_t, expert_t, winner) -> dict:
    """Étapes 8 et 10 : réentraînement sur tout le jeu de conception, seuil fixé sur ce
    même jeu avec CE modèle, puis note unique sur le jeu de test avec ce seuil inchangé.

    Pour les supervisés, le seuil est calculé sur des ventes que le modèle a vues
    à l'apprentissage : il est donc un peu optimiste (limite signalée).
    """
    eligible_c = ~expert_c.reindex(Xc.index).fillna(False).to_numpy(bool)
    seuils = {}
    yt = truth_t.loc[Xt.index, "est_anomalie"].to_numpy(bool)
    all_ids = pd.Index(tx_t["transaction_id"])
    t_all = truth_t.loc[all_ids]
    expert_all = expert_t.reindex(all_ids).fillna(False).astype(bool)
    out = {"expert_seul": {**scores(t_all["est_anomalie"], expert_all),
                           "rappel_par_famille": recall_by_family(t_all["famille"], t_all["est_anomalie"], expert_all)}}
    for name in [*AD.UNSUPERVISED, *AD.SUPERVISED]:
        model = _fit(name, 0, Xc, yc.to_numpy())
        seuils[name] = _complement_threshold(model.score(Xc), eligible_c, BUDGET)
        s = model.score(Xt)
        ia = pd.Series(s > seuils[name], index=Xt.index).reindex(all_ids).fillna(False)
        combo = expert_all | ia
        out[name] = {"auc_pr": round(float(average_precision_score(yt, s)), 4),
                     "auc_roc": round(float(roc_auc_score(yt, s)), 4),
                     "alertes_ia_en_plus": int((ia & ~expert_all).sum()),
                     "expert_plus_ia": {**scores(t_all["est_anomalie"], combo),
                                        "rappel_par_famille": recall_by_family(t_all["famille"], t_all["est_anomalie"], combo),
                                        "fausses_alertes_par_statut": false_alerts_by_status(t_all["statut"], t_all["est_anomalie"], combo)}}
    out["gagnant"] = winner
    out["seuils"] = seuils
    out["taux_anomalies_perimetre"] = round(float(yt.mean()), 4)
    return out


def to_markdown(res: dict) -> str:
    L = AD.LABELS
    cv = pd.DataFrame(res["validation_croisee"])
    agg = cv.groupby("methode").agg(
        auc_pr=("auc_pr", "median"), auc_pr_min=("auc_pr", "min"), auc_pr_max=("auc_pr", "max"),
        auc_roc=("auc_roc", "median"), rappel_budget=("rappel_budget", "median"),
        rappel_complement=("rappel_complement", "median"),
        precision_complement=("precision_complement", "median"))
    order = [*AD.UNSUPERVISED, *AD.SUPERVISED]
    c, t = res["choix"], res["examen_test"]
    lines = ["# Mécanisme 1 : comparaison des méthodes de détection", "",
             "Généré par `python -m evaluation.compare_anomaly_models`. Ne pas modifier à la main.", "",
             f"## Jeu de conception : {N_SPLITS} découpages 70 / 30 (médianes)", "",
             f"Hasard : AUC-PR = {res['taux_anomalies_conception']:.3f}, AUC-ROC = 0,5. "
             f"Budget : {BUDGET:.0%} des ventes examinées en plus de la quarantaine de l'expert.", "",
             "| Méthode | Type | AUC-PR (min – max) | AUC-ROC | Rappel au budget | Rappel sur ce que l'expert rate | Précision de ces alertes |",
             "|---|---|---|---|---|---|---|"]
    for n in order:
        r = agg.loc[n]
        kind = "supervisé (repère)" if AD.is_supervised(n) else "non supervisé"
        lines.append(f"| {L[n]} | {kind} | {r.auc_pr:.3f} ({r.auc_pr_min:.3f} – {r.auc_pr_max:.3f}) | {r.auc_roc:.3f} | "
                     f"{r.rappel_budget:.3f} | {r.rappel_complement:.3f} | {r.precision_complement:.3f} |")
    lines += ["", "## Choix (règle fixée à l'avance)", "",
              f"- Premier : {L[c['premier']]} ; deuxième : {L[c['deuxieme']]}.",
              f"- Wilcoxon apparié : p = {c['wilcoxon_p']:.4f} "
              f"({'écart significatif' if c['ecart_significatif'] else 'écart non significatif : on prend la plus simple'}).",
              f"- **Gagnant : {L[c['gagnant']]}.**", "",
              "## Examen unique sur le jeu de test", "",
              f"Hasard : AUC-PR = {t['taux_anomalies_perimetre']:.3f}.", "",
              "| Système | AUC-PR | AUC-ROC | Alertes IA en plus | Précision | Rappel | F1 |",
              "|---|---|---|---|---|---|---|"]
    e = t["expert_seul"]
    lines.append(f"| Expert seul | — | — | 0 | {e['precision']:.3f} | {e['rappel']:.3f} | {e['F1']:.3f} |")
    for n in order:
        r = t[n]; s = r["expert_plus_ia"]
        mark = " **(gagnant)**" if n == c["gagnant"] else ""
        lines.append(f"| Expert + {L[n]}{mark} | {r['auc_pr']:.3f} | {r['auc_roc']:.3f} | {r['alertes_ia_en_plus']} | "
                     f"{s['precision']:.3f} | {s['rappel']:.3f} | {s['F1']:.3f} |")
    fams = sorted(e["rappel_par_famille"])
    cols = ["expert_seul", c["gagnant"], *AD.SUPERVISED]
    heads = ["Expert seul"] + [f"Expert + {L[n]}" for n in cols[1:]]
    lines += ["", "## Rappel par famille sur le jeu de test", "",
              "| Famille | " + " | ".join(heads) + " |", "|---|" + "---|" * len(cols)]
    for f in fams:
        vals = [e["rappel_par_famille"][f]] + [t[n]["expert_plus_ia"]["rappel_par_famille"][f] for n in cols[1:]]
        lines.append(f"| {f} | " + " | ".join(f"{v:.2f}" for v in vals) + " |")
    return "\n".join(lines) + "\n"


def figures(res: dict) -> list:
    import matplotlib.pyplot as plt
    from notebooks import viz

    viz.setup()
    L = AD.LABELS
    cv = pd.DataFrame(res["validation_croisee"])
    order = [*AD.UNSUPERVISED, *AD.SUPERVISED]
    winner = res["choix"]["gagnant"]
    paths = []

    # Figure 11 : AUC-PR sur les 10 découpages, une boîte par méthode.
    fig, ax = plt.subplots(figsize=(10, 5.4))
    data = [cv[cv["methode"] == n]["auc_pr"].to_numpy() for n in order][::-1]
    labels = [L[n] + ("  (gagnant)" if n == winner else "") for n in order][::-1]
    colors = [viz.PALETTE[1] if AD.is_supervised(n) else viz.PALETTE[0] for n in order][::-1]
    bp = ax.boxplot(data, vert=False, widths=0.55, patch_artist=True, showfliers=True,
                    medianprops={"color": viz.INK, "linewidth": 2})
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col); patch.set_alpha(0.35); patch.set_edgecolor(col)
    for i, (d, col) in enumerate(zip(data, colors), start=1):
        ax.scatter(d, np.full(len(d), i) + np.linspace(-0.12, 0.12, len(d)), s=14, color=col, zorder=3)
    ax.set_yticks(range(1, len(order) + 1), labels)
    base = res["taux_anomalies_conception"]
    ax.axvline(base, color=viz.MUTED, linestyle="--", linewidth=1.2)
    ax.text(base, 0.45, f" hasard ({base:.3f})", color=viz.INK_2, fontsize=9, va="center")
    ax.set_xlim(0, 1); ax.set_ylim(0.2, len(order) + 0.5)
    ax.set_xlabel("AUC-PR sur les 30 % mis de côté (1 = parfait)")
    ax.set_title("Méthodes de détection : AUC-PR sur 10 découpages du jeu de conception")
    ax.text(0.99, 0.03, "bleu : non supervisé (candidats)   orange : supervisé (repères)",
            transform=ax.transAxes, ha="right", fontsize=9, color=viz.INK_2)
    paths.append(viz.save(fig, "11_comparaison_auc_pr", "anomalies")); plt.close(fig)

    # Figure 12 : ce qui distingue les systèmes sur le jeu de test. Les familles que
    # l'expert attrape déjà à 100 % sont omises : elles sont identiques partout.
    t = res["examen_test"]
    exp = t["expert_seul"]
    missed = [f for f, v in exp["rappel_par_famille"].items() if v < 0.5]
    rows = ["expert_seul", *order]
    row_labels = ["Expert seul"] + [f"Expert + {L[n]}" + (" (gagnant)" if n == winner else "") for n in order]
    cols = [f.replace("_", " ") for f in missed] + ["rappel\nglobal", "précision\nglobale"]

    def line(n):
        r = exp if n == "expert_seul" else t[n]["expert_plus_ia"]
        return [r["rappel_par_famille"][f] for f in missed] + [r["rappel"], r["precision"]]

    M = np.array([line(n) for n in rows])
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(rows) + 1.9))
    ax.imshow(M, cmap="Blues", vmin=0, vmax=1.25, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0%}", ha="center", va="center",
                    color="white" if M[i, j] > 0.7 else viz.INK, fontsize=10)
    ax.axvline(len(missed) - 0.5, color=viz.SURFACE, linewidth=6)
    for y in (0.5, len(AD.UNSUPERVISED) + 0.5):
        ax.axhline(y, color=viz.SURFACE, linewidth=6)
    ax.set_xticks(range(len(cols)), cols); ax.xaxis.tick_top(); ax.tick_params(length=0)
    ax.set_yticks(range(len(rows)), row_labels); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title("Jeu de test : les trois familles que l'expert rate, et le bilan global", pad=40)
    paths.append(viz.save(fig, "12_rappel_par_famille_test", "anomalies")); plt.close(fig)
    return paths


def evaluate() -> dict:
    tx_c, truth_c, Xc, expert_c = _load("conception")
    yc = truth_c.loc[Xc.index, "est_anomalie"].astype(bool)
    cv = cross_validate(Xc, yc, expert_c)
    choice = choose(cv["tableau"])
    tx_t, truth_t, Xt, expert_t = _load("test")
    exam = examine(Xc, yc, expert_c, Xt, truth_t, tx_t, expert_t, choice["gagnant"])
    return {"protocole": {"decoupages": N_SPLITS, "part_notee": TEST_SIZE, "budget": BUDGET,
                          "variables": AD.MODEL_FEATURES, "alpha": ALPHA},
            "taux_anomalies_conception": round(float(yc.mean()), 4),
            "validation_croisee": cv["tableau"].round(4).to_dict(orient="records"),
            "choix": choice, "examen_test": exam}


def main() -> int:
    res = evaluate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "anomaly_models.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float) + "\n",
                                             encoding="utf-8")
    md = to_markdown(res)
    (OUT / "anomaly_models.md").write_text(md, encoding="utf-8")
    figures(res)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
