"""
04_clean_dgt_fleet.py

Clean DGT vehicle fleet data at two levels of granularity:

1. MUNICIPAL level (primary): Environmental label shares from
   DatosMunicipalesGeneral_{year}.xlsx files (2017-2024).
   These contain per-municipality counts by label (B, C, ECO, 0, Sin Distintivo).

2. PROVINCE level (supplementary): Turismos/motocicletas label breakdown and
   fuel type shares from annual parque_vehiculos_{year}.xlsx workbooks (2019-2024).

Output:
    data/interim/dgt_fleet_labels_municipal.csv   (primary — municipality × year panel)
    data/interim/dgt_fleet_labels_province.csv    (supplementary — province × year × vehicle type)
    data/interim/dgt_fleet_fuel_province.csv      (supplementary — province × year fuel breakdown)

Usage:
    python spain-zbe/src/clean/04_clean_dgt_fleet.py
"""

import os
import pandas as pd

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "dgt_fleet")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

PROVINCE_YEARS = range(2019, 2025)
MUNICIPAL_YEARS = range(2017, 2025)

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
    name = name.replace("\n", " ").replace("\r", "")
    return name.strip()


def province_name_to_code(name):
    """Convert a province name to its 2-digit INE code."""
    norm = normalize_province_name(name)
    if norm in PROVINCE_NAME_TO_CODE:
        return PROVINCE_NAME_TO_CODE[norm]
    for key, code in PROVINCE_NAME_TO_CODE.items():
        if norm.startswith(key) or key.startswith(norm):
            return code
    return None


# =========================================================================
# MUNICIPAL-LEVEL: DatosMunicipalesGeneral_{year}.xlsx
# =========================================================================

def parse_municipal_labels(filepath, year):
    """
    Parse DatosMunicipalesGeneral_{year}.xlsx for environmental label data.

    Columns (consistent across 2017-2024):
        A: Código INE (5-digit municipal code)
        B: Municipio
        C: Provincia
        D: Comunidad Autónoma
        ...
        AZ (col 51): Distintivo B
        BA (col 52): Distintivo C
        BB (col 53): Distintivo ECO
        BC (col 54): Distintivo 0
        BD (col 55): Sin Distintivo
    """
    df = pd.read_excel(filepath, engine="openpyxl")

    # Find the label columns by header name
    col_map = {}
    for col in df.columns:
        col_str = str(col).strip()
        if col_str == "Distintivo B":
            col_map["b"] = col
        elif col_str == "Distintivo C":
            col_map["c"] = col
        elif col_str == "Distintivo ECO":
            col_map["eco"] = col
        elif col_str == "Distintivo 0":
            col_map["cero"] = col
        elif col_str == "Sin Distintivo":
            col_map["sin_distintivo"] = col

    if len(col_map) < 5:
        print(f"    Warning: only found {len(col_map)}/5 label columns in {filepath}")
        return pd.DataFrame()

    # Get INE code column (first column, named "Código INE")
    ine_col = df.columns[0]
    name_col = df.columns[1]

    records = []
    for _, row in df.iterrows():
        cod_ine = str(row[ine_col]).strip()
        # Skip non-numeric or empty codes
        if not cod_ine or not cod_ine.replace(" ", "").isdigit():
            continue
        # Zero-pad to 5 digits
        cod_ine = cod_ine.zfill(5)
        # Skip "unspecified" municipality codes ending in 000
        if cod_ine.endswith("000"):
            continue

        muni_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""

        label_vals = {}
        for label, col in col_map.items():
            v = row[col]
            label_vals[label] = int(v) if pd.notna(v) else 0

        total = sum(label_vals.values())
        records.append({
            "cod_ine": cod_ine,
            "cod_provincia": cod_ine[:2],
            "municipio": muni_name,
            "year": year,
            **label_vals,
            "total": total,
        })

    return pd.DataFrame(records)


def compute_municipal_label_shares(df):
    """Add share columns for each environmental label at municipal level."""
    for col in ["cero", "b", "c", "eco", "sin_distintivo"]:
        df[f"share_{col}"] = df[col] / df["total"].replace(0, float("nan"))
    return df


# =========================================================================
# PROVINCE-LEVEL: parque_vehiculos_{year}.xlsx
# =========================================================================

def parse_label_sheet(filepath, sheet_name, year):
    """Parse a P_TUR_MEDIO or P_MOTO_MEDIO sheet (province-level)."""
    wb = pd.ExcelFile(filepath, engine="openpyxl")
    if sheet_name not in wb.sheet_names:
        return pd.DataFrame()

    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None,
                       engine="openpyxl")

    header_idx = None
    for i, row in df.iterrows():
        vals = [str(v).strip().upper().replace("\n", " ") for v in row if pd.notna(v)]
        if any("CERO" in v for v in vals):
            header_idx = i
            break

    if header_idx is None:
        return pd.DataFrame()

    data_start = header_idx + 1
    records = []
    for i in range(data_start, len(df)):
        row = df.iloc[i]
        prov_name = row.iloc[0]
        if not isinstance(prov_name, str) or prov_name.strip() == "":
            continue
        norm = normalize_province_name(prov_name)
        if norm in ("total", "totales", "total nacional", ""):
            continue

        code = province_name_to_code(prov_name)
        if code is None:
            continue

        vals = []
        for j in range(1, 6):
            v = row.iloc[j] if j < len(row) else 0
            vals.append(int(v) if pd.notna(v) and v != "" else 0)

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
    """Parse V_4_1 sheet (vehicle types by province and fuel)."""
    sheet_name = "V_4_1"
    wb = pd.ExcelFile(filepath, engine="openpyxl")
    if sheet_name not in wb.sheet_names:
        return pd.DataFrame()

    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None,
                       engine="openpyxl")

    header_idx = None
    for i, row in df.iterrows():
        vals = [str(v).strip().upper().replace("\n", " ") for v in row if pd.notna(v)]
        if any("GASOLINA" in v for v in vals):
            header_idx = i
            break

    if header_idx is None:
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

        try:
            tur_gasolina = int(row.iloc[13]) if pd.notna(row.iloc[13]) else 0
            tur_gasoil = int(row.iloc[14]) if pd.notna(row.iloc[14]) else 0
            tur_otros = int(row.iloc[15]) if pd.notna(row.iloc[15]) else 0
            tur_total = int(row.iloc[16]) if pd.notna(row.iloc[16]) else 0
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


def compute_province_label_shares(df):
    """Add share columns (denominator excludes se_desconoce)."""
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


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("DGT Fleet Data — Clean Environmental Labels & Fuel Types")
    print("=" * 70)

    # ==== 1. MUNICIPAL-LEVEL LABELS (primary) ====
    print("\n--- Municipal-level environmental labels (2017-2024) ---\n")
    all_municipal = []
    for year in MUNICIPAL_YEARS:
        filepath = os.path.join(RAW_DIR, f"DatosMunicipalesGeneral_{year}.xlsx")
        if not os.path.exists(filepath):
            print(f"  {year}: file not found, skipping")
            continue

        print(f"  {year}: parsing...", end=" ")
        df = parse_municipal_labels(filepath, year)
        if len(df) > 0:
            all_municipal.append(df)
            print(f"{len(df)} municipalities")
        else:
            print("no data")

    if all_municipal:
        muni_df = pd.concat(all_municipal, ignore_index=True)
        muni_df = compute_municipal_label_shares(muni_df)
        muni_df = muni_df.sort_values(["year", "cod_ine"]).reset_index(drop=True)

        output_path = os.path.join(INTERIM_DIR, "dgt_fleet_labels_municipal.csv")
        muni_df.to_csv(output_path, index=False)
        print(f"\n  Saved: {output_path}")
        print(f"    {len(muni_df)} rows, {muni_df['year'].nunique()} years, "
              f"{muni_df['cod_ine'].nunique()} municipalities")

        # Summary: municipalities near the 50k threshold
        latest = muni_df[muni_df["year"] == muni_df["year"].max()]
        above_50k = latest[latest["total"] > 5000]  # rough proxy
        print(f"    Municipalities with >5000 labeled vehicles ({latest['year'].iloc[0]}): "
              f"{len(above_50k)}")
        print(f"\n    National totals ({latest['year'].iloc[0]}):")
        for col in ["cero", "b", "c", "eco", "sin_distintivo"]:
            total = latest[col].sum()
            grand = latest["total"].sum()
            print(f"      {col:>15s}: {total:>12,.0f} ({total/grand:.1%})")
    else:
        print("\n  No municipal-level data found!")

    # ==== 2. PROVINCE-LEVEL LABELS (supplementary) ====
    print("\n--- Province-level environmental labels by vehicle type (2019-2024) ---\n")
    all_labels = []
    for year in PROVINCE_YEARS:
        filepath = os.path.join(RAW_DIR, f"parque_vehiculos_{year}.xlsx")
        if not os.path.exists(filepath):
            continue

        for sheet in ["P_TUR_MEDIO", "P_MOTO_MEDIO"]:
            df = parse_label_sheet(filepath, sheet, year)
            if len(df) > 0:
                all_labels.append(df)

    if all_labels:
        labels_df = pd.concat(all_labels, ignore_index=True)
        labels_df = compute_province_label_shares(labels_df)
        labels_df = labels_df.sort_values(["year", "vehicle_type", "cod_provincia"])

        output_path = os.path.join(INTERIM_DIR, "dgt_fleet_labels_province.csv")
        labels_df.to_csv(output_path, index=False)
        print(f"  Saved: {output_path} ({len(labels_df)} rows)")

    # ==== 3. PROVINCE-LEVEL FUEL (supplementary) ====
    print("\n--- Province-level fuel types (2019-2024) ---\n")
    all_fuel = []
    for year in PROVINCE_YEARS:
        filepath = os.path.join(RAW_DIR, f"parque_vehiculos_{year}.xlsx")
        if not os.path.exists(filepath):
            continue

        df = parse_fuel_sheet(filepath, year)
        if len(df) > 0:
            all_fuel.append(df)

    if all_fuel:
        fuel_df = pd.concat(all_fuel, ignore_index=True)
        fuel_df = compute_fuel_shares(fuel_df)
        fuel_df = fuel_df.sort_values(["year", "cod_provincia"])

        output_path = os.path.join(INTERIM_DIR, "dgt_fleet_fuel_province.csv")
        fuel_df.to_csv(output_path, index=False)
        print(f"  Saved: {output_path} ({len(fuel_df)} rows)")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
