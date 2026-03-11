"""
02_download_dgt_fleet.py

Download vehicle fleet (parque de vehículos) data from the DGT,
with a focus on the distribution by environmental label (distintivo ambiental)
at the municipal level.

This is the primary outcome variable: the share of vehicles in each
DGT environmental category (Zero, Eco, C, B, no-label) per municipality.

Sources:
    - DGT en cifras: https://www.dgt.es/menusecundario/dgt-en-cifras/
    - Fleet data panel: "Panel de datos del parque de vehículos" (interactive)
    - Annual statistical tables: "Parque de vehículos — Tablas Estadísticas {year}"
    - Old statistical portal (PC-Axis): sedeapl.dgt.gob.es

Key URLs for annual fleet tables (Excel):
    2024: https://www.dgt.es/.../Parque-de-vehiculos-Tablas-estadisticas-2024/
    2023: https://www.dgt.es/.../Parque-de-vehiculos-Tablas-Estadisticas-2023/
    (pattern varies slightly by year)

The annual Excel workbooks contain multiple sheets including:
    - Fleet by province and vehicle type
    - Fleet by province, type, and fuel
    - Fleet of passenger cars (turismos) by environmental label
    - Fleet by municipality and vehicle type

For the environmental label breakdown at municipal level, we need either:
    (a) The annual tables if they include a municipal × label sheet, OR
    (b) The interactive dashboard data export, OR
    (c) A custom data request to DGT

Usage:
    python src/download/02_download_dgt_fleet.py
"""

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR = os.path.join("data", "raw", "dgt_fleet")
INTERIM_DIR = os.path.join("data", "interim")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)

# DGT base URLs
DGT_BASE = "https://www.dgt.es"
DGT_CIFRAS = f"{DGT_BASE}/menusecundario/dgt-en-cifras/"

# Known URLs for annual fleet statistical tables
# These are Excel workbooks published by the DGT
# NB: The exact URL path changes slightly each year — verify before running
FLEET_TABLE_URLS = {
    2024: "https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/"
          "dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-estadisticas-2024/",
    2023: "https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/"
          "dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-Estadisticas-2023/",
    2022: "https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/"
          "dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-Estadisticas-2022/",
    2021: "https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/"
          "dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-Estadisticas-2021/",
    2020: "https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/"
          "dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-Estadisticas-2020/",
}

# Old statistical portal — PC-Axis tables by municipality
# These provide fleet by municipality × vehicle type (and sometimes fuel)
# Pattern: /vehiculos/parque/a{year}/L0/{month}/PV_TDV_MUN_{mm}_{yy}.px
PCAXIS_BASE = "https://sedeapl.dgt.gob.es/IEST2/tabla.do"

# Years to download
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# HTTP session with headers
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research project; university of oxford)",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
})


def find_excel_download_link(page_url: str) -> str | None:
    """
    Scrape a DGT 'cifras detalle' page to find the Excel download link.

    The DGT detail pages typically contain a link to an Excel file
    with the annual statistical tables.
    """
    print(f"  Scraping {page_url} for download link...")

    try:
        resp = SESSION.get(page_url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    Error fetching page: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Look for links to Excel files
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if any(ext in href.lower() for ext in [".xlsx", ".xls", ".zip"]):
            # Make absolute URL if relative
            if href.startswith("/"):
                href = f"{DGT_BASE}{href}"
            elif not href.startswith("http"):
                href = f"{DGT_BASE}/{href}"
            print(f"    Found: {href}")
            return href

    # Also check for download buttons or specific CSS classes
    for link in soup.find_all("a", class_=True):
        classes = " ".join(link.get("class", []))
        if "download" in classes.lower() or "excel" in classes.lower():
            href = link.get("href", "")
            if href:
                if href.startswith("/"):
                    href = f"{DGT_BASE}{href}"
                print(f"    Found (via class): {href}")
                return href

    print("    No Excel download link found on page.")
    return None


def download_fleet_excel(year: int) -> str | None:
    """
    Download the annual fleet statistics Excel workbook for a given year.
    """
    if year not in FLEET_TABLE_URLS:
        print(f"  No known URL for year {year}")
        return None

    page_url = FLEET_TABLE_URLS[year]
    excel_url = find_excel_download_link(page_url)

    if not excel_url:
        print(f"  Could not find Excel link for {year}.")
        print(f"  Try downloading manually from: {page_url}")
        return None

    output_path = os.path.join(RAW_DIR, f"parque_vehiculos_{year}.xlsx")

    print(f"  Downloading {excel_url}...")
    try:
        resp = SESSION.get(excel_url, timeout=120)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        size_mb = len(resp.content) / (1024 * 1024)
        print(f"  Saved to {output_path} ({size_mb:.1f} MB)")
        return output_path

    except requests.exceptions.RequestException as e:
        print(f"  Download failed: {e}")
        return None


def inspect_excel_workbook(filepath: str):
    """
    Inspect the sheet names and structure of a downloaded DGT Excel workbook.
    This helps identify which sheet contains the environmental label data.
    """
    print(f"\n  Inspecting {filepath}...")

    try:
        xl = pd.ExcelFile(filepath)
        sheets = xl.sheet_names
        print(f"  Sheets ({len(sheets)}):")
        for i, name in enumerate(sheets):
            # Read just the first few rows to understand structure
            try:
                sample = pd.read_excel(filepath, sheet_name=name, nrows=5, header=None)
                print(f"    [{i}] {name}: {sample.shape[1]} cols, "
                      f"first cell = {sample.iloc[0, 0] if not sample.empty else 'empty'}")
            except Exception:
                print(f"    [{i}] {name}: (could not read)")
    except Exception as e:
        print(f"  Could not open workbook: {e}")


def download_pcaxis_municipal_fleet(year: int, month: str = "diciembre") -> str | None:
    """
    Try to download PC-Axis tables from the old DGT statistical portal.

    These tables provide fleet data by municipality and vehicle type.
    The portal was migrated in July 2024, so older data may still be accessible.

    URL pattern:
        /vehiculos/parque/a{year}/L0/{month}/PV_TDV_MUN_{mm}_{yy}.px
    """
    # Month mapping
    month_map = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    mm = month_map.get(month, "12")
    yy = str(year)[-2:]

    # Construct the PC-Axis URL
    px_path = (f"/vehiculos/parque/a{year}/L0/{month}/"
               f"PV_TDV_MUN_{mm}_{yy}.px")
    url = f"{PCAXIS_BASE}?path={px_path}&type=pcaxis&L=0&js=1"

    print(f"  Trying PC-Axis portal for {year}/{month}...")
    print(f"    URL: {url}")

    # Note: The PC-Axis portal serves HTML with embedded data,
    # not direct file downloads. We may need to navigate the portal
    # or use a different endpoint.
    # For now, document the URL pattern for manual access.

    output_path = os.path.join(RAW_DIR, f"pcaxis_parque_mun_{year}_{mm}.html")

    try:
        resp = SESSION.get(url, timeout=30)
        if resp.status_code == 200:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"    Saved response to {output_path}")
            return output_path
        else:
            print(f"    Status {resp.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"    Error: {e}")
        return None


def print_data_strategy():
    """
    Print a summary of the data acquisition strategy and next steps.
    """
    strategy = """
    ================================================================
    DGT FLEET DATA — ACQUISITION STRATEGY
    ================================================================

    GOAL: Municipal-level vehicle fleet by DGT environmental label,
          annual, for 2019–2024.

    AVAILABLE DATA STREAMS:

    1. ANNUAL STATISTICAL TABLES (Excel workbooks)
       - Published per year on DGT en cifras
       - Contain fleet by province × type × fuel
       - The 2020+ workbooks include a sheet for "turismos por
         distintivo medioambiental" — but at PROVINCE level
       - Municipal breakdown is by vehicle type only, not by label
       - STATUS: Province-level label data is useful but insufficient
         for the municipal RD design

    2. INTERACTIVE DASHBOARD (Panel de datos del parque)
       - URL: https://www.dgt.es/.../Panel-de-datos-del-parque-de-vehiculos/
       - Shows fleet by environmental label at the municipal level
       - KEY ISSUE: This is an embedded Power BI or similar dashboard;
         data export options may be limited
       - STRATEGY: Check if the dashboard allows CSV/Excel export
         filtered by municipality. If so, batch-download.

    3. PC-AXIS TABLES (Old statistical portal)
       - URL: sedeapl.dgt.gob.es
       - Provides fleet by municipality × vehicle type × fuel
       - Environmental label is NOT a standard dimension in these tables
       - Portal was migrated in July 2024; some tables may be unavailable
       - STATUS: Useful for fleet composition but not label breakdown

    4. CUSTOM DATA REQUEST
       - The DGT accepts data requests via their electronic headquarters
       - Request: municipal-level fleet by environmental label, 2019–2024
       - This is likely the most reliable path for the exact data needed
       - Use the datos.gob.es portal or DGT contact form

    5. MATRABA MICRODATA (Registration microdata)
       - Monthly/daily microdata of all new registrations
       - Contains CO2 emissions, fuel type, electric category
       - Can compute the DGT label from these fields
       - Province-level geography (municipality code TBC)
       - Useful for FLOW analysis (new registrations) even if not STOCK

    RECOMMENDED APPROACH:
       (a) Download the annual Excel tables for province-level label data
       (b) Check the interactive dashboard for municipal-level export
       (c) File a DGT data request for the municipal × label panel
       (d) Use MATRABA microdata for registration flow analysis
       (e) Use PC-Axis municipal × fuel data as a proxy if (c) is slow

    ================================================================
    """
    print(strategy)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("DGT Fleet Data (Parque de Vehículos) — Download")
    print("=" * 70)

    # Step 1: Print overall strategy
    print_data_strategy()

    # Step 2: Try to download annual Excel workbooks
    print("\n--- Downloading Annual Statistical Tables ---\n")

    downloaded = {}
    for year in YEARS:
        print(f"\nYear {year}:")
        path = download_fleet_excel(year)
        if path:
            downloaded[year] = path
        time.sleep(2)  # be polite

    # Step 3: Inspect downloaded workbooks
    if downloaded:
        print("\n\n--- Inspecting Downloaded Workbooks ---\n")
        for year, path in downloaded.items():
            print(f"\nYear {year}:")
            inspect_excel_workbook(path)

    # Step 4: Try PC-Axis tables for a sample year
    print("\n\n--- Trying PC-Axis Portal (Sample) ---\n")
    download_pcaxis_municipal_fleet(2023)

    # Step 5: Summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Downloaded {len(downloaded)} annual workbooks")
    if downloaded:
        print(f"  Years: {sorted(downloaded.keys())}")
    print()
    print("Next steps:")
    print("  1. Inspect Excel sheets for environmental label data")
    print("  2. Check the DGT interactive dashboard for municipal export:")
    print("     https://www.dgt.es/.../Panel-de-datos-del-parque-de-vehiculos/")
    print("  3. Consider filing a DGT data request for municipal × label panel")
    print("  4. Run 03_download_elections.py for electoral data")
    print("=" * 70)
