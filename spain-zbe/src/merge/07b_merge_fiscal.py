"""
07b_merge_fiscal.py

Merge Hacienda fiscal variables onto the election panel for use in the
ZBE compliance analysis (script 12b).

For each municipality in the election panel, we attach pre-mandate fiscal
variables averaged over 2019-2020 (baseline period before the June 2021
Climate Change Law). This avoids post-treatment contamination.

Input:
    data/interim/hacienda_fiscal_panel.csv   (from 05c_)
    data/processed/election_panel.csv        (from 07_)

Output:
    data/processed/election_fiscal_panel.csv

Usage:
    python spain-zbe/src/merge/07b_merge_fiscal.py
"""

import os
import pandas as pd
import numpy as np

INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
PROCESSED_DIR = os.path.join("spain-zbe", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Baseline years: pre-mandate (Ley 7/2021 passed June 2021)
BASELINE_YEARS = [2019, 2020]

# Fiscal variables to merge (ratios + per-capita)
FISCAL_VARS = [
    "total_revenue",
    "own_revenue",
    "transfers_current",
    "transfers_capital",
    "transfers_state",
    "transfers_ccaa",
    "transfers_eu",
    "total_expenditure",
    "debt_service",
    "capital_spending",
    "transfer_dependency",
    "debt_burden",
    "eu_transfer_share",
    "own_revenue_share",
    "capital_share",
    "revenue_pc",
    "own_revenue_pc",
    "transfers_pc",
    "debt_service_pc",
    "capital_spending_pc",
]


def load_fiscal():
    """Load fiscal panel."""
    path = os.path.join(INTERIM_DIR, "hacienda_fiscal_panel.csv")
    df = pd.read_csv(path, dtype={"cod_ine": str})
    df["cod_ine"] = df["cod_ine"].str.zfill(5)
    print(f"  Fiscal panel: {len(df)} rows, "
          f"{df['cod_ine'].nunique()} municipalities, "
          f"years {sorted(df['year'].unique())}")
    return df


def compute_baseline(fiscal_df):
    """
    Compute baseline (pre-mandate) fiscal characteristics by averaging
    over BASELINE_YEARS.
    """
    baseline = fiscal_df[fiscal_df["year"].isin(BASELINE_YEARS)].copy()
    print(f"  Baseline years {BASELINE_YEARS}: {len(baseline)} obs")

    # Keep only the fiscal variables we need
    available = [v for v in FISCAL_VARS if v in baseline.columns]
    missing = [v for v in FISCAL_VARS if v not in baseline.columns]
    if missing:
        print(f"  Warning: missing columns: {missing}")

    # Average over baseline years
    agg = baseline.groupby("cod_ine")[available].mean()
    agg = agg.reset_index()

    # Add prefix to avoid column name conflicts
    rename = {v: f"fiscal_{v}" for v in available}
    agg = agg.rename(columns=rename)

    print(f"  Baseline fiscal profiles: {len(agg)} municipalities")
    return agg


def main():
    print("=" * 70)
    print("Stage 3c: Merge Fiscal Variables onto Election Panel")
    print("=" * 70)

    # Load
    fiscal_df = load_fiscal()
    baseline = compute_baseline(fiscal_df)

    election_path = os.path.join(PROCESSED_DIR, "election_panel.csv")
    election = pd.read_csv(election_path, dtype={"cod_ine": str})
    election["cod_ine"] = election["cod_ine"].str.zfill(5)
    print(f"  Election panel: {len(election)} rows, "
          f"{election['cod_ine'].nunique()} municipalities")

    # Merge
    merged = election.merge(baseline, on="cod_ine", how="left")

    # Coverage
    fiscal_cols = [c for c in merged.columns if c.startswith("fiscal_")]
    has_fiscal = merged[fiscal_cols[0]].notna().sum() if fiscal_cols else 0
    total = len(merged)
    print(f"\n  Merged: {total} rows, fiscal data matched: "
          f"{has_fiscal} ({has_fiscal/total:.1%})")

    # Coverage for >50k municipalities
    if "above_50k" in merged.columns:
        above = merged[merged["above_50k"] == True]
        above_fiscal = above[fiscal_cols[0]].notna().sum() if fiscal_cols else 0
        print(f"  Above 50k: {len(above)} rows, fiscal matched: "
              f"{above_fiscal} ({above_fiscal/len(above):.1%})")

    # Summary stats for >50k municipalities (2019 election year)
    sub = merged[(merged.get("above_50k", False) == True) &
                 (merged["year"] == 2019)]
    if not sub.empty and fiscal_cols:
        print(f"\n  Fiscal summary for >50k municipalities (N={len(sub)}):")
        for var in ["fiscal_transfer_dependency", "fiscal_debt_burden",
                     "fiscal_eu_transfer_share", "fiscal_own_revenue_share"]:
            if var in sub.columns:
                vals = sub[var].dropna()
                print(f"    {var:40s}  mean={vals.mean():.3f}  "
                      f"sd={vals.std():.3f}  "
                      f"min={vals.min():.3f}  max={vals.max():.3f}")

    # Save
    out_path = os.path.join(PROCESSED_DIR, "election_fiscal_panel.csv")
    merged.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    print(f"    {len(merged)} rows × {len(merged.columns)} columns")

    print("\n" + "=" * 70)
    print("Next: run 12b_fiscal_zbe_adoption.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
