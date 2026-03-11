"""
01_download_ine_population.py

Download official municipal population figures (Cifras Oficiales de Población)
from the INE Padrón Municipal. This provides the running variable for the
regression discontinuity at the 50,000 inhabitant threshold.

Source: INE — Cifras oficiales de población de los municipios españoles:
        Revisión del Padrón Municipal
URL:    https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177011

Download method:
    INE bulk CSV download for Table 29005 ("Cifras oficiales del padrón
    por municipio"), which covers all 8,000+ municipalities from 1996 onward.

Usage:
    python src/download/01_download_ine_population.py
"""

import os
import sys
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR = os.path.join("data", "raw", "ine_population")
INTERIM_DIR = os.path.join("data", "interim")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)

# Table 29005: "Cifras oficiales del padrón por municipio"
# All municipalities × sex × year (1996–present), ~730k rows
TABLE_ID = "29005"
CSV_URL = f"https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{TABLE_ID}.csv"

# Years of interest for the analysis
YEARS_OF_INTEREST = list(range(2017, 2026))


def download_ine_csv(output_path: str) -> bool:
    """
    Download the full municipal population CSV from INE's bulk download endpoint.
    """
    print(f"Downloading INE Table {TABLE_ID} (all municipalities, all years)...")
    print(f"  URL: {CSV_URL}")

    resp = requests.get(CSV_URL, timeout=300)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    size_mb = len(resp.content) / (1024 * 1024)
    print(f"  Saved to {output_path} ({size_mb:.1f} MB)")
    return True


def parse_ine_csv(csv_path: str) -> pd.DataFrame:
    """
    Parse the INE CSV into a clean panel DataFrame.

    The CSV has columns: Municipios, Sexo, Periodo, Total
    - Municipios: "28079 Madrid" (5-digit INE code + name)
    - Sexo: Total / Hombres / Mujeres
    - Periodo: year (int)
    - Total: population (may use dots as thousands separator)
    """
    print(f"\nParsing {csv_path}...")

    df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", dtype={"Total": str})
    print(f"  Raw rows: {len(df)}")

    # Keep only "Total" sex (not sex-disaggregated)
    df = df[df["Sexo"] == "Total"].copy()
    print(f"  After filtering Sexo=Total: {len(df)}")

    # Extract INE 5-digit code and municipality name
    df["cod_ine"] = df["Municipios"].str[:5]
    df["municipio"] = df["Municipios"].str[6:].str.strip()

    # Parse population: remove dots (thousands separator), handle NaN
    df["poblacion"] = (
        df["Total"]
        .str.replace(".", "", regex=False)
        .apply(pd.to_numeric, errors="coerce")
    )

    # Rename period to year
    df["year"] = df["Periodo"].astype(int)

    # Keep only valid records
    df = df.dropna(subset=["poblacion"]).copy()

    # Select columns
    df = df[["cod_ine", "municipio", "year", "poblacion"]].copy()

    print(f"  Unique municipalities: {df['cod_ine'].nunique()}")
    print(f"  Years: {sorted(df['year'].unique())}")

    return df


def build_population_panel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a clean municipality-year population panel from parsed INE data.
    Filter to years of interest and add RD threshold variables.
    """
    if df.empty:
        print("  No data to build panel from.")
        return df

    # Filter to years of interest
    panel = df[df["year"].isin(YEARS_OF_INTEREST)].copy()
    print(f"\n  Filtered to {len(YEARS_OF_INTEREST)} years of interest: {len(panel)} rows")

    # Extract province code
    panel["cod_provincia"] = panel["cod_ine"].str[:2]

    # Flag municipalities above 50k
    panel["above_50k"] = panel["poblacion"] >= 50000

    # Distance from threshold (running variable for RD)
    panel["pop_distance_50k"] = panel["poblacion"] - 50000

    # Sort
    panel = panel.sort_values(["cod_ine", "year"]).reset_index(drop=True)

    # Summary stats
    for yr in sorted(panel["year"].unique()):
        yr_data = panel[panel["year"] == yr]
        n_above = yr_data["above_50k"].sum()
        print(f"  {yr}: {len(yr_data)} municipalities, "
              f"{n_above} above 50k threshold")

    return panel


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("INE Padrón Municipal — Municipal Population Download")
    print("=" * 70)

    csv_path = os.path.join(RAW_DIR, f"table_{TABLE_ID}_cifras_oficiales.csv")
    parse_only = "--parse-only" in sys.argv

    # Step 1: Download
    if not parse_only:
        try:
            download_ine_csv(csv_path)
        except requests.exceptions.RequestException as e:
            print(f"\n  Download failed: {e}")
            if not os.path.exists(csv_path):
                print("  No cached file found. Exiting.")
                print(f"\n  Manual alternative: download from")
                print(f"    https://www.ine.es/jaxiT3/Tabla.htm?t={TABLE_ID}")
                print(f"  and save as {csv_path}")
                sys.exit(1)
            print(f"  Using cached file: {csv_path}")

    # Step 2: Parse
    if os.path.exists(csv_path):
        df = parse_ine_csv(csv_path)

        if not df.empty:
            # Save full parsed data
            full_path = os.path.join(INTERIM_DIR, "ine_population_all_years.csv")
            df.to_csv(full_path, index=False, encoding="utf-8")
            print(f"\n  Full data saved to {full_path} ({df.shape})")

            # Build the analysis panel (filtered years)
            panel = build_population_panel(df)

            if not panel.empty:
                panel_path = os.path.join(INTERIM_DIR, "ine_population_panel.csv")
                panel.to_csv(panel_path, index=False, encoding="utf-8")
                print(f"\n  Panel saved to {panel_path}")
                print(f"  Shape: {panel.shape}")
    else:
        print(f"\n  File not found: {csv_path}")
        print(f"  Run without --parse-only to download, or place file manually.")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  1. Run 02_download_dgt_fleet.py for vehicle fleet data")
    print("  2. Run 03_download_elections_py.py for electoral data")
    print("=" * 70)
