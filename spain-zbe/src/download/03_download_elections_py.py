"""
03_download_elections_py.py

Python alternative for downloading Spanish election results directly
from the Ministry of Interior's download area.

The Ministry provides fixed-width ASCII files with results at various
geographic levels. The SEA database (Scientific Data, 2021) provides
cleaned versions in Excel format.

If you have R installed, prefer 03_download_elections.R with the
infoelectoral package — it handles the parsing automatically.

Sources:
    Ministry of Interior: https://infoelectoral.interior.gob.es/
    Download area: https://infoelectoral.interior.gob.es/en/elecciones-celebradas/resultados-electorales/
    SEA database: https://www.nature.com/articles/s41597-021-00975-y
    SEA data: https://dataverse.harvard.edu/dataverse/SEA

Usage:
    python src/download/03_download_elections_py.py
"""

import os
import requests

RAW_DIR = os.path.join("data", "raw", "elections")
os.makedirs(RAW_DIR, exist_ok=True)

# The Ministry of Interior provides ZIP files containing fixed-width
# ASCII files with election results. The URL pattern is:
#   https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/
#       {election_type}{MM}{YYYY}.zip
#
# Where:
#   election_type: "04" for municipal, "02" for Congress
#   MM: month (05 for May, 07 for July, etc.)
#   YYYY: year

ELECTION_ZIPS = {
    "municipal_2015": {
        "url": "https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/04052015.zip",
        "desc": "Municipal elections May 2015",
    },
    "municipal_2019": {
        "url": "https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/04052019.zip",
        "desc": "Municipal elections May 2019",
    },
    "municipal_2023": {
        "url": "https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/04052023.zip",
        "desc": "Municipal elections May 2023",
    },
    "congress_2023": {
        "url": "https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/02072023.zip",
        "desc": "Congress elections July 2023",
    },
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research project; university of oxford)",
})


def download_election_zip(key: str, info: dict) -> str | None:
    """Download an election results ZIP file."""
    url = info["url"]
    desc = info["desc"]
    output_path = os.path.join(RAW_DIR, f"{key}.zip")

    if os.path.exists(output_path):
        print(f"  {desc}: already downloaded")
        return output_path

    print(f"  Downloading {desc}...")
    print(f"    URL: {url}")

    try:
        resp = SESSION.get(url, timeout=120)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        size_kb = len(resp.content) / 1024
        print(f"    Saved to {output_path} ({size_kb:.0f} KB)")
        return output_path

    except requests.exceptions.RequestException as e:
        print(f"    Error: {e}")
        print(f"    The URL pattern may have changed.")
        print(f"    Try browsing: https://infoelectoral.interior.gob.es/")
        return None


def print_parsing_notes():
    """
    Print notes on parsing the Ministry of Interior's fixed-width files.
    """
    notes = """
    ================================================================
    PARSING NOTES — Ministry of Interior Election Files
    ================================================================

    The ZIP files contain several fixed-width ASCII text files:
        01{TTMMYYYY}.DAT — Control file
        02{TTMMYYYY}.DAT — Candidacies (party list identifiers)
        03{TTMMYYYY}.DAT — Candidates
        04{TTMMYYYY}.DAT — Results by municipality (CANDIDACIES)
        05{TTMMYYYY}.DAT — Results by municipality (SUMMARY)
        06{TTMMYYYY}.DAT — Results by polling station
        ...

    File 04 is the key one: results by municipality and candidacy.
    File 02 maps candidacy codes to party names/abbreviations.

    The fixed-width format is documented in the Interior Ministry's
    technical specifications. The infoelectoral R package handles
    this parsing automatically — strongly recommended over manual parsing.

    If you must parse in Python, key fields in file 04:
        Cols 1-2:   Election type (04 = municipal)
        Cols 3-6:   Year
        Cols 7-8:   Month
        Cols 9-10:  Province code
        Cols 11-13: Municipality code
        ...
        (See Ministry documentation for full layout)

    ALTERNATIVE: The SEA database (Harvard Dataverse) provides the
    same data pre-parsed into Excel workbooks with clear column headers.
    URL: https://dataverse.harvard.edu/dataverse/SEA

    RECOMMENDATION:
        Use R + infoelectoral for initial download and parsing.
        Export to CSV.
        Continue analysis in Python.
    ================================================================
    """
    print(notes)


if __name__ == "__main__":
    print("=" * 70)
    print("Spanish Election Results — Direct Download (Python)")
    print("=" * 70)
    print()

    # Try downloading
    downloaded = {}
    for key, info in ELECTION_ZIPS.items():
        result = download_election_zip(key, info)
        if result:
            downloaded[key] = result

    print(f"\n  Downloaded {len(downloaded)}/{len(ELECTION_ZIPS)} files")

    # Print parsing guidance
    print_parsing_notes()

    print("=" * 70)
    print("Next steps:")
    print("  1. PREFERRED: Use R script (03_download_elections.R) to parse")
    print("  2. OR: Download pre-parsed data from SEA database (Harvard Dataverse)")
    print("  3. OR: Parse fixed-width files in Python (see notes above)")
    print("  4. Then run 04_merge_panel.py to combine all data sources")
    print("=" * 70)
