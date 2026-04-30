"""02_anova_posthoc.py — three-way ANOVA and post-hoc tests for 2025 TPE.

For each numeric response:
  1. Fit models on raw data; check Shapiro-Wilk (residuals) + Levene (groups).
  2. If either test fails (p < 0.05), apply log1p transform and refit.
  3. Report which scale was used (raw / log1p) in the diagnostics table.
  4. Three-way ANOVA (Type III SS): Soil * Fertilizer * Biochar (all rows)
     plus a two-way ANOVA restricted to fertilized rows (T3-T8) for the
     Biochar main effect and its Soil interaction.
  5. One-way ANOVA by Treatment + Fisher's LSD compact letter display (p < 0.05).

Outputs
-------
outputs/tables/anova_summary.csv          — Type III F-tables (all responses)
outputs/tables/anova_diagnostics.csv      — per-response normality/homogeneity
outputs/tables/lsd_<response>.csv         — Fisher's LSD pairwise p-values
outputs/tables/lsd_<response>_summary.csv — mean, SE, letter group per treatment
outputs/figures/residuals_<response>.png  — Q-Q + fitted-vs-residuals
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
warnings.filterwarnings("ignore", category=UserWarning)

PKL = Path("data/tpe25.pkl")
TBL = Path("outputs/tables")
FIG = Path("outputs/figures")
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────
bundle = pd.read_pickle(PKL)
df = bundle["data"].copy()

ID_COLS = ["Treatment", "Rep", "Soil", "Biochar", "Fertilizer"]
num_cols = [c for c in df.columns if c not in ID_COLS]

for c in ("Soil", "Biochar", "Fertilizer", "Treatment", "Rep"):
    df[c] = df[c].astype(str)

df_fert = df[df["Fertilizer"] == "YES"].copy()


# ── helpers ────────────────────────────────────────────────────────────────

def _check(residuals: np.ndarray, groups: list[np.ndarray]) -> tuple[float, float]:
    """Return (shapiro_p, levene_p)."""
    _, sw_p  = stats.shapiro(residuals)
    _, lev_p = stats.levene(*groups)
    return float(sw_p), float(lev_p)


def _tukey_letters(ph: pd.DataFrame, alpha: float = 0.05) -> pd.Series:
    groups = list(ph.index)
    n = len(groups)
    letters: list[set] = [set() for _ in range(n)]
    assigned = [False] * n
    letter_idx = 0

    for i in range(n):
        for j in range(i + 1, n):
            if ph.iloc[i, j] >= alpha:
                ltr = chr(ord("a") + letter_idx)
                letters[i].add(ltr)
                letters[j].add(ltr)
                assigned[i] = assigned[j] = True
        letter_idx += 1

    for i in range(n):
        if not assigned[i]:
            letters[i].add(chr(ord("a") + letter_idx))
            letter_idx += 1

    return pd.Series(["".join(sorted(s)) for s in letters],
                     index=groups, name="group")


def _fit_all(sub_all: pd.DataFrame, sub_fert: pd.DataFrame,
             sub_treat: pd.DataFrame, ycol: str,
             response_label: str) -> dict:
    """Fit three-way, two-way (fertilized), and one-way models on ycol.

    Returns dict with model objects + ANOVA DataFrames.
    """
    out: dict = {}

    # Three-way
    formula = f"Q('{ycol}') ~ C(Soil) * C(Fertilizer) * C(Biochar)"
    try:
        m3 = ols(formula, data=sub_all).fit()
        tbl = anova_lm(m3, typ=3)
        tbl.insert(0, "response", response_label)
        tbl.insert(1, "model", "3way_all")
        out["m3"] = m3; out["tbl3"] = tbl
    except Exception as e:
        out["m3_err"] = str(e)

    # Two-way on fertilized rows
    if len(sub_fert) >= 6:
        try:
            mf = ols(f"Q('{ycol}') ~ C(Soil) * C(Biochar)", data=sub_fert).fit()
            tblf = anova_lm(mf, typ=3)
            tblf.insert(0, "response", response_label)
            tblf.insert(1, "model", "2way_fertilized")
            out["mf"] = mf; out["tblf"] = tblf
        except Exception as e:
            out["mf_err"] = str(e)

    # One-way by treatment
    try:
        m1 = ols(f"Q('{ycol}') ~ C(Treatment)", data=sub_treat).fit()
        tbl1 = anova_lm(m1, typ=1)
        tbl1.insert(0, "response", response_label)
        tbl1.insert(1, "model", "1way_treatment")
        out["m1"] = m1; out["tbl1"] = tbl1
    except Exception as e:
        out["m1_err"] = str(e)

    return out


def run_one(response: str) -> dict:
    sub = df[["Soil", "Fertilizer", "Biochar", "Treatment", response]].dropna()
    if len(sub) < 8 or sub[response].nunique() < 2:
        return {}

    sub_f = df_fert[["Soil", "Biochar", response]].dropna()
    sub_t = df[["Treatment", response]].dropna()

    groups_raw = [g[response].values for _, g in sub_t.groupby("Treatment")]

    # ── Pass 1: raw data ───────────────────────────────────────────────────
    fit_raw = _fit_all(sub, sub_f, sub_t, response, response)
    m_primary = fit_raw.get("m3") or fit_raw.get("m1")
    if m_primary is None:
        return {}

    sw_p_raw, lev_p_raw = _check(m_primary.resid.values, groups_raw)
    needs_transform = (sw_p_raw < 0.05) or (lev_p_raw < 0.05)

    # ── Pass 2: log1p if needed ────────────────────────────────────────────
    transform = "none"
    if needs_transform and (sub[response] >= 0).all():
        ycol_log = f"log1p_{response}"
        sub    = sub.copy();    sub[ycol_log]    = np.log1p(sub[response])
        sub_f2 = sub_f.copy();  sub_f2[ycol_log] = np.log1p(sub_f2[response])
        sub_t2 = sub_t.copy();  sub_t2[ycol_log] = np.log1p(sub_t2[response])

        fit_log = _fit_all(sub, sub_f2, sub_t2, ycol_log, response)
        m_log   = fit_log.get("m3") or fit_log.get("m1")
        if m_log is not None:
            groups_log = [g[ycol_log].values for _, g in sub_t2.groupby("Treatment")]
            sw_p_log, lev_p_log = _check(m_log.resid.values, groups_log)
            # Always use log1p when raw failed, regardless of whether log passes
            # (log rarely makes things worse; avoids cherry-picking).
            transform = "log1p"
            fit_use  = fit_log
            sub_t_use = sub_t2
            ycol_use  = ycol_log
            sw_p_fin, lev_p_fin = sw_p_log, lev_p_log
        else:
            fit_use = fit_raw; sub_t_use = sub_t; ycol_use = response
            sw_p_fin, lev_p_fin = sw_p_raw, lev_p_raw
    else:
        fit_use = fit_raw; sub_t_use = sub_t; ycol_use = response
        sw_p_fin, lev_p_fin = sw_p_raw, lev_p_raw

    result: dict = {
        "response": response, "n": len(sub),
        "transform": transform,
        "shapiro_p_raw": sw_p_raw, "levene_p_raw": lev_p_raw,
        "shapiro_p_final": sw_p_fin, "levene_p_final": lev_p_fin,
        "flag": "!" if (sw_p_fin < 0.05 or lev_p_fin < 0.05) else "",
    }

    # ── Collect ANOVA tables ───────────────────────────────────────────────
    for key in ("tbl3", "tblf", "tbl1"):
        if key in fit_use:
            result.setdefault("anova_tables", []).append(fit_use[key])

    # ── Fisher's LSD on final scale (pairwise t-test, pooled var, no adj.) ──
    try:
        ph = sp.posthoc_ttest(sub_t_use, val_col=ycol_use, group_col="Treatment",
                              equal_var=True, p_adjust=None)
        ph.to_csv(TBL / f"lsd_{response}.csv")
        letters = _tukey_letters(ph)          # same letter-grouping logic, alpha=0.05
        # Means and SE on original (back-transformed if log1p) scale.
        means_orig = sub_t.groupby("Treatment")[response].mean().rename("mean")
        se_orig    = sub_t.groupby("Treatment")[response].sem().rename("se")
        lsd_sum = pd.concat([means_orig, se_orig, letters], axis=1)
        lsd_sum.insert(0, "transform", transform)
        lsd_sum.to_csv(TBL / f"lsd_{response}_summary.csv")
    except Exception as e:
        result["lsd_error"] = str(e)

    # ── Diagnostic plot on final scale ────────────────────────────────────
    try:
        m_plot = fit_use.get("m3") or fit_use.get("m1")
        residuals = m_plot.resid.values
        fitted    = m_plot.fittedvalues.values
        scale_note = f" [{transform}]" if transform != "none" else ""
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        stats.probplot(residuals, plot=axes[0])
        axes[0].set_title(f"{response}{scale_note}: Q-Q")
        axes[1].scatter(fitted, residuals, alpha=0.7, s=30)
        axes[1].axhline(0, color="red", linewidth=0.8)
        axes[1].set_xlabel("Fitted"); axes[1].set_ylabel("Residuals")
        axes[1].set_title(f"{response}{scale_note}: Fitted vs Residuals")
        fig.tight_layout()
        fig.savefig(FIG / f"residuals_{response}.png", dpi=150)
        plt.close(fig)
    except Exception:
        pass

    return result


# ── run all ────────────────────────────────────────────────────────────────
all_anova_rows: list[pd.DataFrame] = []
diag_rows: list[dict] = []

print(f"Running ANOVA for {len(num_cols)} responses...\n")
print(f"  {'Response':<40} {'n':>3}  {'SW-raw':>8}  {'Lev-raw':>8}  "
      f"{'SW-fin':>8}  {'Lev-fin':>8}  {'Transform':<10}  Flag")
print("  " + "-" * 100)

for col in num_cols:
    res = run_one(col)
    if not res:
        print(f"  {col:<40}  SKIPPED")
        continue

    sw_r  = res["shapiro_p_raw"];   lev_r = res["levene_p_raw"]
    sw_f  = res["shapiro_p_final"]; lev_f = res["levene_p_final"]
    tf    = res["transform"];       flag  = res["flag"]
    print(f"  {col:<40} {res['n']:>3}  {sw_r:>8.3f}  {lev_r:>8.3f}  "
          f"{sw_f:>8.3f}  {lev_f:>8.3f}  {tf:<10}  {flag}")

    diag_rows.append({
        "response": col, "n": res["n"], "transform": tf,
        "shapiro_p_raw": sw_r, "levene_p_raw": lev_r,
        "shapiro_p_final": sw_f, "levene_p_final": lev_f,
        "flag": flag,
    })
    for tbl in res.get("anova_tables", []):
        all_anova_rows.append(tbl)

# ── write outputs ──────────────────────────────────────────────────────────
if all_anova_rows:
    pd.concat(all_anova_rows).to_csv(TBL / "anova_summary.csv")
    print(f"\nWrote {TBL}/anova_summary.csv")

diag_df = pd.DataFrame(diag_rows)
diag_df.to_csv(TBL / "anova_diagnostics.csv", index=False)
print(f"Wrote {TBL}/anova_diagnostics.csv")

n_log  = diag_df["transform"].eq("log1p").sum()
n_flag = diag_df["flag"].eq("!").sum()
print(f"\n  {n_log} responses log1p-transformed.")
if n_flag:
    print(f"  {n_flag} still flagged after transform (review manually).")
else:
    print("  All responses pass normality/homogeneity after transform.")
