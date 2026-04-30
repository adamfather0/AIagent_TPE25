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
│   ├── 01_load_clean.R
│   ├── 02_anova_posthoc.R
│   ├── 03_correlation.R
│   ├── 04_pca.R
│   └── 05_nue_summary.R
└── outputs/
    ├── figures/                    # 300 dpi PNGs from each script
    └── tables/                     # ANOVA + post-hoc CSVs
```

Scripts beyond `01_load_clean.R` are written on-demand in subsequent sessions.

## 5. Analysis stack

R ≥ 4.3. Install once:

```r
install.packages(c(
  "tidyverse", "readxl", "janitor",
  "agricolae", "emmeans", "car",
  "corrplot", "FactoMineR", "factoextra",
  "ggplot2", "patchwork"
))
```

## 6. Analysis workflow

### `scripts/01_load_clean.R`
- `readxl::read_excel("data/2025TPE_raw.xlsx", skip = 1)` then drop the units row, OR read with `col_types` and discard row 1 of the data.
- `janitor::clean_names()` for safe column names.
- Recode `"#VALUE!"` → `NA`; coerce numerics.
- Set factor order: `Treatment` = T1..T8; `Soil` = Red_soil, Alluvial_soil; `Biochar` = NO, Rice_husk, Leucaena; `Fertilizer` = NO, YES.
- `saveRDS(df, "data/tpe25.rds")` for downstream scripts.

### `scripts/02_anova_posthoc.R`
- Three-way ANOVA per response: `lm(y ~ Soil * Fertilizer * Biochar, data = df)` then `car::Anova(., type = "III")`.
- Where Biochar is nested under Fertilizer = YES (T1/T2 have no biochar level), restrict to fertilized rows for the Biochar effect, or model the 8 treatments as `lm(y ~ Treatment)` and use planned contrasts.
- Post-hoc:
  - `agricolae::HSD.test(model, "Treatment", group = TRUE)` for letter groupings.
  - `emmeans(model, pairwise ~ Soil | Biochar)` for interaction probes.
- Diagnostics: `plot(model)`, Shapiro–Wilk, Levene; log-transform if heteroscedastic.
- Outputs: `outputs/tables/anova_<response>.csv`, `outputs/tables/hsd_<response>.csv`.

### `scripts/03_correlation.R`
- Pearson and Spearman matrices on numeric columns.
- `corrplot::corrplot(..., order = "hclust")`.
- Output: `outputs/figures/corr_pearson.png`, `corr_spearman.png`.

### `scripts/04_pca.R`
- Aggregate to treatment means, scale, `FactoMineR::PCA()`.
- `factoextra::fviz_pca_biplot()` colored by Soil and shaped by Biochar.
- Optional k-means (k = 2..4) on PC scores; elbow plot.
- Outputs: `outputs/figures/pca_biplot.png`, `pca_screeplot.png`.

### `scripts/05_nue_summary.R`
- Filter to fertilized treatments (T3–T8).
- Group by Soil × Biochar; mean ± SE for `PFPN`, `Agronomic NUE`, `Recovery_rate_N/P/K`, `Physiological Efficiency`.
- Barplots with error bars (`geom_col` + `geom_errorbar`).
- Outputs: `outputs/tables/nue_summary.csv`, `outputs/figures/nue_*.png`.

## 7. Conventions

- `set.seed(2025)` at the top of every analysis script.
- Figures: `ggsave(..., width = 6, height = 4, dpi = 300)`.
- Tables: `readr::write_csv()`.
- All scripts assume the working directory is the repo root and use paths relative to it.

## 8. Hypotheses → tests

| Hypothesis                                              | Test                                                                 |
|---------------------------------------------------------|----------------------------------------------------------------------|
| H1 — Biochar boosts fertilizer effect                   | Fertilizer × Biochar interaction in three-way ANOVA; contrast T3 vs (T5,T6) and T4 vs (T7,T8). |
| H2 — Biochar benefits acidic soil more                  | Soil × Biochar interaction; emmeans contrast `(T5+T6 − T3) vs (T7+T8 − T4)`. |
| H3 — Rice husk ≈ Leucaena                               | Within fertilized rows, `lm(y ~ Soil * Biochar)` and contrast Rice_husk vs Leucaena per soil. |

## 9. Reproduce

```bash
Rscript scripts/01_load_clean.R \
  && Rscript scripts/02_anova_posthoc.R \
  && Rscript scripts/03_correlation.R \
  && Rscript scripts/04_pca.R \
  && Rscript scripts/05_nue_summary.R
```

## 10. Source documents

| File                                                           | Drive ID                              |
|----------------------------------------------------------------|---------------------------------------|
| `2025TPE_raw.xlsx`                                             | `18nkWLbUGst67_rULvMb6QbfDULFGESXf`   |
| `Pot Expt-Plan-form_Tomato biochar pot study_2025 FINAL.pdf`   | `1u6pei4B1yrvSeF_sv1b2MZHG3phRQ2QG`   |
