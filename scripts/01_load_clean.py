"""01_load_clean.py — load and clean 2025 TPE pot experiment data.

Reads data/2025TPE_raw.xlsx (sheet "summary"), normalizes column names,
coerces numerics (treating "#VALUE!" as NaN), sets categorical levels for the
identifier columns, and writes data/tpe25.pkl as {"data": df, "units": df}.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path("data/2025TPE_raw.xlsx")
OUT_PATH = Path("data/tpe25.pkl")

ID_COLS = ["Treatment", "Rep", "Soil", "Biochar", "Fertilizer"]
TREATMENT_LEVELS = [f"T{i}" for i in range(1, 9)]
SOIL_LEVELS = ["Red_soil", "Alluvial_soil"]
BIOCHAR_LEVELS = ["NO", "Rice_husk", "Leucaena"]
FERT_LEVELS = ["NO", "YES"]
NA_TOKENS = ["", "NA", "#VALUE!", "#DIV/0!", "#N/A"]


def clean_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r"\*$", "", name)
    name = name.replace("/", "_")
    name = re.sub(r"\s+", "_", name)
    return name


def main() -> None:
    np.random.seed(2025)

    # Row 1 = headers, row 2 = units, data starts row 3.
    headers_raw = pd.read_excel(
        RAW_PATH, sheet_name="summary", header=None, nrows=1
    ).iloc[0].tolist()
    units_row = pd.read_excel(
        RAW_PATH, sheet_name="summary", header=None, skiprows=1, nrows=1
    ).iloc[0].tolist()

    df = pd.read_excel(
        RAW_PATH, sheet_name="summary", header=0, skiprows=[1],
        na_values=NA_TOKENS, keep_default_na=True,
    )

    headers = [clean_name(h) for h in headers_raw]
    assert df.shape[1] == len(headers), "Column count mismatch"
    df.columns = headers

    # Coerce all measurement columns to numeric.
    num_cols = [c for c in df.columns if c not in ID_COLS]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Trim string ID cols (preserves NaN via the nullable "string" dtype).
    for c in ("Treatment", "Soil", "Biochar", "Fertilizer"):
        df[c] = df[c].astype("string").str.strip()

    # Drop trailing summary / junk rows: keep only rows with Treatment in T1..T8.
    df = df[df["Treatment"].isin(TREATMENT_LEVELS)].reset_index(drop=True)
    rep_int = pd.to_numeric(df["Rep"], errors="coerce").astype("Int64")

    df["Treatment"] = pd.Categorical(df["Treatment"], categories=TREATMENT_LEVELS, ordered=True)
    df["Soil"] = pd.Categorical(df["Soil"], categories=SOIL_LEVELS)
    df["Biochar"] = pd.Categorical(df["Biochar"], categories=BIOCHAR_LEVELS)
    df["Fertilizer"] = pd.Categorical(df["Fertilizer"], categories=FERT_LEVELS)
    df["Rep"] = pd.Categorical(rep_int, categories=[1, 2, 3, 4], ordered=True)

    # Integrity report.
    print(f"Rows: {len(df)}  Cols: {df.shape[1]}")
    print("\nTreatment x Rep counts (4 reps x 8 treatments expected):")
    print(pd.crosstab(df["Treatment"], df["Rep"], margins=True))
    print("\nTop 15 columns by NA count:")
    print(df.isna().sum().sort_values(ascending=False).head(15))

    # Units lookup (id columns get None).
    units = pd.DataFrame({
        "column": headers,
        "unit": [str(u).strip() if pd.notna(u) else None for u in units_row],
    })
    units.loc[units["column"].isin(ID_COLS), "unit"] = None

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle({"data": df, "units": units}, OUT_PATH)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
