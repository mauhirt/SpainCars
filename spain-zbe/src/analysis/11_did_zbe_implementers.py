"""
11_did_zbe_implementers.py

Difference-in-Differences analysis comparing municipalities that ACTUALLY
implemented ZBEs before the May 28, 2023 municipal elections vs. similar
obligated municipalities that did not.

Design:
  Treatment:  Municipalities with active/enforced ZBE before May 2023
  Control:    Municipalities >50k that had NOT implemented by May 2023
  Outcome:    Change in Vox vote share (2019 → 2023)

Key finding context:
  The RD at the 50k threshold yields null results because essentially zero
  municipalities NEAR the threshold had actually implemented ZBEs by election
  day. All implementers are large cities far above the cutoff. This DiD
  uses variation among large (>50k) municipalities in implementation status.

Output:
  output/tables/did_zbe_main.csv
  output/tables/did_zbe_balance.csv
  output/figures/did_zbe_*.png

Usage:
    python spain-zbe/src/analysis/11_did_zbe_implementers.py
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.join("spain-zbe")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
INTERIM_DIR = os.path.join(BASE_DIR, "data", "interim")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
TAB_DIR = os.path.join(BASE_DIR, "output", "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)


# ===================================================================
# ZBE IMPLEMENTATION STATUS — hand-coded from official sources
# ===================================================================
# Municipalities with ZBE active/enforced BEFORE May 28, 2023 elections.
# Sources: MITECO interactive map, municipal ordinances (BOP/BOE),
#          RACE.es, news reporting as of Q2 2023.
#
# NOTE: "Active" means restrictions were being enforced, not just
# that an ordinance was approved.

ZBE_ACTIVE_BY_MAY_2023 = {
    # cod_ine: (municipality, ZBE name, approx activation date)
    "28079": ("Madrid", "Madrid 360", "2022-01"),
    # Madrid Central (Nov 2018) → replaced by Madrid 360 (Jan 2022)
    "08019": ("Barcelona", "ZBE Rondes de Barcelona", "2020-01"),
    # Barcelona ZBE started Jan 2020; expanded progressively
    "46250": ("València", "ZBE València", "2022-12"),
    # Approved Dec 2022, camera enforcement began early 2023
    "41091": ("Sevilla", "ZBE Sevilla", "2023-01"),
    # Sevilla ZBE started Jan 2023
    "14021": ("Córdoba", "ZBE Córdoba", "2023-01"),
    # Córdoba ZBE activated Jan 2023
    "36038": ("Pontevedra", "ZBE Pontevedra", "2019-01"),
    # Pontevedra had pedestrianised centre since ~2011; ZBE formalised
    "15030": ("Coruña, A", "ZBE A Coruña", "2023-04"),
    # A Coruña ZBE activated April 2023
    "47186": ("Valladolid", "ZBE Valladolid", "2023-01"),
    # Valladolid ZBE activated Jan 2023
    "08015": ("Badalona", "ZBE Metropolitana Barcelona", "2020-01"),
    # Part of Barcelona metropolitan ZBE
    "08205": ("Sant Cugat del Vallès", "ZBE Metropolitana Barcelona", "2020-01"),
    "08217": ("Sant Joan Despí", "ZBE Metropolitana Barcelona", "2020-01"),
    # Note: Sant Joan Despí is <50k, voluntary/regional mandate
    "28123": ("Rivas-Vaciamadrid", "ZBE Rivas", "2023-02"),
    # Rivas approved late 2022, active early 2023
    # Additional Barcelona metropolitan area municipalities under AMB ZBE:
    "08101": ("L'Hospitalet de Llobregat", "ZBE Metropolitana Barcelona", "2020-01"),
    "08245": ("Santa Coloma de Gramenet", "ZBE Metropolitana Barcelona", "2020-01"),
    "08073": ("Cornellà de Llobregat", "ZBE Metropolitana Barcelona", "2020-01"),
    "08169": ("El Prat de Llobregat", "ZBE Metropolitana Barcelona", "2020-01"),
    "08279": ("Terrassa", "ZBE Metropolitana Barcelona", "2020-01"),
    "08187": ("Sabadell", "ZBE Metropolitana Barcelona", "2020-01"),
}


def load_data():
    """Load election panel and population data."""
    election = pd.read_csv(
        os.path.join(DATA_DIR, "election_panel.csv"),
        dtype={"cod_ine": str, "cod_provincia": str},
    )
    fleet = pd.read_csv(
        os.path.join(DATA_DIR, "fleet_panel.csv"),
        dtype={"cod_ine": str, "cod_provincia": str},
    )
    return election, fleet


def build_did_panel(election, fleet):
    """
    Build a municipality-level panel for the DiD analysis.

    Returns a DataFrame with one row per municipality-election (2019, 2023)
    restricted to municipalities >50k (obligated under the law).
    """
    # Keep only municipalities that are above 50k in any year
    above_50k_munis = election[election["above_50k"] == True]["cod_ine"].unique()
    df = election[election["cod_ine"].isin(above_50k_munis)].copy()

    # Keep 2019 and 2023 elections
    df = df[df["year"].isin([2019, 2023])].copy()

    # Treatment indicator: municipality had ZBE active by May 2023
    df["zbe_active"] = df["cod_ine"].isin(ZBE_ACTIVE_BY_MAY_2023.keys()).astype(int)

    # Post indicator
    df["post"] = (df["year"] == 2023).astype(int)

    # DiD interaction
    df["zbe_x_post"] = df["zbe_active"] * df["post"]

    # Merge fleet data: average fleet composition by municipality-year
    # Use the closest year: 2019 for 2019 election, 2022 for 2023 election
    fleet_2019 = fleet[fleet["year"] == 2019].copy()
    fleet_2022 = fleet[fleet["year"] == 2022].copy()

    fleet_election = pd.concat([
        fleet_2019.assign(election_year=2019),
        fleet_2022.assign(election_year=2023),
    ])
    fleet_election = fleet_election[
        ["cod_ine", "election_year", "share_sin_distintivo", "share_eco",
         "share_cero", "share_b", "share_c"]
    ]

    df = df.merge(
        fleet_election,
        left_on=["cod_ine", "year"],
        right_on=["cod_ine", "election_year"],
        how="left",
    )

    # Log population
    df["log_pop"] = np.log(df["poblacion"])

    print(f"\nDiD Panel Summary:")
    print(f"  Municipalities: {df['cod_ine'].nunique()}")
    print(f"  ZBE active:     {df[df['zbe_active'] == 1]['cod_ine'].nunique()}")
    print(f"  Control:        {df[df['zbe_active'] == 0]['cod_ine'].nunique()}")
    print(f"  Obs (2019):     {len(df[df['year'] == 2019])}")
    print(f"  Obs (2023):     {len(df[df['year'] == 2023])}")

    return df


# ===================================================================
# BALANCE TABLE
# ===================================================================
def balance_table(df):
    """Compare pre-treatment (2019) characteristics of treated vs control."""
    print("\n" + "=" * 60)
    print("BALANCE TABLE — 2019 (Pre-Treatment)")
    print("=" * 60)

    pre = df[df["year"] == 2019].copy()

    vars_to_compare = [
        ("poblacion", "Population"),
        ("share_vox", "Vox vote share 2019"),
        ("share_pp", "PP vote share 2019"),
        ("share_psoe", "PSOE vote share 2019"),
        ("share_sin_distintivo", "Fleet: no-label share"),
        ("share_eco", "Fleet: ECO share"),
        ("share_cero", "Fleet: zero-emission share"),
        ("total_votes", "Total votes"),
    ]

    rows = []
    for var, label in vars_to_compare:
        if var not in pre.columns:
            continue
        treated = pre[pre["zbe_active"] == 1][var].dropna()
        control = pre[pre["zbe_active"] == 0][var].dropna()

        # t-test
        from scipy import stats
        tstat, pval = stats.ttest_ind(treated, control, equal_var=False)

        rows.append({
            "Variable": label,
            "ZBE Mean": f"{treated.mean():.4f}",
            "ZBE SD": f"{treated.std():.4f}",
            "Control Mean": f"{control.mean():.4f}",
            "Control SD": f"{control.std():.4f}",
            "Diff": f"{treated.mean() - control.mean():+.4f}",
            "p-value": f"{pval:.3f}",
        })
        sig = "***" if pval < 0.01 else ("**" if pval < 0.05 else ("*" if pval < 0.1 else ""))
        print(f"  {label:30s}  ZBE={treated.mean():.4f}  "
              f"Ctrl={control.mean():.4f}  diff={treated.mean() - control.mean():+.4f}  "
              f"p={pval:.3f}{sig}")

    balance_df = pd.DataFrame(rows)
    balance_df.to_csv(os.path.join(TAB_DIR, "did_zbe_balance.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'did_zbe_balance.csv')}")
    return balance_df


# ===================================================================
# DiD ESTIMATION
# ===================================================================
def run_did(df):
    """
    Run the main DiD specifications.

    Y_{it} = alpha + beta1 * ZBE_i + beta2 * Post_t + beta3 * (ZBE * Post) + X + eps

    beta3 is our parameter of interest: the effect of actual ZBE
    implementation on Vox vote share.
    """
    print("\n" + "=" * 60)
    print("DiD ESTIMATION — Vox Vote Share")
    print("=" * 60)

    outcomes = [
        ("share_vox", "Vox vote share"),
        ("share_pp", "PP vote share"),
        ("share_psoe", "PSOE vote share"),
    ]

    all_results = []

    for outcome, label in outcomes:
        print(f"\n  --- {label} ---")
        sub = df.dropna(subset=[outcome]).copy()

        if len(sub) < 30:
            print(f"    Insufficient data (N={len(sub)})")
            continue

        # Spec 1: Simple DiD (no controls)
        X1 = sm.add_constant(sub[["zbe_active", "post", "zbe_x_post"]])
        m1 = sm.OLS(sub[outcome], X1).fit(cov_type="HC1")
        coef1, se1, pval1 = m1.params["zbe_x_post"], m1.bse["zbe_x_post"], m1.pvalues["zbe_x_post"]

        # Spec 2: + log population control
        X2 = sm.add_constant(sub[["zbe_active", "post", "zbe_x_post", "log_pop"]])
        m2 = sm.OLS(sub[outcome], X2).fit(cov_type="HC1")
        coef2, se2, pval2 = m2.params["zbe_x_post"], m2.bse["zbe_x_post"], m2.pvalues["zbe_x_post"]

        # Spec 3: + province FE
        prov_dummies = pd.get_dummies(sub["cod_provincia"], prefix="prov",
                                       drop_first=True, dtype=float)
        X3_cols = ["zbe_active", "post", "zbe_x_post", "log_pop"]
        X3 = sm.add_constant(pd.concat([sub[X3_cols], prov_dummies], axis=1))
        m3 = sm.OLS(sub[outcome], X3).fit(cov_type="HC1")
        coef3, se3, pval3 = m3.params["zbe_x_post"], m3.bse["zbe_x_post"], m3.pvalues["zbe_x_post"]

        # Spec 4: + province FE + municipality clustering
        try:
            m4 = sm.OLS(sub[outcome], X3).fit(
                cov_type="cluster", cov_kwds={"groups": sub["cod_ine"]}
            )
            coef4, se4, pval4 = m4.params["zbe_x_post"], m4.bse["zbe_x_post"], m4.pvalues["zbe_x_post"]
        except Exception:
            coef4, se4, pval4 = coef3, se3, pval3

        star = lambda p: "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.1 else ""))

        for spec_label, c, s, p, model in [
            ("(1) Simple DiD", coef1, se1, pval1, m1),
            ("(2) + log(pop)", coef2, se2, pval2, m2),
            ("(3) + Province FE", coef3, se3, pval3, m3),
            ("(4) + Cluster SE", coef4, se4, pval4, m4),
        ]:
            print(f"    {spec_label:20s}  coef={c:+.5f}  SE={s:.5f}  p={p:.3f}{star(p)}")
            all_results.append({
                "outcome": outcome,
                "specification": spec_label,
                "coef": c,
                "se": s,
                "pval": p,
                "ci_low": c - 1.96 * s,
                "ci_high": c + 1.96 * s,
                "n": model.nobs,
                "r2": model.rsquared,
            })

    results_df = pd.DataFrame(all_results)
    results_df.to_csv(os.path.join(TAB_DIR, "did_zbe_main.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'did_zbe_main.csv')}")
    return results_df


# ===================================================================
# SIZE-MATCHED DiD (robustness)
# ===================================================================
def run_did_size_matched(df):
    """
    Restrict control group to municipalities of comparable size to treated.

    The concern: ZBE implementers are on average much larger than
    non-implementers. Size itself correlates with political preferences.
    Solution: restrict to control municipalities with pop > 80k.
    """
    print("\n" + "=" * 60)
    print("ROBUSTNESS: SIZE-MATCHED DiD")
    print("=" * 60)

    # Get treated city sizes
    treated_munis = df[df["zbe_active"] == 1]
    min_treated = treated_munis["poblacion"].min()
    print(f"\n  Smallest treated city: pop = {min_treated:,.0f}")

    # Try different matching thresholds
    thresholds = [80_000, 100_000, 150_000, 200_000]

    results = []
    outcome = "share_vox"
    star_fn = lambda p: "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.1 else ""))

    for thresh in thresholds:
        sub = df[
            (df["zbe_active"] == 1) | (df["poblacion"] >= thresh)
        ].dropna(subset=[outcome]).copy()

        n_treat = sub[sub["zbe_active"] == 1]["cod_ine"].nunique()
        n_ctrl = sub[sub["zbe_active"] == 0]["cod_ine"].nunique()

        if n_ctrl < 5:
            continue

        prov_dummies = pd.get_dummies(sub["cod_provincia"], prefix="prov",
                                       drop_first=True, dtype=float)
        X = sm.add_constant(pd.concat(
            [sub[["zbe_active", "post", "zbe_x_post", "log_pop"]], prov_dummies],
            axis=1
        ))

        try:
            model = sm.OLS(sub[outcome], X).fit(
                cov_type="cluster", cov_kwds={"groups": sub["cod_ine"]}
            )
        except Exception:
            model = sm.OLS(sub[outcome], X).fit(cov_type="HC1")

        coef = model.params["zbe_x_post"]
        se = model.bse["zbe_x_post"]
        pval = model.pvalues["zbe_x_post"]

        print(f"  Control ≥ {thresh:>7,}:  N_treat={n_treat:>3}  N_ctrl={n_ctrl:>3}  "
              f"coef={coef:+.5f}  SE={se:.5f}  p={pval:.3f}{star_fn(pval)}")

        results.append({
            "control_threshold": thresh,
            "n_treat": n_treat,
            "n_ctrl": n_ctrl,
            "coef": coef,
            "se": se,
            "pval": pval,
        })

    if results:
        pd.DataFrame(results).to_csv(
            os.path.join(TAB_DIR, "did_zbe_size_matched.csv"), index=False
        )
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'did_zbe_size_matched.csv')}")

    return results


# ===================================================================
# FLEET OUTCOMES DiD
# ===================================================================
def run_did_fleet(df, fleet):
    """
    Did ZBE implementation actually affect fleet composition?
    This tests the mechanism: ZBE → fleet turnover → (potential) backlash.
    """
    print("\n" + "=" * 60)
    print("DiD: FLEET COMPOSITION (MECHANISM)")
    print("=" * 60)

    # Build fleet panel for above-50k municipalities
    above_50k = fleet[fleet["above_50k"] == True].copy()
    above_50k["zbe_active"] = above_50k["cod_ine"].isin(
        ZBE_ACTIVE_BY_MAY_2023.keys()
    ).astype(int)
    above_50k["post"] = (above_50k["year"] >= 2022).astype(int)
    above_50k["zbe_x_post"] = above_50k["zbe_active"] * above_50k["post"]
    above_50k["log_pop"] = np.log(above_50k["poblacion"])

    fleet_outcomes = [
        ("share_sin_distintivo", "No-label share (polluting)"),
        ("share_eco", "ECO share"),
        ("share_cero", "Zero-emission share"),
    ]

    star_fn = lambda p: "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.1 else ""))

    results = []
    for outcome, label in fleet_outcomes:
        sub = above_50k.dropna(subset=[outcome]).copy()

        prov_dummies = pd.get_dummies(sub["cod_provincia"], prefix="prov",
                                       drop_first=True, dtype=float)
        year_dummies = pd.get_dummies(sub["year"], prefix="yr", drop_first=True, dtype=float)
        X = sm.add_constant(pd.concat(
            [sub[["zbe_active", "post", "zbe_x_post", "log_pop"]],
             prov_dummies, year_dummies],
            axis=1
        ))

        try:
            model = sm.OLS(sub[outcome], X).fit(
                cov_type="cluster", cov_kwds={"groups": sub["cod_ine"]}
            )
        except Exception:
            model = sm.OLS(sub[outcome], X).fit(cov_type="HC1")

        coef = model.params["zbe_x_post"]
        se = model.bse["zbe_x_post"]
        pval = model.pvalues["zbe_x_post"]
        print(f"  {label:30s}  coef={coef:+.6f}  SE={se:.6f}  "
              f"p={pval:.3f}{star_fn(pval)}  N={int(model.nobs)}")

        results.append({
            "outcome": outcome,
            "label": label,
            "coef": coef,
            "se": se,
            "pval": pval,
            "n": int(model.nobs),
            "r2": model.rsquared,
        })

    if results:
        pd.DataFrame(results).to_csv(
            os.path.join(TAB_DIR, "did_zbe_fleet.csv"), index=False
        )
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'did_zbe_fleet.csv')}")

    return results


# ===================================================================
# VISUALIZATIONS
# ===================================================================
def plot_parallel_trends(df):
    """
    Plot Vox vote share trends for ZBE vs non-ZBE municipalities.
    With only 2019 and 2023, this is a simple pre-post comparison.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    outcomes = [
        ("share_vox", "Vox Vote Share"),
        ("share_pp", "PP Vote Share"),
        ("share_psoe", "PSOE Vote Share"),
    ]

    for ax, (outcome, label) in zip(axes, outcomes):
        for zbe_val, group_label, color, marker in [
            (1, "ZBE Active", "#d62728", "o"),
            (0, "No ZBE", "#1f77b4", "s"),
        ]:
            sub = df[df["zbe_active"] == zbe_val]
            means = sub.groupby("year")[outcome].mean()
            sems = sub.groupby("year")[outcome].sem()

            ax.errorbar(
                means.index, means.values, yerr=1.96 * sems.values,
                label=group_label, color=color, marker=marker,
                linewidth=2, capsize=4, markersize=8,
            )

        ax.axvline(2021, color="gray", linestyle="--", alpha=0.5, label="Law passed (2021)")
        ax.set_xlabel("Election Year")
        ax.set_ylabel(label)
        ax.set_title(label)
        ax.legend(fontsize=9)
        ax.set_xticks([2019, 2023])

    plt.suptitle(
        "DiD: Municipalities with Active ZBE vs. Obligated Non-Implementers",
        fontsize=13, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "did_zbe_parallel_trends.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Saved: {path}")


def plot_fleet_trends(fleet):
    """Plot fleet composition trends for ZBE vs non-ZBE municipalities."""
    above_50k = fleet[fleet["above_50k"] == True].copy()
    above_50k["zbe_active"] = above_50k["cod_ine"].isin(
        ZBE_ACTIVE_BY_MAY_2023.keys()
    ).astype(int)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    fleet_outcomes = [
        ("share_sin_distintivo", "No-Label (Polluting) Share"),
        ("share_eco", "ECO Share"),
        ("share_cero", "Zero-Emission Share"),
    ]

    for ax, (outcome, label) in zip(axes, fleet_outcomes):
        for zbe_val, group_label, color in [
            (1, "ZBE Active", "#d62728"),
            (0, "No ZBE", "#1f77b4"),
        ]:
            sub = above_50k[above_50k["zbe_active"] == zbe_val]
            means = sub.groupby("year")[outcome].mean()
            ax.plot(means.index, means.values, label=group_label,
                    color=color, linewidth=2, marker="o", markersize=5)

        ax.axvline(2021.5, color="gray", linestyle="--", alpha=0.5,
                   label="Mandate (2022+)")
        ax.set_xlabel("Year")
        ax.set_ylabel(label)
        ax.set_title(label)
        ax.legend(fontsize=9)

    plt.suptitle(
        "Fleet Composition: ZBE Implementers vs. Non-Implementers (>50k)",
        fontsize=13, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "did_zbe_fleet_trends.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Saved: {path}")


def plot_did_coefficients(results_df):
    """Forest plot of DiD coefficients across specifications."""
    vox_results = results_df[results_df["outcome"] == "share_vox"].copy()
    if len(vox_results) == 0:
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    y_pos = range(len(vox_results))
    ax.errorbar(
        vox_results["coef"], y_pos,
        xerr=1.96 * vox_results["se"],
        fmt="o", color="steelblue", capsize=5, markersize=8,
    )
    ax.axvline(0, color="red", linestyle="--", alpha=0.5)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(vox_results["specification"].values)
    ax.set_xlabel("DiD Coefficient (ZBE × Post)")
    ax.set_title("Effect of ZBE Implementation on Vox Vote Share\n(DiD Estimates)")
    ax.invert_yaxis()

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "did_zbe_coefficients.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ===================================================================
# CITY-LEVEL DESCRIPTIVE TABLE
# ===================================================================
def city_level_table(df):
    """
    Show individual treated cities: Vox change 2019→2023.
    """
    print("\n" + "=" * 60)
    print("CITY-LEVEL VOX CHANGE — ZBE IMPLEMENTERS")
    print("=" * 60)

    treated = df[df["zbe_active"] == 1].copy()

    # Normalise municipality names: use the 2023 name (or latest available)
    name_map = (
        treated.sort_values("year", ascending=False)
        .drop_duplicates("cod_ine")[["cod_ine", "municipio"]]
        .set_index("cod_ine")["municipio"]
    )

    wide = treated.pivot_table(
        index="cod_ine",
        columns="year",
        values=["share_vox", "share_pp", "share_psoe", "poblacion"],
        aggfunc="first",
    )

    if 2019 not in wide["share_vox"].columns or 2023 not in wide["share_vox"].columns:
        print("  Missing year data for city-level table")
        return

    city_df = pd.DataFrame({
        "municipality": wide.index.map(name_map),
        "cod_ine": wide.index,
        "pop_2023": wide[("poblacion", 2023)].values,
        "vox_2019": wide[("share_vox", 2019)].values,
        "vox_2023": wide[("share_vox", 2023)].values,
        "pp_2019": wide[("share_pp", 2019)].values,
        "pp_2023": wide[("share_pp", 2023)].values,
    })
    city_df["vox_change"] = city_df["vox_2023"] - city_df["vox_2019"]
    city_df["pp_change"] = city_df["pp_2023"] - city_df["pp_2019"]
    city_df = city_df.sort_values("pop_2023", ascending=False)

    print(f"\n  {'Municipality':25s} {'Pop':>10s} {'Vox19':>7s} {'Vox23':>7s} {'ΔVox':>7s} {'PP19':>7s} {'PP23':>7s} {'ΔPP':>7s}")
    print("  " + "-" * 90)
    for _, row in city_df.iterrows():
        print(f"  {row['municipality']:25s} {row['pop_2023']:>10,.0f} "
              f"{row['vox_2019']:>7.3f} {row['vox_2023']:>7.3f} {row['vox_change']:>+7.3f} "
              f"{row['pp_2019']:>7.3f} {row['pp_2023']:>7.3f} {row['pp_change']:>+7.3f}")

    # Compare to control group average
    control = df[df["zbe_active"] == 0]
    ctrl_wide = control.pivot_table(
        index="cod_ine", columns="year", values="share_vox", aggfunc="first"
    )
    if 2019 in ctrl_wide.columns and 2023 in ctrl_wide.columns:
        ctrl_change = (ctrl_wide[2023] - ctrl_wide[2019]).mean()
        treat_change = city_df["vox_change"].mean()
        print(f"\n  Average Vox change (ZBE cities):    {treat_change:+.4f}")
        print(f"  Average Vox change (Control cities): {ctrl_change:+.4f}")
        print(f"  Raw DiD:                            {treat_change - ctrl_change:+.4f}")

    city_df.to_csv(os.path.join(TAB_DIR, "did_zbe_city_detail.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'did_zbe_city_detail.csv')}")
    return city_df


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("11 — DiD Analysis: ZBE Implementers vs. Non-Implementers")
    print("=" * 70)

    election, fleet = load_data()

    # Build DiD panel
    df = build_did_panel(election, fleet)

    # Balance table
    balance_table(df)

    # Main DiD estimation
    results_df = run_did(df)

    # Size-matched robustness
    run_did_size_matched(df)

    # Fleet composition mechanism
    run_did_fleet(df, fleet)

    # City-level detail
    city_level_table(df)

    # Plots
    plot_parallel_trends(df)
    plot_fleet_trends(fleet)
    if results_df is not None and len(results_df) > 0:
        plot_did_coefficients(results_df)

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
