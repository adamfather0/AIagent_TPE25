"""06_bar_cld.py — bar charts with compact letter display (CLD).

Reads each hsd_<response>_summary.csv produced by 02_anova_posthoc.py
(treatment mean, SE, Tukey HSD letter group) and renders:

  1. A 4 x 3 panel figure of the 12 most informative responses.
  2. Individual bar+CLD figures for every response with HSD letters.

Bars are colored by Soil and hatched by Biochar.  Error bars are SE.
A letter label sits above each error bar; treatments sharing a letter
are not significantly different (Tukey HSD, alpha = 0.05).

Outputs
-------
outputs/figures/bar_cld_panel.png        — 4 x 3 key responses
outputs/figures/bar_cld_<response>.png   — one per HSD-tested response
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
FIG.mkdir(parents=True, exist_ok=True)

TREATMENTS = [f"T{i}" for i in range(1, 9)]
SOIL_OF = {"T1": "Red_soil", "T2": "Alluvial_soil",
           "T3": "Red_soil", "T4": "Alluvial_soil",
           "T5": "Red_soil", "T6": "Red_soil",
           "T7": "Alluvial_soil", "T8": "Alluvial_soil"}
BIOCHAR_OF = {"T1": "NO", "T2": "NO", "T3": "NO", "T4": "NO",
              "T5": "Rice_husk", "T6": "Leucaena",
              "T7": "Rice_husk", "T8": "Leucaena"}
FERT_OF = {"T1": "NO", "T2": "NO", **{f"T{i}": "YES" for i in range(3, 9)}}

SOIL_COLOR = {"Red_soil": "#d62728", "Alluvial_soil": "#1f77b4"}
HATCH_OF   = {"NO": "", "Rice_husk": "//", "Leucaena": "xx"}

KEY_RESPONSES = [
    "Above_ground_biomass", "Dry_matter", "Plant_height_35DAT",
    "Stem_diameter_35DAT", "SPAD_35DAT", "Flower_buds",
    "N_uptake", "P_uptake", "K_uptake",
    "pH", "Acid_phosphomonosterase", "Dehydrogenase",
]

UNIT_OF = {
    "Above_ground_biomass": "g plant⁻¹",
    "Dry_matter": "g",
    "Plant_height_35DAT": "cm",
    "Stem_diameter_35DAT": "mm",
    "SPAD_35DAT": "SPAD",
    "Flower_buds": "count",
    "N_uptake": "kg ha⁻¹",
    "P_uptake": "kg ha⁻¹",
    "K_uptake": "kg ha⁻¹",
    "pH": "(1:2.5)",
    "Acid_phosphomonosterase": "mg kg⁻¹ h⁻¹",
    "Dehydrogenase": "mg kg⁻¹ h⁻¹",
}


def _load_hsd(response: str) -> pd.DataFrame | None:
    f = TBL / f"lsd_{response}_summary.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    # Treatment is the index column (unnamed) when read back.
    d = d.rename(columns={d.columns[0]: "Treatment"})
    d = d[d["Treatment"].isin(TREATMENTS)].copy()
    d["Treatment"] = pd.Categorical(d["Treatment"], categories=TREATMENTS, ordered=True)
    d = d.sort_values("Treatment").reset_index(drop=True)
    return d


def _bar_cld(ax: plt.Axes, response: str, *, title: bool = True) -> bool:
    d = _load_hsd(response)
    if d is None or d.empty:
        ax.set_visible(False)
        return False

    x = np.arange(len(d))
    means = d["mean"].astype(float).values
    ses   = d["se"].astype(float).fillna(0).values
    letters = d.get("group", pd.Series([""] * len(d))).astype(str).values
    transform = d["transform"].iloc[0] if "transform" in d.columns else "none"

    colors  = [SOIL_COLOR[SOIL_OF[t]]    for t in d["Treatment"].astype(str)]
    hatches = [HATCH_OF[BIOCHAR_OF[t]]   for t in d["Treatment"].astype(str)]

    bars = ax.bar(x, means, yerr=ses, capsize=3, color=colors,
                  edgecolor="black", linewidth=0.7, hatch=hatches,
                  error_kw=dict(ecolor="black", lw=1))
    for b in bars:
        b.set_alpha(0.85)

    # CLD letters above error bars.
    span = (means + ses).max() - min(0, (means - ses).min())
    pad  = 0.04 * span if span > 0 else 0.5
    for xi, m, se_i, lt in zip(x, means, ses, letters):
        if lt and lt != "nan":
            ax.text(xi, m + se_i + pad, lt, ha="center", va="bottom",
                    fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(d["Treatment"].astype(str), fontsize=8)
    ax.set_ylabel(UNIT_OF.get(response, ""), fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    suffix = " (log1p-fitted)" if transform == "log1p" else ""
    if title:
        ax.set_title(f"{response.replace('_', ' ')}{suffix}", fontsize=10)

    # Headroom for letters.
    ymax = (means + ses).max() + 4 * pad
    ymin = min(0, (means - ses).min() - pad)
    ax.set_ylim(ymin, ymax)
    return True


def _legend_handles() -> list:
    soil_h = [Patch(facecolor=c, edgecolor="black", label=s.replace("_", " "))
              for s, c in SOIL_COLOR.items()]
    bio_h  = [Patch(facecolor="white", edgecolor="black",
                    hatch=HATCH_OF[b], label=b.replace("_", " "))
              for b in HATCH_OF]
    return soil_h + bio_h


# ── panel figure ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(4, 3, figsize=(13, 13))
made = 0
for ax, resp in zip(axes.flat, KEY_RESPONSES):
    if _bar_cld(ax, resp):
        made += 1
for ax in axes.flat[made:]:
    ax.set_visible(False)

fig.legend(handles=_legend_handles(), loc="lower center",
           ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.suptitle("Treatment means ± SE with Fisher's LSD letters "
             "(p < 0.05; bars sharing a letter are not significantly different)",
             fontsize=12, y=1.00)
fig.tight_layout(rect=(0, 0.03, 1, 0.99))
fig.savefig(FIG / "bar_cld_panel.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIG}/bar_cld_panel.png  ({made} responses)")

# ── individual figures for every HSD-tested response ──────────────────────
hsd_files = sorted(TBL.glob("lsd_*_summary.csv"))
n_individual = 0
for f in hsd_files:
    response = f.stem.replace("lsd_", "").replace("_summary", "")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if _bar_cld(ax, response):
        ax.legend(handles=_legend_handles(), loc="upper left",
                  fontsize=7, ncol=2, frameon=False)
        fig.tight_layout()
        fig.savefig(FIG / f"bar_cld_{response}.png", dpi=300, bbox_inches="tight")
        n_individual += 1
    plt.close(fig)
print(f"Wrote {n_individual} individual bar_cld_*.png files in {FIG}/")
