"""
Markov-Switching Regime Analysis on SMOOTHED-DIFFERENCED std_4y.

The raw std_4y level has a structural break (~0.05 → ~0.45+), so we can't
feed it directly.  Raw daily diffs fix stationarity but are too noisy
(std ≈ 0.029 vs mean ≈ 0.00007), causing the Markov model to flip regimes
on every single day ("barcode" pattern).

Solution: use a **20-day rolling mean of daily diffs**.  This captures the
*trend* of fiscal uncertainty change over ~1 month, giving a smooth signal
that the 2-regime model can meaningfully split:
  - Regime "Rising":   positive trend → uncertainty is accelerating
  - Regime "Stable":   near-zero/negative trend → uncertainty flat or falling

Regime transitions now persist for weeks/months, not hours.
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from datetime import datetime
import calendar as cal_module
import os
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_PATH = (
    "/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus/"
    "src/data/processed/focus/primary_1y_3y_4y_interp.csv"
)
CALENDAR_PATH = (
    "/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus/"
    "src/data/processed/calendar/fiscal_release_dates.csv"
)
OUTPUT_DIR = (
    "/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus/"
    "src/data/processed/regime_analysis"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading interpolated fiscal data...")
df = pd.read_csv(DATA_PATH, parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)

# Compute smoothed differences (20-day rolling mean of daily diffs)
SMOOTH_WINDOW = 20
df["std_4y_diff"] = df["std_4y"].diff()
df["std_4y_smooth_diff"] = df["std_4y_diff"].rolling(SMOOTH_WINDOW, min_periods=SMOOTH_WINDOW).mean()

print(f"Data range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Total observations: {len(df)}")
print(f"Std_4y LEVEL range:  {df['std_4y'].min():.4f} → {df['std_4y'].max():.4f}")
print(f"Std_4y daily DIFF:   mean={df['std_4y_diff'].mean():.8f}, std={df['std_4y_diff'].std():.6f}")
print(f"Std_4y {SMOOTH_WINDOW}d smooth:  mean={df['std_4y_smooth_diff'].mean():.8f}, std={df['std_4y_smooth_diff'].std():.6f}")

# Load fiscal release calendar
print("\nLoading fiscal release calendar...")
calendar_df = pd.read_csv(CALENDAR_PATH)
calendar_df["release_date"] = pd.to_datetime(calendar_df["release_date"])
calendar_df = calendar_df.sort_values("release_date").reset_index(drop=True)
print(
    f"Calendar range: {calendar_df['release_date'].min().date()} "
    f"to {calendar_df['release_date'].max().date()}"
)

# Prepare the smoothed series (drop NaN from rolling window)
series = df[["date", "std_4y", "std_4y_smooth_diff"]].copy()
series = series.dropna(subset=["std_4y_smooth_diff"])

print(f"\nSmoothed diff series: {len(series)} observations (after {SMOOTH_WINDOW}d warmup)")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def get_last_day_of_month(year: int, month: int) -> int:
    return cal_module.monthrange(year, month)[1]


# ---------------------------------------------------------------------------
# Markov-Switching on differenced series
# ---------------------------------------------------------------------------
def run_markov_switching(data_values, k_regimes=2):
    """
    Fit a 2-regime Markov-Switching model on the smoothed-differenced std_4y.
    Input should be the 20-day rolling mean of daily diffs.
    """
    clean = pd.Series(data_values).dropna()
    if len(clean) < 30:
        return {"success": False, "error": f"Too few observations: {len(clean)}"}

    try:
        model = MarkovRegression(
            clean.values,
            k_regimes=k_regimes,
            switching_variance=True,
            trend="c",  # switching constant (intercept = regime mean)
        )
        result = model.fit(disp=False)

        smoothed_probs = result.smoothed_marginal_probabilities
        params = result.params

        # Parameter order (with trend='c', switching_variance=True):
        #   p[0->0], p[1->0], const[0], const[1], sigma2[0], sigma2[1]
        regime0_mean = params[2]   # const[0]
        regime1_mean = params[3]   # const[1]
        regime0_var = params[4]    # sigma2[0]
        regime1_var = params[5]    # sigma2[1]

        p00 = params[0]           # persistence of regime 0
        p10 = params[1]           # transition 1→0
        p11 = 1.0 - p10           # persistence of regime 1

        # Identify "rising uncertainty" regime = the one with the higher
        # (more positive) mean.  For differenced data:
        #   positive mean → uncertainty is accelerating
        #   negative/zero mean → uncertainty is stable/declining
        if regime0_mean > regime1_mean:
            high_vol_regime = 0
            low_vol_regime = 1
        else:
            high_vol_regime = 1
            low_vol_regime = 0

        return {
            "success": True,
            "result": result,
            "smoothed_probs": smoothed_probs,
            "high_vol_regime": high_vol_regime,
            "low_vol_regime": low_vol_regime,
            "regime0_mean": regime0_mean,
            "regime1_mean": regime1_mean,
            "regime0_var": regime0_var,
            "regime1_var": regime1_var,
            "p00": p00,
            "p11": p11,
            "aic": result.aic,
            "bic": result.bic,
            "loglik": result.llf,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main analysis loop
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("RUNNING MARKOV-SWITCHING ON DIFFERENCED STD_4Y")
print("=" * 70)

all_results = []

for idx, row in calendar_df.iterrows():
    year = row["report_year"]
    month = row["report_month"]
    release_date = row["release_date"]

    print(
        f"\n[{idx + 1}/{len(calendar_df)}] "
        f"Processing {year}-{month:02d} (release: {release_date.date()})"
    )

    # Check data availability
    data_end_date = series["date"].max()

    if release_date > data_end_date:
        last_day = get_last_day_of_month(year, month)
        ad_hoc_date = pd.Timestamp(f"{year}-{month:02d}-{last_day:02d}")
        if ad_hoc_date > data_end_date:
            print(f"  Beyond data range. Skipping.")
            continue
        release_date = ad_hoc_date
        is_ad_hoc = True
    else:
        is_ad_hoc = False

    # Filter up to release date
    mask = series["date"] <= release_date
    available = series[mask].copy()
    n_obs = len(available)

    print(f"  Data available: {n_obs} observations up to {release_date.date()}")

    if n_obs < 30:
        print(f"  Skipping: insufficient data ({n_obs} < 30)")
        continue

    # Run Markov-switching on SMOOTHED differenced series
    ms_result = run_markov_switching(available["std_4y_smooth_diff"].values)

    if not ms_result["success"]:
        print(f"  Model fitting failed: {ms_result.get('error', 'Unknown')}")
        continue

    # Build results dataframe using the LEVEL data (for downstream use)
    # but with probabilities from the differenced model
    results_df = available[["date", "std_4y"]].copy()

    # Smoothed probs — aligned to the differenced series (same length)
    smoothed = ms_result["smoothed_probs"]
    high_r = ms_result["high_vol_regime"]
    low_r = ms_result["low_vol_regime"]

    results_df["prob_regime_0"] = smoothed[:, 0]
    results_df["prob_regime_1"] = smoothed[:, 1]
    results_df["prob_high_vol"] = smoothed[:, high_r]
    results_df["prob_low_vol"] = smoothed[:, low_r]

    # Metadata
    results_df["model_run_release_date"] = release_date
    results_df["model_n_obs"] = n_obs
    results_df["model_aic"] = ms_result["aic"]
    results_df["model_bic"] = ms_result["bic"]
    results_df["is_ad_hoc_date"] = is_ad_hoc
    results_df["regime_high_mean"] = ms_result[f"regime{high_r}_mean"]
    results_df["regime_low_mean"] = ms_result[f"regime{low_r}_mean"]

    # Save
    date_str = release_date.strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"regime_probs_{date_str}.csv")
    results_df.to_csv(output_file, index=False)

    # Diagnostics
    high_count = (results_df["prob_high_vol"] > 0.5).sum()
    low_count = (results_df["prob_high_vol"] <= 0.5).sum()
    total = len(results_df)

    print(f"  Rising uncertainty regime (Regime {high_r}):")
    print(f"    Mean(Δstd_4y) = {ms_result[f'regime{high_r}_mean']:.6f}")
    print(f"    Var(Δstd_4y)  = {ms_result[f'regime{high_r}_var']:.8f}")
    print(f"  Stable/falling regime (Regime {low_r}):")
    print(f"    Mean(Δstd_4y) = {ms_result[f'regime{low_r}_mean']:.6f}")
    print(f"    Var(Δstd_4y)  = {ms_result[f'regime{low_r}_var']:.8f}")
    print(f"  Persistence: p00={ms_result['p00']:.3f}, p11={ms_result['p11']:.3f}")
    print(f"  Regime split: High={high_count} ({high_count/total:.1%}), "
          f"Low={low_count} ({low_count/total:.1%})")
    print(f"  Saved: regime_probs_{date_str}.csv")
    print(f"  AIC: {ms_result['aic']:.2f}, BIC: {ms_result['bic']:.2f}")

    all_results.append({
        "release_date": release_date,
        "year": year,
        "month": month,
        "n_obs": n_obs,
        "is_ad_hoc": is_ad_hoc,
        "high_vol_regime": high_r,
        "high_mean": ms_result[f"regime{high_r}_mean"],
        "low_mean": ms_result[f"regime{low_r}_mean"],
        "p00": ms_result["p00"],
        "p11": ms_result["p11"],
        "aic": ms_result["aic"],
        "bic": ms_result["bic"],
        "pct_high": high_count / total if total > 0 else 0,
        "file": output_file,
    })


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

summary_df = pd.DataFrame(all_results)
summary_file = os.path.join(OUTPUT_DIR, "analysis_summary.csv")
summary_df.to_csv(summary_file, index=False)

print(f"\nProcessed {len(all_results)} release dates")
print(f"Summary saved to: {summary_file}")

if len(all_results) > 0:
    avg_pct_high = summary_df["pct_high"].mean()
    print(f"\nAverage high-regime fraction: {avg_pct_high:.1%}")
    print(f"  (should be 30–70%, not 99%)")

    print("\nFirst 5 outputs:")
    for r in all_results[:5]:
        print(
            f"  {r['release_date'].strftime('%Y-%m-%d')}: n={r['n_obs']}, "
            f"high={r['pct_high']:.1%}, ad_hoc={r['is_ad_hoc']}"
        )

    print("\nLast 5 outputs:")
    for r in all_results[-5:]:
        print(
            f"  {r['release_date'].strftime('%Y-%m-%d')}: n={r['n_obs']}, "
            f"high={r['pct_high']:.1%}, ad_hoc={r['is_ad_hoc']}"
        )
