"""
08_descriptive_validation.py

Descriptive statistics and identification-validity diagnostics for the
Spain ZBE regression discontinuity design.

Produces:
  1. Summary statistics table (fleet + elections)
  2. McCrary (2008) density test at the 50k threshold
  3. Balance / smoothness tests on pre-treatment covariates
  4. Pre-trend validation: RD estimates on pre-mandate years (2017-2020)

Output:
  output/figures/  — density plot, pre-trend event-study, RD scatter plots
  output/tables/   — summary statistics, balance tests

Usage:
    python spain-zbe/src/analysis/08_descriptive_validation.py
"""

import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

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

# RD parameters
THRESHOLD = 50_000
BW_DEFAULT = 20_000  # default bandwidth: 30k-70k

# Plotting defaults
sns.set_style("whitegrid")
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
})


# ===================================================================
# 1. LOAD DATA
# ===================================================================
def load_panels():
    fleet = pd.read_csv(os.path.join(DATA_DIR, "fleet_panel.csv"),
                        dtype={"cod_ine": str, "cod_provincia": str})
    election = pd.read_csv(os.path.join(DATA_DIR, "election_panel.csv"),
                           dtype={"cod_ine": str, "cod_provincia": str})
    print(f"Fleet panel:    {fleet.shape[0]:>7,} rows  |  "
          f"years {fleet['year'].min()}-{fleet['year'].max()}  |  "
          f"{fleet['cod_ine'].nunique()} municipalities")
    print(f"Election panel: {election.shape[0]:>7,} rows  |  "
          f"years {sorted(election['year'].unique())}  |  "
          f"{election['cod_ine'].nunique()} municipalities")
    return fleet, election


# ===================================================================
# 2. SUMMARY STATISTICS
# ===================================================================
def summary_statistics(fleet, election):
    """Produce summary statistics tables."""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    # Fleet panel: latest year with full data
    latest_year = fleet.dropna(subset=["share_sin_distintivo"])["year"].max()
    fl = fleet[fleet["year"] == latest_year].copy()

    fleet_vars = ["poblacion", "total", "share_sin_distintivo", "share_b",
                  "share_c", "share_eco", "share_cero"]

    # Split by treatment status
    above = fl[fl["above_50k"] == True]
    below = fl[fl["above_50k"] == False]

    rows = []
    for v in fleet_vars:
        row = {
            "Variable": v,
            f"Below 50k (N={len(below)})  Mean": below[v].mean(),
            f"Below 50k  SD": below[v].std(),
            f"Above 50k (N={len(above)})  Mean": above[v].mean(),
            f"Above 50k  SD": above[v].std(),
        }
        rows.append(row)

    summ_fleet = pd.DataFrame(rows)
    print(f"\nFleet summary ({latest_year}):")
    print(summ_fleet.to_string(index=False, float_format="%.4f"))

    # Near-threshold subsample (within default bandwidth)
    near = fl[fl["pop_distance_50k"].abs() <= BW_DEFAULT]
    near_above = near[near["above_50k"] == True]
    near_below = near[near["above_50k"] == False]

    rows_near = []
    for v in fleet_vars:
        a = near_above[v].dropna()
        b = near_below[v].dropna()
        tstat, pval = stats.ttest_ind(a, b, equal_var=False) if len(a) > 1 and len(b) > 1 else (np.nan, np.nan)
        rows_near.append({
            "Variable": v,
            f"Below (N={len(near_below)})": f"{b.mean():.4f} ({b.std():.4f})",
            f"Above (N={len(near_above)})": f"{a.mean():.4f} ({a.std():.4f})",
            "Diff p-value": f"{pval:.3f}" if not np.isnan(pval) else "—",
        })

    summ_near = pd.DataFrame(rows_near)
    print(f"\nNear-threshold balance ({THRESHOLD - BW_DEFAULT:,}-{THRESHOLD + BW_DEFAULT:,}):")
    print(summ_near.to_string(index=False))

    # Save tables
    summ_fleet.to_csv(os.path.join(TAB_DIR, "summary_fleet.csv"), index=False)
    summ_near.to_csv(os.path.join(TAB_DIR, "balance_near_threshold.csv"), index=False)

    return summ_fleet, summ_near


# ===================================================================
# 3. McCRARY DENSITY TEST
# ===================================================================
def mccrary_density_test(fleet):
    """
    McCrary (2008) density test: is there bunching at the 50k threshold?

    We use the latest population year and test whether the density of
    municipalities is smooth at the cutoff.
    """
    print("\n" + "=" * 60)
    print("McCRARY DENSITY TEST")
    print("=" * 60)

    # Use one observation per municipality (latest year)
    latest_year = fleet["year"].max()
    cross = fleet[fleet["year"] == latest_year].copy()
    pop = cross["poblacion"].dropna()

    # Focus on municipalities within a reasonable range for visualization
    bw_density = 40_000
    near = pop[(pop >= THRESHOLD - bw_density) & (pop <= THRESHOLD + bw_density)]

    print(f"\nMunicipalities in [{THRESHOLD - bw_density:,}, {THRESHOLD + bw_density:,}]: "
          f"{len(near)}")
    print(f"  Below 50k: {(near < THRESHOLD).sum()}")
    print(f"  Above 50k: {(near >= THRESHOLD).sum()}")

    # Histogram-based visual test
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel A: Histogram
    ax = axes[0]
    bins = np.arange(THRESHOLD - bw_density, THRESHOLD + bw_density + 2000, 2000)
    ax.hist(near, bins=bins, color="steelblue", alpha=0.7, edgecolor="white")
    ax.axvline(THRESHOLD, color="red", linestyle="--", linewidth=1.5, label="50k threshold")
    ax.set_xlabel("Population")
    ax.set_ylabel("Number of municipalities")
    ax.set_title("A. Histogram of Municipal Population")
    ax.legend()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x/1000:.0f}k"))

    # Panel B: Kernel density (separate above/below)
    ax = axes[1]
    below_pop = near[near < THRESHOLD]
    above_pop = near[near >= THRESHOLD]

    if len(below_pop) > 5:
        from scipy.stats import gaussian_kde
        try:
            kde_below = gaussian_kde(below_pop, bw_method=0.3)
            x_below = np.linspace(THRESHOLD - bw_density, THRESHOLD, 200)
            ax.plot(x_below, kde_below(x_below), color="steelblue", linewidth=2,
                    label="Below 50k")
        except Exception:
            pass

    if len(above_pop) > 5:
        try:
            kde_above = gaussian_kde(above_pop, bw_method=0.3)
            x_above = np.linspace(THRESHOLD, THRESHOLD + bw_density, 200)
            ax.plot(x_above, kde_above(x_above), color="coral", linewidth=2,
                    label="Above 50k")
        except Exception:
            pass

    ax.axvline(THRESHOLD, color="red", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Population")
    ax.set_ylabel("Density")
    ax.set_title("B. Kernel Density (Split at Threshold)")
    ax.legend()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x/1000:.0f}k"))

    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "mccrary_density.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {os.path.join(FIG_DIR, 'mccrary_density.png')}")

    # Formal test: compare counts in bins just below vs just above
    # Using a simple binomial test on the bin immediately below/above
    bin_width = 5000
    n_below = ((near >= THRESHOLD - bin_width) & (near < THRESHOLD)).sum()
    n_above = ((near >= THRESHOLD) & (near < THRESHOLD + bin_width)).sum()
    n_total = n_below + n_above
    if n_total > 0:
        binom_p = stats.binomtest(n_below, n_total, 0.5).pvalue
        print(f"\n  Municipalities in [{THRESHOLD - bin_width:,}, {THRESHOLD:,}): {n_below}")
        print(f"  Municipalities in [{THRESHOLD:,}, {THRESHOLD + bin_width:,}): {n_above}")
        print(f"  Binomial test p-value: {binom_p:.4f}")
        if binom_p < 0.05:
            print("  WARNING: Evidence of density discontinuity at the threshold!")
        else:
            print("  No evidence of manipulation (fail to reject smooth density)")


# ===================================================================
# 4. PRE-TREATMENT BALANCE (COVARIATE SMOOTHNESS)
# ===================================================================
def covariate_smoothness(fleet):
    """
    Test whether covariates are smooth at the threshold BEFORE the
    ZBE mandate (2017-2020). Uses local linear regression approach.
    """
    print("\n" + "=" * 60)
    print("COVARIATE SMOOTHNESS (PRE-MANDATE)")
    print("=" * 60)

    pre = fleet[fleet["year"] <= 2020].copy()
    outcomes = ["share_sin_distintivo", "share_b", "share_c",
                "share_eco", "share_cero", "total"]

    # For each outcome, run a simple local linear regression near threshold
    near = pre[pre["pop_distance_50k"].abs() <= BW_DEFAULT].copy()
    near["treat"] = near["above_50k"].astype(int)

    results = []
    for outcome in outcomes:
        sub = near.dropna(subset=[outcome])
        if len(sub) < 20:
            continue

        import statsmodels.api as sm
        X = sm.add_constant(sub[["treat", "pop_distance_50k"]])
        try:
            model = sm.OLS(sub[outcome], X).fit(cov_type="HC1")
            coef = model.params["treat"]
            se = model.bse["treat"]
            pval = model.pvalues["treat"]
            results.append({
                "Outcome": outcome,
                "Coef (above_50k)": f"{coef:.5f}",
                "SE": f"{se:.5f}",
                "p-value": f"{pval:.3f}",
                "N": len(sub),
                "Significant": "*" if pval < 0.05 else "",
            })
            print(f"  {outcome:25s}  coef={coef:+.5f}  SE={se:.5f}  "
                  f"p={pval:.3f} {'***' if pval < 0.01 else '**' if pval < 0.05 else ''}")
        except Exception as e:
            print(f"  {outcome}: error — {e}")

    if results:
        balance_df = pd.DataFrame(results)
        balance_df.to_csv(os.path.join(TAB_DIR, "covariate_smoothness_pre2021.csv"),
                          index=False)
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'covariate_smoothness_pre2021.csv')}")
    return results


# ===================================================================
# 5. PRE-TREND VALIDATION (PLACEBO RD)
# ===================================================================
def pre_trend_event_study(fleet):
    """
    Year-by-year RD estimates on share_sin_distintivo.
    Pre-2021 coefficients should be ~0 (null effect before mandate).
    Post-2021 coefficients capture the treatment effect.
    This is the KEY identification test.
    """
    print("\n" + "=" * 60)
    print("PRE-TREND / EVENT STUDY (Year-by-Year RD)")
    print("=" * 60)

    import statsmodels.api as sm

    outcome = "share_sin_distintivo"
    years = sorted(fleet["year"].unique())

    rd_coefs = []
    for yr in years:
        sub = fleet[(fleet["year"] == yr) &
                    (fleet["pop_distance_50k"].abs() <= BW_DEFAULT)].copy()
        sub = sub.dropna(subset=[outcome])
        if len(sub) < 20:
            continue

        sub["treat"] = sub["above_50k"].astype(int)
        # Local linear with interaction
        sub["dist_x_treat"] = sub["pop_distance_50k"] * sub["treat"]
        X = sm.add_constant(sub[["treat", "pop_distance_50k", "dist_x_treat"]])

        try:
            model = sm.OLS(sub[outcome], X).fit(cov_type="HC1")
            rd_coefs.append({
                "year": yr,
                "coef": model.params["treat"],
                "se": model.bse["treat"],
                "pval": model.pvalues["treat"],
                "ci_low": model.conf_int().loc["treat", 0],
                "ci_high": model.conf_int().loc["treat", 1],
                "n": len(sub),
            })
            star = "***" if model.pvalues["treat"] < 0.01 else \
                   "**" if model.pvalues["treat"] < 0.05 else \
                   "*" if model.pvalues["treat"] < 0.1 else ""
            print(f"  {yr}:  coef={model.params['treat']:+.5f}  "
                  f"SE={model.bse['treat']:.5f}  p={model.pvalues['treat']:.3f} {star}  "
                  f"N={len(sub)}")
        except Exception as e:
            print(f"  {yr}: error — {e}")

    if not rd_coefs:
        print("  No valid RD estimates produced.")
        return

    rd_df = pd.DataFrame(rd_coefs)
    rd_df.to_csv(os.path.join(TAB_DIR, "event_study_rd_coefs.csv"), index=False)

    # Plot event study
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.errorbar(rd_df["year"], rd_df["coef"],
                yerr=[rd_df["coef"] - rd_df["ci_low"],
                      rd_df["ci_high"] - rd_df["coef"]],
                fmt="o-", color="steelblue", capsize=4, linewidth=1.5,
                markersize=7, label="RD coefficient")
    ax.axhline(0, color="grey", linestyle="-", linewidth=0.8)
    ax.axvline(2020.5, color="red", linestyle="--", linewidth=1.5,
               label="ZBE mandate (Ley 7/2021)")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"RD estimate: effect on {outcome}")
    ax.set_title("Event Study: Year-by-Year RD at 50k Threshold\n"
                 "(Pre-2021 = placebo; Post-2021 = treatment effect)")
    ax.set_xticks(rd_df["year"])
    ax.legend(loc="best")
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "event_study_rd.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {os.path.join(FIG_DIR, 'event_study_rd.png')}")

    return rd_df


# ===================================================================
# 6. RD SCATTER PLOTS (VISUAL)
# ===================================================================
def rd_scatter_plots(fleet):
    """
    Classic RD visualizations: binned scatter plots with local polynomial fits.
    """
    print("\n" + "=" * 60)
    print("RD SCATTER PLOTS")
    print("=" * 60)

    outcomes = {
        "share_sin_distintivo": "Share No-Label Vehicles",
        "share_eco": "Share ECO Vehicles",
        "share_cero": "Share Zero-Emission Vehicles",
    }

    # Post-mandate period
    post = fleet[fleet["year"] >= 2022].copy()
    post = post.dropna(subset=["share_sin_distintivo"])
    # Collapse to municipality mean (across post years)
    muni_post = post.groupby("cod_ine").agg({
        "pop_distance_50k": "mean",
        "above_50k": "first",
        "share_sin_distintivo": "mean",
        "share_eco": "mean",
        "share_cero": "mean",
    }).reset_index()

    bw_plot = 30_000
    near = muni_post[muni_post["pop_distance_50k"].abs() <= bw_plot].copy()

    fig, axes = plt.subplots(1, len(outcomes), figsize=(5 * len(outcomes), 5))
    if len(outcomes) == 1:
        axes = [axes]

    for ax, (var, label) in zip(axes, outcomes.items()):
        sub = near.dropna(subset=[var])

        # Create bins
        n_bins = 20
        sub["bin"] = pd.cut(sub["pop_distance_50k"], bins=n_bins)
        binned = sub.groupby("bin", observed=True).agg(
            x=("pop_distance_50k", "mean"),
            y=(var, "mean"),
            n=(var, "count"),
        ).dropna()

        # Scatter of bin means
        ax.scatter(binned["x"], binned["y"], s=binned["n"] * 3 + 10,
                   color="steelblue", alpha=0.7, edgecolors="white", zorder=3)

        # Local polynomial fits (separate each side)
        for side, color in [("below", "steelblue"), ("above", "coral")]:
            mask = sub["pop_distance_50k"] < 0 if side == "below" else sub["pop_distance_50k"] >= 0
            side_data = sub[mask]
            if len(side_data) > 10:
                z = np.polyfit(side_data["pop_distance_50k"], side_data[var], deg=1)
                p = np.poly1d(z)
                x_line = np.linspace(side_data["pop_distance_50k"].min(),
                                     side_data["pop_distance_50k"].max(), 100)
                ax.plot(x_line, p(x_line), color=color, linewidth=2)

        ax.axvline(0, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.set_xlabel("Population - 50,000")
        ax.set_ylabel(label)
        ax.set_title(f"RD Plot: {label}")
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, p: f"{x/1000:+.0f}k"))

    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "rd_scatter_post_mandate.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.join(FIG_DIR, 'rd_scatter_post_mandate.png')}")

    # Also do pre-mandate for comparison
    pre = fleet[fleet["year"] <= 2020].copy()
    pre = pre.dropna(subset=["share_sin_distintivo"])
    muni_pre = pre.groupby("cod_ine").agg({
        "pop_distance_50k": "mean",
        "above_50k": "first",
        "share_sin_distintivo": "mean",
    }).reset_index()
    near_pre = muni_pre[muni_pre["pop_distance_50k"].abs() <= bw_plot]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (data, title) in zip(axes, [(near_pre, "Pre-Mandate (2017-2020)"),
                                         (near.copy(), "Post-Mandate (2022-2024)")]):
        sub = data.dropna(subset=["share_sin_distintivo"])
        n_bins = 20
        sub = sub.copy()
        sub["bin"] = pd.cut(sub["pop_distance_50k"], bins=n_bins)
        binned = sub.groupby("bin", observed=True).agg(
            x=("pop_distance_50k", "mean"),
            y=("share_sin_distintivo", "mean"),
            n=("share_sin_distintivo", "count"),
        ).dropna()

        ax.scatter(binned["x"], binned["y"], s=binned["n"] * 3 + 10,
                   color="steelblue", alpha=0.7, edgecolors="white", zorder=3)

        for side, color in [("below", "steelblue"), ("above", "coral")]:
            mask = sub["pop_distance_50k"] < 0 if side == "below" else sub["pop_distance_50k"] >= 0
            side_data = sub[mask]
            if len(side_data) > 10:
                z = np.polyfit(side_data["pop_distance_50k"],
                               side_data["share_sin_distintivo"], deg=1)
                p = np.poly1d(z)
                x_line = np.linspace(side_data["pop_distance_50k"].min(),
                                     side_data["pop_distance_50k"].max(), 100)
                ax.plot(x_line, p(x_line), color=color, linewidth=2)

        ax.axvline(0, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.set_xlabel("Population - 50,000")
        ax.set_ylabel("Share No-Label Vehicles")
        ax.set_title(title)
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, p: f"{x/1000:+.0f}k"))

    plt.suptitle("RD Plot: Share of No-Label Vehicles\n(Pre vs Post ZBE Mandate)",
                 fontsize=14, y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "rd_scatter_pre_vs_post.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.join(FIG_DIR, 'rd_scatter_pre_vs_post.png')}")


# ===================================================================
# 7. TEMPORAL TRENDS BY TREATMENT STATUS
# ===================================================================
def temporal_trends(fleet):
    """
    Plot average outcome trends for above vs below 50k municipalities.
    Addresses anticipation and timing concerns.
    """
    print("\n" + "=" * 60)
    print("TEMPORAL TRENDS")
    print("=" * 60)

    # Restrict to near-threshold for comparability
    near = fleet[fleet["pop_distance_50k"].abs() <= BW_DEFAULT].copy()
    near = near.dropna(subset=["share_sin_distintivo"])

    trends = near.groupby(["year", "above_50k"]).agg(
        mean_sin=("share_sin_distintivo", "mean"),
        se_sin=("share_sin_distintivo", "sem"),
        mean_eco=("share_eco", "mean"),
        mean_cero=("share_cero", "mean"),
        n=("share_sin_distintivo", "count"),
    ).reset_index()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (var, label) in zip(axes, [
        ("mean_sin", "Share No-Label"),
        ("mean_eco", "Share ECO"),
        ("mean_cero", "Share Zero"),
    ]):
        for treat, color, lbl in [(True, "coral", "Above 50k (obligated)"),
                                   (False, "steelblue", "Below 50k (not obligated)")]:
            d = trends[trends["above_50k"] == treat]
            ax.plot(d["year"], d[var], "o-", color=color, label=lbl, linewidth=1.5)

        ax.axvline(2021, color="grey", linestyle="--", linewidth=1, alpha=0.7,
                   label="Ley 7/2021")
        ax.set_xlabel("Year")
        ax.set_ylabel(label)
        ax.set_title(label)
        if var == "mean_sin":
            ax.legend(fontsize=9)

    plt.suptitle(f"Trends Near Threshold (within {BW_DEFAULT/1000:.0f}k of cutoff)",
                 fontsize=13, y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "temporal_trends.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.join(FIG_DIR, 'temporal_trends.png')}")


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("08 — Descriptive Statistics & Validation Diagnostics")
    print("=" * 70)

    fleet, election = load_panels()

    summary_statistics(fleet, election)
    mccrary_density_test(fleet)
    covariate_smoothness(fleet)
    pre_trend_event_study(fleet)
    rd_scatter_plots(fleet)
    temporal_trends(fleet)

    # Election pre-treatment balance (if 2023 data available)
    election_years = sorted(election["year"].unique())
    if 2023 in election_years:
        print("\n  2023 election data available — election RD analysis feasible")
    else:
        print(f"\n  NOTE: Election panel only has years {election_years}.")
        print("  2023 municipal election data needed for post-treatment voting analysis.")
        print("  Ministry of Interior source currently unavailable (503).")
        print("  When available, re-run pipeline with 2023 data added.")

    print("\n" + "=" * 70)
    print("Done. Outputs in:")
    print(f"  Figures: {FIG_DIR}/")
    print(f"  Tables:  {TAB_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
