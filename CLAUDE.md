# CLAUDE.md — Tomato Biochar Pot Experiment (2025 TPE)

This file orients Claude Code (and humans) to the project. Read it first.

## 1. Project

Pot experiment by **Kesamreddy Lokeshwar** (World Vegetable Center, Flagship: SSVC, 30 June 2025):

> **Assessing the Interactive Effects of Soil Type, Fertilizer, and Biochar Source on Soil Health and Tomato Performance**

Source plan PDF: Drive ID `1u6pei4B1yrvSeF_sv1b2MZHG3phRQ2QG`
(`Pot Expt-Plan-form_Tomato biochar pot study_2025 FINAL.pdf`).

### Hypotheses
1. Biochar enhances the effectiveness of mineral fertilizer.
2. Biochar gives a larger benefit on **acidic (Red) soil** than on near-neutral alluvial soil.
3. The two biochar types (rice husk vs Leucaena) produce similar responses.

## 2. Experimental design

- **Design**: Completely Randomized Design (CRD)
- **Replications**: 4 (`Rep` = 1–4)
- **Total pots**: 256 (pot 17 cm H × 18 cm Ø, 10 cm spacing)
- **Three factors → 8 treatment codes**:

| Code | Soil           | Fertilizer | Biochar    |
|------|----------------|------------|------------|
| T1   | Red_soil       | NO         | NO         |
| T2   | Alluvial_soil  | NO         | NO         |
| T3   | Red_soil       | YES        | NO         |
| T4   | Alluvial_soil  | YES        | NO         |
| T5   | Red_soil       | YES        | Rice_husk  |
| T6   | Red_soil       | YES        | Leucaena   |
| T7   | Alluvial_soil  | YES        | Rice_husk  |
| T8   | Alluvial_soil  | YES        | Leucaena   |

- **RDF (100% mineral fertilizer)**: 250 : 200 : 180 kg ha⁻¹ N : P : K, applied as basal + 4 top-dressings (see PDF for split percentages).
- **Biochar**: ~30 t ha⁻¹ (≈30.08 g pot⁻¹) of either rice-husk or Leucaena biochar.

## 3. Data file

- **Path**: `data/2025TPE_raw.xlsx`
- **Drive ID**: `18nkWLbUGst67_rULvMb6QbfDULFGESXf`
- **Owner**: adam.liu@worldveg.org
- **Layout**: row 1 = column names, row 2 = units, data starts row 3.
- **Missing values**: `NA`. One known `#VALUE!` error cell in T6 / Rep 2 (`Recovery_rate_K`) — treat as `NA`. T1/T2 (no fertilizer) have `NA` for all `Recovery_rate_*`, `Agronomic NUE`, `Physiological Efficiency`, `PFPN` by design.

### Variables (groups + units)

| Group               | Columns                                                                                     | Unit             |
|---------------------|---------------------------------------------------------------------------------------------|------------------|
| Identifiers         | `Treatment`, `Rep`, `Soil`, `Biochar`, `Fertilizer`                                         | factor           |
| Yield               | `Dry_matter`, `Above_ground_biomass`                                                        | g, g plant⁻¹     |
| Plant chemistry     | `Protein`, `N`, `P`, `K`, `Ca`, `Fe`, `Zn`, `Mg`                                            | mg g⁻¹           |
| Plant uptake        | `N_uptake`, `P_uptake`, `K_uptake`, `Ca_uptake`, `Fe_uptake`, `Zn_uptake`, `Mg_uptake`      | kg ha⁻¹          |
| Soil enzymes        | `Acid_phosphomonosterase`, `Dehydrogenase`                                                  | mg kg⁻¹ soil h⁻¹ |
| Soil chemistry      | `pH` (1:2.5), `EC`                                                                          | —, µS m⁻¹        |
| Growth @ 20 DAT     | `Plant_height_20DAT`, `Stem_diameter_20DAT`, `SPAD_20DAT`, `NDVI_20DAT`                     | cm, mm, —, —     |
| Growth @ 35 DAT     | `Plant_height_35DAT`, `Stem_diameter_35DAT`, `SPAD_35DAT`, `NDVI_35DAT`                     | cm, mm, —, —     |
| Reproductive        | `Flower_buds`                                                                               | count            |
| NUE indices         | `PFPN`, `Agronomic NUE`, `Recovery_rate_N`, `Recovery_rate_P`, `Recovery_rate_K`, `Physiological Efficiency`, `N/P ratio` | mixed (see header row) |

## 4. Repository layout

```
.
├── CLAUDE.md                       # this file
├── data/
│   └── 2025TPE_raw.xlsx
├── scripts/
│   ├── 01_load_clean.py
│   ├── 02_anova_posthoc.py
│   ├── 03_correlation.py
│   ├── 04_pca.py
│   └── 05_nue_summary.py
└── outputs/
    ├── figures/                    # 300 dpi PNGs from each script
    └── tables/                     # ANOVA + post-hoc CSVs
```

The raw xlsx has multiple sheets; the analysis uses the **`summary`** sheet only. The sheet contains 32 valid observation rows (8 treatments × 4 reps) followed by ~46 trailing summary/junk rows that `01_load_clean.py` filters out by keeping only rows with `Treatment ∈ {T1..T8}`.

Scripts beyond `01_load_clean.py` are written on-demand in subsequent sessions.

## 5. Analysis stack

Python ≥ 3.11. Install once:

```bash
pip install pandas openpyxl numpy scipy statsmodels pingouin \
            scikit-learn scikit-posthocs seaborn matplotlib
```

| Purpose                  | Library                                       |
|--------------------------|-----------------------------------------------|
| Read xlsx                | `pandas` + `openpyxl`                         |
| ANOVA (Type III)         | `statsmodels.formula.api.ols` + `anova_lm`    |
| Post-hoc (Tukey HSD, letter groups) | `pingouin.pairwise_tukey`, `scikit_posthocs` |
| Estimated marginal means | `statsmodels.stats.multicomp` / `pingouin`    |
| PCA, k-means             | `scikit-learn` (`PCA`, `KMeans`, `StandardScaler`) |
| Plots                    | `matplotlib`, `seaborn`                       |

## 6. Analysis workflow

### `scripts/01_load_clean.py`
- Reads sheet `"summary"`: row 1 = headers, row 2 = units (skipped), data starts row 3.
- Normalizes column names: trims trailing spaces (`Treatment `, `Plant_height_20DAT `, `Plant_height_35DAT `), strips trailing `*` (`Dry_matter*`), replaces `/` and inner spaces with `_` (`N uptake`, `Agronomic NUE`, `Physiological Efficiency`, `N/P ratio`).
- `na_values=["", "NA", "#VALUE!", "#DIV/0!", "#N/A"]`; `pd.to_numeric(..., errors="coerce")` for measurement columns.
- Sets `pd.Categorical` levels: `Treatment` = T1..T8 (ordered); `Soil` = Red_soil, Alluvial_soil; `Biochar` = NO, Rice_husk, Leucaena; `Fertilizer` = NO, YES; `Rep` = 1..4.
- Drops trailing summary rows by filtering `Treatment ∈ T1..T8`.
- Saves `data/tpe25.pkl` as `{"data": df, "units": units_df}`.

### `scripts/02_anova_posthoc.py`
- For each response `y`: `ols("y ~ C(Soil) * C(Fertilizer) * C(Biochar)", data=df).fit()`, then `sm.stats.anova_lm(model, typ=3)`.
- Where Biochar is nested under Fertilizer=YES (T1/T2 have no biochar level), either restrict to fertilized rows for the Biochar effect or fit `ols("y ~ C(Treatment)")` and use planned contrasts via `model.t_test()`.
- Post-hoc:
  - `pingouin.pairwise_tukey(data=df, dv=y, between="Treatment")` for pairwise.
  - `scikit_posthocs.posthoc_tukey` + helper for compact-letter display.
- Diagnostics: `scipy.stats.shapiro` on residuals, `scipy.stats.levene` for variance; log-transform if heteroscedastic.
- Outputs: `outputs/tables/anova_<response>.csv`, `outputs/tables/hsd_<response>.csv`.

### `scripts/03_correlation.py`
- Pearson and Spearman: `df[num_cols].corr(method="pearson"|"spearman")`.
- Heatmap with hierarchical clustering: `sns.clustermap(corr, cmap="vlag", center=0)`.
- Outputs: `outputs/figures/corr_pearson.png`, `corr_spearman.png`.

### `scripts/04_pca.py`
- Aggregate to treatment means, standardize with `StandardScaler`, fit `sklearn.decomposition.PCA`.
- Biplot (PC1 vs PC2) coloured by Soil, marker by Biochar; loadings as arrows.
- Optional `KMeans` on PC scores (k=2..4) with elbow plot from `inertia_`.
- Outputs: `outputs/figures/pca_biplot.png`, `pca_screeplot.png`.

### `scripts/05_nue_summary.py`
- Filter to fertilized treatments (T3–T8).
- `df.groupby(["Soil", "Biochar"])[nue_cols].agg(["mean", "sem"])` for `PFPN`, `Agronomic_NUE`, `Recovery_rate_N/P/K`, `Physiological_Efficiency`.
- Barplots with error bars via `seaborn.barplot(..., errorbar="se")` or `matplotlib.pyplot.bar` + `errorbar`.
- Outputs: `outputs/tables/nue_summary.csv`, `outputs/figures/nue_*.png`.

## 7. Conventions

- `np.random.seed(2025)` at the top of every analysis script.
- Figures: `plt.savefig(..., dpi=300, bbox_inches="tight")`, default size 6×4 in.
- Tables: `df.to_csv(..., index=False)`.
- All scripts assume the working directory is the repo root and use paths relative to it (`pathlib.Path`).
- Cleaned data is loaded via `pd.read_pickle("data/tpe25.pkl")["data"]`.

## 8. Hypotheses → tests

| Hypothesis                                              | Test                                                                 |
|---------------------------------------------------------|----------------------------------------------------------------------|
| H1 — Biochar boosts fertilizer effect                   | Fertilizer × Biochar interaction in three-way ANOVA; contrast T3 vs (T5,T6) and T4 vs (T7,T8) via `model.t_test()`. |
| H2 — Biochar benefits acidic soil more                  | Soil × Biochar interaction; contrast `(T5+T6 − T3) vs (T7+T8 − T4)`. |
| H3 — Rice husk ≈ Leucaena                               | Within fertilized rows, `ols("y ~ C(Soil) * C(Biochar)")` and contrast Rice_husk vs Leucaena per soil. |

## 9. Reproduce

```bash
python3 scripts/01_load_clean.py \
  && python3 scripts/02_anova_posthoc.py \
  && python3 scripts/03_correlation.py \
  && python3 scripts/04_pca.py \
  && python3 scripts/05_nue_summary.py
```

## 10. Source documents

| File                                                           | Drive ID                              |
|----------------------------------------------------------------|---------------------------------------|
| `2025TPE_raw.xlsx`                                             | `18nkWLbUGst67_rULvMb6QbfDULFGESXf`   |
| `Pot Expt-Plan-form_Tomato biochar pot study_2025 FINAL.pdf`   | `1u6pei4B1yrvSeF_sv1b2MZHG3phRQ2QG`   |
