"""
07_merge_election_panel.py

Merge INE population data with cleaned municipal election results to create
an analysis-ready municipality-election panel for voting outcomes.

Merge key: cod_ine (with population matched to election year or closest
available year when exact match is unavailable).

Input:
    data/interim/ine_population_panel.csv
    data/interim/elections_municipal_panel.csv        (2015, 2019 from DAT files)
    data/interim/elections_municipal_2023.csv          (2023 municipal from Excel)
    data/interim/elections_congress_2023.csv           (2023 congress from Excel)

Output:
    data/processed/election_panel.csv
    data/processed/congress_panel.csv

Usage:
    python spain-zbe/src/merge/07_merge_election_panel.py
"""

import os
import pandas as pd
import numpy as np

INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
PROCESSED_DIR = os.path.join("spain-zbe", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_population():
    """Load INE population panel with standardised cod_ine."""
    path = os.path.join(INTERIM_DIR, "ine_population_panel.csv")
    df = pd.read_csv(path)
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df["cod_provincia"] = df["cod_ine"].str[:2]
    print(f"  Population: {len(df)} rows, "
          f"years {sorted(df['year'].unique())}, "
          f"{df['cod_ine'].nunique()} municipalities")
    return df


def load_elections():
    """Load elections panel with standardised cod_ine (2015, 2019 + 2023)."""
    # Load 2015/2019 from DAT-parsed file
    path_dat = os.path.join(INTERIM_DIR, "elections_municipal_panel.csv")
    df_dat = pd.read_csv(path_dat)
    df_dat["cod_ine"] = df_dat["cod_ine"].astype(str).str.zfill(5)
    df_dat["cod_provincia"] = df_dat["cod_ine"].str[:2]
    print(f"  Elections (DAT 2015/2019): {len(df_dat)} rows, "
          f"years {sorted(df_dat['year'].unique())}")

    # Load 2023 municipal from Excel-parsed file
    path_2023 = os.path.join(INTERIM_DIR, "elections_municipal_2023.csv")
    if os.path.exists(path_2023):
        df_2023 = pd.read_csv(path_2023)
        df_2023["cod_ine"] = df_2023["cod_ine"].astype(str).str.zfill(5)
        df_2023["cod_provincia"] = df_2023["cod_ine"].str[:2]
        print(f"  Elections (Excel 2023 municipal): {len(df_2023)} rows")

        # Harmonise columns: rename to match DAT format
        # The 2023 Excel doesn't have seats data — that's OK
        df_2023 = df_2023.rename(columns={})  # no renames needed, schema matches
        df_dat = pd.concat([df_dat, df_2023], ignore_index=True)
    else:
        print(f"  Warning: {path_2023} not found — 2023 municipal data missing")

    print(f"  Combined elections: {len(df_dat)} rows, "
          f"years {sorted(df_dat['year'].unique())}, "
          f"{df_dat['cod_ine'].nunique()} municipalities")
    return df_dat


def load_congress():
    """Load 2023 congress election data."""
    path = os.path.join(INTERIM_DIR, "elections_congress_2023.csv")
    if not os.path.exists(path):
        print(f"  Congress data not found: {path}")
        return None
    df = pd.read_csv(path)
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df["cod_provincia"] = df["cod_ine"].str[:2]
    print(f"  Congress 2023: {len(df)} rows")
    return df


def get_population_for_election(pop_df, election_year, pop_years):
    """
    Get population for a given election year.

    If the exact year is available, use it. Otherwise use the closest
    available year (preferring the year just before the election).
    """
    if election_year in pop_years:
        return pop_df[pop_df["year"] == election_year].copy()

    # Find closest available year (prefer earlier year)
    earlier = [y for y in pop_years if y <= election_year]
    later = [y for y in pop_years if y > election_year]

    if earlier:
        best_year = max(earlier)
    elif later:
        best_year = min(later)
    else:
        return None

    print(f"    Population year {election_year} not available; "
          f"using {best_year} instead")
    subset = pop_df[pop_df["year"] == best_year].copy()
    subset["pop_year_used"] = best_year
    return subset


def merge_election_panel(pop_df, elections_df):
    """
    Merge population data onto election results for each election year.

    For each election year, finds the matching (or closest) population year
    and merges on cod_ine.
    """
    pop_years = sorted(pop_df["year"].unique())
    election_years = sorted(elections_df["year"].unique())

    panels = []
    for eyear in election_years:
        print(f"\n  Processing election year {eyear}:")
        elec_subset = elections_df[elections_df["year"] == eyear].copy()

        pop_subset = get_population_for_election(pop_df, eyear, pop_years)
        if pop_subset is None:
            print(f"    No population data available — skipping {eyear}")
            continue

        # Population columns to merge
        pop_merge = pop_subset[["cod_ine", "poblacion", "above_50k",
                                "pop_distance_50k"]].copy()
        if "pop_year_used" in pop_subset.columns:
            pop_merge["pop_year_used"] = pop_subset["pop_year_used"].values

        # Election columns (drop cod_provincia/municipio duplication handled below)
        elec_cols = ["cod_ine", "cod_provincia", "municipio", "year",
                     "total_votes",
                     "votos_pp", "votos_psoe", "votos_vox",
                     "votos_cs", "votos_up",
                     "share_pp", "share_psoe", "share_vox",
                     "share_cs", "share_up",
                     "seats_pp", "seats_psoe", "seats_vox",
                     "seats_cs", "seats_up"]
        # Only keep columns that actually exist
        elec_cols = [c for c in elec_cols if c in elec_subset.columns]
        elec_merge = elec_subset[elec_cols].copy()

        # Merge
        merged = elec_merge.merge(pop_merge, on="cod_ine", how="left")

        n_matched = merged["poblacion"].notna().sum()
        n_total = len(merged)
        print(f"    Merged: {n_total} municipalities, "
              f"population matched: {n_matched} ({n_matched/n_total:.1%})")

        panels.append(merged)

    if not panels:
        return pd.DataFrame()

    panel = pd.concat(panels, ignore_index=True)
    panel = panel.sort_values(["year", "cod_ine"]).reset_index(drop=True)

    # Reorder columns: identifiers first, then population, then election data
    id_cols = ["cod_ine", "cod_provincia", "municipio", "year"]
    pop_cols = ["poblacion", "above_50k", "pop_distance_50k"]
    if "pop_year_used" in panel.columns:
        pop_cols.append("pop_year_used")
    remaining = [c for c in panel.columns
                 if c not in id_cols and c not in pop_cols]
    panel = panel[id_cols + pop_cols + remaining]

    return panel


def merge_single_year_panel(pop_df, single_year_df, year_label):
    """Merge population onto a single-year election DataFrame."""
    pop_years = sorted(pop_df["year"].unique())
    pop_subset = get_population_for_election(pop_df, single_year_df["year"].iloc[0],
                                              pop_years)
    if pop_subset is None:
        return single_year_df

    pop_merge = pop_subset[["cod_ine", "poblacion", "above_50k",
                            "pop_distance_50k"]].copy()
    if "pop_year_used" in pop_subset.columns:
        pop_merge["pop_year_used"] = pop_subset["pop_year_used"].values

    merged = single_year_df.merge(pop_merge, on="cod_ine", how="left")
    n_matched = merged["poblacion"].notna().sum()
    print(f"  {year_label}: {len(merged)} municipalities, "
          f"population matched: {n_matched} ({n_matched/len(merged):.1%})")
    return merged


def main():
    print("=" * 70)
    print("Stage 3b: Merge Election Panel (Municipality-Election)")
    print("=" * 70)

    pop_df = load_population()
    elections_df = load_elections()
    panel = merge_election_panel(pop_df, elections_df)

    if panel.empty:
        print("\n  No data merged — check inputs.")
        return

    # Summary
    n_total = len(panel)
    n_munis = panel["cod_ine"].nunique()
    election_years = sorted(panel["year"].unique())

    print(f"\n  Final panel: {n_total} rows ({n_munis} municipalities × "
          f"{len(election_years)} elections)")
    print(f"  Election years: {election_years}")

    # Above/below 50k breakdown
    matched = panel[panel["poblacion"].notna()]
    above = matched[matched["above_50k"] == True]
    below = matched[matched["above_50k"] == False]
    print(f"  Above 50k: {above['cod_ine'].nunique()} municipalities")
    print(f"  Below 50k: {below['cod_ine'].nunique()} municipalities")

    # Vox stats
    if "share_vox" in panel.columns:
        for yr in election_years:
            yr_data = panel[panel["year"] == yr]
            vox_present = (yr_data["votos_vox"] > 0).sum()
            vox_mean = yr_data["share_vox"].mean()
            print(f"  {yr}: Vox ran in {vox_present}/{len(yr_data)} munis, "
                  f"mean share={vox_mean:.3%}")

    # Save
    output_path = os.path.join(PROCESSED_DIR, "election_panel.csv")
    panel.to_csv(output_path, index=False)
    print(f"\n  Saved: {output_path}")
    print(f"    {len(panel)} rows × {len(panel.columns)} columns")
    print(f"    Columns: {panel.columns.tolist()}")

    # ---------------------------------------------------------------
    # Congress panel (robustness)
    # ---------------------------------------------------------------
    congress_df = load_congress()
    if congress_df is not None:
        print("\n  --- Congress Panel ---")
        congress_panel = merge_single_year_panel(pop_df, congress_df,
                                                  "Congress 2023")

        # Reorder columns
        id_cols = ["cod_ine", "cod_provincia", "municipio", "year"]
        pop_cols = ["poblacion", "above_50k", "pop_distance_50k"]
        if "pop_year_used" in congress_panel.columns:
            pop_cols.append("pop_year_used")
        remaining = [c for c in congress_panel.columns
                     if c not in id_cols and c not in pop_cols]
        ordered = [c for c in id_cols + pop_cols + remaining
                   if c in congress_panel.columns]
        congress_panel = congress_panel[ordered]

        cong_path = os.path.join(PROCESSED_DIR, "congress_panel.csv")
        congress_panel.to_csv(cong_path, index=False)
        print(f"  Saved: {cong_path}")
        print(f"    {len(congress_panel)} rows × {len(congress_panel.columns)} columns")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
