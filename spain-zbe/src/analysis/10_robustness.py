"""
10_robustness.py

Robustness checks for the Spain ZBE regression discontinuity analysis.

Tests:
  1. Bandwidth sensitivity — RD estimate across multiple bandwidths
  2. Polynomial order sensitivity — linear vs quadratic
  3. Placebo thresholds — run RD at fake cutoffs (20k, 30k, 40k, 60k, 70k, 80k)
  4. Donut-hole RD — exclude municipalities very close to the threshold
  5. Multiple testing corrections (Bonferroni, Benjamini-Hochberg)
  6. Summary greenness index (Anderson 2008 style)

Output:
  output/figures/robustness_*.png
  output/tables/robustness_*.csv

Usage:
    python spain-zbe/src/analysis/10_robustness.py
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

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


def load_fleet():
    return pd.read_csv(os.path.join(DATA_DIR, "fleet_panel.csv"),
                       dtype={"cod_ine": str, "cod_provincia": str})


def run_rd_simple(data, outcome, bandwidth, threshold_dist=0, poly_order=1):
    """
    Run local polynomial RD.
    threshold_dist: shift running variable by this amount (for placebo tests)
    """
    running = data["pop_distance_50k"] - threshold_dist
    sub = data[running.abs() <= bandwidth].copy()
    sub = sub.dropna(subset=[outcome])
    sub["running"] = running.loc[sub.index]
    sub["treat"] = (sub["running"] >= 0).astype(float)

    if len(sub) < 30:
        return None

    # Build regressors
    regressors = ["treat", "running"]
    sub["run_x_treat"] = sub["running"] * sub["treat"]
    regressors.append("run_x_treat")

    if poly_order >= 2:
        sub["running_sq"] = sub["running"] ** 2
        sub["running_sq_x_treat"] = sub["running_sq"] * sub["treat"]
        regressors += ["running_sq", "running_sq_x_treat"]

    X = sm.add_constant(sub[regressors])
    y = sub[outcome]

    try:
        model = sm.OLS(y, X).fit(cov_type="HC1")
        ci = model.conf_int().loc["treat"]
        return {
            "coef": model.params["treat"],
            "se": model.bse["treat"],
            "pval": model.pvalues["treat"],
            "ci_low": ci[0],
            "ci_high": ci[1],
            "n": len(sub),
            "n_above": int(sub["treat"].sum()),
        }
    except Exception:
        return None


def star(pval):
    if pval < 0.01: return "***"
    elif pval < 0.05: return "**"
    elif pval < 0.1: return "*"
    return ""


# ===================================================================
# 1. BANDWIDTH SENSITIVITY
# ===================================================================
def bandwidth_sensitivity(fleet):
    """
    Run the main RD at different bandwidths and plot the coefficient path.
    """
    print("\n" + "=" * 60)
    print("BANDWIDTH SENSITIVITY")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()
    outcome = "share_sin_distintivo"

    bandwidths = [5000, 8000, 10000, 12000, 15000, 18000, 20000,
                  25000, 30000, 35000, 40000]

    results = []
    for bw in bandwidths:
        res = run_rd_simple(post, outcome, bandwidth=bw)
        if res:
            res["bandwidth"] = bw
            results.append(res)
            print(f"  BW={bw/1000:5.0f}k:  coef={res['coef']:+.6f}  "
                  f"SE={res['se']:.6f}  p={res['pval']:.3f}{star(res['pval'])}  "
                  f"N={res['n']}")

    if not results:
        print("  No valid results.")
        return

    df = pd.DataFrame(results)
    df.to_csv(os.path.join(TAB_DIR, "robustness_bandwidth.csv"), index=False)

    # Plot
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.errorbar(df["bandwidth"] / 1000, df["coef"],
                yerr=[df["coef"] - df["ci_low"], df["ci_high"] - df["coef"]],
                fmt="o-", color="steelblue", capsize=4, linewidth=1.5, markersize=6)
    ax.axhline(0, color="grey", linestyle="-", linewidth=0.8)
    ax.axvline(BW_DEFAULT / 1000, color="red", linestyle="--", alpha=0.5,
               label=f"Default BW ({BW_DEFAULT/1000:.0f}k)")
    ax.set_xlabel("Bandwidth (thousands)")
    ax.set_ylabel(f"RD coefficient on {outcome}")
    ax.set_title("Bandwidth Sensitivity: RD Estimate Stability")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "robustness_bandwidth.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {os.path.join(FIG_DIR, 'robustness_bandwidth.png')}")


# ===================================================================
# 2. POLYNOMIAL ORDER SENSITIVITY
# ===================================================================
def polynomial_sensitivity(fleet):
    """Compare linear vs quadratic polynomial fits."""
    print("\n" + "=" * 60)
    print("POLYNOMIAL ORDER SENSITIVITY")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()
    outcome = "share_sin_distintivo"

    for order, label in [(1, "Linear"), (2, "Quadratic")]:
        res = run_rd_simple(post, outcome, bandwidth=BW_DEFAULT, poly_order=order)
        if res:
            print(f"  {label} (p={order}):  coef={res['coef']:+.6f}  "
                  f"SE={res['se']:.6f}  p={res['pval']:.3f}{star(res['pval'])}  "
                  f"N={res['n']}")


# ===================================================================
# 3. PLACEBO THRESHOLDS
# ===================================================================
def placebo_thresholds(fleet):
    """
    Run the RD at fake thresholds where there should be no effect.
    Tests whether we're just picking up a smooth population gradient.
    """
    print("\n" + "=" * 60)
    print("PLACEBO THRESHOLD TESTS")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()
    outcome = "share_sin_distintivo"

    # Placebo cutoffs (in terms of pop_distance_50k)
    # E.g., threshold_dist=-20000 means testing at 30k population
    placebo_thresholds_dist = {
        "20k": -30_000,
        "30k": -20_000,
        "40k": -10_000,
        "50k (TRUE)": 0,
        "60k": 10_000,
        "70k": 20_000,
        "80k": 30_000,
    }

    results = []
    for label, dist in placebo_thresholds_dist.items():
        res = run_rd_simple(post, outcome, bandwidth=BW_DEFAULT,
                            threshold_dist=dist)
        if res:
            res["threshold"] = label
            res["threshold_dist"] = dist
            results.append(res)
            true_marker = " ← TRUE THRESHOLD" if dist == 0 else ""
            print(f"  Threshold={label:>12s}:  coef={res['coef']:+.6f}  "
                  f"p={res['pval']:.3f}{star(res['pval'])}{true_marker}")

    if results:
        df = pd.DataFrame(results)
        df.to_csv(os.path.join(TAB_DIR, "robustness_placebo_thresholds.csv"),
                  index=False)

        # Plot
        fig, ax = plt.subplots(figsize=(9, 5))
        colors = ["coral" if r["threshold_dist"] == 0 else "steelblue"
                  for r in results]
        ax.bar(range(len(results)), [r["coef"] for r in results],
               yerr=[[r["coef"] - r["ci_low"] for r in results],
                     [r["ci_high"] - r["coef"] for r in results]],
               color=colors, alpha=0.7, capsize=4, edgecolor="white")
        ax.set_xticks(range(len(results)))
        ax.set_xticklabels([r["threshold"] for r in results], rotation=45)
        ax.axhline(0, color="grey", linestyle="-", linewidth=0.8)
        ax.set_xlabel("Placebo Threshold")
        ax.set_ylabel(f"RD coefficient on {outcome}")
        ax.set_title("Placebo Threshold Test\n(Only 50k should be significant)")
        plt.tight_layout()
        fig.savefig(os.path.join(FIG_DIR, "robustness_placebo_thresholds.png"),
                    dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"\n  Saved: {os.path.join(FIG_DIR, 'robustness_placebo_thresholds.png')}")


# ===================================================================
# 4. DONUT-HOLE RD
# ===================================================================
def donut_hole(fleet):
    """
    Exclude municipalities very close to the threshold (±2k, ±5k)
    to check if results are driven by precise manipulators.
    """
    print("\n" + "=" * 60)
    print("DONUT-HOLE RD")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()
    outcome = "share_sin_distintivo"

    donut_sizes = [0, 1000, 2000, 3000, 5000]

    results = []
    for donut in donut_sizes:
        sub = post[post["pop_distance_50k"].abs() >= donut].copy()
        res = run_rd_simple(sub, outcome, bandwidth=BW_DEFAULT)
        if res:
            res["donut"] = donut
            results.append(res)
            print(f"  Donut={donut/1000:4.0f}k:  coef={res['coef']:+.6f}  "
                  f"SE={res['se']:.6f}  p={res['pval']:.3f}{star(res['pval'])}  "
                  f"N={res['n']}")

    if results:
        pd.DataFrame(results).to_csv(
            os.path.join(TAB_DIR, "robustness_donut_hole.csv"), index=False)
        print(f"  Saved: {os.path.join(TAB_DIR, 'robustness_donut_hole.csv')}")


# ===================================================================
# 5. MULTIPLE TESTING CORRECTIONS
# ===================================================================
def multiple_testing(fleet):
    """
    Apply Bonferroni and Benjamini-Hochberg corrections to the
    family of fleet outcome tests.
    """
    print("\n" + "=" * 60)
    print("MULTIPLE TESTING CORRECTIONS")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()
    outcomes = ["share_sin_distintivo", "share_b", "share_c",
                "share_eco", "share_cero"]

    pvals = []
    coefs = []
    for outcome in outcomes:
        res = run_rd_simple(post, outcome, bandwidth=BW_DEFAULT)
        if res:
            pvals.append(res["pval"])
            coefs.append(res["coef"])
        else:
            pvals.append(np.nan)
            coefs.append(np.nan)

    valid = [i for i, p in enumerate(pvals) if not np.isnan(p)]
    valid_pvals = [pvals[i] for i in valid]

    if len(valid_pvals) < 2:
        print("  Not enough valid p-values for correction.")
        return

    # Bonferroni
    bonf_reject, bonf_pvals, _, _ = multipletests(valid_pvals, method="bonferroni")
    # Benjamini-Hochberg
    bh_reject, bh_pvals, _, _ = multipletests(valid_pvals, method="fdr_bh")

    print(f"\n  {'Outcome':<25s} {'Coef':>10s} {'Raw p':>8s} "
          f"{'Bonf p':>8s} {'BH p':>8s}")
    print("  " + "-" * 65)

    results = []
    for idx, i in enumerate(valid):
        print(f"  {outcomes[i]:<25s} {coefs[i]:>+10.6f} {pvals[i]:>8.4f} "
              f"{bonf_pvals[idx]:>8.4f} {bh_pvals[idx]:>8.4f}")
        results.append({
            "outcome": outcomes[i],
            "coef": coefs[i],
            "raw_pval": pvals[i],
            "bonferroni_pval": bonf_pvals[idx],
            "benjamini_hochberg_pval": bh_pvals[idx],
            "bonferroni_reject_05": bonf_reject[idx],
            "bh_reject_05": bh_reject[idx],
        })

    pd.DataFrame(results).to_csv(
        os.path.join(TAB_DIR, "robustness_multiple_testing.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'robustness_multiple_testing.csv')}")


# ===================================================================
# 6. GREENNESS SUMMARY INDEX (Anderson 2008)
# ===================================================================
def greenness_index(fleet):
    """
    Construct a summary index of fleet greenness to reduce multiple
    testing concerns. Following Anderson (2008), the index is a
    weighted average of standardized outcomes, where weights are
    the inverse of the covariance matrix.

    Simplified version: equally-weighted z-score index.
    """
    print("\n" + "=" * 60)
    print("GREENNESS SUMMARY INDEX")
    print("=" * 60)

    post = fleet[fleet["year"] >= 2022].copy()

    # Components: higher = greener
    # share_sin_distintivo: REVERSE (higher = dirtier)
    # share_eco, share_cero: higher = greener
    components = {
        "share_sin_distintivo": -1,  # reverse sign
        "share_eco": 1,
        "share_cero": 1,
    }

    sub = post.dropna(subset=list(components.keys())).copy()

    # Standardize each component
    for var, direction in components.items():
        mean = sub[var].mean()
        std = sub[var].std()
        sub[f"z_{var}"] = direction * (sub[var] - mean) / std

    # Equally-weighted index
    z_cols = [f"z_{v}" for v in components]
    sub["greenness_index"] = sub[z_cols].mean(axis=1)

    print(f"  Index components: {list(components.keys())}")
    print(f"  Index mean: {sub['greenness_index'].mean():.4f}  "
          f"SD: {sub['greenness_index'].std():.4f}")

    # Run RD on the index
    res = run_rd_simple(sub, "greenness_index", bandwidth=BW_DEFAULT)
    if res:
        print(f"\n  RD on greenness index:")
        print(f"    coef = {res['coef']:+.6f}")
        print(f"    SE   = {res['se']:.6f}")
        print(f"    p    = {res['pval']:.4f} {star(res['pval'])}")
        print(f"    N    = {res['n']}")

        pd.DataFrame([{
            "outcome": "greenness_index",
            **res,
        }]).to_csv(os.path.join(TAB_DIR, "robustness_greenness_index.csv"),
                   index=False)
        print(f"  Saved: {os.path.join(TAB_DIR, 'robustness_greenness_index.csv')}")


# ===================================================================
# 7. TEMPORAL HETEROGENEITY
# ===================================================================
def temporal_heterogeneity(fleet):
    """
    Test whether the RD effect strengthens over time (2022 vs 2023 vs 2024).
    Addresses the anticipation/enforcement timing concern.
    """
    print("\n" + "=" * 60)
    print("TEMPORAL HETEROGENEITY")
    print("=" * 60)

    outcome = "share_sin_distintivo"

    results = []
    for yr in sorted(fleet["year"].unique()):
        yr_data = fleet[fleet["year"] == yr]
        res = run_rd_simple(yr_data, outcome, bandwidth=BW_DEFAULT)
        if res:
            res["year"] = yr
            results.append(res)
            period = "PRE" if yr < 2021 else "POST"
            print(f"  {yr} ({period}):  coef={res['coef']:+.6f}  "
                  f"p={res['pval']:.3f}{star(res['pval'])}  N={res['n']}")

    if results:
        pd.DataFrame(results).to_csv(
            os.path.join(TAB_DIR, "robustness_temporal_heterogeneity.csv"),
            index=False)
        print(f"\n  Saved: {os.path.join(TAB_DIR, 'robustness_temporal_heterogeneity.csv')}")


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("10 — Robustness Checks")
    print("=" * 70)

    fleet = load_fleet()

    bandwidth_sensitivity(fleet)
    polynomial_sensitivity(fleet)
    placebo_thresholds(fleet)
    donut_hole(fleet)
    multiple_testing(fleet)
    greenness_index(fleet)
    temporal_heterogeneity(fleet)

    print("\n" + "=" * 70)
    print("Done. Outputs in:")
    print(f"  Figures: {FIG_DIR}/")
    print(f"  Tables:  {TAB_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
