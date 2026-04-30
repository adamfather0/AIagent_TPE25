"""03_correlation.py — Pearson and Spearman correlation matrices for 2025 TPE.

Computes pairwise correlations among all numeric measurement columns and
saves hierarchically-clustered heatmaps (Pearson and Spearman) plus the
raw CSV matrices.

Outputs
-------
outputs/figures/corr_pearson.png
outputs/figures/corr_spearman.png
outputs/tables/corr_pearson.csv
outputs/tables/corr_spearman.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform

np.random.seed(2025)

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────
df = pd.read_pickle(PKL)["data"]

ID_COLS = ["Treatment", "Rep", "Soil", "Biochar", "Fertilizer"]
num_cols = [c for c in df.columns if c not in ID_COLS]
data = df[num_cols].apply(pd.to_numeric, errors="coerce")

# ── helper: clustered heatmap ──────────────────────────────────────────────

def _clustered_heatmap(corr: pd.DataFrame, method: str, out_png: Path) -> None:
    # Reorder rows/columns by hierarchical clustering on the distance matrix.
    dist_arr = (1 - corr.abs().values).copy()
    np.fill_diagonal(dist_arr, 0)
    dist_arr = (dist_arr + dist_arr.T) / 2
    dist = pd.DataFrame(dist_arr, index=corr.index, columns=corr.columns)
    condensed = squareform(dist.values.clip(0))
    linkage   = hierarchy.linkage(condensed, method="average")
    order     = hierarchy.leaves_list(linkage)
    corr_ord  = corr.iloc[order, order]

    n = len(corr_ord)
    fig_size = max(10, n * 0.38)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.9))
    mask = np.zeros_like(corr_ord, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True  # show lower triangle only
    sns.heatmap(
        corr_ord, mask=mask, cmap="RdBu_r", center=0,
        vmin=-1, vmax=1, linewidths=0.3, linecolor="white",
        annot=(n <= 20), fmt=".2f", annot_kws={"size": 7},
        ax=ax, cbar_kws={"shrink": 0.6}
    )
    ax.set_title(f"{method.capitalize()} correlation (hierarchical order)", pad=10)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {out_png}")


# ── compute and save ───────────────────────────────────────────────────────
for method in ("pearson", "spearman"):
    corr = data.corr(method=method)
    corr.to_csv(TBL / f"corr_{method}.csv")
    print(f"  Wrote {TBL}/corr_{method}.csv")
    _clustered_heatmap(corr, method, FIG / f"corr_{method}.png")

# ── also print top-10 strongest Pearson pairs (|r| > 0.7) ─────────────────
pearson = data.corr(method="pearson")
mask = np.triu(np.ones_like(pearson, dtype=bool), k=1)
pairs = (
    pearson.where(mask)
    .stack()
    .reset_index()
    .rename(columns={"level_0": "var1", "level_1": "var2", 0: "r"})
    .assign(abs_r=lambda x: x["r"].abs())
    .sort_values("abs_r", ascending=False)
)
strong = pairs[pairs["abs_r"] >= 0.7]
print(f"\nStrongly correlated pairs (|r| ≥ 0.7): {len(strong)}")
print(strong[["var1", "var2", "r"]].head(15).to_string(index=False))
