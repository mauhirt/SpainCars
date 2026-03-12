"""
05c_clean_hacienda_fiscal.py

Parse downloaded Hacienda CONPREL Access databases and extract municipal-level
fiscal variables for the ZBE compliance analysis.

Input:  data/raw/hacienda_fiscal/Liquidaciones{year}.zip  (from 03b_)
Output: data/interim/hacienda_fiscal_panel.csv

Key variables constructed:
  - total_revenue: total liquidated revenue (chapters 1-7)
  - own_revenue: own taxes + fees (chapters 1-3)
  - transfers_current: current transfers received (chapter 4)
  - transfers_capital: capital transfers received (chapter 7)
  - transfers_state: from central government (sub-chapters 42 + 72)
  - transfers_ccaa: from regional government (sub-chapters 45 + 75)
  - transfers_eu: from exterior/EU (sub-chapters 49 + 79)
  - total_expenditure: total liquidated expenditure (chapters 1-7)
  - debt_service: financial expenditure (chapter 3, expense side)
  - capital_spending: investment (chapter 6, expense side)
  - transfer_dependency: transfers / total_revenue
  - debt_burden: debt_service / total_revenue
  - eu_transfer_share: transfers_eu / total_revenue

Usage:
    python src/clean/05c_clean_hacienda_fiscal.py
"""

import os
import sys
import zipfile
import pandas as pd
import numpy as np

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "hacienda_fiscal")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

YEARS = [2019, 2020, 2021, 2022, 2023]


def parse_accdb(accdb_path: str) -> tuple:
    """
    Parse an Access database file using access_parser.
    Returns (inventory_df, economic_df) DataFrames.
    """
    from access_parser import AccessParser

    db = AccessParser(accdb_path)

    # Parse inventory (entity registry)
    inv_raw = db.parse_table("tb_inventario")
    inv = pd.DataFrame(inv_raw)
    for c in inv.columns:
        inv[c] = inv[c].astype(str).str.strip()

    # Parse economic data (revenue + expenditure)
    eco_raw = db.parse_table("tb_economica")
    eco = pd.DataFrame(eco_raw)
    for c in eco.columns:
        eco[c] = eco[c].astype(str).str.strip()

    return inv, eco


def extract_fiscal_variables(inv: pd.DataFrame, eco: pd.DataFrame) -> pd.DataFrame:
    """
    Extract municipality-level fiscal variables from the parsed Access tables.

    We keep only Ayuntamiento entities (codente ending in 'AA000') to avoid
    double-counting with autonomous organisms.
    """
    # Filter inventory to Ayuntamiento entities only
    ayto = inv[inv["codente"].str.endswith("AA000")].copy()
    ayto["cod_ine"] = ayto["codente"].str[:5]
    ayto["poblacion_hda"] = pd.to_numeric(
        ayto["poblacion"].str.rstrip("."), errors="coerce"
    )

    # Build idente -> cod_ine mapping
    id_map = ayto.set_index("idente")["cod_ine"].to_dict()

    # Map idente to cod_ine in economic data
    eco["cod_ine"] = eco["idente"].map(id_map)
    eco = eco.dropna(subset=["cod_ine"]).copy()

    # Parse numeric columns
    for col in ["imported", "importer", "importel", "importec"]:
        eco[col] = pd.to_numeric(eco[col], errors="coerce").fillna(0)

    # We use 'importel' = liquidated amount (derechos reconocidos netos for
    # revenue, obligaciones reconocidas netas for expenditure)

    # ─── Revenue aggregation ───
    rev = eco[eco["tipreig"] == "I"].copy()

    # Chapter-level sums (1-digit cdcta)
    rev_ch = rev[rev["cdcta"].str.len() == 1].copy()
    rev_ch["chapter"] = rev_ch["cdcta"].astype(int)

    rev_agg = rev_ch.groupby(["cod_ine", "chapter"])["importel"].sum().unstack(
        fill_value=0
    )

    # Ensure all needed columns exist
    for ch in range(1, 10):
        if ch not in rev_agg.columns:
            rev_agg[ch] = 0.0

    result = pd.DataFrame(index=rev_agg.index)
    result["own_revenue"] = rev_agg[1] + rev_agg[2] + rev_agg[3]
    result["transfers_current"] = rev_agg[4]
    result["transfers_capital"] = rev_agg[7]
    result["total_revenue"] = rev_agg[[1, 2, 3, 4, 5, 6, 7]].sum(axis=1)
    result["revenue_ch9_debt"] = rev_agg[9]  # new borrowing

    # Sub-chapter detail for transfers (2-digit codes)
    rev_sub = rev[rev["cdcta"].str.len() == 2].copy()
    rev_sub["subch"] = rev_sub["cdcta"].str.strip()

    sub_agg = rev_sub.groupby(["cod_ine", "subch"])["importel"].sum().unstack(
        fill_value=0
    )

    # State transfers (42 = current from Estado, 72 = capital from Estado)
    for code in ["42", "45", "49", "72", "75", "79"]:
        if code not in sub_agg.columns:
            sub_agg[code] = 0.0

    result["transfers_state"] = (
        sub_agg.get("42", 0).reindex(result.index, fill_value=0)
        + sub_agg.get("72", 0).reindex(result.index, fill_value=0)
    )
    result["transfers_ccaa"] = (
        sub_agg.get("45", 0).reindex(result.index, fill_value=0)
        + sub_agg.get("75", 0).reindex(result.index, fill_value=0)
    )
    result["transfers_eu"] = (
        sub_agg.get("49", 0).reindex(result.index, fill_value=0)
        + sub_agg.get("79", 0).reindex(result.index, fill_value=0)
    )

    # ─── Expenditure aggregation ───
    exp = eco[eco["tipreig"] == "G"].copy()
    exp_ch = exp[exp["cdcta"].str.len() == 1].copy()
    exp_ch["chapter"] = exp_ch["cdcta"].astype(int)

    exp_agg = exp_ch.groupby(["cod_ine", "chapter"])["importel"].sum().unstack(
        fill_value=0
    )

    for ch in range(1, 10):
        if ch not in exp_agg.columns:
            exp_agg[ch] = 0.0

    result["total_expenditure"] = exp_agg[[1, 2, 3, 4, 5, 6, 7]].sum(axis=1)
    result["debt_service"] = exp_agg[3].reindex(result.index, fill_value=0)
    result["capital_spending"] = exp_agg[6].reindex(result.index, fill_value=0)

    # ─── Derived ratios ───
    safe_rev = result["total_revenue"].replace(0, np.nan)
    result["transfer_dependency"] = (
        result["transfers_current"] + result["transfers_capital"]
    ) / safe_rev
    result["debt_burden"] = result["debt_service"] / safe_rev
    result["eu_transfer_share"] = result["transfers_eu"] / safe_rev
    result["own_revenue_share"] = result["own_revenue"] / safe_rev
    result["capital_share"] = result["capital_spending"] / result[
        "total_expenditure"
    ].replace(0, np.nan)

    # Add population from inventory
    pop_map = ayto.set_index("cod_ine")["poblacion_hda"]
    # Handle duplicates by taking the first
    pop_map = pop_map[~pop_map.index.duplicated(keep="first")]
    result["poblacion_hda"] = pop_map.reindex(result.index)

    # Per-capita variables
    safe_pop = result["poblacion_hda"].replace(0, np.nan)
    result["revenue_pc"] = result["total_revenue"] / safe_pop
    result["own_revenue_pc"] = result["own_revenue"] / safe_pop
    result["transfers_pc"] = (
        result["transfers_current"] + result["transfers_capital"]
    ) / safe_pop
    result["debt_service_pc"] = result["debt_service"] / safe_pop
    result["capital_spending_pc"] = result["capital_spending"] / safe_pop

    result = result.reset_index()
    return result


def process_year(year: int) -> pd.DataFrame:
    """Process one year's ZIP → fiscal panel."""
    zip_path = os.path.join(RAW_DIR, f"Liquidaciones{year}.zip")
    if not os.path.exists(zip_path):
        print(f"  {zip_path} not found, skipping {year}.")
        return pd.DataFrame()

    print(f"  Processing {year}...")

    # Extract accdb/mdb from ZIP
    with zipfile.ZipFile(zip_path, "r") as zf:
        db_names = [n for n in zf.namelist()
                     if n.endswith(".accdb") or n.endswith(".mdb")]
        if not db_names:
            print(f"    No .accdb/.mdb file found in {zip_path}")
            return pd.DataFrame()
        db_name = db_names[0]
        extract_dir = os.path.join(RAW_DIR, f"extracted_{year}")
        os.makedirs(extract_dir, exist_ok=True)
        zf.extract(db_name, extract_dir)
        accdb_path = os.path.join(extract_dir, db_name)

    # Parse
    inv, eco = parse_accdb(accdb_path)
    print(f"    Entities in inventory: {len(inv)}")
    print(f"    Economic records: {len(eco)}")

    # Extract variables
    df = extract_fiscal_variables(inv, eco)
    df["year"] = year
    print(f"    Municipalities extracted: {len(df)}")

    # Clean up extracted file
    try:
        os.remove(accdb_path)
        os.rmdir(extract_dir)
    except OSError:
        pass

    return df


if __name__ == "__main__":
    print("=" * 70)
    print("Hacienda Fiscal Data — Clean & Extract")
    print("=" * 70)

    panels = []
    for year in YEARS:
        df = process_year(year)
        if not df.empty:
            panels.append(df)

    if panels:
        panel = pd.concat(panels, ignore_index=True)
        panel = panel.sort_values(["cod_ine", "year"]).reset_index(drop=True)

        # Summary
        print(f"\n  Final panel: {panel.shape}")
        print(f"  Years: {sorted(panel['year'].unique())}")
        print(f"  Municipalities: {panel['cod_ine'].nunique()}")

        # Quick sanity check: Madrid
        madrid = panel[panel["cod_ine"] == "28079"]
        if not madrid.empty:
            row = madrid.iloc[-1]
            print(f"\n  Sanity check — Madrid ({int(row['year'])}):")
            print(f"    Total revenue:       EUR {row['total_revenue']:>15,.0f}")
            print(f"    Own revenue:         EUR {row['own_revenue']:>15,.0f}")
            print(f"    Transfer dependency: {row['transfer_dependency']:.1%}")
            print(f"    Debt burden:         {row['debt_burden']:.1%}")
            print(f"    EU transfers:        EUR {row['transfers_eu']:>15,.0f}")

        # Save
        out_path = os.path.join(INTERIM_DIR, "hacienda_fiscal_panel.csv")
        panel.to_csv(out_path, index=False)
        print(f"\n  Saved to {out_path}")
    else:
        print("\n  No data processed. Run 03b_download_hacienda_fiscal.py first.")

    print("\n" + "=" * 70)
    print("Next: run 07b_merge_fiscal.py")
    print("=" * 70)
