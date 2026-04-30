"""05_nue_summary.py — NUE and nutrient recovery summary for 2025 TPE.

Filters to fertilized treatments (T3-T8), computes mean ± SE by
Soil x Biochar, and produces a barplot panel for each NUE index.

Outputs
-------
outputs/tables/nue_summary.csv
outputs/figures/nue_panel.png          — all six NUE indices in one figure
outputs/figures/nue_<index>.png        — individual plots (6 files)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

np.random.seed(2025)

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ── load & filter ──────────────────────────────────────────────────────────
df = pd.read_pickle(PKL)["data"]
df["Fertilizer"] = df["Fertilizer"].astype(str)
df["Soil"]       = df["Soil"].astype(str)
df["Biochar"]    = df["Biochar"].astype(str)

fert = df[df["Fertilizer"] == "YES"].copy()   # T3-T8

NUE_COLS = [
    "PFPN",
    "Agronomic_NUE",
    "Recovery_rate_N",
    "Recovery_rate_P",
    "Recovery_rate_K",
    "Physiological_Efficiency",
]
NUE_LABELS = {
    "PFPN": "PFPN (kg AGB kg N⁻¹)",
    "Agronomic_NUE": "Agronomic NUE (kg AGB kg N⁻¹)",
    "Recovery_rate_N": "Recovery rate N (%)",
    "Recovery_rate_P": "Recovery rate P (%)",
    "Recovery_rate_K": "Recovery rate K (%)",
    "Physiological_Efficiency": "Physiological Efficiency\n(kg AGB kg N-uptake⁻¹)",
}

SOIL_ORDER   = ["Red_soil", "Alluvial_soil"]
BIOCHAR_ORDER = ["NO", "Rice_husk", "Leucaena"]
SOIL_PALETTE  = {"Red_soil": "#d62728", "Alluvial_soil": "#1f77b4"}
HATCH_MAP     = {"NO": "", "Rice_husk": "//", "Leucaena": "xx"}

# ── aggregate mean ± SE ────────────────────────────────────────────────────
summary = (
    fert.groupby(["Soil", "Biochar"])[NUE_COLS]
    .agg(["mean", "sem"])
    .reset_index()
)
# Flatten multi-level columns.
summary.columns = [
    "_".join(c).strip("_") if c[1] else c[0]
    for c in summary.columns
]
summary.to_csv(TBL / "nue_summary.csv", index=False)
print(f"Wrote {TBL}/nue_summary.csv")

# ── plotting helper ────────────────────────────────────────────────────────

def _nue_barplot(ax: plt.Axes, col: str) -> None:
    mean_col = f"{col}_mean"
    se_col   = f"{col}_sem"

    x_positions: list[float] = []
    bar_colors:  list[str]   = []
    bar_hatches: list[str]   = []
    means_vals:  list[float] = []
    se_vals:     list[float] = []
    xtick_labels: list[str]  = []

    group_width = len(BIOCHAR_ORDER) + 0.6
    for g_idx, soil in enumerate(SOIL_ORDER):
        sub = summary[summary["Soil"] == soil].set_index("Biochar")
        for b_idx, biochar in enumerate(BIOCHAR_ORDER):
            x = g_idx * group_width + b_idx
            x_positions.append(x)
            bar_colors.append(SOIL_PALETTE[soil])
            bar_hatches.append(HATCH_MAP[biochar])
            row = sub.loc[biochar] if biochar in sub.index else None
            means_vals.append(float(row[mean_col]) if row is not None and not pd.isna(row[mean_col]) else 0)
            se_vals.append(float(row[se_col])   if row is not None and not pd.isna(row[se_col])   else 0)
            xtick_labels.append(biochar.replace("_", "\n"))

    bars = ax.bar(
        x_positions, means_vals, color=bar_colors, hatch=bar_hatches,
        edgecolor="black", linewidth=0.6, width=0.8,
    )
    ax.errorbar(
        x_positions, means_vals, yerr=se_vals,
        fmt="none", color="black", capsize=3, linewidth=1,
    )
    ax.set_xticks(x_positions)
    ax.set_xticklabels(xtick_labels, fontsize=7)
    ax.set_ylabel(NUE_LABELS[col], fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))
    ax.tick_params(axis="y", labelsize=7)

    # Soil group labels.
    for g_idx, soil in enumerate(SOIL_ORDER):
        centre = g_idx * group_width + (len(BIOCHAR_ORDER) - 1) / 2
        ax.text(centre, ax.get_ylim()[1] * 0.98,
                soil.replace("_", " "), ha="center", va="top",
                fontsize=8, fontweight="bold", color=SOIL_PALETTE[soil])

    # Hatch legend.
    from matplotlib.patches import Patch
    hatch_legend = [
        Patch(facecolor="white", edgecolor="black", hatch=HATCH_MAP[b], label=b)
        for b in BIOCHAR_ORDER
    ]
    ax.legend(handles=hatch_legend, fontsize=6, loc="upper right",
              title="Biochar", title_fontsize=6)


# ── panel figure (2 rows × 3 cols) ────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
for ax, col in zip(axes.flat, NUE_COLS):
    _nue_barplot(ax, col)
fig.suptitle("NUE indices — fertilized treatments (T3–T8)\nMean ± SE by Soil × Biochar",
             fontsize=11, y=1.01)
fig.tight_layout()
fig.savefig(FIG / "nue_panel.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIG}/nue_panel.png")

# ── individual figures ─────────────────────────────────────────────────────
for col in NUE_COLS:
    fig, ax = plt.subplots(figsize=(6, 4))
    _nue_barplot(ax, col)
    ax.set_title(NUE_LABELS[col])
    fig.tight_layout()
    fig.savefig(FIG / f"nue_{col}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {FIG}/nue_{col}.png")
