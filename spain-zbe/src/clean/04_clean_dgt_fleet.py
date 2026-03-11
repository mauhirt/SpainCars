"""
04_clean_dgt_fleet.py

Clean DGT vehicle fleet data: extract environmental label shares by province
from annual Excel workbooks (2019-2024).

Sheets used:
    - P_TUR_MEDIO: Turismos (passenger cars) by environmental label
    - P_MOTO_MEDIO: Motocicletas (motorcycles) by environmental label
    - V_4_1: All vehicle types by province and fuel type

Output:
    data/interim/dgt_fleet_labels_province.csv
    data/interim/dgt_fleet_fuel_province.csv

Usage:
    python spain-zbe/src/clean/04_clean_dgt_fleet.py
"""

import os
import re
import pandas as pd

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "dgt_fleet")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

YEARS = range(2019, 2025)

# Standard DGT environmental labels
LABEL_COLS = ["CERO", "B", "C", "ECO", "Sin distintivo"]

# Map province names (as they appear in DGT Excel) to INE 2-digit codes
# DGT uses slightly different names/accents across years
PROVINCE_NAME_TO_CODE = {
    "araba/álava": "01", "álava": "01", "araba": "01",
    "albacete": "02",
    "alicante/alacant": "03", "alicante": "03", "alacant": "03",
    "almería": "04", "almeria": "04",
    "ávila": "05", "avila": "05",
    "badajoz": "06",
    "balears (illes)": "07", "illes balears": "07", "baleares": "07",
    "barcelona": "08",
    "burgos": "09",
    "cáceres": "10", "caceres": "10",
    "cádiz": "11", "cadiz": "11",
    "castellón/castelló": "12", "castellón": "12", "castelló": "12",
    "castellon/castello": "12", "castellon": "12", "castello": "12",
    "ciudad real": "13",
    "córdoba": "14", "cordoba": "14",
    "coruña (a)": "15", "a coruña": "15", "coruña, a": "15",
    "cuenca": "16",
    "girona": "17", "gerona": "17",
    "granada": "18",
    "guadalajara": "19",
    "gipuzkoa": "20", "guipúzcoa": "20", "guipuzcoa": "20",
    "huelva": "21",
    "huesca": "22",
    "jaén": "23", "jaen": "23",
    "león": "24", "leon": "24",
    "lleida": "25", "lérida": "25",
    "rioja (la)": "26", "la rioja": "26",
    "lugo": "27",
    "madrid": "28",
    "málaga": "29", "malaga": "29",
    "murcia": "30",
    "navarra": "31",
    "ourense": "32", "orense": "32",
    "asturias": "33", "oviedo": "33",
    "palencia": "34",
    "palmas (las)": "35", "las palmas": "35",
    "pontevedra": "36",
    "salamanca": "37",
    "santa cruz de tenerife": "38", "s.c.tenerife": "38",
    "cantabria": "39", "santander": "39",
    "segovia": "40",
    "sevilla": "41",
    "soria": "42",
    "tarragona": "43",
    "teruel": "44",
    "toledo": "45",
    "valencia/valència": "46", "valencia": "46", "valència": "46",
    "valladolid": "47",
    "bizkaia": "48", "vizcaya": "48",
    "zamora": "49",
    "zaragoza": "50",
    "ceuta": "51",
    "melilla": "52",
    "alicante/ala": "03",
}


def normalize_province_name(name):
    """Normalize a province name for matching."""
    if not isinstance(name, str):
        return ""
    name = name.strip().lower()
    # Remove newlines that appear in some Excel cells
    name = name.replace("\n", " ").replace("\r", "")
    # Remove leading/trailing whitespace again
    name = name.strip()
    return name


def province_name_to_code(name):
    """Convert a province name to its 2-digit INE code."""
    norm = normalize_province_name(name)
    if norm in PROVINCE_NAME_TO_CODE:
        return PROVINCE_NAME_TO_CODE[norm]
    # Try partial matching for truncated names
    for key, code in PROVINCE_NAME_TO_CODE.items():
        if norm.startswith(key) or key.startswith(norm):
            return code
    return None


def parse_label_sheet(filepath, sheet_name, year):
    """
    Parse a P_TUR_MEDIO or P_MOTO_MEDIO sheet.

    Returns a DataFrame with columns:
        cod_provincia, year, vehicle_type, CERO, B, C, ECO, sin_distintivo, total
    """
    wb = pd.ExcelFile(filepath, engine="openpyxl")
    if sheet_name not in wb.sheet_names:
        print(f"  Warning: sheet {sheet_name} not found in {filepath}")
        return pd.DataFrame()

    # Read all data, skip the title row and blank row
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None,
                       engine="openpyxl")

    # Find the header row (contains "CERO" or "Provincias")
    header_idx = None
    for i, row in df.iterrows():
        vals = [str(v).strip().upper().replace("\n", " ") for v in row if pd.notna(v)]
        if any("CERO" in v for v in vals):
            header_idx = i
            break

    if header_idx is None:
        print(f"  Warning: could not find header in {sheet_name} for {year}")
        return pd.DataFrame()

    # Use the row after header as start of data
    data_start = header_idx + 1

    # Parse data rows
    records = []
    for i in range(data_start, len(df)):
        row = df.iloc[i]
        prov_name = row.iloc[0]
        if not isinstance(prov_name, str) or prov_name.strip() == "":
            continue
        # Skip total/summary rows
        norm = normalize_province_name(prov_name)
        if norm in ("total", "totales", "total nacional", ""):
            continue

        code = province_name_to_code(prov_name)
        if code is None:
            continue

        # Extract label counts (columns 1-5, possibly 6 for "Se desconoce")
        vals = []
        for j in range(1, 6):
            v = row.iloc[j] if j < len(row) else 0
            vals.append(int(v) if pd.notna(v) and v != "" else 0)

        # Check for "Se desconoce" column
        se_desconoce = 0
        if len(row) > 6 and pd.notna(row.iloc[6]):
            try:
                se_desconoce = int(row.iloc[6])
            except (ValueError, TypeError):
                pass

        vehicle_type = "turismos" if "TUR" in sheet_name else "motocicletas"
        total = sum(vals) + se_desconoce

        records.append({
            "cod_provincia": code,
            "year": year,
            "vehicle_type": vehicle_type,
            "cero": vals[0],
            "b": vals[1],
            "c": vals[2],
            "eco": vals[3],
            "sin_distintivo": vals[4],
            "se_desconoce": se_desconoce,
            "total": total,
        })

    return pd.DataFrame(records)


def parse_fuel_sheet(filepath, year):
    """
    Parse V_4_1 sheet (vehicle types by province and fuel).

    Returns a DataFrame with province-level fuel breakdown for turismos.
    """
    sheet_name = "V_4_1"
    wb = pd.ExcelFile(filepath, engine="openpyxl")
    if sheet_name not in wb.sheet_names:
        print(f"  Warning: sheet {sheet_name} not found in {filepath}")
        return pd.DataFrame()

    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None,
                       engine="openpyxl")

    # Find header row
    header_idx = None
    for i, row in df.iterrows():
        vals = [str(v).strip().upper().replace("\n", " ") for v in row if pd.notna(v)]
        if any("GASOLINA" in v for v in vals):
            header_idx = i
            break

    if header_idx is None:
        print(f"  Warning: could not find header in {sheet_name} for {year}")
        return pd.DataFrame()

    data_start = header_idx + 1

    records = []
    for i in range(data_start, len(df)):
        row = df.iloc[i]
        prov_name = row.iloc[0]
        if not isinstance(prov_name, str):
            continue
        norm = normalize_province_name(prov_name)
        if norm in ("total", "totales", "total nacional", ""):
            continue

        code = province_name_to_code(prov_name)
        if code is None:
            continue

        # Turismos columns: Gasolina (idx 12), Gasoil (13), Otros (14), Total (15)
        # Column positions vary by year but turismos are always after autobuses
        # We look for the pattern: province, then blocks of 4 cols per vehicle type
        # Camiones(4) + Furgonetas(4) + Autobuses(4) + Turismos(4) + ...
        # So turismos start at column 13 (0-indexed)
        try:
            tur_gasolina = int(row.iloc[13]) if pd.notna(row.iloc[13]) else 0
            tur_gasoil = int(row.iloc[14]) if pd.notna(row.iloc[14]) else 0
            tur_otros = int(row.iloc[15]) if pd.notna(row.iloc[15]) else 0
            tur_total = int(row.iloc[16]) if pd.notna(row.iloc[16]) else 0
            # Totals for all vehicle types
            total_gasolina = int(row.iloc[29]) if pd.notna(row.iloc[29]) else 0
            total_gasoil = int(row.iloc[30]) if pd.notna(row.iloc[30]) else 0
            total_otros = int(row.iloc[31]) if pd.notna(row.iloc[31]) else 0
            total_total = int(row.iloc[32]) if pd.notna(row.iloc[32]) else 0
        except (IndexError, ValueError, TypeError):
            continue

        records.append({
            "cod_provincia": code,
            "year": year,
            "tur_gasolina": tur_gasolina,
            "tur_gasoil": tur_gasoil,
            "tur_otros": tur_otros,
            "tur_total": tur_total,
            "total_gasolina": total_gasolina,
            "total_gasoil": total_gasoil,
            "total_otros": total_otros,
            "total_total": total_total,
        })

    return pd.DataFrame(records)


def compute_label_shares(df):
    """Add share columns for each environmental label.

    Denominator excludes 'se_desconoce' so shares of known labels sum to 1.0.
    """
    known_total = df["total"] - df["se_desconoce"]
    for col in ["cero", "b", "c", "eco", "sin_distintivo"]:
        df[f"share_{col}"] = df[col] / known_total.replace(0, float("nan"))
    return df


def compute_fuel_shares(df):
    """Add fuel share columns."""
    df["tur_share_gasolina"] = df["tur_gasolina"] / df["tur_total"].replace(0, float("nan"))
    df["tur_share_gasoil"] = df["tur_gasoil"] / df["tur_total"].replace(0, float("nan"))
    df["tur_share_otros"] = df["tur_otros"] / df["tur_total"].replace(0, float("nan"))
    return df


def main():
    print("=" * 70)
    print("DGT Fleet Data — Clean Environmental Labels & Fuel Types")
    print("=" * 70)

    # ---- Environmental label data ----
    all_labels = []
    for year in YEARS:
        filepath = os.path.join(RAW_DIR, f"parque_vehiculos_{year}.xlsx")
        if not os.path.exists(filepath):
            print(f"  {year}: file not found, skipping")
            continue

        print(f"  {year}: parsing environmental labels...")
        for sheet in ["P_TUR_MEDIO", "P_MOTO_MEDIO"]:
            df = parse_label_sheet(filepath, sheet, year)
            if len(df) > 0:
                all_labels.append(df)
                print(f"    {sheet}: {len(df)} provinces")

    if all_labels:
        labels_df = pd.concat(all_labels, ignore_index=True)
        labels_df = compute_label_shares(labels_df)
        labels_df = labels_df.sort_values(["year", "vehicle_type", "cod_provincia"])

        output_path = os.path.join(INTERIM_DIR, "dgt_fleet_labels_province.csv")
        labels_df.to_csv(output_path, index=False)
        print(f"\n  Saved environmental labels: {output_path}")
        print(f"    {len(labels_df)} rows, {labels_df['year'].nunique()} years, "
              f"{labels_df['cod_provincia'].nunique()} provinces")
        print(f"    Vehicle types: {labels_df['vehicle_type'].unique().tolist()}")

        # Summary statistics
        latest = labels_df[labels_df["year"] == labels_df["year"].max()]
        for vtype in latest["vehicle_type"].unique():
            sub = latest[latest["vehicle_type"] == vtype]
            print(f"\n    {vtype} ({sub['year'].iloc[0]}) — national averages:")
            total = sub[["cero", "b", "c", "eco", "sin_distintivo"]].sum()
            grand = total.sum()
            for col in ["cero", "b", "c", "eco", "sin_distintivo"]:
                print(f"      {col:>15s}: {total[col]:>10,.0f} ({total[col]/grand:.1%})")
    else:
        print("\n  No environmental label data found!")

    # ---- Fuel type data ----
    all_fuel = []
    for year in YEARS:
        filepath = os.path.join(RAW_DIR, f"parque_vehiculos_{year}.xlsx")
        if not os.path.exists(filepath):
            continue

        print(f"\n  {year}: parsing fuel types...")
        df = parse_fuel_sheet(filepath, year)
        if len(df) > 0:
            all_fuel.append(df)
            print(f"    V_4_1: {len(df)} provinces")

    if all_fuel:
        fuel_df = pd.concat(all_fuel, ignore_index=True)
        fuel_df = compute_fuel_shares(fuel_df)
        fuel_df = fuel_df.sort_values(["year", "cod_provincia"])

        output_path = os.path.join(INTERIM_DIR, "dgt_fleet_fuel_province.csv")
        fuel_df.to_csv(output_path, index=False)
        print(f"\n  Saved fuel types: {output_path}")
        print(f"    {len(fuel_df)} rows, {fuel_df['year'].nunique()} years")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
