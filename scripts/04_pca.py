"""04_pca.py — PCA and k-means clustering on treatment means for 2025 TPE.

Aggregates observations to treatment means, standardises, fits PCA, and
produces a biplot coloured by Soil and shaped by Biochar.  Optional k-means
(k = 2..4) on PC scores with an elbow plot.

Outputs
-------
outputs/figures/pca_biplot.png
outputs/figures/pca_screeplot.png
outputs/figures/pca_kmeans_elbow.png
outputs/tables/pca_scores.csv
outputs/tables/pca_loadings.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

np.random.seed(2025)

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ── load & aggregate to treatment means ────────────────────────────────────
df = pd.read_pickle(PKL)["data"]
ID_COLS = ["Treatment", "Rep", "Soil", "Biochar", "Fertilizer"]
num_cols = [c for c in df.columns if c not in ID_COLS]

# Use subset of informative columns: drop NUE indices (too many NAs) for PCA.
# NUE cols only exist for fertilized treatments, making the biplot unbalanced.
NUE_COLS = {"PFPN", "Agronomic_NUE", "Recovery_rate_N", "Recovery_rate_P",
            "Recovery_rate_K", "Physiological_Efficiency"}
pca_cols = [c for c in num_cols if c not in NUE_COLS]

means = (
    df.groupby("Treatment")[pca_cols]
    .mean()
    .dropna(axis=1)          # drop any column that still has NaN after averaging
)
treatment_meta = (
    df.drop_duplicates("Treatment")
    .set_index("Treatment")[["Soil", "Biochar", "Fertilizer"]]
)
meta = treatment_meta.loc[means.index]

# ── standardise and fit PCA ────────────────────────────────────────────────
scaler = StandardScaler()
X = scaler.fit_transform(means)

pca = PCA(random_state=2025)
scores = pca.fit_transform(X)
loadings = pca.components_          # shape (n_components, n_features)
explained = pca.explained_variance_ratio_ * 100

n_features = len(means.columns)
n_samples  = len(means)

# ── save scores and loadings ───────────────────────────────────────────────
scores_df = pd.DataFrame(
    scores[:, :min(5, n_samples - 1)],
    index=means.index,
    columns=[f"PC{i+1}" for i in range(min(5, n_samples - 1))],
)
scores_df.to_csv(TBL / "pca_scores.csv")

loadings_df = pd.DataFrame(
    loadings[:min(5, n_samples - 1), :].T,
    index=means.columns,
    columns=[f"PC{i+1}" for i in range(min(5, n_samples - 1))],
)
loadings_df.to_csv(TBL / "pca_loadings.csv")
print(f"PC1 {explained[0]:.1f}%  PC2 {explained[1]:.1f}%  (cumulative {explained[:2].sum():.1f}%)")

# ── scree plot ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 4))
cumul = np.cumsum(explained)
ax.bar(range(1, len(explained) + 1), explained, color="steelblue", alpha=0.8)
ax.plot(range(1, len(explained) + 1), cumul, "ro-", markersize=4)
ax.axhline(80, color="grey", linestyle="--", linewidth=0.8)
ax.set_xlabel("PC"); ax.set_ylabel("Variance explained (%)")
ax.set_title("Scree plot — PCA on treatment means")
fig.tight_layout()
fig.savefig(FIG / "pca_screeplot.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIG}/pca_screeplot.png")

# ── biplot (PC1 vs PC2) ────────────────────────────────────────────────────
SOIL_COLORS = {"Red_soil": "#d62728", "Alluvial_soil": "#1f77b4"}
BIOCHAR_MARKERS = {"NO": "s", "Rice_husk": "^", "Leucaena": "o"}

fig, ax = plt.subplots(figsize=(8, 6))

for _, row in pd.concat([scores_df[["PC1", "PC2"]], meta], axis=1).iterrows():
    soil   = str(row["Soil"])
    bioch  = str(row["Biochar"])
    color  = SOIL_COLORS.get(soil, "grey")
    marker = BIOCHAR_MARKERS.get(bioch, "D")
    ax.scatter(row["PC1"], row["PC2"], c=color, marker=marker,
               s=120, edgecolors="black", linewidths=0.6, zorder=3)
    ax.annotate(row.name, (row["PC1"], row["PC2"]),
                textcoords="offset points", xytext=(5, 4), fontsize=8)

# Loading arrows: top-8 by length on PC1+PC2.
load2 = loadings_df[["PC1", "PC2"]].copy()
load2["len"] = np.hypot(load2["PC1"], load2["PC2"])
top_load = load2.nlargest(8, "len")
scale = 0.4 * min(scores_df["PC1"].abs().max(), scores_df["PC2"].abs().max()) / top_load["len"].max()
for var, lrow in top_load.iterrows():
    ax.annotate(
        "", xy=(lrow["PC1"] * scale, lrow["PC2"] * scale), xytext=(0, 0),
        arrowprops=dict(arrowstyle="->", color="darkgreen", lw=1.2),
    )
    ax.text(lrow["PC1"] * scale * 1.1, lrow["PC2"] * scale * 1.1,
            var, fontsize=7, color="darkgreen")

ax.axhline(0, color="grey", linewidth=0.5, linestyle="--")
ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
ax.set_xlabel(f"PC1 ({explained[0]:.1f}%)")
ax.set_ylabel(f"PC2 ({explained[1]:.1f}%)")
ax.set_title("PCA biplot — treatment means")

# Legend: Soil (color) and Biochar (marker).
from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
           markersize=9, markeredgecolor="black", label=s)
    for s, c in SOIL_COLORS.items()
] + [
    Line2D([0], [0], marker=m, color="w", markerfacecolor="grey",
           markersize=9, markeredgecolor="black", label=b)
    for b, m in BIOCHAR_MARKERS.items()
]
ax.legend(handles=legend_handles, fontsize=8, loc="upper left",
          title="Soil / Biochar", title_fontsize=8)

fig.tight_layout()
fig.savefig(FIG / "pca_biplot.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIG}/pca_biplot.png")

# ── k-means elbow (k = 2..4) ──────────────────────────────────────────────
X2 = scores[:, :2]      # cluster on first two PCs
ks = range(2, 5)
inertias = [KMeans(n_clusters=k, random_state=2025, n_init=10).fit(X2).inertia_
            for k in ks]

fig, ax = plt.subplots(figsize=(5, 3))
ax.plot(list(ks), inertias, "bo-")
ax.set_xlabel("k"); ax.set_ylabel("Inertia")
ax.set_title("K-means elbow on PC1+PC2 scores")
ax.set_xticks(list(ks))
fig.tight_layout()
fig.savefig(FIG / "pca_kmeans_elbow.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIG}/pca_kmeans_elbow.png")
