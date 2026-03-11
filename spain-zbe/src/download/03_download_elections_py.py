"""
03_download_elections_py.py

Python script for downloading Spanish election results from multiple sources.

Primary source: Ministry of Interior fixed-width ASCII ZIP files
    https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/
    URL pattern: {tipo}{anno}{mes}_{level}.zip
    (Same pattern used by the infoelectoral R package)

Fallback source: SEA (Spanish Electoral Archive) on Harvard Dataverse
    https://doi.org/10.7910/DVN/53FCE6 (Local elections)
    https://doi.org/10.7910/DVN/0GPRYW (General elections)

If you have R installed, prefer 03_download_elections.R with the
infoelectoral package — it handles the parsing automatically.

Usage:
    python src/download/03_download_elections_py.py
"""

import os
import time
import requests

RAW_DIR = os.path.join("data", "raw", "elections")
os.makedirs(RAW_DIR, exist_ok=True)

# -------------------------------------------------------------------------
# Source 1: Ministry of Interior
# -------------------------------------------------------------------------
# The infoelectoral R package uses this URL pattern:
#   https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/{tipo}{anno}{mes}_{level}.zip
#
# The older/alternative pattern (used in some documentation) is:
#   https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/{tipo}{mes}{anno}.zip
#
# We try both patterns.

MIR_BASE_NEW = "https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr"
MIR_BASE_OLD = "https://infoelectoral.interior.gob.es/estaticos/docxl/apliext"

# Municipal elections: tipo=04, General/Congress: tipo=02
ELECTIONS = {
    "municipal_2015": {
        "tipo": "04", "anno": "2015", "mes": "05",
        "desc": "Municipal elections May 2015",
    },
    "municipal_2019": {
        "tipo": "04", "anno": "2019", "mes": "05",
        "desc": "Municipal elections May 2019",
    },
    "municipal_2023": {
        "tipo": "04", "anno": "2023", "mes": "05",
        "desc": "Municipal elections May 2023",
    },
    "congress_2023": {
        "tipo": "02", "anno": "2023", "mes": "07",
        "desc": "Congress elections July 2023",
    },
}

# Levels used by the infoelectoral R package URL pattern
MIR_LEVELS = ["TOTA", "MUNI", "MESA"]

# -------------------------------------------------------------------------
# Source 2: SEA database on Harvard Dataverse
# -------------------------------------------------------------------------
# Spanish Local Elections dataset: doi:10.7910/DVN/53FCE6
# Files are RAR archives split by "CAPITALES DE PROVINCIA" and
# "GRANDES MUNICIPIOS NO CAPITALES". These contain pre-parsed Excel sheets.
# Download URL: https://dataverse.harvard.edu/api/access/datafile/{file_id}

SEA_FILES = {
    "sea_local_2015_capitales": {
        "file_id": 4985916,
        "desc": "SEA Local 2015 — Capitales de provincia",
        "filename": "2015_CAPITALES.rar",
    },
    "sea_local_2015_grandes": {
        "file_id": 4985913,
        "desc": "SEA Local 2015 — Grandes municipios",
        "filename": "2015_GRANDES_MUNICIPIOS.rar",
    },
    "sea_local_2019_capitales": {
        "file_id": 4985902,
        "desc": "SEA Local 2019 — Capitales de provincia",
        "filename": "2019_CAPITALES.rar",
    },
    "sea_local_2019_grandes": {
        "file_id": 4985910,
        "desc": "SEA Local 2019 — Grandes municipios",
        "filename": "2019_GRANDES_MUNICIPIOS.rar",
    },
    "sea_local_2023_capitales": {
        "file_id": 10194045,
        "desc": "SEA Local 2023 — Capitales de provincia",
        "filename": "2023_CAPITALES.rar",
    },
    "sea_local_2023_grandes": {
        "file_id": 10194044,
        "desc": "SEA Local 2023 — Grandes municipios",
        "filename": "2023_GRANDES_MUNICIPIOS.rar",
    },
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research project; university of oxford)",
})

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def download_with_retry(url: str, output_path: str, desc: str,
                        max_retries: int = MAX_RETRIES) -> bool:
    """Download a file with exponential backoff retry on failure."""
    for attempt in range(max_retries + 1):
        try:
            resp = SESSION.get(url, timeout=120)
            if resp.status_code == 503:
                wait = BACKOFF_BASE ** (attempt + 1)
                if attempt < max_retries:
                    print(f"    503 Service Unavailable — retrying in {wait}s "
                          f"(attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    continue
                else:
                    print(f"    503 Service Unavailable — server appears to be down.")
                    return False
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

            size_kb = len(resp.content) / 1024
            print(f"    Saved to {output_path} ({size_kb:.0f} KB)")
            return True

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = BACKOFF_BASE ** (attempt + 1)
                print(f"    Error: {e} — retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    Error: {e}")
                return False

    return False


def download_mir_elections() -> dict:
    """
    Try to download election ZIP files from the Ministry of Interior.
    Tries multiple URL patterns per election.
    """
    downloaded = {}

    for key, info in ELECTIONS.items():
        tipo, anno, mes = info["tipo"], info["anno"], info["mes"]
        desc = info["desc"]
        output_path = os.path.join(RAW_DIR, f"{key}.zip")

        if os.path.exists(output_path):
            print(f"  {desc}: already downloaded")
            downloaded[key] = output_path
            continue

        print(f"  {desc}:")

        # Try URL patterns
        urls_to_try = []
        # Pattern 1: infoelectoral R package pattern (apliextr)
        for level in MIR_LEVELS:
            urls_to_try.append(
                f"{MIR_BASE_NEW}/{tipo}{anno}{mes}_{level}.zip"
            )
        # Pattern 2: older documentation pattern (apliext)
        urls_to_try.append(f"{MIR_BASE_OLD}/{tipo}{mes}{anno}.zip")

        success = False
        for url in urls_to_try:
            print(f"    Trying: {url}")
            if download_with_retry(url, output_path, desc, max_retries=1):
                downloaded[key] = output_path
                success = True
                break

        if not success:
            print(f"    All Ministry URLs failed for {desc}.")
            print(f"    The server may be experiencing an outage.")

    return downloaded


def download_sea_elections() -> dict:
    """
    Download pre-parsed election data from the SEA database on Harvard Dataverse.
    This is the fallback when the Ministry of Interior is unavailable.
    """
    downloaded = {}

    for key, info in SEA_FILES.items():
        file_id = info["file_id"]
        desc = info["desc"]
        filename = info["filename"]
        output_path = os.path.join(RAW_DIR, filename)

        if os.path.exists(output_path):
            print(f"  {desc}: already downloaded")
            downloaded[key] = output_path
            continue

        print(f"  {desc}:")
        url = f"https://dataverse.harvard.edu/api/access/datafile/{file_id}"

        if download_with_retry(url, output_path, desc):
            downloaded[key] = output_path

    return downloaded


def print_parsing_notes():
    """Print notes on parsing the election data files."""
    notes = """
    ================================================================
    PARSING NOTES — Election Data Files
    ================================================================

    MINISTRY OF INTERIOR (ZIP files):
        The ZIP files contain several fixed-width ASCII text files:
            01{TTMMYYYY}.DAT — Control file
            02{TTMMYYYY}.DAT — Candidacies (party code -> party name)
            03{TTMMYYYY}.DAT — Candidates
            04{TTMMYYYY}.DAT — Results by municipality and candidacy (KEY)
            05{TTMMYYYY}.DAT — Results by municipality (summary)
            06{TTMMYYYY}.DAT — Results by polling station

        File 04 key fields (fixed-width):
            Cols 1-2:   Election type
            Cols 3-6:   Year
            Cols 7-8:   Month
            Cols 9-10:  Province code
            Cols 11-13: Municipality code

        RECOMMENDATION: Use R + infoelectoral for parsing, then export CSV.

    SEA DATABASE (RAR files):
        Pre-parsed Excel workbooks with clear column headers.
        Split by "CAPITALES DE PROVINCIA" (provincial capitals) and
        "GRANDES MUNICIPIOS NO CAPITALES" (large non-capital cities).
        NOTE: The SEA may not cover all 8,000+ municipalities —
        it focuses on larger ones. For full coverage, the Ministry
        files are needed.

    ================================================================
    """
    print(notes)


if __name__ == "__main__":
    print("=" * 70)
    print("Spanish Election Results — Download")
    print("=" * 70)
    print()

    # Step 1: Try Ministry of Interior
    print("--- Source 1: Ministry of Interior ---\n")
    mir_downloaded = download_mir_elections()

    # Step 2: If Ministry failed, try SEA as fallback
    if len(mir_downloaded) < len(ELECTIONS):
        missing = set(ELECTIONS.keys()) - set(mir_downloaded.keys())
        print(f"\n  Missing {len(missing)} elections from Ministry.")
        print("  Falling back to SEA database (Harvard Dataverse)...\n")

        print("--- Source 2: SEA Database (Harvard Dataverse) ---\n")
        sea_downloaded = download_sea_elections()
    else:
        sea_downloaded = {}

    # Step 3: Summary
    print()
    print_parsing_notes()

    print("=" * 70)
    print("Summary:")
    print(f"  Ministry of Interior: {len(mir_downloaded)}/{len(ELECTIONS)} elections")
    print(f"  SEA Database: {len(sea_downloaded)}/{len(SEA_FILES)} files")
    if mir_downloaded:
        print(f"  Ministry files: {list(mir_downloaded.keys())}")
    if sea_downloaded:
        print(f"  SEA files: {list(sea_downloaded.keys())}")
    print()
    print("Next steps:")
    if mir_downloaded:
        print("  1. Parse Ministry ZIP files (use R + infoelectoral, or manual Python)")
    if sea_downloaded:
        print("  2. Extract and inspect SEA RAR files for pre-parsed Excel data")
    if not mir_downloaded and not sea_downloaded:
        print("  1. Both sources failed. Try again later or download manually:")
        print("     Ministry: https://infoelectoral.interior.gob.es/")
        print("     SEA: https://doi.org/10.7910/DVN/53FCE6")
    print("  3. Compute Vox and PP vote shares by municipality")
    print("  4. Note: Vox did not run in 2015 municipal elections")
    print("  5. Run merge script to combine with population panel")
    print("=" * 70)
