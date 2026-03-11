"""
09_rd_analysis.py

Main regression discontinuity analysis for the Spain ZBE paper.

Specifications:
  1. ITT (Intent-to-Treat / reduced-form): effect of crossing 50k threshold
     on fleet composition — PRIMARY specification
  2. Local linear RD with separate slopes (rdrobust-style, manual)
  3. Fuzzy RD (2SLS): instrument actual ZBE with threshold crossing
     — requires ZBE implementation status data (MITECO)
  4. Election RD: effect on Vox vote share (requires 2023 data)

Addresses reviewer concerns:
  - ITT as primary spec (avoids weak first-stage problem)
  - Local linear with interaction (allows slope change)
  - Province fixed effects (absorbs regional confounders)
  - Clustered standard errors at municipality level

Output:
  output/tables/rd_main_results.csv
  output/tables/rd_fleet_all_outcomes.csv
  output/tables/rd_elections.csv
  output/figures/rd_main_*.png

Usage:
    python spain-zbe/src/analysis/09_rd_analysis.py
"""

import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.join("spain-zbe")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
TAB_DIR = os.path.join(BASE_DIR, "output", "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

THRESHOLD = 50_000
BW_DEFAULT = 20_000


# ===================================================================
# UTILITIES
# ===================================================================
def load_panels():
    fleet = pd.read_csv(os.path.join(DATA_DIR, "fleet_panel.csv"),
                        dtype={"cod_ine": str, "cod_provincia": str})
    election = pd.read_csv(os.path.join(DATA_DIR, "election_panel.csv"),
                           dtype={"cod_ine": str, "cod_provincia": str})
    return fleet, election


def run_rd(data, outcome, bandwidth=BW_DEFAULT, controls=None,
           cluster_var=None, province_fe=False):
    """
    Run a local linear RD regression.

    Model: Y = a + b*Treat + c*RunVar + d*Treat*RunVar + e*Controls + eps

    Parameters
    ----------
    data : DataFrame with pop_distance_50k, above_50k, and the outcome
    outcome : str — column name
    bandwidth : float — symmetric bandwidth around 0
    controls : list of str — additional control columns
    cluster_var : str — column to cluster on (e.g. cod_ine)
    province_fe : bool — include province fixed effects

    Returns
    -------
    dict with coefficient, SE, CI, p-value, N, R2
    """
    sub = data[data["pop_distance_50k"].abs() <= bandwidth].copy()
    sub = sub.dropna(subset=[outcome])

    if len(sub) < 30:
        return None

    sub["treat"] = sub["above_50k"].astype(float)
    sub["dist_x_treat"] = sub["pop_distance_50k"] * sub["treat"]

    regressors = ["treat", "pop_distance_50k", "dist_x_treat"]

    if controls:
        for c in controls:
            if c in sub.columns:
                regressors.append(c)

    if province_fe and "cod_provincia" in sub.columns:
        prov_dummies = pd.get_dummies(sub["cod_provincia"], prefix="prov",
                                       drop_first=True, dtype=float)
        sub = pd.concat([sub, prov_dummies], axis=1)
        regressors += list(prov_dummies.columns)

    X = sm.add_constant(sub[regressors])
    y = sub[outcome]

    # Choose covariance estimator
    if cluster_var and cluster_var in sub.columns:
        try:
            model = sm.OLS(y, X).fit(
                cov_type="cluster",
                cov_kwds={"groups": sub[cluster_var]}
            )
        except Exception:
            model = sm.OLS(y, X).fit(cov_type="HC1")
    else:
        model = sm.OLS(y, X).fit(cov_type="HC1")

    coef = model.params["treat"]
    se = model.bse["treat"]
    pval = model.pvalues["treat"]
    ci = model.conf_int().loc["treat"]

    return {
        "coef": coef,
        "se": se,
        "pval": pval,
        "ci_low": ci[0],
        "ci_high": ci[1],
        "n": len(sub),
        "n_above": int(sub["treat"].sum()),
        "n_below": int((~sub["treat"].astype(bool)).sum()),
        "r2": model.rsquared,
        "outcome_mean": y.mean(),
    }


def star(pval):
    if pval < 0.01:
        return "***"
    elif pval < 0.05:
        return "**"
    elif pval < 0.1:
        return "*"
    return ""


# ===================================================================
# 1. MAIN FLEET RD (ITT)
# ===================================================================
def fleet_rd_main(fleet):
    """
    Primary specification: ITT effect of ZBE mandate obligation on
    municipal fleet composition, post-mandate (2022-2024).
    """
    print("\n" + "=" * 60)
    print("MAIN FLEET RD — ITT (Intent-to-Treat)")
    print("=" * 60)

    # Post-mandate: 2022+ (law passed May 2021, original deadline Jan 2023)
    post = fleet[fleet["year"] >= 2022].copy()

    primary_outcome = "share_sin_distintivo"
    all_outcomes = ["share_sin_distintivo", "share_b", "share_c",
                    "share_eco", "share_cero"]

    # ---------------------------------------------------------------
    # Specification 1: Simple local linear (no FE)
    # ---------------------------------------------------------------
    print("\n--- Spec 1: Local linear, HC1, no FE ---")
    res1 = run_rd(post, primary_outcome, bandwidth=BW_DEFAULT)
    if res1:
        print(f"  {primary_outcome}:  coef={res1['coef']:+.5f}  "
              f"SE={res1['se']:.5f}  p={res1['pval']:.4f}{star(res1['pval'])}  "
              f"N={res1['n']} (above={res1['n_above']}, below={res1['n_below']})")

    # ---------------------------------------------------------------
    # Specification 2: With province FE
    # ---------------------------------------------------------------
    print("\n--- Spec 2: Local linear + province FE ---")
    res2 = run_rd(post, primary_outcome, bandwidth=BW_DEFAULT,
                  province_fe=True)
    if res2:
        print(f"  {primary_outcome}:  coef={res2['coef']:+.5f}  "
              f"SE={res2['se']:.5f}  p={res2['pval']:.4f}{star(res2['pval'])}  "
              f"N={res2['n']}")

    # ---------------------------------------------------------------
    # Specification 3: With province FE + municipality clustering
    # ---------------------------------------------------------------
    print("\n--- Spec 3: Province FE + cluster(municipality) ---")
    res3 = run_rd(post, primary_outcome, bandwidth=BW_DEFAULT,
                  province_fe=True, cluster_var="cod_ine")
    if res3:
        print(f"  {primary_outcome}:  coef={res3['coef']:+.5f}  "
              f"SE={res3['se']:.5f}  p={res3['pval']:.4f}{star(res3['pval'])}  "
              f"N={res3['n']}")

    # ---------------------------------------------------------------
    # All outcomes (preferred spec: province FE + clustering)
    # ---------------------------------------------------------------
    print("\n--- All Fleet Outcomes (Spec 3: Province FE + cluster) ---")
    results_all = []
    for outcome in all_outcomes:
        res = run_rd(post, outcome, bandwidth=BW_DEFAULT,
                     province_fe=True, cluster_var="cod_ine")
        if res:
            res["outcome"] = outcome
            results_all.append(res)
            print(f"  {outcome:25s}  coef={res['coef']:+.6f}  "
                  f"SE={res['se']:.6f}  p={res['pval']:.3f}{star(res['pval'])}")

    # Save main results table
    if results_all:
        main_df = pd.DataFrame(results_all)
        main_df = main_df[["outcome", "coef", "se", "pval", "ci_low", "ci_high",
                            "n", "n_above", "n_below", "r2", "outcome_mean"]]
        main_df.to_csv(os.path.join(TAB_DIR, "rd_fleet_all_outcomes.csv"), index=False)
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'rd_fleet_all_outcomes.csv')}")

    # Compile specification comparison for primary outcome
    specs = []
    for label, res in [("(1) Local linear", res1),
                        ("(2) + Province FE", res2),
                        ("(3) + Cluster SE", res3)]:
        if res:
            specs.append({
                "Specification": label,
                "Coefficient": f"{res['coef']:+.5f}",
                "SE": f"({res['se']:.5f})",
                "p-value": f"{res['pval']:.4f}",
                "N": res["n"],
                "R²": f"{res['r2']:.4f}",
            })

    if specs:
        spec_df = pd.DataFrame(specs)
        spec_df.to_csv(os.path.join(TAB_DIR, "rd_main_results.csv"), index=False)
        print(f"  Saved: {os.path.join(TAB_DIR, 'rd_main_results.csv')}")
        print(f"\n  Specification comparison for {primary_outcome}:")
        print(spec_df.to_string(index=False))

    return results_all


# ===================================================================
# 2. DIFFERENCE-IN-DISCONTINUITIES (DiD + RD)
# ===================================================================
def diff_in_disc(fleet):
    """
    Difference-in-discontinuities: compare post-pre RD estimates.
    This differences out any time-invariant confounders at the threshold.
    """
    print("\n" + "=" * 60)
    print("DIFFERENCE-IN-DISCONTINUITIES")
    print("=" * 60)

    outcome = "share_sin_distintivo"

    # Create pre/post indicator
    df = fleet.copy()
    df = df.dropna(subset=[outcome])
    df["post"] = (df["year"] >= 2022).astype(float)
    df["treat"] = df["above_50k"].astype(float)

    # Restrict to bandwidth
    df = df[df["pop_distance_50k"].abs() <= BW_DEFAULT].copy()

    # Interaction terms
    df["treat_x_post"] = df["treat"] * df["post"]
    df["dist_x_treat"] = df["pop_distance_50k"] * df["treat"]
    df["dist_x_post"] = df["pop_distance_50k"] * df["post"]
    df["dist_x_treat_x_post"] = df["pop_distance_50k"] * df["treat"] * df["post"]

    regressors = ["treat", "post", "treat_x_post",
                  "pop_distance_50k", "dist_x_treat",
                  "dist_x_post", "dist_x_treat_x_post"]

    X = sm.add_constant(df[regressors])
    y = df[outcome]

    try:
        model = sm.OLS(y, X).fit(
            cov_type="cluster",
            cov_kwds={"groups": df["cod_ine"]}
        )
    except Exception:
        model = sm.OLS(y, X).fit(cov_type="HC1")

    # Key coefficient: treat_x_post = DiD-in-RD
    coef = model.params["treat_x_post"]
    se = model.bse["treat_x_post"]
    pval = model.pvalues["treat_x_post"]

    print(f"\n  Diff-in-Disc coefficient (treat x post):")
    print(f"    coef = {coef:+.6f}")
    print(f"    SE   = {se:.6f}")
    print(f"    p    = {pval:.4f} {star(pval)}")
    print(f"    N    = {len(df)}")
    print(f"    R²   = {model.rsquared:.4f}")

    # Also report the time-invariant RD (pre-existing discontinuity)
    coef_treat = model.params["treat"]
    pval_treat = model.pvalues["treat"]
    print(f"\n  Pre-existing discontinuity (treat, pre-period):")
    print(f"    coef = {coef_treat:+.6f}  p = {pval_treat:.4f} {star(pval_treat)}")

    result = {
        "did_rd_coef": coef,
        "did_rd_se": se,
        "did_rd_pval": pval,
        "pre_disc_coef": coef_treat,
        "pre_disc_pval": pval_treat,
        "n": len(df),
        "r2": model.rsquared,
    }

    # Save
    pd.DataFrame([result]).to_csv(
        os.path.join(TAB_DIR, "rd_diff_in_disc.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'rd_diff_in_disc.csv')}")

    return result


# ===================================================================
# 3. rdrobust ESTIMATION (if available)
# ===================================================================
def rdrobust_estimation(fleet):
    """
    Use the rdrobust package for MSE-optimal bandwidth selection
    and robust confidence intervals.
    """
    print("\n" + "=" * 60)
    print("rdrobust ESTIMATION")
    print("=" * 60)

    try:
        from rdrobust import rdrobust
    except ImportError:
        print("  rdrobust not available. Install with: pip install rdrobust")
        print("  Skipping rdrobust estimation.")
        return None

    post = fleet[fleet["year"] >= 2022].copy()
    # Collapse to municipality means for cross-sectional RD
    muni = post.groupby("cod_ine").agg({
        "pop_distance_50k": "mean",
        "share_sin_distintivo": "mean",
        "share_eco": "mean",
        "share_cero": "mean",
    }).reset_index().dropna()

    outcomes = {
        "share_sin_distintivo": "Share No-Label",
        "share_eco": "Share ECO",
        "share_cero": "Share Zero",
    }

    results = []
    for var, label in outcomes.items():
        y = muni[var].values
        x = muni["pop_distance_50k"].values

        try:
            rd = rdrobust(y, x, c=0)

            # rdrobust returns DataFrames; use .iloc to extract scalars
            coef = float(rd.coef.iloc[0, 0])
            se = float(rd.se.iloc[2, 0])       # Robust SE (row 2)
            pval = float(rd.pv.iloc[2, 0])     # Robust p-value
            bw = float(rd.bws.iloc[0, 0])      # h (MSE-optimal)
            ci_l = float(rd.ci.iloc[2, 0])     # Robust CI
            ci_h = float(rd.ci.iloc[2, 1])
            n_eff = int(rd.N_h[0]) + int(rd.N_h[1])

            results.append({
                "outcome": var,
                "coef": coef,
                "se_robust": se,
                "pval": pval,
                "ci_low": ci_l,
                "ci_high": ci_h,
                "bw_mse": bw,
                "n_effective": n_eff,
            })
            print(f"\n  {label} ({var}):")
            print(f"    Coef     = {coef:+.6f}")
            print(f"    SE (rob) = {se:.6f}")
            print(f"    p-value  = {pval:.4f} {star(pval)}")
            print(f"    95% CI   = [{ci_l:.6f}, {ci_h:.6f}]")
            print(f"    BW (MSE) = {bw:.0f}")
            print(f"    N (eff)  = {n_eff}")

        except Exception as e:
            print(f"\n  {label}: rdrobust error — {e}")

    if results:
        rd_df = pd.DataFrame(results)
        rd_df.to_csv(os.path.join(TAB_DIR, "rd_rdrobust_results.csv"), index=False)
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'rd_rdrobust_results.csv')}")

    return results


# ===================================================================
# 4. ELECTION RD
# ===================================================================
def election_rd(election):
    """
    RD on voting outcomes. Requires 2023 election data for
    post-treatment analysis.

    If only 2015 and 2019 are available, reports pre-treatment
    balance at the threshold (should show no discontinuity).
    """
    print("\n" + "=" * 60)
    print("ELECTION RD")
    print("=" * 60)

    years = sorted(election["year"].unique())
    has_post = 2023 in years

    if not has_post:
        print(f"\n  Available years: {years}")
        print("  No post-mandate (2023) election data available.")
        print("  Reporting pre-treatment balance only.\n")

    vote_outcomes = ["share_vox", "share_pp", "share_psoe"]

    for yr in years:
        yr_data = election[election["year"] == yr].copy()
        print(f"\n  --- {yr} Municipal Election ---")

        for outcome in vote_outcomes:
            if outcome not in yr_data.columns:
                continue
            res = run_rd(yr_data, outcome, bandwidth=BW_DEFAULT,
                         province_fe=True, cluster_var="cod_ine")
            if res:
                label = "POST-TREATMENT" if yr >= 2023 else "pre-treatment"
                print(f"    {outcome:15s} ({label}):  coef={res['coef']:+.5f}  "
                      f"SE={res['se']:.5f}  p={res['pval']:.3f}{star(res['pval'])}  "
                      f"N={res['n']}")

    # If we have 2023, do DiD: 2019 vs 2023
    if has_post:
        print("\n  --- Diff-in-Disc: 2019 vs 2023 ---")
        did_data = election[election["year"].isin([2019, 2023])].copy()

        for outcome in vote_outcomes:
            did_data_clean = did_data.dropna(subset=[outcome])
            did_data_clean = did_data_clean[
                did_data_clean["pop_distance_50k"].abs() <= BW_DEFAULT
            ].copy()

            if len(did_data_clean) < 30:
                continue

            did_data_clean["post"] = (did_data_clean["year"] == 2023).astype(float)
            did_data_clean["treat"] = did_data_clean["above_50k"].astype(float)
            did_data_clean["treat_x_post"] = (
                did_data_clean["treat"] * did_data_clean["post"]
            )
            did_data_clean["dist_x_treat"] = (
                did_data_clean["pop_distance_50k"] * did_data_clean["treat"]
            )

            regressors = ["treat", "post", "treat_x_post",
                          "pop_distance_50k", "dist_x_treat"]
            X = sm.add_constant(did_data_clean[regressors])
            y = did_data_clean[outcome]

            try:
                model = sm.OLS(y, X).fit(
                    cov_type="cluster",
                    cov_kwds={"groups": did_data_clean["cod_ine"]}
                )
                coef = model.params["treat_x_post"]
                se = model.bse["treat_x_post"]
                pval = model.pvalues["treat_x_post"]
                print(f"    {outcome:15s}  DiD-RD coef={coef:+.5f}  "
                      f"SE={se:.5f}  p={pval:.3f}{star(pval)}")
            except Exception as e:
                print(f"    {outcome}: error — {e}")


# ===================================================================
# 5. FIRST STAGE DIAGNOSTIC
# ===================================================================
def first_stage_diagnostic(fleet):
    """
    Report the relationship between threshold crossing (above_50k)
    and actual ZBE implementation.

    Without MITECO implementation status data merged in, we report
    the descriptive statistics on which municipalities are above/below
    and flag this as requiring the MITECO scrape.
    """
    print("\n" + "=" * 60)
    print("FIRST-STAGE DIAGNOSTIC")
    print("=" * 60)

    latest = fleet[fleet["year"] == fleet["year"].max()]
    n_above = latest["above_50k"].sum()
    n_total = len(latest)

    print(f"\n  Municipalities above 50k: {n_above}")
    print(f"  Total municipalities:     {n_total}")
    print(f"  Share above threshold:    {n_above / n_total:.4f}")
    print(f"\n  NOTE: First-stage (threshold → actual ZBE) requires MITECO")
    print(f"  implementation status data. As of end-2025:")
    print(f"    - 58 ZBEs vigentes (active)")
    print(f"    - 91 en trámite (in process)")
    print(f"    - ~20 pendientes (pending)")
    print(f"  Compliance rate among obligated: ~34%")
    print(f"\n  Implication: Fuzzy RD first stage is WEAK.")
    print(f"  → ITT (reduced-form) is the preferred specification.")
    print(f"  → ITT captures the effect of the MANDATE, not implementation.")


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("09 — Main RD Analysis")
    print("=" * 70)

    fleet, election = load_panels()

    # Primary analysis: Fleet composition
    fleet_rd_main(fleet)

    # Difference-in-discontinuities
    diff_in_disc(fleet)

    # rdrobust with optimal bandwidth
    rdrobust_estimation(fleet)

    # First-stage diagnostic
    first_stage_diagnostic(fleet)

    # Election analysis
    election_rd(election)

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
