"""02_anova_posthoc.py — three-way ANOVA and post-hoc tests for 2025 TPE.

For each numeric response:
  1. Three-way ANOVA (Type III SS): Soil * Fertilizer * Biochar
     - T1/T2 have Biochar = NO by design, so the three-way model is used
       on all 32 rows; a separate Biochar-only ANOVA is run on fertilized
       rows (T3-T8) for the Biochar main effect and its interaction with Soil.
  2. One-way ANOVA over Treatment (8 levels) + Tukey HSD letter groupings.
  3. Shapiro-Wilk and Levene diagnostics; results flagged if assumptions fail.

Outputs
-------
outputs/tables/anova_summary.csv     — Type III F-table for every response
outputs/tables/hsd_<response>.csv    — Tukey HSD pairwise + letter groups
outputs/figures/residuals_<response>.png  — Q-Q and fitted-vs-residuals
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm

np.random.seed(2025)
warnings.filterwarnings("ignore", category=FutureWarning)

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ── load data ──────────────────────────────────────────────────────────────
bundle = pd.read_pickle(PKL)
df = bundle["data"].copy()

ID_COLS = ["Treatment", "Rep", "Soil", "Biochar", "Fertilizer"]
num_cols = [c for c in df.columns if c not in ID_COLS]

# Work with plain strings / floats so statsmodels formulas work cleanly.
df["Soil"]       = df["Soil"].astype(str)
df["Biochar"]    = df["Biochar"].astype(str)
df["Fertilizer"] = df["Fertilizer"].astype(str)
df["Treatment"]  = df["Treatment"].astype(str)
df["Rep"]        = df["Rep"].astype(str)

df_fert = df[df["Fertilizer"] == "YES"].copy()   # T3-T8 for Biochar tests


# ── helpers ────────────────────────────────────────────────────────────────

def _tukey_letters(ph: pd.DataFrame, alpha: float = 0.05) -> pd.Series:
    """Derive compact letter display from scikit-posthocs Tukey matrix."""
    # ph is a symmetric p-value DataFrame (groups as index/columns).
    groups = list(ph.index)
    n = len(groups)
    letters: list[set] = [set() for _ in range(n)]
    letter_idx = 0
    chr_a = ord("a")
    assigned: list[bool] = [False] * n

    # Simple sequential approach: groups connected by p >= alpha share a letter.
    for i in range(n):
        for j in range(i + 1, n):
            if ph.iloc[i, j] >= alpha:
                ltr = chr(chr_a + letter_idx)
                letters[i].add(ltr)
                letters[j].add(ltr)
                assigned[i] = assigned[j] = True
        letter_idx += 1

    # Groups with no connections get a unique letter.
    for i in range(n):
        if not assigned[i]:
            letters[i].add(chr(chr_a + letter_idx))
            letter_idx += 1

    return pd.Series(
        ["".join(sorted(s)) for s in letters], index=groups, name="group"
    )


def run_one(response: str) -> dict:
    sub = df[["Soil", "Fertilizer", "Biochar", "Treatment", response]].dropna()
    if len(sub) < 8 or sub[response].nunique() < 2:
        return {}

    result: dict = {"response": response, "n": len(sub)}

    # ── 1. Three-way ANOVA (all rows) ──────────────────────────────────────
    formula_3way = f"Q('{response}') ~ C(Soil) * C(Fertilizer) * C(Biochar)"
    try:
        m3 = ols(formula_3way, data=sub).fit()
        tbl3 = anova_lm(m3, typ=3)
        tbl3.insert(0, "response", response)
        tbl3.insert(1, "model", "3way_all")
        result["anova_3way"] = tbl3
    except Exception as e:
        result["anova_3way_error"] = str(e)

    # ── 2. Biochar ANOVA restricted to fertilized rows ─────────────────────
    sub_f = df_fert[["Soil", "Biochar", response]].dropna()
    if len(sub_f) >= 6:
        try:
            mf = ols(f"Q('{response}') ~ C(Soil) * C(Biochar)", data=sub_f).fit()
            tbl_f = anova_lm(mf, typ=3)
            tbl_f.insert(0, "response", response)
            tbl_f.insert(1, "model", "2way_fertilized")
            result["anova_biochar"] = tbl_f
        except Exception as e:
            result["anova_biochar_error"] = str(e)

    # ── 3. One-way ANOVA by Treatment → Tukey HSD ──────────────────────────
    sub_t = df[["Treatment", response]].dropna()
    try:
        m1 = ols(f"Q('{response}') ~ C(Treatment)", data=sub_t).fit()
        tbl1 = anova_lm(m1, typ=1)
        tbl1.insert(0, "response", response)
        tbl1.insert(1, "model", "1way_treatment")
        result["anova_1way"] = tbl1

        ph = sp.posthoc_tukey(sub_t, val_col=response, group_col="Treatment")
        ph.to_csv(TBL / f"hsd_{response}.csv")
        letters = _tukey_letters(ph)
        means = sub_t.groupby("Treatment")[response].mean().rename("mean")
        se    = sub_t.groupby("Treatment")[response].sem().rename("se")
        hsd_summary = pd.concat([means, se, letters], axis=1)
        hsd_summary.to_csv(TBL / f"hsd_{response}_summary.csv")
        result["hsd_letters"] = letters
    except Exception as e:
        result["hsd_error"] = str(e)

    # ── 4. Diagnostics ─────────────────────────────────────────────────────
    try:
        residuals = m3.resid if "anova_3way" in result else m1.resid
        sw_stat, sw_p = stats.shapiro(residuals)
        groups_lev = [g[response].values for _, g in sub_t.groupby("Treatment")]
        lev_stat, lev_p = stats.levene(*groups_lev)
        result["shapiro_p"] = sw_p
        result["levene_p"]  = lev_p
        result["flag"]      = "!" if (sw_p < 0.05 or lev_p < 0.05) else ""

        # Q-Q plot + fitted-vs-residuals
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        stats.probplot(residuals, plot=axes[0])
        axes[0].set_title(f"{response}: Q-Q")
        fitted = m3.fittedvalues if "anova_3way" in result else m1.fittedvalues
        axes[1].scatter(fitted, residuals, alpha=0.7, s=30)
        axes[1].axhline(0, color="red", linewidth=0.8)
        axes[1].set_xlabel("Fitted"); axes[1].set_ylabel("Residuals")
        axes[1].set_title(f"{response}: Fitted vs Residuals")
        fig.tight_layout()
        fig.savefig(FIG / f"residuals_{response}.png", dpi=150)
        plt.close(fig)
    except Exception:
        pass

    return result


# ── run all responses ───────────────────────────────────────────────────────
all_anova_rows: list[pd.DataFrame] = []
diag_rows: list[dict] = []

print(f"Running ANOVA for {len(num_cols)} responses...\n")
for col in num_cols:
    res = run_one(col)
    if not res:
        print(f"  {col:40s}  SKIPPED (too few observations or no variance)")
        continue
    flag = res.get("flag", "")
    sw   = res.get("shapiro_p", float("nan"))
    lev  = res.get("levene_p",  float("nan"))
    print(f"  {col:40s}  n={res['n']:2d}  Shapiro p={sw:.3f}  Levene p={lev:.3f}  {flag}")
    diag_rows.append({"response": col, "n": res["n"],
                       "shapiro_p": sw, "levene_p": lev,
                       "flag": flag})
    for key in ("anova_3way", "anova_biochar", "anova_1way"):
        if key in res:
            all_anova_rows.append(res[key])

# ── write combined ANOVA table ──────────────────────────────────────────────
if all_anova_rows:
    anova_all = pd.concat(all_anova_rows)
    anova_all.to_csv(TBL / "anova_summary.csv")
    print(f"\nWrote {TBL}/anova_summary.csv")

diag_df = pd.DataFrame(diag_rows)
diag_df.to_csv(TBL / "anova_diagnostics.csv", index=False)
print(f"Wrote {TBL}/anova_diagnostics.csv")
n_flag = diag_df["flag"].eq("!").sum()
if n_flag:
    print(f"\n  {n_flag} responses flagged — consider log-transform (see flag column).")
