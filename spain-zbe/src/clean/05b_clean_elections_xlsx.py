"""
05b_clean_elections_xlsx.py

Parse 2023 election Excel files from the Ministry of Interior download portal.

Handles:
    - 04_202305_1.xlsx  → Municipal elections May 2023
    - 02_202307_1.xlsx  → Congress elections July 2023

Both files have the same structure:
    Row 5: full party names (cols 13+)
    Row 6: column headers (abbreviated party names in cols 13+)
    Row 7+: data

Output:
    data/interim/elections_municipal_2023.csv
    data/interim/elections_congress_2023.csv

Usage:
    python spain-zbe/src/clean/05b_clean_elections_xlsx.py
"""

import os
import pandas as pd
import numpy as np

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "elections")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

# Key parties to track (match abbreviations in row 6 of Excel)
# For municipal 2023, VOX column is labeled "VOX"
# For congress 2023, VOX column is labeled "VOX"
PARTY_ABBREVS_MUNICIPAL = {
    "pp": ["PP"],
    "psoe": ["PSOE"],
    "vox": ["VOX"],
    "cs": ["CS"],
    # UP/left coalition is fragmented in municipal 2023 across many local brands
    "up": ["PODEMOS-IU", "UNIDAS-PODEMOS-IZQUIERDA UNIDA", "PODEMOS", "MM-VQ",
           "PODEMOS-AV", "IU-MÁS PAÍS-IAS", "PODEMOS, EZKER ANITZA / IU, BERDEAK EQUO, ALIANZA VERDE",
           "I.U.", "PARA LA GENTE", "EUPV: ENDAVANT", "IU-MÁSMADRID-EQUO",
           "PODEMOS - ESQUERDA UNIDA"],
}

PARTY_ABBREVS_CONGRESS = {
    "pp": ["PP"],
    "psoe": ["PSOE"],
    "vox": ["VOX"],
    "sumar": ["SUMAR"],
}


def parse_election_xlsx(filepath, party_map, header_row=6, data_start=7,
                        sheet_name=0, col_offset=0):
    """
    Parse an election Excel file from the Ministry of Interior.

    Parameters
    ----------
    filepath : str
    party_map : dict — maps our label -> list of column abbreviations to sum
    header_row : int — 1-indexed row with abbreviated column headers
    data_start : int — 1-indexed row where data begins
    sheet_name : str or int
    col_offset : int — column offset (municipal file has 1-based cols)

    Returns
    -------
    DataFrame with municipality-level results
    """
    print(f"\n  Reading: {filepath} (sheet={sheet_name})")

    # Read header row to get column names
    df_header = pd.read_excel(filepath, sheet_name=sheet_name,
                              header=None, nrows=1,
                              skiprows=header_row - 1)
    col_names = df_header.iloc[0].tolist()

    # Read data
    df = pd.read_excel(filepath, sheet_name=sheet_name,
                       header=None, skiprows=data_start - 1)
    df.columns = range(len(df.columns))

    # Map header names to column indices
    name_to_idx = {}
    for i, name in enumerate(col_names):
        if name is not None and str(name).strip():
            name_to_idx[str(name).strip()] = i

    # Extract standard columns
    # Congress: col 0 = Comunidad, 1 = Cod Prov, 2 = Nombre Prov, 3 = Cod Muni, 4 = Nombre Muni, 5 = Población
    # Municipal: col 1 = Comunidad, 2 = Cod Prov, 3 = Nombre Prov, 4 = Cod Muni, 5 = Nombre Muni, 6 = Población
    # Detect based on header
    ccaa_idx = name_to_idx.get("Nombre de Comunidad", 0)

    records = []
    for _, row in df.iterrows():
        cod_prov = row.get(ccaa_idx + 1)
        cod_muni = row.get(ccaa_idx + 3)
        nombre_muni = row.get(ccaa_idx + 4)
        poblacion = row.get(ccaa_idx + 5)
        censo = row.get(ccaa_idx + 7)
        total_votantes = row.get(ccaa_idx + 8)
        votos_validos = row.get(ccaa_idx + 9)
        votos_candidaturas = row.get(ccaa_idx + 10)
        votos_blanco = row.get(ccaa_idx + 11)
        votos_nulos = row.get(ccaa_idx + 12)

        # Skip empty rows
        if pd.isna(cod_prov) or pd.isna(cod_muni):
            continue

        try:
            cod_prov_str = str(int(cod_prov)).zfill(2)
            cod_muni_str = str(int(cod_muni)).zfill(3)
        except (ValueError, TypeError):
            continue

        cod_ine = cod_prov_str + cod_muni_str

        rec = {
            "cod_ine": cod_ine,
            "cod_provincia": cod_prov_str,
            "municipio": str(nombre_muni).strip() if nombre_muni else "",
            "poblacion_elec": int(poblacion) if pd.notna(poblacion) else None,
            "censo": int(censo) if pd.notna(censo) else None,
            "total_votantes": int(total_votantes) if pd.notna(total_votantes) else None,
            "votos_validos": int(votos_validos) if pd.notna(votos_validos) else None,
            "votos_candidaturas": int(votos_candidaturas) if pd.notna(votos_candidaturas) else None,
            "votos_blanco": int(votos_blanco) if pd.notna(votos_blanco) else None,
            "votos_nulos": int(votos_nulos) if pd.notna(votos_nulos) else None,
        }

        # Sum votes for each tracked party
        for party_label, abbrevs in party_map.items():
            total = 0
            for abbrev in abbrevs:
                if abbrev in name_to_idx:
                    idx = name_to_idx[abbrev]
                    val = row.get(idx)
                    if pd.notna(val):
                        try:
                            total += int(val)
                        except (ValueError, TypeError):
                            pass
            rec[f"votos_{party_label}"] = total

        records.append(rec)

    result = pd.DataFrame(records)

    # Use votos_candidaturas as total_votes (sum of all party votes)
    result["total_votes"] = result["votos_candidaturas"]

    # Compute vote shares
    for party_label in party_map:
        col = f"votos_{party_label}"
        result[f"share_{party_label}"] = (
            result[col] / result["total_votes"].replace(0, np.nan)
        )

    print(f"    Parsed: {len(result)} municipalities")

    # Quick stats
    for party_label in party_map:
        present = (result[f"votos_{party_label}"] > 0).sum()
        mean_share = result[f"share_{party_label}"].mean()
        print(f"    {party_label.upper():8s}: ran in {present}/{len(result)} munis, "
              f"mean share = {mean_share:.3%}")

    return result


def main():
    print("=" * 70)
    print("05b — Clean 2023 Election Excel Files")
    print("=" * 70)

    # ---------------------------------------------------------------
    # 1. Municipal elections May 2023
    # ---------------------------------------------------------------
    muni_path = os.path.join(RAW_DIR, "04_202305_1.xlsx")
    if os.path.exists(muni_path):
        muni_df = parse_election_xlsx(
            muni_path,
            party_map=PARTY_ABBREVS_MUNICIPAL,
            header_row=6,
            data_start=7,
            sheet_name="Municipios",
        )
        muni_df["year"] = 2023
        muni_df["election_type"] = "municipal"

        # Save
        out_path = os.path.join(INTERIM_DIR, "elections_municipal_2023.csv")
        muni_df.to_csv(out_path, index=False)
        print(f"\n  Saved: {out_path}")
        print(f"    {len(muni_df)} rows × {len(muni_df.columns)} columns")
    else:
        print(f"\n  Missing: {muni_path}")

    # ---------------------------------------------------------------
    # 2. Congress elections July 2023
    # ---------------------------------------------------------------
    cong_path = os.path.join(RAW_DIR, "02_202307_1.xlsx")
    if os.path.exists(cong_path):
        cong_df = parse_election_xlsx(
            cong_path,
            party_map=PARTY_ABBREVS_CONGRESS,
            header_row=6,
            data_start=7,
            sheet_name="Municipios",
        )
        cong_df["year"] = 2023
        cong_df["election_type"] = "congress"

        # Save
        out_path = os.path.join(INTERIM_DIR, "elections_congress_2023.csv")
        cong_df.to_csv(out_path, index=False)
        print(f"\n  Saved: {out_path}")
        print(f"    {len(cong_df)} rows × {len(cong_df.columns)} columns")
    else:
        print(f"\n  Missing: {cong_path}")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
