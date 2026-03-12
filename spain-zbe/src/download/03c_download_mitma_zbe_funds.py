"""
03c_download_mitma_zbe_funds.py

Download municipality-level Next Generation EU fund allocations for ZBE
implementation from the BDNS (Base de Datos Nacional de Subvenciones).

Source: BDNS — Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas
API:    https://www.pap.hacienda.gob.es/bdnstrans/api/
Program: "Ayudas a municipios para la implantación de ZBE y la
         transformación digital y sostenible del transporte urbano"

Two convocatorias:
  - 2021 call (BDNS 576282): EUR 1bn to 169 municipalities
  - 2022 call (BDNS 640563): EUR 500m to 109 municipalities

Usage:
    python spain-zbe/src/download/03c_download_mitma_zbe_funds.py
"""

import json
import os
import time
import urllib.request

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "mitma_zbe_funds")
os.makedirs(RAW_DIR, exist_ok=True)

API_BASE = "https://www.pap.hacienda.gob.es/bdnstrans/api"

CONVOCATORIAS = {
    2021: "576282",
    2022: "640563",
}


def fetch_concesiones(bdns_code, label, max_retries=4):
    """
    Fetch all concesiones for a given BDNS convocatoria code.
    Returns a list of dicts.
    """
    url = (
        f"{API_BASE}/concesiones/busqueda"
        f"?vpd=GE&numeroConvocatoria={bdns_code}"
        f"&page=0&pageSize=500"
    )
    print(f"  Fetching {label} (BDNS {bdns_code})...")

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            records = data["content"]
            total = data["totalElements"]
            print(f"    Retrieved {len(records)}/{total} records")
            return records
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                print(f"    Error: {e}. Retry {attempt+1}/{max_retries} "
                      f"in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    Failed after {max_retries} retries: {e}")
                raise


if __name__ == "__main__":
    print("=" * 70)
    print("BDNS — Next Generation EU ZBE Fund Allocations")
    print("=" * 70)

    all_records = []

    for year, bdns_code in CONVOCATORIAS.items():
        records = fetch_concesiones(bdns_code, f"{year} call")
        for r in records:
            r["convocatoria_year"] = year
        all_records.extend(records)
        time.sleep(1)

    # Save raw JSON
    out_path = os.path.join(RAW_DIR, "bdns_zbe_concesiones.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n  Saved {len(all_records)} records to {out_path}")

    # Summary
    years = {}
    for r in all_records:
        y = r["convocatoria_year"]
        years.setdefault(y, {"count": 0, "total": 0})
        years[y]["count"] += 1
        years[y]["total"] += r["importe"]

    for y, info in sorted(years.items()):
        print(f"    {y}: {info['count']} grants, "
              f"EUR {info['total']:,.0f}")

    print(f"\n  Total: {len(all_records)} grants, "
          f"EUR {sum(r['importe'] for r in all_records):,.0f}")

    print("\n" + "=" * 70)
    print("Next: run 05d_clean_mitma_zbe_funds.py")
    print("=" * 70)
