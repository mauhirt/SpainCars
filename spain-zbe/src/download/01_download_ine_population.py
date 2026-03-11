"""
01_download_ine_population.py

Download official municipal population figures (Cifras Oficiales de Población)
from the INE Padrón Municipal. This provides the running variable for the
regression discontinuity at the 50,000 inhabitant threshold.

Source: INE — Cifras oficiales de población de los municipios españoles:
        Revisión del Padrón Municipal
URL:    https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177011

The INE JSON-stat API endpoint:
    https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table_id}

Table 2852: Población por municipios y sexo (cifras oficiales del Padrón)

Usage:
    python src/download/01_download_ine_population.py
"""

import os
import time
import json
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR = os.path.join("data", "raw", "ine_population")
INTERIM_DIR = os.path.join("data", "interim")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)

# INE JSON-stat API base
INE_API_BASE = "https://servicios.ine.es/wstempus/js/ES"

# Years of interest: 2017-2025 covers pre- and post-mandate periods
YEARS = list(range(2017, 2026))

# The INE table for "Población por municipios y sexo" from Padrón
# Table 2852 contains total population by municipality
# We request nult=2 to get municipality-level detail
TABLE_ID = "2852"


def download_ine_table(table_id: str, output_path: str) -> dict:
    """
    Download a table from the INE JSON-stat API.

    The INE API returns data in JSON-stat format. We request with
    tip=AM to get metadata, or without for data.
    """
    url = f"{INE_API_BASE}/DATOS_TABLA/{table_id}"
    params = {"nult": 10}  # last 10 periods available

    print(f"Requesting INE table {table_id}...")
    print(f"  URL: {url}")

    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()

    data = resp.json()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Saved raw JSON to {output_path}")
    return data


def download_ine_municipal_population_by_year():
    """
    Alternative approach: use the INE's series endpoint to get
    municipal population for specific years.

    The INE API for Padrón data uses operation code "DPOP" (id 29005).
    Municipal-level data can be accessed via:
        /DATOS_SERIE/{serie_id}
    or via the table endpoint with filters.

    Since the full table can be very large (8000+ municipalities × years),
    we download the complete table and filter locally.
    """
    # First, try to get the table metadata to understand structure
    meta_url = f"{INE_API_BASE}/GRUPOS_TABLA/{TABLE_ID}"
    print(f"Fetching table metadata from {meta_url}...")

    try:
        resp = requests.get(meta_url, timeout=60)
        resp.raise_for_status()
        meta = resp.json()

        meta_path = os.path.join(RAW_DIR, "table_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"  Metadata saved to {meta_path}")

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Could not fetch metadata: {e}")
        print("  Continuing with direct data download...")


def download_padron_cifras_oficiales():
    """
    Download the Cifras Oficiales de Población table.

    The INE publishes this as downloadable PC-Axis (.px) or Excel files.
    The JSON API can also serve this data.

    Strategy:
    1. Try the JSON-stat API for the full table
    2. If that fails or is too large, fall back to downloading
       the published Excel files year by year
    """

    # --- Approach 1: JSON API ---
    json_path = os.path.join(RAW_DIR, f"table_{TABLE_ID}_raw.json")

    try:
        data = download_ine_table(TABLE_ID, json_path)
        print(f"  Downloaded {len(data)} records from API")
        return data

    except requests.exceptions.RequestException as e:
        print(f"  API download failed: {e}")
        print("  Falling back to manual download instructions...\n")
        print_manual_download_instructions()
        return None


def print_manual_download_instructions():
    """
    If the API approach fails, print instructions for manual download.
    The INE website sometimes requires interactive navigation.
    """
    instructions = """
    ================================================================
    MANUAL DOWNLOAD INSTRUCTIONS — INE Padrón Municipal
    ================================================================

    The INE API may not serve the full municipal-level table directly.
    To download manually:

    1. Go to: https://www.ine.es/dynt3/inebase/index.htm?padre=517
    2. Click on the desired year (e.g., "Cifras oficiales de población
       de los municipios españoles: Revisión del Padrón Municipal
       Resultados por municipios")
    3. Select "Población por municipios y sexo"
    4. Select all municipalities and "Total" for sex
    5. Download as CSV or Excel
    6. Save to: data/raw/ine_population/

    Alternative: Use the PC-Axis files from the statistical portal:
        https://www.ine.es/jaxi/Tabla.htm?path=/t20/e260/a{year}/l0/&file=mun00.px

    Where {year} is the 4-digit year (e.g., 2023).

    Once downloaded, place files as:
        data/raw/ine_population/padron_{year}.csv

    Then re-run this script with --parse-only to build the panel.
    ================================================================
    """
    print(instructions)


def parse_ine_json_to_panel(json_path: str) -> pd.DataFrame:
    """
    Parse the INE JSON API response into a clean panel DataFrame.

    The INE API returns records as a list of dicts with structure:
    [
        {
            "Nombre": "municipality name",
            "T3_Periodo": "1 de enero de 2023",
            "T3_TipoDato": "Cifra",
            "Anyo": 2023,
            "Valor": 12345,
            ...
        },
        ...
    ]

    We need to extract: municipality code, municipality name, year, population.
    """
    print(f"\nParsing {json_path}...")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("  Unexpected JSON structure. Inspecting top-level keys...")
        if isinstance(data, dict):
            print(f"  Keys: {list(data.keys())[:10]}")
        return pd.DataFrame()

    # The API returns a flat list of observation records
    records = []
    for item in data:
        # Extract fields — exact structure depends on the table
        record = {}

        # The "Nombre" field typically contains the municipality name
        # with the INE code embedded, e.g., "28079 Madrid"
        nombre = item.get("Nombre", "")

        # Try to extract INE code from the name
        if nombre and len(nombre) >= 5 and nombre[:5].isdigit():
            record["cod_ine"] = nombre[:5]
            record["municipio"] = nombre[6:].strip() if len(nombre) > 5 else ""
        else:
            record["nombre_raw"] = nombre

        # Year
        record["year"] = item.get("Anyo", None)

        # Population value
        record["poblacion"] = item.get("Valor", None)

        # Period description
        record["periodo"] = item.get("T3_Periodo", "")

        records.append(record)

    df = pd.DataFrame(records)
    print(f"  Parsed {len(df)} records")

    if "cod_ine" in df.columns:
        print(f"  Unique municipalities: {df['cod_ine'].nunique()}")
    if "year" in df.columns:
        print(f"  Years: {sorted(df['year'].dropna().unique())}")

    return df


def build_population_panel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a clean municipality-year population panel from parsed INE data.
    Identify municipalities above/below the 50k threshold.
    """
    if df.empty:
        print("  No data to build panel from.")
        return df

    # Keep only records with valid municipal codes and population
    panel = df.dropna(subset=["poblacion"]).copy()

    if "cod_ine" in panel.columns:
        panel = panel.dropna(subset=["cod_ine"])

        # Extract province code
        panel["cod_provincia"] = panel["cod_ine"].str[:2]

        # Flag municipalities above 50k
        panel["above_50k"] = panel["poblacion"] >= 50000

        # Distance from threshold (running variable for RD)
        panel["pop_distance_50k"] = panel["poblacion"] - 50000

        # Sort
        panel = panel.sort_values(["cod_ine", "year"]).reset_index(drop=True)

        # Summary stats
        if "year" in panel.columns:
            for yr in sorted(panel["year"].dropna().unique()):
                yr_data = panel[panel["year"] == yr]
                n_above = yr_data["above_50k"].sum()
                print(f"  {int(yr)}: {len(yr_data)} municipalities, "
                      f"{n_above} above 50k threshold")

    return panel


def parse_manual_csv(csv_path: str, year: int) -> pd.DataFrame:
    """
    Parse a manually downloaded CSV from the INE website.

    The INE CSV format typically has:
    - First column: municipality code + name (e.g., "28079 Madrid")
    - Subsequent columns: Total, Males, Females

    Adjust parsing as needed based on actual file structure.
    """
    print(f"  Parsing {csv_path} for year {year}...")

    # Try common INE CSV formats
    try:
        # Try semicolon-separated (common in Spanish data)
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", dtype=str)
    except Exception:
        try:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8", dtype=str)
        except Exception:
            df = pd.read_csv(csv_path, sep="\t", encoding="latin-1", dtype=str)

    print(f"    Columns: {list(df.columns)}")
    print(f"    Shape: {df.shape}")
    print(f"    First rows:\n{df.head(3)}")

    # This will need adjustment based on actual column names
    # Common patterns:
    #   "Municipios" or first unnamed column contains "28079 Madrid"
    #   "Total" contains the population figure

    df["year"] = year
    return df


def check_for_manual_downloads() -> list:
    """Check if any manually downloaded files exist in the raw directory."""
    files = []
    for fname in os.listdir(RAW_DIR):
        if fname.endswith((".csv", ".xlsx", ".xls", ".px")):
            files.append(os.path.join(RAW_DIR, fname))
    return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("INE Padrón Municipal — Municipal Population Download")
    print("=" * 70)

    # Step 1: Try API download
    result = download_padron_cifras_oficiales()

    # Step 2: Parse if we got data
    json_path = os.path.join(RAW_DIR, f"table_{TABLE_ID}_raw.json")

    if os.path.exists(json_path):
        df = parse_ine_json_to_panel(json_path)

        if not df.empty:
            # Build the panel
            panel = build_population_panel(df)

            # Save
            if not panel.empty:
                output_path = os.path.join(INTERIM_DIR, "ine_population_panel.csv")
                panel.to_csv(output_path, index=False, encoding="utf-8")
                print(f"\n  Panel saved to {output_path}")
                print(f"  Shape: {panel.shape}")
        else:
            print("\n  Could not parse API response into a usable format.")
            print("  Check data/raw/ine_population/table_2852_raw.json")
            print("  and adjust parse_ine_json_to_panel() accordingly.")

    # Step 3: Check for manual downloads
    manual_files = check_for_manual_downloads()
    if manual_files:
        print(f"\n  Found {len(manual_files)} manual download(s) in {RAW_DIR}:")
        for f in manual_files:
            print(f"    {f}")
        print("  Use parse_manual_csv() to process these.")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  1. Inspect the raw JSON in data/raw/ine_population/")
    print("  2. If API didn't work, download manually (see instructions above)")
    print("  3. Run 02_download_dgt_fleet.py for vehicle fleet data")
    print("=" * 70)
