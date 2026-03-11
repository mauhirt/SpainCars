"""
05_clean_elections.py

Clean Spanish municipal election data from Ministry of Interior fixed-width
DAT files (GitHub mirror of JaimeObregon/infoelectoral).

Parses:
    - File 03 (candidacies): maps candidacy codes to party names and
      national accumulation codes
    - File 06 (results by municipality + candidacy): votes per party per
      municipality (district 99 = municipal total)
    - File 05 (summary by municipality): census, total votes, blank/null
      votes for turnout computation

Output:
    data/interim/elections_municipal_panel.csv

Usage:
    python spain-zbe/src/clean/05_clean_elections.py
"""

import os
import pandas as pd

RAW_DIR = os.path.join("spain-zbe", "data", "raw", "elections")
INTERIM_DIR = os.path.join("spain-zbe", "data", "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

# Elections available from the GitHub mirror (2015 and 2019 municipal)
ELECTIONS = {
    2015: {
        "candidacies": "gh_2015_03_candidacies.DAT",
        "results": "gh_2015_06_results_muni_candidacy.DAT",
        "summary": "gh_2015_05_summary_muni.DAT",
    },
    2019: {
        "candidacies": "gh_2019_03_candidacies.DAT",
        "results": "gh_2019_06_results_muni_candidacy.DAT",
        "summary": "gh_2019_05_summary_muni.DAT",
    },
}

# Key parties to track — identified by their national accumulation code
# (last 6 digits of the candidacy record). These codes change between elections,
# so we identify parties by abbreviation pattern matching.
PARTY_PATTERNS = {
    "PP": r"^PP$|^P\.P\.$|^PARTIDO POPULAR",
    "PSOE": r"^PSOE|^P\.S\.O\.E|^PSdeG-PSOE|^PSC-PSOE|^PSE-EE",
    "VOX": r"^VOX$",
    "Cs": r"^C'[sS]$|^Cs$|^CIUDADANOS",
    "UP": (r"^PODEMOS|^UNIDAS PODEMOS|^EN COM[UÚ] PODEM|^BARCELONA EN COM"
           r"|^AhoraMadrid$|^AHORA MADRID|^M[ÁA]S MADRID|^MasMadrid"
           r"|^M[ÁA]S PA[ÍI]S"),
}


def parse_candidacies(filepath, encoding="latin-1"):
    """
    Parse file 03 (candidacies).

    Format (fixed-width):
        Cols 1-2:   Election type
        Cols 3-6:   Year
        Cols 7-8:   Month
        Cols 9-14:  Candidacy code (6 digits)
        Cols 15-64: Party abbreviation (50 chars)
        Cols 65-214: Party full name (150 chars)
        Cols 215-220: Accumulation code (province level)
        Cols 221-226: Accumulation code (CCAA level)
        Cols 227-232: Accumulation code (national level)
    """
    records = []
    with open(filepath, "r", encoding=encoding) as f:
        for line in f:
            line = line.rstrip("\n\r")
            if len(line) < 64:
                continue
            candidacy_code = line[8:14]
            abbreviation = line[14:64].strip()
            full_name = line[64:214].strip() if len(line) > 64 else ""
            # National accumulation code (last 6 digits)
            nat_accum = line[226:232].strip() if len(line) >= 232 else ""

            records.append({
                "candidacy_code": candidacy_code,
                "abbreviation": abbreviation,
                "full_name": full_name,
                "nat_accum_code": nat_accum,
            })

    df = pd.DataFrame(records)
    # Deduplicate: same candidacy code may appear multiple times
    # (regional variants with same code). Keep first occurrence.
    df = df.drop_duplicates(subset=["candidacy_code"], keep="first")
    return df


def identify_parties(candidacies_df):
    """
    Identify key parties by matching abbreviation or full name patterns.
    Returns a dict mapping candidacy_code -> party label.
    """
    import re

    code_to_party = {}
    for _, row in candidacies_df.iterrows():
        abbr = row["abbreviation"]
        name = row["full_name"]
        code = row["candidacy_code"]

        for party_label, pattern in PARTY_PATTERNS.items():
            if re.search(pattern, abbr, re.IGNORECASE) or \
               re.search(pattern, name, re.IGNORECASE):
                code_to_party[code] = party_label
                break

    return code_to_party


def find_national_accum_codes(candidacies_df, code_to_party):
    """
    Find the national accumulation code for each major party.
    This allows us to catch all regional variants.
    """
    party_nat_codes = {}
    for code, party in code_to_party.items():
        row = candidacies_df[candidacies_df["candidacy_code"] == code]
        if len(row) > 0:
            nat_code = row.iloc[0]["nat_accum_code"]
            if nat_code and party not in party_nat_codes:
                party_nat_codes[party] = set()
            if nat_code:
                party_nat_codes[party].add(nat_code)

    # Now expand: any candidacy with a matching national accum code
    # also belongs to that party
    expanded = {}
    for _, row in candidacies_df.iterrows():
        nat_code = row["nat_accum_code"]
        code = row["candidacy_code"]
        for party, nat_codes in party_nat_codes.items():
            if nat_code in nat_codes:
                expanded[code] = party
                break

    # Merge with direct matches (direct takes priority)
    for code, party in code_to_party.items():
        expanded[code] = party

    return expanded


def parse_results_file06(filepath, encoding="latin-1"):
    """
    Parse file 06 (results by municipality + candidacy).

    Format (fixed-width):
        Cols 1-2:   Election type
        Cols 3-6:   Year
        Cols 7-8:   Month
        Col 9:      Turn
        Cols 10-11: Province code
        Cols 12-14: Municipality code
        Cols 15-16: District (99 = municipal total)
        Cols 17-22: Candidacy code
        Cols 23-30: Votes (8 digits)
        Cols 31-33: Seats/concejales (3 digits)
    """
    records = []
    with open(filepath, "r", encoding=encoding) as f:
        for line in f:
            line = line.rstrip("\n\r")
            if len(line) < 30:
                continue

            province = line[9:11]
            municipality = line[11:14]
            district = line[14:16]
            candidacy_code = line[16:22]
            votes_str = line[22:30]
            seats_str = line[30:33] if len(line) >= 33 else "0"

            try:
                votes = int(votes_str)
                seats = int(seats_str) if seats_str.strip() else 0
            except ValueError:
                continue

            records.append({
                "cod_provincia": province,
                "cod_municipio": municipality,
                "district": district,
                "candidacy_code": candidacy_code,
                "votes": votes,
                "seats": seats,
            })

    return pd.DataFrame(records)


def parse_summary_file05(filepath, encoding="latin-1"):
    """
    Parse file 05 (summary by municipality).

    Format (fixed-width):
        Cols 1-2:   Election type
        Cols 3-6:   Year
        Cols 7-8:   Month
        Col 9:      Turn
        Cols 10-11: CCAA code
        Cols 12-13: Province code
        Cols 14-16: Municipality code
        Cols 17-18: District (99 = municipal total)
        Cols 19-118: Municipality name (100 chars)
        Cols 119+:  Numeric fields (mesas, census, votes, etc.)

    We extract the municipality name and attempt to parse
    key numeric fields for turnout computation.
    """
    records = []
    with open(filepath, "r", encoding=encoding) as f:
        for line in f:
            line = line.rstrip("\n\r")
            if len(line) < 119:
                continue

            ccaa = line[9:11]
            province = line[11:13]
            municipality = line[13:16]
            district = line[16:18]
            muni_name = line[18:118].strip()
            numeric_part = line[118:]

            records.append({
                "cod_ccaa": ccaa,
                "cod_provincia": province,
                "cod_municipio": municipality,
                "district": district,
                "municipio": muni_name,
                "numeric_raw": numeric_part,
            })

    return pd.DataFrame(records)


def process_election_year(year, files):
    """Process all data for a single election year."""
    print(f"\n  --- {year} Municipal Election ---")

    # Check files exist
    for key, fname in files.items():
        fpath = os.path.join(RAW_DIR, fname)
        if not os.path.exists(fpath):
            print(f"    Missing: {fname}")
            return None

    # 1. Parse candidacies
    cand_df = parse_candidacies(os.path.join(RAW_DIR, files["candidacies"]))
    print(f"    Candidacies: {len(cand_df)} unique codes")

    # 2. Identify key parties
    code_to_party = identify_parties(cand_df)
    code_to_party = find_national_accum_codes(cand_df, code_to_party)
    party_counts = {}
    for p in code_to_party.values():
        party_counts[p] = party_counts.get(p, 0) + 1
    print(f"    Identified parties: {party_counts}")

    # 3. Parse results (file 06)
    results_df = parse_results_file06(os.path.join(RAW_DIR, files["results"]))
    print(f"    Results: {len(results_df)} records")

    # Filter to district 99 (municipal totals)
    totals = results_df[results_df["district"] == "99"].copy()
    print(f"    Municipal totals (district 99): {len(totals)} records")

    if len(totals) == 0:
        print("    Warning: no district 99 records found. "
              "Aggregating across districts...")
        totals = results_df.groupby(
            ["cod_provincia", "cod_municipio", "candidacy_code"],
            as_index=False
        ).agg({"votes": "sum", "seats": "sum"})

    # 4. Map candidacy codes to parties
    totals["party"] = totals["candidacy_code"].map(code_to_party)

    # 5. Build INE code
    totals["cod_ine"] = totals["cod_provincia"] + totals["cod_municipio"]

    # 6. Compute total valid votes per municipality (all candidacies, not just tracked)
    muni_total_votes = totals.groupby("cod_ine")["votes"].sum().rename("total_votes")

    # 7. Get full list of municipalities (so we don't drop any)
    all_munis = muni_total_votes.index

    # 8. Pivot: one row per municipality, columns for each party's votes
    tracked = totals[totals["party"].notna()]
    if len(tracked) > 0:
        party_votes = tracked.groupby(
            ["cod_ine", "party"]
        )["votes"].sum().unstack(fill_value=0)
        party_votes.columns = [f"votos_{c.lower()}" for c in party_votes.columns]

        party_seats = tracked.groupby(
            ["cod_ine", "party"]
        )["seats"].sum().unstack(fill_value=0)
        party_seats.columns = [f"seats_{c.lower()}" for c in party_seats.columns]
    else:
        party_votes = pd.DataFrame(index=all_munis)
        party_seats = pd.DataFrame(index=all_munis)

    # 9. Merge — use reindex to keep ALL municipalities (fill zeros for missing parties)
    muni_df = party_votes.reindex(all_munis, fill_value=0).join(
        party_seats.reindex(all_munis, fill_value=0)
    ).join(muni_total_votes)
    muni_df["year"] = year

    # Compute vote shares
    for col in muni_df.columns:
        if col.startswith("votos_"):
            party_name = col.replace("votos_", "")
            muni_df[f"share_{party_name}"] = (
                muni_df[col] / muni_df["total_votes"].replace(0, float("nan"))
            )

    muni_df = muni_df.reset_index()
    muni_df["cod_provincia"] = muni_df["cod_ine"].str[:2]

    # 9. Add municipality names from file 05
    summary_df = parse_summary_file05(os.path.join(RAW_DIR, files["summary"]))
    # Filter to district 99 (municipal totals)
    summary_totals = summary_df[summary_df["district"] == "99"].copy()
    if len(summary_totals) == 0:
        # Some files might use a different district code for totals
        summary_totals = summary_df.drop_duplicates(
            subset=["cod_provincia", "cod_municipio"], keep="first"
        )
    summary_totals["cod_ine"] = (
        summary_totals["cod_provincia"] + summary_totals["cod_municipio"]
    )
    name_map = summary_totals.set_index("cod_ine")["municipio"].to_dict()
    muni_df["municipio"] = muni_df["cod_ine"].map(name_map)

    print(f"    Output: {len(muni_df)} municipalities")

    # Quick stats
    if "votos_vox" in muni_df.columns:
        vox_munis = (muni_df["votos_vox"] > 0).sum()
        print(f"    VOX ran in {vox_munis}/{len(muni_df)} municipalities")
    else:
        print(f"    VOX: not present in {year} (expected for 2015)")

    if "votos_pp" in muni_df.columns:
        pp_mean = muni_df["share_pp"].mean()
        print(f"    PP mean vote share: {pp_mean:.1%}")

    if "votos_psoe" in muni_df.columns:
        psoe_mean = muni_df["share_psoe"].mean()
        print(f"    PSOE mean vote share: {psoe_mean:.1%}")

    return muni_df


def main():
    print("=" * 70)
    print("Election Data — Clean Municipal Results")
    print("=" * 70)

    all_years = []
    for year, files in ELECTIONS.items():
        df = process_election_year(year, files)
        if df is not None:
            all_years.append(df)

    if not all_years:
        print("\n  No election data could be processed!")
        print("  Ensure DAT files are in data/raw/elections/")
        return

    # Combine all years
    panel = pd.concat(all_years, ignore_index=True)

    # Ensure consistent columns (fill missing party columns with 0)
    for party in ["pp", "psoe", "vox", "cs", "up"]:
        for prefix in ["votos_", "share_", "seats_"]:
            col = f"{prefix}{party}"
            if col not in panel.columns:
                panel[col] = 0

    # Sort
    panel = panel.sort_values(["year", "cod_ine"]).reset_index(drop=True)

    # Reorder columns
    id_cols = ["cod_ine", "cod_provincia", "municipio", "year"]
    vote_cols = sorted([c for c in panel.columns if c.startswith("votos_")])
    share_cols = sorted([c for c in panel.columns if c.startswith("share_")])
    seat_cols = sorted([c for c in panel.columns if c.startswith("seats_")])
    other_cols = ["total_votes"]
    ordered = id_cols + other_cols + vote_cols + share_cols + seat_cols
    remaining = [c for c in panel.columns if c not in ordered]
    panel = panel[ordered + remaining]

    output_path = os.path.join(INTERIM_DIR, "elections_municipal_panel.csv")
    panel.to_csv(output_path, index=False)
    print(f"\n  Saved: {output_path}")
    print(f"    {len(panel)} rows × {len(panel.columns)} columns")
    print(f"    Years: {sorted(panel['year'].unique())}")
    print(f"    Municipalities per year: "
          f"{panel.groupby('year')['cod_ine'].nunique().to_dict()}")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
