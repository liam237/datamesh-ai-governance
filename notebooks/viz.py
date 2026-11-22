"""Style commun des graphiques du projet.

- Une figure = une image, enregistrée dans results/figures/<dossier>/.
- Palette catégorielle fixe, validée pour le daltonisme (ordre jamais modifié).
  Trois couleurs sont peu contrastées sur fond clair : chaque courbe est donc
  aussi étiquetée directement, pour ne jamais reposer sur la couleur seule.
"""

from pathlib import Path

import matplotlib.pyplot as plt

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "contracts").is_dir())

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
HIGHLIGHT = "#6250d6"     # mise en évidence d'un point particulier
PERIOD_FILL = "#eda100"   # bandes des temps forts commerciaux

CATEGORY_ORDER = ["Alimentation", "Mode", "Sport", "Maison", "Électronique"]
CATEGORY_COLOR = dict(zip(CATEGORY_ORDER, PALETTE))
CHANNEL_ORDER = ["Web", "Mobile", "Magasin"]
CHANNEL_COLOR = dict(zip(CHANNEL_ORDER, PALETTE))


def setup() -> None:
    plt.rcParams.update({
        "figure.figsize": (10, 5.2), "figure.dpi": 110, "savefig.dpi": 150,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "semibold",
        "axes.titlelocation": "left", "axes.labelcolor": INK_2, "text.color": INK,
        "axes.edgecolor": MUTED, "xtick.color": INK_2, "ytick.color": INK_2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "lines.linewidth": 2.0, "legend.frameon": False,
    })


def save(fig, name: str, folder: str = "exploration") -> Path:
    """Enregistre la figure dans results/figures/<folder>/<name>.png."""
    out = ROOT / "results" / "figures" / folder / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    return out.relative_to(ROOT)


def euros(ax, axis: str = "x") -> None:
    """Graduations en euros lisibles sur une échelle logarithmique."""
    ticks = [1, 10, 100, 1_000, 10_000]
    labels = ["1 €", "10 €", "100 €", "1 000 €", "10 000 €"]
    if axis == "x":
        ax.set_xscale("log"); ax.set_xticks(ticks, labels); ax.minorticks_off()
    else:
        ax.set_yscale("log"); ax.set_yticks(ticks, labels); ax.minorticks_off()
