"""
12b_fiscal_zbe_adoption.py

Does fiscal structure predict ZBE compliance?

Extends the party-politics analysis (script 12) by adding municipal fiscal
variables from Hacienda liquidaciones data. Tests two competing hypotheses:

  H_conditionality: Municipalities more dependent on central/EU transfers
    were MORE likely to comply (had more to lose from fund clawback).

  H_capacity: Municipalities under fiscal stress (high debt, low own revenue)
    were LESS likely to comply (couldn't afford ZBE infrastructure).

Uses pre-mandate (2019-2020 average) fiscal variables to avoid post-treatment
contamination.

Input:
    data/processed/election_fiscal_panel.csv  (from 07b_)
Output:
    output/tables/fiscal_zbe_*.csv
    output/figures/fiscal_zbe_*.png

Usage:
    python spain-zbe/src/analysis/12b_fiscal_zbe_adoption.py
"""

import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
TAB_DIR = os.path.join(BASE_DIR, "output", "tables")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
os.makedirs(TAB_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# Import ZBE status and governing party from script 12
import sys
sys.path.insert(0, os.path.dirname(__file__))
from party_zbe_adoption_data import ZBE_STATUS, GOVERNING_PARTY_2019  # noqa: E402


def load_data():
    """Load election-fiscal panel."""
    path = os.path.join(DATA_DIR, "election_fiscal_panel.csv")
    if not os.path.exists(path):
        # Fall back to election_panel + separate fiscal merge
        print("  election_fiscal_panel.csv not found, trying manual merge...")
        election = pd.read_csv(
            os.path.join(DATA_DIR, "election_panel.csv"),
            dtype={"cod_ine": str, "cod_provincia": str},
        )
        fiscal_path = os.path.join(BASE_DIR, "data", "interim",
                                    "hacienda_fiscal_panel.csv")
        if os.path.exists(fiscal_path):
            fiscal = pd.read_csv(fiscal_path, dtype={"cod_ine": str})
            fiscal["cod_ine"] = fiscal["cod_ine"].str.zfill(5)
            # Average 2019-2020
            baseline = fiscal[fiscal["year"].isin([2019, 2020])].copy()
            fiscal_vars = [c for c in baseline.columns
                          if c not in ["cod_ine", "year", "poblacion_hda"]]
            agg = baseline.groupby("cod_ine")[fiscal_vars].mean().reset_index()
            agg = agg.rename(columns={v: f"fiscal_{v}" for v in fiscal_vars})
            election = election.merge(agg, on="cod_ine", how="left")
        return election

    df = pd.read_csv(path, dtype={"cod_ine": str, "cod_provincia": str})
    df["cod_ine"] = df["cod_ine"].str.zfill(5)
    return df


def build_analysis_df(election):
    """
    Build municipality-level dataset with governing party, ZBE status,
    fiscal variables, and election outcomes. Restricted to >50k municipalities.
    """
    above_50k = election[election["above_50k"] == True]["cod_ine"].unique()
    df = election[(election["cod_ine"].isin(above_50k)) &
                  (election["year"] == 2019)].copy()

    # Governing party
    df["gov_party"] = df["cod_ine"].map(
        lambda x: GOVERNING_PARTY_2019.get(x, (None, None, None))[1]
    )
    df["gov_bloc"] = df["cod_ine"].map(
        lambda x: GOVERNING_PARTY_2019.get(x, (None, None, None))[2]
    )

    # ZBE status
    df["zbe_status"] = df["cod_ine"].map(
        lambda x: ZBE_STATUS.get(x, ("none", 0, "none", ""))[0]
    )
    df["zbe_any"] = df["zbe_status"].isin(["enforced", "nominal"]).astype(int)
    df["zbe_enforced"] = (df["zbe_status"] == "enforced").astype(int)

    df["left"] = (df["gov_bloc"] == "left").astype(int)
    df["log_pop"] = np.log(df["poblacion"])

    return df


# ===================================================================
# ANALYSIS 1: Fiscal predictors of ZBE adoption
# ===================================================================
def fiscal_predicts_zbe(df):
    """
    Logit models: P(ZBE) = f(fiscal variables, party, population).
    """
    print("\n" + "=" * 70)
    print("FISCAL PREDICTORS OF ZBE ADOPTION")
    print("=" * 70)

    # Check fiscal data availability
    fiscal_cols = [c for c in df.columns if c.startswith("fiscal_")]
    if not fiscal_cols:
        print("  No fiscal variables found. Run 07b_merge_fiscal.py first.")
        return

    has_fiscal = df[fiscal_cols[0]].notna().sum()
    print(f"\n  Municipalities >50k: {len(df)}")
    print(f"  With fiscal data: {has_fiscal}")

    sub = df.dropna(subset=["gov_bloc"] + fiscal_cols[:3]).copy()
    print(f"  Complete cases: {len(sub)}")

    if len(sub) < 20:
        print("  Too few complete cases for regression.")
        return

    # ─── Descriptive: fiscal characteristics by ZBE status ───
    print("\n  Fiscal characteristics by ZBE status:")
    print(f"  {'Variable':45s} {'Implemented':>12s} {'Not impl.':>12s} {'Diff':>8s}")
    print("  " + "-" * 80)

    key_vars = [
        ("fiscal_transfer_dependency", "Transfer dependency (ratio)"),
        ("fiscal_debt_burden", "Debt burden (ratio)"),
        ("fiscal_eu_transfer_share", "EU transfer share (ratio)"),
        ("fiscal_own_revenue_share", "Own revenue share (ratio)"),
        ("fiscal_revenue_pc", "Revenue per capita (EUR)"),
        ("fiscal_transfers_pc", "Transfers per capita (EUR)"),
        ("fiscal_debt_service_pc", "Debt service per capita (EUR)"),
        ("fiscal_capital_spending_pc", "Capital spending per capita (EUR)"),
        ("total_eu_funds", "NGEU ZBE funds received (EUR)"),
        ("eu_funds_pc", "NGEU ZBE funds per capita (EUR)"),
    ]

    desc_rows = []
    for var, label in key_vars:
        if var not in sub.columns:
            continue
        impl = sub[sub["zbe_any"] == 1][var]
        noimpl = sub[sub["zbe_any"] == 0][var]
        diff = impl.mean() - noimpl.mean()
        print(f"  {label:45s} {impl.mean():>12.4f} {noimpl.mean():>12.4f} "
              f"{diff:>+8.4f}")
        desc_rows.append({
            "variable": label,
            "implemented_mean": impl.mean(),
            "not_implemented_mean": noimpl.mean(),
            "difference": diff,
        })

    pd.DataFrame(desc_rows).to_csv(
        os.path.join(TAB_DIR, "fiscal_zbe_descriptive.csv"), index=False
    )

    # ─── Logit models ───
    print("\n  Logistic regressions: P(ZBE_any = 1)")

    models = {}

    # Model 1: Baseline (party + population only — same as script 12)
    print("\n  --- Model 1: Party + Population (baseline) ---")
    X1 = sm.add_constant(sub[["left", "log_pop"]])
    m1 = sm.Logit(sub["zbe_any"], X1).fit(disp=0)
    _print_logit(m1, ["left", "log_pop"])
    models["M1_baseline"] = m1

    # Model 2: Add transfer dependency
    print("\n  --- Model 2: + Transfer dependency ---")
    X2 = sm.add_constant(sub[["left", "log_pop", "fiscal_transfer_dependency"]])
    m2 = sm.Logit(sub["zbe_any"], X2).fit(disp=0)
    _print_logit(m2, ["left", "log_pop", "fiscal_transfer_dependency"])
    models["M2_transfers"] = m2

    # Model 3: Add debt burden
    print("\n  --- Model 3: + Debt burden ---")
    X3 = sm.add_constant(sub[["left", "log_pop",
                               "fiscal_transfer_dependency",
                               "fiscal_debt_burden"]])
    m3 = sm.Logit(sub["zbe_any"], X3).fit(disp=0)
    _print_logit(m3, ["left", "log_pop", "fiscal_transfer_dependency",
                       "fiscal_debt_burden"])
    models["M3_debt"] = m3

    # Model 4: EU transfers specifically
    if "fiscal_eu_transfer_share" in sub.columns:
        print("\n  --- Model 4: + EU transfer share ---")
        X4 = sm.add_constant(sub[["left", "log_pop",
                                   "fiscal_transfer_dependency",
                                   "fiscal_eu_transfer_share"]])
        m4 = sm.Logit(sub["zbe_any"], X4).fit(disp=0)
        _print_logit(m4, ["left", "log_pop", "fiscal_transfer_dependency",
                           "fiscal_eu_transfer_share"])
        models["M4_eu"] = m4

    # Model 5: Own revenue share (capacity channel)
    if "fiscal_own_revenue_share" in sub.columns:
        print("\n  --- Model 5: + Own revenue share (capacity) ---")
        X5 = sm.add_constant(sub[["left", "log_pop",
                                   "fiscal_own_revenue_share",
                                   "fiscal_debt_burden"]])
        m5 = sm.Logit(sub["zbe_any"], X5).fit(disp=0)
        _print_logit(m5, ["left", "log_pop", "fiscal_own_revenue_share",
                           "fiscal_debt_burden"])
        models["M5_capacity"] = m5

    # Model 6: EU fund receipt (binary)
    if "total_eu_funds" in sub.columns:
        sub["received_eu_funds"] = (sub["total_eu_funds"] > 0).astype(int)
        print("\n  --- Model 6: + Received NGEU ZBE funds (binary) ---")
        X6 = sm.add_constant(sub[["left", "log_pop", "received_eu_funds"]])
        m6 = sm.Logit(sub["zbe_any"], X6).fit(disp=0)
        _print_logit(m6, ["left", "log_pop", "received_eu_funds"])
        models["M6_eu_funds_binary"] = m6

    # Model 7: EU funds per capita
    if "eu_funds_pc" in sub.columns:
        sub7 = sub.dropna(subset=["eu_funds_pc"]).copy()
        if len(sub7) >= 20:
            print("\n  --- Model 7: + NGEU ZBE funds per capita ---")
            X7 = sm.add_constant(sub7[["left", "log_pop", "eu_funds_pc"]])
            m7 = sm.Logit(sub7["zbe_any"], X7).fit(disp=0)
            _print_logit(m7, ["left", "log_pop", "eu_funds_pc"])
            models["M7_eu_funds_pc"] = m7

    # Model 8: Transfers PC + EU funds PC (both fiscal channels)
    if ("fiscal_transfers_pc" in sub.columns and
            "eu_funds_pc" in sub.columns):
        sub8 = sub.dropna(subset=["fiscal_transfers_pc", "eu_funds_pc"]).copy()
        if len(sub8) >= 20:
            print("\n  --- Model 8: Transfers PC + NGEU funds PC ---")
            X8 = sm.add_constant(sub8[["left", "log_pop",
                                        "fiscal_transfers_pc",
                                        "eu_funds_pc"]])
            m8 = sm.Logit(sub8["zbe_any"], X8).fit(disp=0)
            _print_logit(m8, ["left", "log_pop", "fiscal_transfers_pc",
                               "eu_funds_pc"])
            models["M8_both_fiscal"] = m8

    # ─── Save regression table ───
    _save_regression_table(models, sub)

    return sub


def _print_logit(model, varnames):
    """Print logit coefficients with odds ratios."""
    for var in varnames:
        star = ("***" if model.pvalues[var] < 0.01
                else "**" if model.pvalues[var] < 0.05
                else "*" if model.pvalues[var] < 0.1
                else "")
        print(f"    {var:40s}  coef={model.params[var]:+.3f}  "
              f"SE={model.bse[var]:.3f}  p={model.pvalues[var]:.3f}  "
              f"OR={np.exp(model.params[var]):.2f}{star}")
    print(f"    N={int(model.nobs)}  Pseudo-R2={model.prsquared:.3f}  "
          f"AIC={model.aic:.1f}")


def _save_regression_table(models, data):
    """Save regression results to CSV."""
    rows = []
    for model_name, model in models.items():
        for var in model.params.index:
            rows.append({
                "model": model_name,
                "variable": var,
                "coefficient": model.params[var],
                "std_error": model.bse[var],
                "p_value": model.pvalues[var],
                "odds_ratio": np.exp(model.params[var]),
            })
        rows.append({
            "model": model_name,
            "variable": "_N",
            "coefficient": model.nobs,
        })
        rows.append({
            "model": model_name,
            "variable": "_pseudo_r2",
            "coefficient": model.prsquared,
        })
        rows.append({
            "model": model_name,
            "variable": "_aic",
            "coefficient": model.aic,
        })

    out = pd.DataFrame(rows)
    path = os.path.join(TAB_DIR, "fiscal_zbe_logit_models.csv")
    out.to_csv(path, index=False)
    print(f"\n  Saved: {path}")


# ===================================================================
# ANALYSIS 2: Fiscal conditionality — pre vs post EU clawback
# ===================================================================
def fiscal_conditionality(df):
    """
    Did transfer-dependent municipalities comply faster once fiscal
    conditionality was introduced (mid-2024)?

    This is descriptive — we compare ZBE implementation status at two
    points: May 2023 (pre-conditionality) vs. Jan 2026 (post-conditionality).
    """
    print("\n" + "=" * 70)
    print("FISCAL CONDITIONALITY: TRANSFER DEPENDENCE × COMPLIANCE TIMING")
    print("=" * 70)

    if "fiscal_transfer_dependency" not in df.columns:
        print("  No fiscal data available.")
        return

    sub = df.dropna(subset=["fiscal_transfer_dependency"]).copy()

    # Median split on transfer dependency
    median_td = sub["fiscal_transfer_dependency"].median()
    sub["high_transfer_dep"] = (
        sub["fiscal_transfer_dependency"] > median_td
    ).astype(int)

    print(f"\n  Median transfer dependency: {median_td:.3f}")
    print(f"  High transfer dep (above median): {sub['high_transfer_dep'].sum()}")
    print(f"  Low transfer dep (below median): {(sub['high_transfer_dep']==0).sum()}")

    # Compliance rates by transfer dependency
    print(f"\n  {'Group':35s} {'N':>4s} {'ZBE (any)':>10s} {'Enforced':>10s}")
    print("  " + "-" * 65)

    for label, mask in [
        ("Low transfer dependency", sub["high_transfer_dep"] == 0),
        ("High transfer dependency", sub["high_transfer_dep"] == 1),
    ]:
        group = sub[mask]
        n = len(group)
        any_rate = group["zbe_any"].mean()
        enf_rate = group["zbe_enforced"].mean()
        print(f"  {label:35s} {n:>4} {any_rate:>10.1%} {enf_rate:>10.1%}")

    # By quartile
    sub["td_quartile"] = pd.qcut(
        sub["fiscal_transfer_dependency"], 4, labels=["Q1", "Q2", "Q3", "Q4"]
    )

    print(f"\n  {'Quartile':10s} {'N':>4s} {'Mean TD':>8s} {'ZBE rate':>10s}")
    print("  " + "-" * 40)
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        group = sub[sub["td_quartile"] == q]
        print(f"  {q:10s} {len(group):>4} {group['fiscal_transfer_dependency'].mean():>8.3f} "
              f"{group['zbe_any'].mean():>10.1%}")


# ===================================================================
# PLOTS
# ===================================================================
def plot_fiscal_zbe(df):
    """Scatter plots of fiscal variables vs ZBE adoption."""
    if "fiscal_transfer_dependency" not in df.columns:
        return

    sub = df.dropna(subset=["fiscal_transfer_dependency",
                             "fiscal_debt_burden"]).copy()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    plot_vars = [
        ("fiscal_transfer_dependency", "Transfer dependency\n(transfers / revenue)"),
        ("fiscal_debt_burden", "Debt burden\n(debt service / revenue)"),
        ("fiscal_own_revenue_share", "Own revenue share\n(own taxes / revenue)"),
    ]

    for ax, (var, label) in zip(axes, plot_vars):
        if var not in sub.columns:
            ax.set_visible(False)
            continue

        colors = sub["zbe_any"].map({0: "#cccccc", 1: "#d7191c"})
        ax.scatter(sub[var], sub["log_pop"], c=colors, s=40, alpha=0.6,
                   edgecolor="black", linewidth=0.3)
        ax.set_xlabel(label)
        ax.set_ylabel("log(population)")

        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#d7191c",
                   markersize=8, label="ZBE implemented"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#cccccc",
                   markersize=8, label="No ZBE"),
        ]
        ax.legend(handles=legend_elements, loc="upper left", fontsize=8)

    plt.suptitle("Fiscal characteristics and ZBE adoption (>50k municipalities)",
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fiscal_zbe_scatter.png"),
                dpi=150, bbox_inches="tight")
    print(f"\n  Saved: {os.path.join(FIG_DIR, 'fiscal_zbe_scatter.png')}")
    plt.close()

    # Bar chart: ZBE rate by transfer dependency quartile
    if "fiscal_transfer_dependency" in sub.columns:
        fig, ax = plt.subplots(figsize=(6, 4))

        sub["td_quartile"] = pd.qcut(
            sub["fiscal_transfer_dependency"], 4,
            labels=["Q1\n(low)", "Q2", "Q3", "Q4\n(high)"]
        )
        rates = sub.groupby("td_quartile", observed=True)["zbe_any"].agg(
            ["mean", "count", "sum"]
        )

        bars = ax.bar(range(len(rates)), rates["mean"],
                      color=["#fee5d9", "#fcae91", "#fb6a4a", "#cb181d"],
                      edgecolor="black", linewidth=0.5)

        for i, (_, row) in enumerate(rates.iterrows()):
            ax.text(i, row["mean"] + 0.01,
                    f"{int(row['sum'])}/{int(row['count'])}",
                    ha="center", va="bottom", fontsize=10)

        ax.set_xticks(range(len(rates)))
        ax.set_xticklabels(rates.index)
        ax.set_xlabel("Transfer dependency quartile")
        ax.set_ylabel("ZBE adoption rate")
        ax.set_title("ZBE adoption by fiscal transfer dependency")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.set_ylim(0, min(1, rates["mean"].max() * 1.4 + 0.05))

        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "fiscal_zbe_quartile.png"),
                    dpi=150, bbox_inches="tight")
        print(f"  Saved: {os.path.join(FIG_DIR, 'fiscal_zbe_quartile.png')}")
        plt.close()


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 70)
    print("12b — Fiscal Predictors of ZBE Adoption")
    print("=" * 70)

    election = load_data()
    df = build_analysis_df(election)

    print(f"\n  Municipalities >50k (2019): {len(df)}")

    # Check fiscal coverage
    fiscal_cols = [c for c in df.columns if c.startswith("fiscal_")]
    if fiscal_cols:
        has_fiscal = df[fiscal_cols[0]].notna().sum()
        print(f"  With fiscal data: {has_fiscal}")
    else:
        print("  WARNING: No fiscal variables found.")
        print("  Run the pipeline: 03b → 05c → 07b first.")

    # Run analyses
    fiscal_predicts_zbe(df)
    fiscal_conditionality(df)

    # Plots
    plot_fiscal_zbe(df)

    # Save analysis dataset
    df.to_csv(os.path.join(TAB_DIR, "fiscal_zbe_full.csv"), index=False)
    print(f"\n  Saved: {os.path.join(TAB_DIR, 'fiscal_zbe_full.csv')}")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
