"""
13_rd_fleet_composition.py

Regression Discontinuity: Does the 50k ZBE mandate threshold shift
vehicle fleet composition?

Running variable: Municipal population (INE Padrón)
Threshold: 50,000 inhabitants
Treatment: ZBE obligation (Ley 7/2021 de Cambio Climático, effective 2023)
Outcomes: Share of vehicles by environmental label
  - share_sin_distintivo (most polluting, no label)
  - share_cero (zero emission)
  - share_eco (ECO label)
  - share_c + share_b (intermediate labels)

Design:
  Pre-mandate:  2017-2020 (placebo — should show NO discontinuity)
  Post-mandate: 2021-2024 (treatment — should show discontinuity IF mandate works)

We test whether even without enforcement, the mandate itself shifted
fleet composition through anticipatory behavior (dealerships, consumers,
local subsidies, scrappage awareness).

Output:
  output/tables/rd_fleet_*.csv
  output/figures/rd_fleet_*.png
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
TAB_DIR = os.path.join(BASE_DIR, "output", "tables")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
os.makedirs(TAB_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


def load_data():
    """Load fleet panel."""
    df = pd.read_csv(
        os.path.join(DATA_DIR, "fleet_panel.csv"),
        dtype={"cod_ine": str, "cod_provincia": str},
    )
    return df


def rd_estimate(df, outcome, bandwidth, year_range=None, label=""):
    """
    Local linear RD estimate at the 50k threshold.

    Y_i = alpha + beta * above_50k + gamma * (pop - 50k) +
          delta * above_50k * (pop - 50k) + epsilon
    """
    sub = df.copy()
    if year_range is not None:
        sub = sub[sub["year"].between(*year_range)]

    # Collapse to municipality-level means (average across years in range)
    muni = sub.groupby("cod_ine").agg({
        outcome: "mean",
        "poblacion": "mean",
        "above_50k": "first",
        "pop_distance_50k": "mean",
        "municipio": "first",
        "cod_provincia": "first",
    }).reset_index()

    # Apply bandwidth
    muni = muni[muni["poblacion"].between(50000 - bandwidth, 50000 + bandwidth)]

    if len(muni) < 20:
        return None

    # Normalize running variable
    muni["x"] = muni["poblacion"] - 50000
    muni["above"] = (muni["x"] >= 0).astype(int)
    muni["x_above"] = muni["x"] * muni["above"]

    y = muni[outcome]
    X = sm.add_constant(muni[["above", "x", "x_above"]])

    model = sm.OLS(y, X).fit(cov_type="HC1")

    result = {
        "label": label,
        "outcome": outcome,
        "bandwidth": bandwidth,
        "n_total": len(muni),
        "n_above": muni["above"].sum(),
        "n_below": len(muni) - muni["above"].sum(),
        "mean_below": muni.loc[muni["above"] == 0, outcome].mean(),
        "mean_above": muni.loc[muni["above"] == 1, outcome].mean(),
        "rd_estimate": model.params["above"],
        "rd_se": model.bse["above"],
        "rd_pvalue": model.pvalues["above"],
        "r2": model.rsquared,
    }
    return result


def run_all_rd(df):
    """Run RD estimates for all outcomes, periods, and bandwidths."""
    print("\n" + "=" * 80)
    print("REGRESSION DISCONTINUITY: FLEET COMPOSITION AT 50k THRESHOLD")
    print("=" * 80)

    outcomes = [
        ("share_sin_distintivo", "No-label (most polluting)"),
        ("share_cero", "Zero emission"),
        ("share_eco", "ECO label"),
        ("share_c", "C label"),
        ("share_b", "B label"),
    ]

    periods = [
        ((2017, 2020), "Pre-mandate (2017-2020)"),
        ((2021, 2024), "Post-mandate (2021-2024)"),
        ((2023, 2024), "Late post-mandate (2023-2024)"),
    ]

    bandwidths = [15000, 20000, 25000, 30000]

    all_results = []

    for outcome, outcome_label in outcomes:
        print(f"\n  --- {outcome_label} ({outcome}) ---")

        for year_range, period_label in periods:
            for bw in bandwidths:
                result = rd_estimate(df, outcome, bw, year_range, period_label)
                if result:
                    result["outcome_label"] = outcome_label
                    all_results.append(result)

        # Print main results (bw=20000)
        for year_range, period_label in periods:
            r = rd_estimate(df, outcome, 20000, year_range, period_label)
            if r:
                star = "***" if r["rd_pvalue"] < 0.01 else (
                    "**" if r["rd_pvalue"] < 0.05 else (
                        "*" if r["rd_pvalue"] < 0.1 else ""))
                print(f"    {period_label:30s}  RD={r['rd_estimate']:+.5f}  "
                      f"SE={r['rd_se']:.5f}  p={r['rd_pvalue']:.3f}{star}  "
                      f"N={r['n_total']}  (below={r['mean_below']:.4f}, above={r['mean_above']:.4f})")

    # Save results
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(os.path.join(TAB_DIR, "rd_fleet_estimates.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'rd_fleet_estimates.csv')}")

    return results_df


def run_yearly_rd(df):
    """
    Year-by-year RD estimates to see when discontinuity appears.
    If mandate matters: no jump pre-2021, jump post-2021.
    """
    print("\n" + "=" * 80)
    print("YEAR-BY-YEAR RD ESTIMATES (share_sin_distintivo, bw=20k)")
    print("=" * 80)

    results = []
    for year in sorted(df["year"].unique()):
        r = rd_estimate(df, "share_sin_distintivo", 20000, (year, year), str(year))
        if r:
            results.append(r)
            star = "***" if r["rd_pvalue"] < 0.01 else (
                "**" if r["rd_pvalue"] < 0.05 else (
                    "*" if r["rd_pvalue"] < 0.1 else ""))
            print(f"    {year}:  RD={r['rd_estimate']:+.5f}  SE={r['rd_se']:.5f}  "
                  f"p={r['rd_pvalue']:.3f}{star}  N={r['n_total']}")

    return results


def run_did_rd(df):
    """
    Difference-in-RD: Compare the RD estimate before vs after mandate.
    This is the cleanest test: does the CHANGE in discontinuity appear
    after the mandate?
    """
    print("\n" + "=" * 80)
    print("DIFFERENCE-IN-RD (DiRD): Pre vs Post mandate")
    print("=" * 80)

    outcome = "share_sin_distintivo"
    bw = 20000

    sub = df[df["poblacion"].between(50000 - bw, 50000 + bw)].copy()
    sub["x"] = sub["poblacion"] - 50000
    sub["above"] = (sub["x"] >= 0).astype(int)
    sub["post"] = (sub["year"] >= 2021).astype(int)
    sub["above_post"] = sub["above"] * sub["post"]
    sub["x_above"] = sub["x"] * sub["above"]
    sub["x_post"] = sub["x"] * sub["post"]
    sub["x_above_post"] = sub["x"] * sub["above"] * sub["post"]

    y = sub[outcome]
    X = sm.add_constant(sub[["above", "post", "above_post",
                              "x", "x_above", "x_post", "x_above_post"]])

    # Cluster by municipality
    model = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": sub["cod_ine"]})

    print(f"\n  Outcome: {outcome}")
    print(f"  Bandwidth: +/- {bw:,}")
    print(f"  N obs: {int(model.nobs)}")
    print(f"  N municipalities: {sub['cod_ine'].nunique()}")
    print(f"\n  Key coefficients:")
    for var in ["above", "post", "above_post"]:
        star = "***" if model.pvalues[var] < 0.01 else (
            "**" if model.pvalues[var] < 0.05 else (
                "*" if model.pvalues[var] < 0.1 else ""))
        print(f"    {var:20s}  coef={model.params[var]:+.5f}  "
              f"SE={model.bse[var]:.5f}  p={model.pvalues[var]:.3f}{star}")

    print(f"\n  Interpretation:")
    print(f"    'above':      RD in pre-period = {model.params['above']:+.5f}")
    print(f"    'above_post': CHANGE in RD after mandate = {model.params['above_post']:+.5f}")
    print(f"    → This is the DiRD estimate: did the discontinuity widen after 2021?")

    return model


def plot_rd_scatter(df, outcome="share_sin_distintivo", bw=25000):
    """
    RD scatter plots: pre-mandate vs post-mandate.
    Binned scatter with local linear fit on each side.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    periods = [
        ((2017, 2018), "Pre-mandate: 2017-2018"),
        ((2019, 2020), "Pre-mandate: 2019-2020"),
        ((2021, 2022), "Post-mandate: 2021-2022"),
        ((2023, 2024), "Post-mandate: 2023-2024"),
    ]

    for ax, (year_range, title) in zip(axes.flat, periods):
        sub = df[df["year"].between(*year_range)]

        # Collapse to municipality means
        muni = sub.groupby("cod_ine").agg({
            outcome: "mean",
            "poblacion": "mean",
            "above_50k": "first",
        }).reset_index()

        muni = muni[muni["poblacion"].between(50000 - bw, 50000 + bw)]
        muni["x"] = muni["poblacion"] - 50000

        # Binned scatter
        n_bins = 30
        muni["bin"] = pd.cut(muni["x"], bins=n_bins)
        binned = muni.groupby("bin", observed=True).agg({
            "x": "mean",
            outcome: "mean",
        }).dropna()

        # Color by side
        below = binned[binned["x"] < 0]
        above = binned[binned["x"] >= 0]
        ax.scatter(below["x"] / 1000, below[outcome], color="#2166ac", s=40, alpha=0.7, zorder=3)
        ax.scatter(above["x"] / 1000, above[outcome], color="#b2182b", s=40, alpha=0.7, zorder=3)

        # Local linear fit on each side
        for side, color in [("below", "#2166ac"), ("above", "#b2182b")]:
            mask = muni["x"] < 0 if side == "below" else muni["x"] >= 0
            side_data = muni[mask]
            if len(side_data) > 5:
                X = sm.add_constant(side_data["x"])
                model = sm.OLS(side_data[outcome], X).fit()
                x_pred = np.linspace(side_data["x"].min(), side_data["x"].max(), 100)
                X_pred = sm.add_constant(x_pred)
                y_pred = model.predict(X_pred)
                ax.plot(x_pred / 1000, y_pred, color=color, linewidth=2, zorder=4)

        ax.axvline(x=0, color="black", linestyle="--", alpha=0.5, linewidth=1)
        ax.set_xlabel("Population - 50,000 (thousands)")
        ax.set_ylabel(f"Share: {outcome.replace('share_', '')}")
        ax.set_title(title)

    plt.suptitle(f"RD Plot: {outcome} at 50k threshold (bw=±{bw//1000}k)", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, f"rd_fleet_{outcome}.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(FIG_DIR, f'rd_fleet_{outcome}.png')}")
    plt.close()


def plot_yearly_rd_coefficients(df):
    """
    Plot the year-by-year RD coefficient for share_sin_distintivo.
    Should see: flat pre-2021, then increasingly negative post-2021.
    """
    results = []
    for year in sorted(df["year"].unique()):
        for bw in [15000, 20000, 25000]:
            r = rd_estimate(df, "share_sin_distintivo", bw, (year, year), str(year))
            if r:
                r["year"] = year
                results.append(r)

    rdf = pd.DataFrame(results)

    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot for each bandwidth
    for bw, marker, alpha in [(15000, "s", 0.4), (20000, "o", 1.0), (25000, "D", 0.4)]:
        sub = rdf[rdf["bandwidth"] == bw]
        ax.errorbar(sub["year"], sub["rd_estimate"],
                    yerr=1.96 * sub["rd_se"],
                    fmt=f"-{marker}", label=f"bw=±{bw//1000}k",
                    capsize=3, alpha=alpha, markersize=6)

    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=2020.5, color="red", linestyle=":", alpha=0.7, label="Mandate (Ley 7/2021)")
    ax.set_xlabel("Year")
    ax.set_ylabel("RD estimate (share_sin_distintivo)")
    ax.set_title("Year-by-year RD coefficient at 50k threshold")
    ax.legend(fontsize=9)
    ax.set_xticks(sorted(df["year"].unique()))

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "rd_fleet_yearly_coefficients.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(FIG_DIR, 'rd_fleet_yearly_coefficients.png')}")
    plt.close()


def plot_rd_multi_outcome(df, bw=20000):
    """
    RD scatter for multiple outcomes side by side: sin_distintivo, cero, eco.
    Post-mandate period only (2023-2024).
    """
    outcomes = [
        ("share_sin_distintivo", "No label (polluting)"),
        ("share_cero", "Zero emission"),
        ("share_eco", "ECO label"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, (outcome, label) in zip(axes, outcomes):
        sub = df[df["year"].between(2023, 2024)]
        muni = sub.groupby("cod_ine").agg({
            outcome: "mean",
            "poblacion": "mean",
        }).reset_index()
        muni = muni[muni["poblacion"].between(50000 - bw, 50000 + bw)]
        muni["x"] = muni["poblacion"] - 50000

        # Binned scatter
        n_bins = 20
        muni["bin"] = pd.cut(muni["x"], bins=n_bins)
        binned = muni.groupby("bin", observed=True).agg({
            "x": "mean", outcome: "mean"
        }).dropna()

        below = binned[binned["x"] < 0]
        above = binned[binned["x"] >= 0]
        ax.scatter(below["x"] / 1000, below[outcome], color="#2166ac", s=50, zorder=3)
        ax.scatter(above["x"] / 1000, above[outcome], color="#b2182b", s=50, zorder=3)

        for side, color in [("below", "#2166ac"), ("above", "#b2182b")]:
            mask = muni["x"] < 0 if side == "below" else muni["x"] >= 0
            side_data = muni[mask]
            if len(side_data) > 5:
                X = sm.add_constant(side_data["x"])
                model = sm.OLS(side_data[outcome], X).fit()
                x_pred = np.linspace(side_data["x"].min(), side_data["x"].max(), 100)
                y_pred = model.predict(sm.add_constant(x_pred))
                ax.plot(x_pred / 1000, y_pred, color=color, linewidth=2, zorder=4)

        ax.axvline(x=0, color="black", linestyle="--", alpha=0.5)
        ax.set_xlabel("Pop - 50k (thousands)")
        ax.set_ylabel(f"Share")
        ax.set_title(label)

    plt.suptitle("RD at 50k threshold: Fleet composition (2023-2024)", fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "rd_fleet_multi_outcome.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(FIG_DIR, 'rd_fleet_multi_outcome.png')}")
    plt.close()


def density_test(df):
    """
    McCrary-style density test: is there bunching at the 50k threshold?
    Check if municipalities strategically report population below 50k.
    """
    print("\n" + "=" * 80)
    print("DENSITY TEST (McCrary)")
    print("=" * 80)

    for year in [2019, 2021, 2023]:
        sub = df[(df["year"] == year) & (df["poblacion"].between(30000, 70000))]
        muni = sub.groupby("cod_ine")["poblacion"].first().reset_index()

        bins = np.arange(30000, 70001, 2000)
        hist, _ = np.histogram(muni["poblacion"], bins=bins)

        # Find bins around threshold
        threshold_idx = 10  # bin containing 50000
        below_density = hist[threshold_idx - 3:threshold_idx].mean()
        above_density = hist[threshold_idx:threshold_idx + 3].mean()

        print(f"\n  {year}: N={len(muni)} municipalities in [30k, 70k]")
        print(f"    Density below 50k (44-50k): {below_density:.1f} per 2k bin")
        print(f"    Density above 50k (50-56k): {above_density:.1f} per 2k bin")
        print(f"    Ratio: {above_density/below_density:.3f}")

        # Bins near threshold
        for i, b in enumerate(bins[:-1]):
            if 40000 <= b <= 60000:
                print(f"      [{b:,}-{bins[i+1]:,}): {hist[i]} municipalities")


def covariate_balance(df):
    """
    Test for balance in pre-treatment covariates at the threshold.
    If there's a pre-existing discontinuity, the RD is invalid.
    """
    print("\n" + "=" * 80)
    print("COVARIATE BALANCE AT THRESHOLD (pre-mandate: 2017-2018)")
    print("=" * 80)

    outcomes = [
        "share_sin_distintivo", "share_cero", "share_eco", "share_c", "share_b"
    ]

    sub = df[df["year"].between(2017, 2018)]
    for outcome in outcomes:
        r = rd_estimate(sub, outcome, 20000, label=f"Balance: {outcome}")
        if r:
            star = "***" if r["rd_pvalue"] < 0.01 else (
                "**" if r["rd_pvalue"] < 0.05 else (
                    "*" if r["rd_pvalue"] < 0.1 else ""))
            print(f"    {outcome:30s}  RD={r['rd_estimate']:+.5f}  "
                  f"SE={r['rd_se']:.5f}  p={r['rd_pvalue']:.3f}{star}")


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 80)
    print("13 — RD: Fleet Composition at the 50k ZBE Threshold")
    print("=" * 80)

    df = load_data()
    print(f"  Loaded: {len(df)} obs, {df['cod_ine'].nunique()} municipalities, "
          f"years {df['year'].min()}-{df['year'].max()}")

    # Density test
    density_test(df)

    # Covariate balance
    covariate_balance(df)

    # Main RD estimates
    results = run_all_rd(df)

    # Year-by-year
    yearly = run_yearly_rd(df)

    # Difference-in-RD
    dird_model = run_did_rd(df)

    # Plots
    plot_rd_scatter(df, "share_sin_distintivo", 25000)
    plot_rd_scatter(df, "share_cero", 25000)
    plot_yearly_rd_coefficients(df)
    plot_rd_multi_outcome(df)

    print("\n" + "=" * 80)
    print("Done.")
    print("=" * 80)


if __name__ == "__main__":
    main()
