"""
03b_download_hacienda_fiscal.py

Download municipal budget settlement data (liquidaciones presupuestarias)
from the Ministerio de Hacienda's CONPREL portal.

Source: CONPREL — Consulta de Presupuestos y Liquidaciones de Entidades Locales
URL:    https://serviciostelematicosext.hacienda.gob.es/SGFAL/CONPREL

Each year's data is a ZIP containing an Access (.accdb) database with:
  - tb_inventario: entity registry (maps entity IDs to INE codes)
  - tb_economica: revenue and expenditure by budget classification
  - tb_remanente: treasury remainder (proxy for fiscal health)
  - tb_cuentasEconomica: code-to-label lookup

Usage:
    python src/download/03b_download_hacienda_fiscal.py
"""

import os
import sys
import time
import requests

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "hacienda_fiscal")
os.makedirs(RAW_DIR, exist_ok=True)

BASE_URL = (
    "https://serviciostelematicosext.hacienda.gob.es"
    "/SGFAL/CONPREL/Consulta/DescargaFichero"
)

YEARS = [2019, 2020, 2021, 2022, 2023]


def download_liquidaciones(year: int, output_path: str) -> bool:
    """Download liquidaciones ZIP for a given year."""
    params = {
        "CCAA": "",
        "TipoDato": "Liquidaciones",
        "Ejercicio": str(year),
        "TipoPublicacion": "Access",
    }
    print(f"  Downloading Liquidaciones {year}...")
    resp = requests.get(BASE_URL, params=params, timeout=300, stream=True)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"    Saved {output_path} ({size_mb:.1f} MB)")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Ministerio de Hacienda — Liquidaciones Presupuestarias (CONPREL)")
    print("=" * 70)

    for year in YEARS:
        zip_path = os.path.join(RAW_DIR, f"Liquidaciones{year}.zip")

        if os.path.exists(zip_path):
            print(f"  {zip_path} already exists, skipping.")
            continue

        try:
            download_liquidaciones(year, zip_path)
        except requests.exceptions.RequestException as e:
            print(f"    Download failed for {year}: {e}")
            # Retry with backoff
            for attempt, wait in enumerate([2, 4, 8, 16], start=1):
                print(f"    Retry {attempt}/4 in {wait}s...")
                time.sleep(wait)
                try:
                    download_liquidaciones(year, zip_path)
                    break
                except requests.exceptions.RequestException:
                    if attempt == 4:
                        print(f"    Giving up on {year}.")

        # Brief pause between years
        time.sleep(1)

    print("\n" + "=" * 70)
    print("Next: run 05c_clean_hacienda_fiscal.py")
    print("=" * 70)
