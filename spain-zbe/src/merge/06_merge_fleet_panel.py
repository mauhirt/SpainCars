"""
06_merge_fleet_panel.py

Merge INE population data with DGT municipal vehicle fleet data to create
an analysis-ready municipality-year panel for fleet outcomes.

Merge key: (cod_ine, year)

Input:
    data/interim/ine_population_panel.csv
    data/interim/dgt_fleet_labels_municipal.csv

Output:
    data/processed/fleet_panel.csv

Usage:
    python spain-zbe/src/merge/06_merge_fleet_panel.py
"""

import os
import pandas as pd

INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
PROCESSED_DIR = os.path.join("spain-zbe", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_population():
    """Load INE population panel with standardised cod_ine."""
    path = os.path.join(INTERIM_DIR, "ine_population_panel.csv")
    df = pd.read_csv(path)
    # Ensure cod_ine is a zero-padded 5-digit string
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df["cod_provincia"] = df["cod_ine"].str[:2]
    print(f"  Population: {len(df)} rows, "
          f"years {sorted(df['year'].unique())}, "
          f"{df['cod_ine'].nunique()} municipalities")
    return df


def load_fleet():
    """Load DGT municipal fleet panel with standardised cod_ine."""
    path = os.path.join(INTERIM_DIR, "dgt_fleet_labels_municipal.csv")
    df = pd.read_csv(path)
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df["cod_provincia"] = df["cod_ine"].str[:2]
    print(f"  Fleet: {len(df)} rows, "
          f"years {sorted(df['year'].unique())}, "
          f"{df['cod_ine'].nunique()} municipalities")
    return df


def merge_fleet_panel(pop_df, fleet_df):
    """
    Left-join fleet data onto the population panel on (cod_ine, year).

    Uses left join so that every municipality-year in the population data
    is preserved, even if DGT fleet data is missing for that observation.
    """
    # Keep only years present in fleet data for the merge base,
    # since fleet outcomes are only meaningful where fleet data exists.
    fleet_years = sorted(fleet_df["year"].unique())
    pop_subset = pop_df[pop_df["year"].isin(fleet_years)].copy()
    print(f"  Population subset (fleet years {fleet_years}): {len(pop_subset)} rows")

    # Select population columns for merge
    pop_cols = ["cod_ine", "year", "municipio", "poblacion",
                "cod_provincia", "above_50k", "pop_distance_50k"]
    pop_merge = pop_subset[pop_cols].copy()

    # Select fleet columns (drop duplicates with pop)
    fleet_cols = ["cod_ine", "year",
                  "b", "c", "eco", "cero", "sin_distintivo", "total",
                  "share_cero", "share_b", "share_c", "share_eco",
                  "share_sin_distintivo"]
    fleet_merge = fleet_df[fleet_cols].copy()

    # Merge
    panel = pop_merge.merge(fleet_merge, on=["cod_ine", "year"], how="left")

    # Sort
    panel = panel.sort_values(["cod_ine", "year"]).reset_index(drop=True)

    return panel


def main():
    print("=" * 70)
    print("Stage 3a: Merge Fleet Panel (Municipality-Year)")
    print("=" * 70)

    pop_df = load_population()
    fleet_df = load_fleet()
    panel = merge_fleet_panel(pop_df, fleet_df)

    # Summary statistics
    n_total = len(panel)
    n_matched = panel["total"].notna().sum()
    n_missing = panel["total"].isna().sum()
    n_munis = panel["cod_ine"].nunique()
    n_years = panel["year"].nunique()

    print(f"\n  Merged panel: {n_total} rows ({n_munis} municipalities × "
          f"{n_years} years)")
    print(f"  Fleet data matched: {n_matched} ({n_matched/n_total:.1%})")
    print(f"  Fleet data missing: {n_missing} ({n_missing/n_total:.1%})")

    # Above/below 50k breakdown
    above = panel[panel["above_50k"] == True]
    below = panel[panel["above_50k"] == False]
    print(f"  Above 50k: {above['cod_ine'].nunique()} municipalities, "
          f"{len(above)} obs")
    print(f"  Below 50k: {below['cod_ine'].nunique()} municipalities, "
          f"{len(below)} obs")

    # Save
    output_path = os.path.join(PROCESSED_DIR, "fleet_panel.csv")
    panel.to_csv(output_path, index=False)
    print(f"\n  Saved: {output_path}")
    print(f"    {len(panel)} rows × {len(panel.columns)} columns")
    print(f"    Columns: {panel.columns.tolist()}")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
