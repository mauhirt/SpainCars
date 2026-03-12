"""
12_party_zbe_adoption.py

Which parties implemented ZBEs? Which delayed? Which were more stringent?

Uses the 2019 municipal election results to identify the governing party
(2019–2023 term) and cross-references with ZBE implementation status.

Key questions:
  1. Is the governing party (left vs right) a predictor of ZBE adoption?
  2. Among implementers, does party predict ZBE stringency?
  3. Among non-implementers, does party predict delay/refusal?
  4. After the May 2023 elections, did new right-wing governments reverse ZBEs?

Output:
  output/tables/party_zbe_*.csv
  output/figures/party_zbe_*.png
"""

import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
TAB_DIR = os.path.join(BASE_DIR, "output", "tables")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
os.makedirs(TAB_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# ===================================================================
# GOVERNING PARTY 2019-2023 — hand-coded for >50k municipalities
# ===================================================================
# Source: 2019 municipal election results + coalition knowledge
# For Spanish municipalities, the mayor's party is what matters.
# "left_bloc" = PSOE, Podemos/UP, local left, BComú, Compromís, Bildu, ERC, BNG
# "right_bloc" = PP, Cs, Vox, local right, PNV (center-right), JxCat (center-right)

# We code the MAYOR'S PARTY for the 2019-2023 term.
# For municipalities where we lack specific coalition data, we use
# the largest-party heuristic from seats data.

GOVERNING_PARTY_2019 = {
    # Major cities — well documented
    "28079": ("Madrid", "PP", "right"),        # Almeida (PP) from Jun 2019
    "08019": ("Barcelona", "BComú", "left"),   # Colau (Barcelona en Comú)
    "46250": ("València", "Compromís", "left"),# Ribó (Compromís)
    "41091": ("Sevilla", "PSOE", "left"),      # Espadas (PSOE)
    "50297": ("Zaragoza", "PSOE", "left"),     # Azcón lost → Lambán era; actually PP won
    "29067": ("Málaga", "PP", "right"),        # De la Torre (PP)
    "30030": ("Murcia", "PP", "right"),        # Ballesta (PP) with Cs
    "07040": ("Palma", "PSOE", "left"),        # Hila (PSOE) with Podemos
    "35016": ("Las Palmas GC", "PSOE", "left"),# Hidalgo (PSOE)
    "48020": ("Bilbao", "PNV", "right"),       # Aburto (PNV)
    "03014": ("Alicante", "PP", "right"),      # Barcala (PP) with Cs
    "14021": ("Córdoba", "PSOE", "left"),      # Bellido (PSOE) with IU
    "47186": ("Valladolid", "PSOE", "left"),   # Puente (PSOE)
    "36057": ("Vigo", "PSOE", "left"),         # Caballero (PSOE), actually independent left (Abel Caballero)
    "33024": ("Gijón", "PSOE", "left"),        # Moriyón lost, Ana González (PSOE)
    "08101": ("L'Hospitalet", "PSC", "left"),  # Marín (PSC/PSOE)
    "01059": ("Vitoria", "PNV", "right"),      # Urtaran (PNV) → actually PNV governs
    "15030": ("A Coruña", "PSOE", "left"),     # Inés Rey (PSOE)
    "03065": ("Elche", "PSOE", "left"),        # González (PSOE) with Compromís
    "18087": ("Granada", "PSOE", "left"),      # Cuenca (PSOE)
    "08279": ("Terrassa", "PSOE", "left"),     # Ballart (independent, Tot per Terrassa, left)
    "08015": ("Badalona", "PSOE", "left"),     # Sabater → actually Albiol(PP) won but lost motion → Rubio (Guanyem/left)
    "33044": ("Oviedo", "PP", "right"),        # Canteli (PP) with Cs
    "30016": ("Cartagena", "PSOE", "left"),    # Castejón (PSOE), with MC
    "08187": ("Sabadell", "PSOE", "left"),     # Farrés (PSC/PSOE)
    "11020": ("Jerez", "PSOE", "left"),        # Mamen Sánchez (PSOE)
    "28092": ("Móstoles", "PSOE", "left"),     # Noelia Posse (PSOE)
    "38038": ("Sta Cruz Tenerife", "PSOE", "left"), # Bermúdez actually CC → let's code CC as local right
    "31201": ("Pamplona", "Bildu", "left"),    # Asiron (EH Bildu) initially, then Esparz (Navarra Suma/PP coalition)
    "04013": ("Almería", "PP", "right"),       # Fernández-Pacheco (PP)
    "28005": ("Alcalá de Henares", "PSOE", "left"),  # Rodríguez (PSOE)
    "28058": ("Fuenlabrada", "PSOE", "left"),  # Ayuso (PSOE)
    "28074": ("Leganés", "PSOE", "left"),      # Llorente (PSOE)
    "20069": ("Donostia/SS", "Bildu", "left"), # Goia (EH Bildu)
    "28065": ("Getafe", "PSOE", "left"),       # Losada (PSOE)
    "09059": ("Burgos", "PSOE", "left"),       # De la Rosa (PSOE)
    "02003": ("Albacete", "PSOE", "left"),     # Casañ actually Cs → PP coalition
    "39075": ("Santander", "PP", "right"),     # Gema = actually Gema Equal (PP)
    "12040": ("Castellón", "PSOE", "left"),    # Amparo Marco (PSOE/Compromís)
    "28007": ("Alcorcón", "PSOE", "left"),     # Natalia de Andrés (PSOE)
    "38023": ("La Laguna", "PSOE", "left"),    # Pérez (PSOE)
    "26089": ("Logroño", "PSOE", "left"),      # Hermoso de Mendoza (PSOE)
    "06015": ("Badajoz", "PP", "right"),       # Fragoso (PP) with Cs
    "37274": ("Salamanca", "PP", "right"),     # García Carbayo (PP) with Cs
    "21041": ("Huelva", "PSOE", "left"),       # Cruz (PSOE)
    "29069": ("Marbella", "PP", "right"),      # Ángeles Muñoz (PP)
    "25120": ("Lleida", "ERC", "left"),        # Pueyo (ERC)
    "43148": ("Tarragona", "ERC", "left"),     # Ricomà (ERC)
    "41038": ("Dos Hermanas", "PSOE", "left"), # Toscano (PSOE)
    "28148": ("Torrejón", "PP", "right"),      # Ignacio Vázquez (PP)
    "28106": ("Parla", "PSOE", "left"),        # Rodríguez (PSOE)
    "08121": ("Mataró", "PSOE", "left"),       # Bote (PSC/PSOE)
    "24089": ("León", "PSOE", "left"),         # Diez (PSOE)
    "11004": ("Algeciras", "PP", "right"),     # Landaluce (PP)
    "08245": ("Sta Coloma Gramenet", "PSOE", "left"), # Parlon (PSC/PSOE)
    "28006": ("Alcobendas", "PSOE", "left"),   # Casado (PSOE)
    "11012": ("Cádiz", "UP", "left"),          # Kichi (Adelante Cádiz / Podemos)
    "23050": ("Jaén", "PSOE", "left"),         # Márquez (PSOE)
    "32054": ("Ourense", "PP", "right"),       # Jácome (independent, right-populist)
    "43123": ("Reus", "ERC", "left"),          # Pellicer (ERC)
    "08205": ("Sant Cugat", "JxCat", "right"), # Carmela Fortuny (JxCat → Junts)
    "08217": ("Sant Joan Despí", "PSOE", "left"), # Sentís (PSC/PSOE)
    "28123": ("Rivas-Vaciamadrid", "UP", "left"),  # Del Cura (IU/UP)
    "36038": ("Pontevedra", "BNG", "left"),    # Lores (BNG)
    "08073": ("Cornellà", "PSOE", "left"),     # Parlon predecessor? Actually Antonio Balmón (PSC)
    "08169": ("El Prat", "PSOE", "left"),      # Parés (PSC/PSOE)

    # Additional >50k municipalities
    "17079": ("Girona", "JxCat", "right"),     # Madrenas (JxCat)
    "28058": ("Fuenlabrada", "PSOE", "left"),
    "11020": ("Jerez", "PSOE", "left"),
    "46131": ("Torrent", "Compromís", "left"),
    "03047": ("Benidorm", "PP", "right"),
    "28148": ("Torrejón", "PP", "right"),
    "08902": ("Castelldefels", "PP", "right"),
    "08307": ("Viladecans", "PSOE", "left"),
    "46220": ("Sagunto/Sagunt", "PSOE", "left"),
    "28150": ("Torrelodones", "PP", "right"),
    "10037": ("Cáceres", "PP", "right"),       # Salaya (PSOE) actually won 2019
    "30024": ("Lorca", "PP", "right"),         # Fulgencio Gil (PP)
    "38038": ("Sta Cruz Tenerife", "CC", "right"),  # Bermúdez (CC, coalition centrists)
}

# Fix: correct Zaragoza — PP (Azcón) won 2019 with Cs/Vox support
GOVERNING_PARTY_2019["50297"] = ("Zaragoza", "PP", "right")
# Fix: Pamplona — Navarra Suma (PP/UPN/Cs coalition) governed after investiture
GOVERNING_PARTY_2019["31201"] = ("Pamplona", "Navarra Suma", "right")
# Fix: Albacete — Manuel Serrano (PP) mayor after Cs pact
GOVERNING_PARTY_2019["02003"] = ("Albacete", "PP", "right")
# Fix: Santa Cruz — CC is centrist/right
GOVERNING_PARTY_2019["38038"] = ("Sta Cruz Tenerife", "CC", "right")
# Fix: Cáceres — Luis Salaya (PSOE) won 2019
GOVERNING_PARTY_2019["10037"] = ("Cáceres", "PSOE", "left")
# Fix: Vitoria — actually Gorka Urtaran (PNV), coding PNV as center-right
GOVERNING_PARTY_2019["01059"] = ("Vitoria", "PNV", "right")
# Fix: Badalona — García Albiol (PP) won most votes in 2019 but Xavier García Albiol
# was NOT mayor initially (left coalition governed); in Nov 2020 Albiol became mayor
# via motion of censure. So for most of the ZBE decision period: PP governed
GOVERNING_PARTY_2019["08015"] = ("Badalona", "PP", "right")


# ===================================================================
# ZBE STATUS — detailed coding from research
# ===================================================================
# Columns: (zbe_status, zbe_stringency, zbe_type, notes)
# zbe_status:
#   "enforced"  = cameras + fines active before May 2023
#   "nominal"   = ZBE designated but no label-based enforcement
#   "delayed"   = obligated but not implemented by May 2023
#   "none"      = no ZBE at all
# zbe_stringency (1-5):
#   5 = full city/large area, cameras, fines, daily restrictions
#   4 = significant area, cameras, fines
#   3 = limited area or limited hours, cameras, fines
#   2 = designated but informational only / relabeled pedestrian zone
#   1 = school zone or micro-area only
#   0 = no ZBE

ZBE_STATUS = {
    "28079": ("enforced", 5, "label", "Madrid 360: full city, cameras, fines since 2021"),
    "08019": ("enforced", 5, "label", "Barcelona ZBE Rondes: 95km2, cameras, fines since 2020"),
    "08101": ("enforced", 5, "label", "Part of Barcelona AMB ZBE"),
    "08245": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08073": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08169": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08279": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08187": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08205": ("enforced", 3, "label", "Sant Cugat: 4km2, fines since Nov 2021"),
    "08217": ("enforced", 3, "label", "Sant Joan Despí: AMB regime"),
    "08015": ("enforced", 3, "label", "Badalona: trial year Mar 2023, later postponed to 2027"),
    "41091": ("nominal", 2, "relabel", "Sevilla: pre-existing restrictions relabeled; fines from Jul 2024"),
    "14021": ("nominal", 2, "relabel", "Córdoba: pre-existing ACIRE zones relabeled"),
    "36038": ("nominal", 2, "relabel", "Pontevedra: traffic-calmed since 1999, no label restrictions"),
    "15030": ("nominal", 2, "relabel", "A Coruña: pedestrianised areas renamed ZBE"),
    "28123": ("nominal", 1, "school", "Rivas: school-zone ZBE only"),
    "30016": ("nominal", 2, "relabel", "Cartagena: ordinance Mar 2023, supermanzanas focus"),
    "28148": ("nominal", 2, "paper", "Torrejón: ordinance Feb 2023, cameras not until Mar 2025"),
    # Delayed — these were obligated but NOT active before May 2023
    "46250": ("delayed", 0, "none", "Valencia: APR declared ZBE Dec 2023"),
    "47186": ("delayed", 0, "none", "Valladolid: activated Nov 2024"),
    "48020": ("delayed", 0, "none", "Bilbao: activated Jun 2024"),
    "29067": ("delayed", 0, "none", "Málaga: informational phase Nov 2024"),
    "50297": ("delayed", 0, "none", "Zaragoza: activated Dec 2025"),
    "20069": ("delayed", 0, "none", "San Sebastián: activated Dec 2024"),
    "01059": ("delayed", 0, "none", "Vitoria: activated Sep 2025"),
    "09059": ("delayed", 0, "none", "Burgos: activated Aug 2025"),
    "39075": ("delayed", 0, "none", "Santander: activated Dec 2025"),
    "33024": ("delayed", 0, "none", "Gijón: ZBE derogated after May 2023 change of govt"),
}


def load_data():
    """Load election panel."""
    election = pd.read_csv(
        os.path.join(DATA_DIR, "election_panel.csv"),
        dtype={"cod_ine": str, "cod_provincia": str},
    )
    return election


def build_party_panel(election):
    """
    Build a municipality-level dataset with governing party, ZBE status,
    and election outcomes.
    """
    # Restrict to >50k municipalities
    above_50k = election[election["above_50k"] == True]["cod_ine"].unique()
    df = election[election["cod_ine"].isin(above_50k)].copy()

    # Get 2019 data for governing party assignment
    df19 = df[df["year"] == 2019].copy()
    df23 = df[df["year"] == 2023].copy()

    # Assign governing party from hand-coded data
    df19["gov_party"] = df19["cod_ine"].map(
        lambda x: GOVERNING_PARTY_2019.get(x, (None, None, None))[1]
    )
    df19["gov_bloc"] = df19["cod_ine"].map(
        lambda x: GOVERNING_PARTY_2019.get(x, (None, None, None))[2]
    )

    # Fallback: for uncoded municipalities, infer from seats plurality
    seat_cols = ["seats_pp", "seats_psoe", "seats_vox", "seats_cs", "seats_up"]
    party_names = ["PP", "PSOE", "VOX", "CS", "UP"]
    right_parties = {"PP", "VOX", "CS"}

    uncoded = df19["gov_party"].isna()
    if uncoded.any():
        seats_matrix = df19.loc[uncoded, seat_cols]
        max_idx = seats_matrix.values.argmax(axis=1)
        df19.loc[uncoded, "gov_party"] = [party_names[i] for i in max_idx]
        df19.loc[uncoded, "gov_bloc"] = [
            "right" if party_names[i] in right_parties else "left"
            for i in max_idx
        ]

    # Assign ZBE status
    df19["zbe_status"] = df19["cod_ine"].map(
        lambda x: ZBE_STATUS.get(x, ("none", 0, "none", ""))[0]
    )
    df19["zbe_stringency"] = df19["cod_ine"].map(
        lambda x: ZBE_STATUS.get(x, ("none", 0, "none", ""))[1]
    )
    df19["zbe_type"] = df19["cod_ine"].map(
        lambda x: ZBE_STATUS.get(x, ("none", 0, "none", ""))[2]
    )

    # Create binary: implemented any form of ZBE before May 2023
    df19["zbe_any"] = df19["zbe_status"].isin(["enforced", "nominal"]).astype(int)
    df19["zbe_enforced"] = (df19["zbe_status"] == "enforced").astype(int)
    df19["zbe_delayed"] = (df19["zbe_status"] == "delayed").astype(int)

    # Merge 2023 outcomes
    df23_slim = df23[["cod_ine", "share_vox", "share_pp", "share_psoe",
                       "share_cs", "share_up", "total_votes", "poblacion"]].copy()
    df23_slim.columns = ["cod_ine"] + [f"{c}_2023" for c in df23_slim.columns[1:]]

    merged = df19.merge(df23_slim, on="cod_ine", how="left")

    # Compute changes
    merged["vox_change"] = merged["share_vox_2023"] - merged["share_vox"]
    merged["pp_change"] = merged["share_pp_2023"] - merged["share_pp"]
    merged["psoe_change"] = merged["share_psoe_2023"] - merged["share_psoe"]

    merged["log_pop"] = np.log(merged["poblacion"])

    return merged


# ===================================================================
# ANALYSIS 1: Party predicts ZBE adoption (probit/logit)
# ===================================================================
def party_predicts_zbe(df):
    """
    Does governing party (left vs right) predict whether a municipality
    implemented a ZBE before May 2023?
    """
    print("\n" + "=" * 70)
    print("Q1: DOES GOVERNING PARTY PREDICT ZBE ADOPTION?")
    print("=" * 70)

    sub = df.dropna(subset=["gov_bloc"]).copy()
    sub["left"] = (sub["gov_bloc"] == "left").astype(int)

    # Cross-tabulation
    print("\n  Cross-tabulation: Governing bloc × ZBE status")
    ct = pd.crosstab(sub["gov_bloc"], sub["zbe_status"], margins=True)
    print(ct.to_string())

    # Rates
    for bloc in ["left", "right"]:
        bloc_df = sub[sub["gov_bloc"] == bloc]
        n = len(bloc_df)
        n_enforced = (bloc_df["zbe_enforced"] == 1).sum()
        n_any = (bloc_df["zbe_any"] == 1).sum()
        n_delayed = (bloc_df["zbe_delayed"] == 1).sum()
        n_none = ((bloc_df["zbe_status"] == "none")).sum()
        print(f"\n  {bloc.upper()} bloc (N={n}):")
        print(f"    Enforced ZBE:  {n_enforced:>3}  ({100*n_enforced/n:.1f}%)")
        print(f"    Nominal ZBE:   {n_any - n_enforced:>3}  ({100*(n_any-n_enforced)/n:.1f}%)")
        print(f"    Delayed:       {n_delayed:>3}  ({100*n_delayed/n:.1f}%)")
        print(f"    None:          {n_none:>3}  ({100*n_none/n:.1f}%)")

    # Logistic regression: ZBE = f(left, log_pop)
    print("\n  Logistic regression: P(ZBE) = f(left_bloc, log_pop)")
    for outcome_var, label in [
        ("zbe_any", "Any ZBE (enforced + nominal)"),
        ("zbe_enforced", "Enforced ZBE (cameras/fines)"),
    ]:
        y = sub[outcome_var]
        if y.sum() < 3:
            print(f"    {label}: too few positive cases ({y.sum()})")
            continue

        X = sm.add_constant(sub[["left", "log_pop"]])
        try:
            model = sm.Logit(y, X).fit(disp=0)
            print(f"\n    --- {label} ---")
            print(f"    left_bloc:  coef={model.params['left']:+.3f}  "
                  f"SE={model.bse['left']:.3f}  p={model.pvalues['left']:.3f}  "
                  f"OR={np.exp(model.params['left']):.2f}")
            print(f"    log_pop:    coef={model.params['log_pop']:+.3f}  "
                  f"SE={model.bse['log_pop']:.3f}  p={model.pvalues['log_pop']:.3f}  "
                  f"OR={np.exp(model.params['log_pop']):.2f}")
            print(f"    N={int(model.nobs)}  Pseudo-R2={model.prsquared:.3f}")
        except Exception as e:
            print(f"    {label}: model failed ({e})")

    return sub


# ===================================================================
# ANALYSIS 2: Stringency by party
# ===================================================================
def stringency_by_party(df):
    """
    Among ZBE implementers, does governing party predict stringency?
    """
    print("\n" + "=" * 70)
    print("Q2: STRINGENCY BY GOVERNING PARTY")
    print("=" * 70)

    impl = df[df["zbe_any"] == 1].dropna(subset=["gov_bloc"]).copy()
    if len(impl) < 3:
        print("  Too few implementers for analysis")
        return

    print(f"\n  ZBE implementers (N={len(impl)}):")
    print(f"  {'Municipality':25s} {'Party':>12s} {'Bloc':>6s} {'Status':>10s} {'Stringency':>10s} {'Type':>8s}")
    print("  " + "-" * 80)
    for _, r in impl.sort_values("zbe_stringency", ascending=False).iterrows():
        print(f"  {r['municipio']:25s} {str(r['gov_party']):>12s} {r['gov_bloc']:>6s} "
              f"{r['zbe_status']:>10s} {r['zbe_stringency']:>10.0f} {r['zbe_type']:>8s}")

    # Average stringency by bloc
    for bloc in ["left", "right"]:
        bloc_impl = impl[impl["gov_bloc"] == bloc]
        if len(bloc_impl) > 0:
            print(f"\n  {bloc.upper()}: avg stringency = {bloc_impl['zbe_stringency'].mean():.2f} "
                  f"(N={len(bloc_impl)})")


# ===================================================================
# ANALYSIS 3: Delay by party
# ===================================================================
def delay_by_party(df):
    """
    Among municipalities that delayed/refused ZBE, is it associated with
    right-wing governance?
    """
    print("\n" + "=" * 70)
    print("Q3: DELAY/REFUSAL BY GOVERNING PARTY")
    print("=" * 70)

    sub = df.dropna(subset=["gov_bloc"]).copy()

    # Among non-implementers (none + delayed), show party distribution
    non_impl = sub[sub["zbe_any"] == 0]
    print(f"\n  Non-implementers (N={len(non_impl)}):")
    print(f"  Governing bloc distribution:")
    print(non_impl["gov_bloc"].value_counts().to_string())

    # Named delayed cities
    delayed = sub[sub["zbe_delayed"] == 1]
    print(f"\n  Explicitly delayed cities (N={len(delayed)}):")
    for _, r in delayed.iterrows():
        print(f"    {r['municipio']:25s}  Party: {str(r['gov_party']):>12s}  Bloc: {r['gov_bloc']}")

    # Non-implementers with no ZBE at all
    no_zbe = sub[sub["zbe_status"] == "none"]
    print(f"\n  No ZBE at all (N={len(no_zbe)}):")
    ct = no_zbe["gov_bloc"].value_counts()
    for bloc, n in ct.items():
        print(f"    {bloc}: {n} ({100*n/len(no_zbe):.1f}%)")


# ===================================================================
# ANALYSIS 4: Electoral consequences by bloc
# ===================================================================
def electoral_consequences_by_bloc(df):
    """
    Did left-governed ZBE implementers face DIFFERENT electoral consequences
    than right-governed ones?
    """
    print("\n" + "=" * 70)
    print("Q4: ELECTORAL CONSEQUENCES BY GOVERNING BLOC")
    print("=" * 70)

    sub = df.dropna(subset=["gov_bloc", "vox_change"]).copy()
    sub["left"] = (sub["gov_bloc"] == "left").astype(int)

    # Summary table
    print(f"\n  {'Category':45s} {'N':>4s} {'ΔVox':>8s} {'ΔPP':>8s} {'ΔPSOE':>8s}")
    print("  " + "-" * 75)

    categories = [
        ("Left + Enforced ZBE", (sub["left"] == 1) & (sub["zbe_enforced"] == 1)),
        ("Left + Nominal ZBE", (sub["left"] == 1) & (sub["zbe_status"] == "nominal")),
        ("Left + No ZBE", (sub["left"] == 1) & (sub["zbe_any"] == 0)),
        ("Right + Enforced ZBE", (sub["left"] == 0) & (sub["zbe_enforced"] == 1)),
        ("Right + Nominal ZBE", (sub["left"] == 0) & (sub["zbe_status"] == "nominal")),
        ("Right + No ZBE", (sub["left"] == 0) & (sub["zbe_any"] == 0)),
    ]

    rows = []
    for label, mask in categories:
        group = sub[mask]
        if len(group) == 0:
            continue
        row = {
            "Category": label,
            "N": len(group),
            "vox_change": group["vox_change"].mean(),
            "pp_change": group["pp_change"].mean(),
            "psoe_change": group["psoe_change"].mean(),
        }
        rows.append(row)
        print(f"  {label:45s} {len(group):>4} {group['vox_change'].mean():>+8.4f} "
              f"{group['pp_change'].mean():>+8.4f} {group['psoe_change'].mean():>+8.4f}")

    # Regression: vox_change = f(left, zbe_enforced, left*zbe, log_pop)
    print("\n  OLS: ΔVox = f(left, zbe_enforced, left×zbe, log_pop)")
    sub["left_x_zbe"] = sub["left"] * sub["zbe_enforced"]
    X = sm.add_constant(sub[["left", "zbe_enforced", "left_x_zbe", "log_pop"]])
    model = sm.OLS(sub["vox_change"], X).fit(cov_type="HC1")

    for var in ["left", "zbe_enforced", "left_x_zbe", "log_pop"]:
        star = "***" if model.pvalues[var] < 0.01 else ("**" if model.pvalues[var] < 0.05 else ("*" if model.pvalues[var] < 0.1 else ""))
        print(f"    {var:20s}  coef={model.params[var]:+.5f}  SE={model.bse[var]:.5f}  p={model.pvalues[var]:.3f}{star}")
    print(f"    N={int(model.nobs)}  R2={model.rsquared:.3f}")

    if rows:
        pd.DataFrame(rows).to_csv(
            os.path.join(TAB_DIR, "party_zbe_electoral_consequences.csv"), index=False
        )

    return sub


# ===================================================================
# ANALYSIS 5: Post-2023 reversals
# ===================================================================
def post_2023_reversals(df):
    """
    After May 2023 elections, did new right-wing governments reverse ZBEs?
    Document known cases.
    """
    print("\n" + "=" * 70)
    print("Q5: POST-2023 ZBE REVERSALS")
    print("=" * 70)

    # These are documented from our research
    reversals = [
        ("Badalona", "PP (Albiol)", "Postponed ZBE to Jan 2027 after winning May 2023"),
        ("Gijón", "PP", "ZBE effectively derogated after PP won May 2023"),
        ("Madrid", "PP (Almeida)", "Madrid 360 maintained — PP chose to keep it"),
    ]

    print("\n  Known post-2023 ZBE policy changes:")
    for city, party, action in reversals:
        print(f"    {city:20s}  {party:15s}  {action}")

    # Broader pattern: cities that activated ZBE AFTER May 2023 — under which party?
    post_2023_activations = [
        ("Bilbao", "PNV", "Jun 2024"),
        ("Valladolid", "PP (after PSOE)", "Nov 2024"),
        ("Málaga", "PP", "Nov 2024"),
        ("Donostia/SS", "Bildu", "Dec 2024"),
        ("Vitoria", "PNV", "Sep 2025"),
        ("Zaragoza", "PP (Azcón→Chueca)", "Dec 2025"),
        ("Burgos", "PP (after PSOE)", "Aug 2025"),
        ("Santander", "PP", "Dec 2025"),
    ]

    print("\n  ZBE activations after May 2023 elections:")
    print(f"  {'City':20s} {'Governing party':>20s} {'Activation':>12s}")
    for city, party, date in post_2023_activations:
        print(f"  {city:20s} {party:>20s} {date:>12s}")

    # Count by bloc
    n_pp = sum(1 for _, p, _ in post_2023_activations if "PP" in p)
    n_left = sum(1 for _, p, _ in post_2023_activations if p in ["Bildu", "PNV"])
    print(f"\n  Post-2023 activations by PP/right: {n_pp}")
    print(f"  Post-2023 activations by left/nationalist: {n_left}")
    print(f"  → Even PP mayors eventually implemented ZBEs (legal mandate + EU pressure)")


# ===================================================================
# PLOT: ZBE adoption by party
# ===================================================================
def plot_zbe_by_party(df):
    """Bar chart showing ZBE adoption rates by governing bloc."""
    sub = df.dropna(subset=["gov_bloc"]).copy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel A: Adoption rate by bloc
    for i, (label, outcome) in enumerate([
        ("Any ZBE (incl. nominal)", "zbe_any"),
        ("Enforced ZBE (cameras/fines)", "zbe_enforced"),
    ]):
        ax = axes[i]
        rates = sub.groupby("gov_bloc")[outcome].mean()
        counts = sub.groupby("gov_bloc")[outcome].agg(["sum", "count"])

        bars = ax.bar(rates.index, rates.values, color=["#2166ac", "#b2182b"],
                      edgecolor="black", linewidth=0.5)

        for j, (bloc, row) in enumerate(counts.iterrows()):
            ax.text(j, rates[bloc] + 0.01,
                    f"{int(row['sum'])}/{int(row['count'])}",
                    ha="center", va="bottom", fontsize=10)

        ax.set_ylabel("Adoption rate")
        ax.set_title(label)
        ax.set_ylim(0, max(rates.values) * 1.3 + 0.05)
        ax.set_xlabel("Governing bloc (2019-2023)")

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "party_zbe_adoption.png"), dpi=150, bbox_inches="tight")
    print(f"\n  Saved: {os.path.join(FIG_DIR, 'party_zbe_adoption.png')}")
    plt.close()


# ===================================================================
# PLOT: Electoral consequences by bloc × ZBE status
# ===================================================================
def plot_electoral_by_bloc_zbe(df):
    """Dot plot of Vox change by party bloc × ZBE status."""
    sub = df.dropna(subset=["gov_bloc", "vox_change"]).copy()

    fig, ax = plt.subplots(figsize=(10, 6))

    categories = [
        ("Left\nEnforced ZBE", (sub["gov_bloc"] == "left") & (sub["zbe_enforced"] == 1)),
        ("Left\nNominal ZBE", (sub["gov_bloc"] == "left") & (sub["zbe_status"] == "nominal")),
        ("Left\nNo ZBE", (sub["gov_bloc"] == "left") & (sub["zbe_any"] == 0)),
        ("Right\nEnforced ZBE", (sub["gov_bloc"] == "right") & (sub["zbe_enforced"] == 1)),
        ("Right\nNo ZBE", (sub["gov_bloc"] == "right") & (sub["zbe_any"] == 0)),
    ]

    positions = []
    means = []
    for i, (label, mask) in enumerate(categories):
        group = sub[mask]
        if len(group) == 0:
            continue
        ax.scatter([i] * len(group), group["vox_change"], alpha=0.4, s=40,
                   color="#2166ac" if "Left" in label else "#b2182b")
        mean_val = group["vox_change"].mean()
        ax.plot([i - 0.3, i + 0.3], [mean_val, mean_val], color="black",
                linewidth=2, zorder=5)
        positions.append(i)
        means.append(mean_val)
        ax.text(i, mean_val + 0.003, f"{mean_val:+.3f}", ha="center",
                va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels([c[0] for c in categories], fontsize=9)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.set_ylabel("Change in Vox vote share (2019 → 2023)")
    ax.set_title("Electoral consequences by governing bloc and ZBE status")

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "party_zbe_electoral.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(FIG_DIR, 'party_zbe_electoral.png')}")
    plt.close()


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("12 — Party Politics of ZBE Adoption")
    print("=" * 70)

    election = load_data()
    df = build_party_panel(election)

    # Coverage check
    coded = df.dropna(subset=["gov_bloc"])
    print(f"\n  Municipalities >50k: {len(df)}")
    print(f"  With governing party coded: {len(coded)} ({100*len(coded)/len(df):.0f}%)")
    print(f"  Left bloc: {(coded['gov_bloc']=='left').sum()}")
    print(f"  Right bloc: {(coded['gov_bloc']=='right').sum()}")

    # Run analyses
    party_predicts_zbe(df)
    stringency_by_party(df)
    delay_by_party(df)
    electoral_consequences_by_bloc(df)
    post_2023_reversals(df)

    # Plots
    plot_zbe_by_party(df)
    plot_electoral_by_bloc_zbe(df)

    # Save full dataset
    df.to_csv(os.path.join(TAB_DIR, "party_zbe_full.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'party_zbe_full.csv')}")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
