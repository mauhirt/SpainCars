"""
05d_clean_mitma_zbe_funds.py

Clean BDNS ZBE fund allocation data: extract INE municipal codes from
beneficiary CIF numbers, aggregate amounts by municipality across calls.

CIF format for Spanish municipalities: Pddmmmcc
  P = prefix letter
  dd = 2-digit province code
  mmm = 3-digit municipality code
  cc = check digits + letter
  => INE code = dd + mmm (5 digits, zero-padded)

Input:
    data/raw/mitma_zbe_funds/bdns_zbe_concesiones.json  (from 03c_)

Output:
    data/interim/mitma_zbe_funds.csv
        Columns: cod_ine, name, total_eu_funds, eu_funds_2021, eu_funds_2022,
                 n_grants, eu_funds_pc (if population available)

Usage:
    python spain-zbe/src/clean/05d_clean_mitma_zbe_funds.py
"""

import json
import os
from collections import defaultdict

import pandas as pd

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "mitma_zbe_funds")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

# Special CIF mappings for non-standard entities
SPECIAL_CIF = {
    "S7900010E": "52001",  # Ciudad Autónoma de Melilla
    "S3500010G": "51001",  # Ciudad Autónoma de Ceuta (if present)
}


def extract_cod_ine(cif):
    """Extract 5-digit INE municipal code from CIF."""
    if cif in SPECIAL_CIF:
        return SPECIAL_CIF[cif]
    if cif.startswith("P") and len(cif) == 9:
        return cif[1:3] + cif[3:6]
    return None


if __name__ == "__main__":
    print("=" * 70)
    print("Clean BDNS ZBE Fund Allocations")
    print("=" * 70)

    # Load raw data
    raw_path = os.path.join(RAW_DIR, "bdns_zbe_concesiones.json")
    with open(raw_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"  Loaded {len(records)} raw records")

    # Extract and aggregate
    mun_data = defaultdict(lambda: {
        "name": "",
        "total": 0.0,
        "by_year": defaultdict(float),
        "n_grants": 0,
    })
    skipped = []

    for r in records:
        ben = r["beneficiario"]
        parts = ben.split(" ", 1)
        cif = parts[0]
        name = parts[1].strip() if len(parts) > 1 else ""

        cod_ine = extract_cod_ine(cif)
        if cod_ine is None:
            skipped.append(ben)
            continue

        entry = mun_data[cod_ine]
        entry["name"] = name
        entry["total"] += r["importe"]
        entry["by_year"][r["convocatoria_year"]] += r["importe"]
        entry["n_grants"] += 1

    if skipped:
        print(f"  Skipped {len(skipped)} records with unrecognized CIF:")
        for s in skipped:
            print(f"    {s}")

    # Build DataFrame
    rows = []
    for cod_ine, d in sorted(mun_data.items()):
        rows.append({
            "cod_ine": cod_ine,
            "name": d["name"],
            "total_eu_funds": d["total"],
            "eu_funds_2021": d["by_year"].get(2021, 0.0),
            "eu_funds_2022": d["by_year"].get(2022, 0.0),
            "n_grants": d["n_grants"],
        })
    df = pd.DataFrame(rows)

    # Try to add per-capita measure using INE population
    pop_path = os.path.join(INTERIM_DIR, "hacienda_fiscal_panel.csv")
    if os.path.exists(pop_path):
        pop = pd.read_csv(pop_path, dtype={"cod_ine": str})
        pop["cod_ine"] = pop["cod_ine"].str.zfill(5)
        # Use 2021 population (year of the first call)
        pop_2021 = pop[pop["year"] == 2021][["cod_ine", "poblacion_hda"]].copy()
        if pop_2021.empty:
            pop_2021 = pop[pop["year"] == 2020][["cod_ine", "poblacion_hda"]].copy()
        df = df.merge(pop_2021, on="cod_ine", how="left")
        df["eu_funds_pc"] = df["total_eu_funds"] / df["poblacion_hda"]
        matched = df["poblacion_hda"].notna().sum()
        print(f"  Population matched: {matched}/{len(df)}")
        df = df.drop(columns=["poblacion_hda"])
    else:
        print("  No fiscal panel found for population — skipping per-capita")

    # Save
    out_path = os.path.join(INTERIM_DIR, "mitma_zbe_funds.csv")
    df.to_csv(out_path, index=False)
    print(f"\n  Saved {len(df)} municipalities to {out_path}")

    # Summary stats
    print(f"\n  Unique municipalities: {len(df)}")
    print(f"  Total funds: EUR {df['total_eu_funds'].sum():,.0f}")
    print(f"  Mean per municipality: EUR {df['total_eu_funds'].mean():,.0f}")
    print(f"  Median: EUR {df['total_eu_funds'].median():,.0f}")
    print(f"  Max: EUR {df['total_eu_funds'].max():,.0f} "
          f"({df.loc[df['total_eu_funds'].idxmax(), 'name']})")
    in_both = (df["eu_funds_2021"] > 0) & (df["eu_funds_2022"] > 0)
    print(f"  In both calls: {in_both.sum()}")
    print(f"  2021 only: {((df['eu_funds_2021'] > 0) & (df['eu_funds_2022'] == 0)).sum()}")
    print(f"  2022 only: {((df['eu_funds_2021'] == 0) & (df['eu_funds_2022'] > 0)).sum()}")

    print("\n" + "=" * 70)
    print("Next: run 07c_merge_eu_funds.py")
    print("=" * 70)
