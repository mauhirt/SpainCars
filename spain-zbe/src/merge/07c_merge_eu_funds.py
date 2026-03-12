"""
07c_merge_eu_funds.py

Merge EU fund allocation data onto the election-fiscal panel for use in
the ZBE compliance analysis (script 12b).

Input:
    data/interim/mitma_zbe_funds.csv              (from 05d_)
    data/processed/election_fiscal_panel.csv      (from 07b_)

Output:
    data/processed/election_fiscal_panel.csv      (updated in place)

Usage:
    python spain-zbe/src/merge/07c_merge_eu_funds.py
"""

import os
import pandas as pd

INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
PROCESSED_DIR = os.path.join("spain-zbe", "data", "processed")

EU_FUND_VARS = [
    "total_eu_funds",
    "eu_funds_2021",
    "eu_funds_2022",
    "n_grants",
    "eu_funds_pc",
]


def main():
    print("=" * 70)
    print("Stage 3d: Merge EU Fund Allocations onto Election-Fiscal Panel")
    print("=" * 70)

    # Load EU fund data
    eu_path = os.path.join(INTERIM_DIR, "mitma_zbe_funds.csv")
    eu = pd.read_csv(eu_path, dtype={"cod_ine": str})
    eu["cod_ine"] = eu["cod_ine"].str.zfill(5)
    print(f"  EU funds: {len(eu)} municipalities")

    # Keep only merge columns
    available = [v for v in EU_FUND_VARS if v in eu.columns]
    eu_merge = eu[["cod_ine"] + available].copy()

    # No prefix needed — EU fund column names are already distinct
    # (total_eu_funds, eu_funds_2021, eu_funds_2022, n_grants, eu_funds_pc)

    # Load panel
    panel_path = os.path.join(PROCESSED_DIR, "election_fiscal_panel.csv")
    panel = pd.read_csv(panel_path, dtype={"cod_ine": str})
    panel["cod_ine"] = panel["cod_ine"].str.zfill(5)
    print(f"  Election-fiscal panel: {len(panel)} rows, "
          f"{panel['cod_ine'].nunique()} municipalities")

    # Drop existing EU fund columns if re-running
    existing_eu_cols = [c for c in panel.columns if c in EU_FUND_VARS
                        or c.startswith("eu_total_eu") or c == "eu_n_grants"]
    if existing_eu_cols:
        panel = panel.drop(columns=existing_eu_cols)
        print(f"  Dropped {len(existing_eu_cols)} existing EU fund columns")

    # Merge
    merged = panel.merge(eu_merge, on="cod_ine", how="left")

    # Fill NaN with 0 for fund amounts (no grant = zero funds)
    fund_cols = [c for c in merged.columns
                 if c.startswith("eu_funds") or c == "total_eu_funds"
                 or c == "n_grants"]
    for c in fund_cols:
        merged[c] = merged[c].fillna(0)

    # Coverage stats
    has_funds = (merged.get("total_eu_funds", merged.get("eu_total_eu_funds",
                 pd.Series([0])))) > 0
    if "total_eu_funds" in merged.columns:
        has_funds = merged["total_eu_funds"] > 0
    print(f"\n  Municipalities with EU funds: "
          f"{merged.loc[has_funds, 'cod_ine'].nunique()}")

    # Coverage for >50k
    if "above_50k" in merged.columns:
        above = merged[(merged["above_50k"] == True) &
                       (merged["year"] == 2019)]
        if "total_eu_funds" in above.columns:
            above_funded = (above["total_eu_funds"] > 0).sum()
            total_above = len(above)
            print(f"  >50k municipalities with EU funds: "
                  f"{above_funded}/{total_above} "
                  f"({above_funded/total_above:.1%})")
            print(f"    Mean EU funds (funded only): "
                  f"EUR {above[above['total_eu_funds'] > 0]['total_eu_funds'].mean():,.0f}")

    # Save
    merged.to_csv(panel_path, index=False)
    print(f"\n  Updated: {panel_path}")
    print(f"    {len(merged)} rows × {len(merged.columns)} columns")

    print("\n" + "=" * 70)
    print("Next: run 12b_fiscal_zbe_adoption.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
