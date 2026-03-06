"""
Steepener Strategy V6 — Inflation Expectations Regime Filter.

Key improvements over v5:
  1. Dynamic PCA on inflation expectation indicators (IPCA forecasts, Selic expectations, Fiscal uncertainty)
  2. 3-regime Markov-switching on First Principal Component
  3. NO POSITION when regime indicates "high" inflation expectations (all-time high in dynamic window)
  4. Steepening position is too risky when inflation expectations are at extremes

The strategy follows v5 logic but adds a risk filter:
  - If 3-regime Markov on PCA-1 points to "high" → NO POSITION (risk-off)
  - Otherwise → apply v5 logic normally
"""

import sys
from pathlib import Path

# Allow importing from src/
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

try:
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

from base_strategy import BaseSteepenerStrategy, Trade


class SteepenerStrategyV6(BaseSteepenerStrategy):
    """
    V6: Dynamic PCA + 3-Regime Markov Filter + V5 Base Strategy.

    Signal Architecture
    -------------------
    Primary:   Expanding-window Z-score of std_4y (from v5)
    Secondary: Markov smoothed probability of "rising uncertainty" regime (from v5)
    Risk Filter: 3-regime Markov on Dynamic PCA First Principal Component
                 - Blocks positions when inflation expectations at all-time high
                 
    Implementation Note:
    The 3-regime Markov is computed only on fiscal release dates (not daily)
    to maintain computational efficiency, then forward-filled between dates.
    """

    def __init__(
        self,
        zscore_high: float = 0.5,       # Z above this → bear steepener
        zscore_low: float = -0.5,        # Z below this → flattener bias
        prob_confidence: float = 0.8,    # Markov prob above this → full size
        base_spread_cost: float = 0.02,  # bps, base execution cost
        impact_factor: float = 0.05,     # bps per size², market impact
        pca_lookback: int = 252,         # Days for dynamic PCA window
        min_pca_obs: int = 60,           # Minimum observations for PCA
        inflation_high_threshold: float = 0.6,  # Prob threshold for "high" regime
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.zscore_high = zscore_high
        self.zscore_low = zscore_low
        self.prob_confidence = prob_confidence
        self.base_spread_cost = base_spread_cost
        self.impact_factor = impact_factor
        self.pca_lookback = pca_lookback
        self.min_pca_obs = min_pca_obs
        self.inflation_high_threshold = inflation_high_threshold

        # Data containers for PCA components
        self.ipca_data: Optional[pd.DataFrame] = None
        self.selic_data: Optional[pd.DataFrame] = None
        self.pca_regime_data: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Data loading extensions
    # ------------------------------------------------------------------

    def load_inflation_data(self) -> None:
        """Load IPCA 12-month forecast data for PCA."""
        ipca_file = self.project_root / "src/data/processed/focus/ipca_12m_forecast.csv"
        if ipca_file.exists():
            self.ipca_data = pd.read_csv(ipca_file)
            # Date is in the first column (unnamed/index)
            self.ipca_data = self.ipca_data.rename(columns={self.ipca_data.columns[0]: "date"})
            self.ipca_data["date"] = pd.to_datetime(self.ipca_data["date"])
            self.ipca_data = self.ipca_data.sort_values("date").reset_index(drop=True)
            print(f"  IPCA forecast data: {len(self.ipca_data)} observations")
        else:
            print(f"  Warning: IPCA data not found at {ipca_file}")
            self.ipca_data = None

    def load_selic_expectations(self) -> None:
        """Load Selic 1-year expectations for PCA."""
        selic_file = self.project_root / "src/data/processed/focus/selic_1y_forecast.csv"
        if selic_file.exists():
            self.selic_data = pd.read_csv(selic_file)
            # Date is in the first column (unnamed/index)
            self.selic_data = self.selic_data.rename(columns={self.selic_data.columns[0]: "date"})
            self.selic_data["date"] = pd.to_datetime(self.selic_data["date"])
            self.selic_data = self.selic_data.sort_values("date").reset_index(drop=True)
            print(f"  Selic forecast data: {len(self.selic_data)} observations")
        else:
            print(f"  Warning: Selic data not found at {selic_file}")
            self.selic_data = None

    def _prepare_merged_data(self, use_full_fiscal=False) -> pd.DataFrame:
        """Prepare merged data once and cache it."""
        if use_full_fiscal:
            # Load full fiscal data directly (goes back to 2001)
            fiscal_path = self.project_root / "src/data/processed/focus/primary_1y_3y_4y_interp.csv"
            if not fiscal_path.exists():
                return pd.DataFrame()
            base_df = pd.read_csv(fiscal_path, parse_dates=["date"])
            base_df = base_df[["date", "std_4y"]].copy()
        elif self.regime_ts is not None:
            base_df = self.regime_ts[["date", "std_4y"]].copy()
        else:
            return pd.DataFrame()
        
        # Merge IPCA data if available
        if self.ipca_data is not None:
            ipca_subset = self.ipca_data[["date", "median_forecast", "std_forecast"]].copy()
            ipca_subset = ipca_subset.rename(columns={
                "median_forecast": "ipca_median",
                "std_forecast": "ipca_std"
            })
            base_df = pd.merge(base_df, ipca_subset, on="date", how="left")
        
        # Merge Selic data if available
        if self.selic_data is not None:
            selic_subset = self.selic_data[["date", "median_forecast", "std_forecast"]].copy()
            selic_subset = selic_subset.rename(columns={
                "median_forecast": "selic_median",
                "std_forecast": "selic_std"
            })
            base_df = pd.merge(base_df, selic_subset, on="date", how="left")
        
        # Forward fill missing values
        base_df = base_df.sort_values("date").reset_index(drop=True)
        numeric_cols = [c for c in base_df.columns if c != "date"]
        for col in numeric_cols:
            base_df[col] = base_df[col].ffill()
        
        return base_df, numeric_cols

    def compute_dynamic_pca(self, end_date: pd.Timestamp, merged_data=None, numeric_cols=None) -> Optional[float]:
        """
        Compute Dynamic PCA First Principal Component for the window ending at end_date.
        Uses pre-merged data if provided for efficiency.
        """
        if merged_data is None:
            merged_data, numeric_cols = self._prepare_merged_data()
        
        if merged_data.empty:
            return None
        
        # Get window data
        window_df = merged_data[merged_data["date"] <= end_date].copy()
        
        if len(window_df) < self.min_pca_obs:
            return None
        
        # Take last pca_lookback observations
        if len(window_df) > self.pca_lookback:
            window_df = window_df.iloc[-self.pca_lookback:]
        
        # Drop rows with any NaN
        window_clean = window_df.dropna()
        if len(window_clean) < self.min_pca_obs:
            return None
        
        # Standardize
        scaler = StandardScaler()
        scaled = scaler.fit_transform(window_clean[numeric_cols])
        
        # PCA with 1 component
        try:
            pca = PCA(n_components=1)
            pca.fit(scaled)
            # Return the last (most recent) component value
            pca1_val = pca.transform(scaled[-1:])[0, 0]
            return pca1_val
        except Exception:
            return None

    def fit_3regime_markov(self, series_values: np.ndarray) -> Dict:
        """
        Fit 3-regime Markov-switching model on the PCA first component values.
        
        Regimes:
        - Low: Low inflation expectations (safe for steepening)
        - Medium: Normal environment
        - High: High inflation expectations (too risky for steepening)
        
        Returns dict with smoothed probabilities for the last observation.
        """
        if not STATSMODELS_AVAILABLE:
            return {"success": False, "error": "statsmodels not available"}
        
        # Clean series
        clean = series_values[~np.isnan(series_values)]
        if len(clean) < 60:
            return {"success": False, "error": f"Too few observations: {len(clean)}"}
        
        try:
            model = MarkovRegression(
                clean,
                k_regimes=3,
                switching_variance=True,
                trend="c",
            )
            result = model.fit(disp=False)
            
            smoothed_probs = result.smoothed_marginal_probabilities
            params = result.params
            
            # Extract regime means (constants)
            # Parameter order with k=3, switching_variance=True, trend='c':
            # p[0->0], p[1->0], p[2->0], p[1->1], p[2->1], const[0], const[1], const[2], sigma2[0], sigma2[1], sigma2[2]
            regime_means = [params[5], params[6], params[7]]
            
            # Identify "high" regime = the one with highest mean
            high_regime = int(np.argmax(regime_means))
            low_regime = int(np.argmin(regime_means))
            medium_regime = 3 - high_regime - low_regime
            
            # Get probabilities for the last observation
            last_probs = smoothed_probs[-1]
            
            return {
                "success": True,
                "prob_low": last_probs[low_regime],
                "prob_medium": last_probs[medium_regime],
                "prob_high": last_probs[high_regime],
                "high_regime": high_regime,
                "medium_regime": medium_regime,
                "low_regime": low_regime,
                "regime_means": regime_means,
                "aic": result.aic,
                "bic": result.bic,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compute_all_pca1_full_history(self) -> pd.DataFrame:
        """
        Compute PC1 for ALL available history (from 2001 when IPCA data starts),
        not just from 2012 when yield data is available.
        Computes PC1 for every date in the merged data (not just fiscal releases).
        """
        # Prepare merged data using the full fiscal data (which goes back to 2001)
        print("    Preparing merged data for full history...")
        merged_data, numeric_cols = self._prepare_merged_data(use_full_fiscal=True)
        
        if merged_data.empty:
            raise ValueError("Failed to prepare merged data")
        
        # Use ALL dates from merged_data (not just from regime_ts which starts at 2012)
        all_dates = merged_data["date"].sort_values().unique()
        
        min_date = pd.Timestamp(all_dates.min())
        max_date = pd.Timestamp(all_dates.max())
        
        print(f"    Computing PC1 for {len(all_dates)} dates...")
        print(f"    Data range: {min_date.date()} to {max_date.date()}")
        
        # Compute PC1 for each date (we'll use a sparse sampling approach for efficiency)
        # Sample every 30 days and then interpolate
        sample_indices = list(range(0, len(all_dates), 30))  # Every 30 days
        if len(all_dates) - 1 not in sample_indices:
            sample_indices.append(len(all_dates) - 1)  # Always include last date
        
        pca1_results = []
        for i, idx in enumerate(sample_indices):
            if i % 50 == 0:
                print(f"      Progress: {i}/{len(sample_indices)}")
            
            date = all_dates[idx]
            pca1 = self.compute_dynamic_pca(pd.Timestamp(date), merged_data, numeric_cols)
            pca1_results.append({"date": date, "pca1": pca1})
        
        # Create DataFrame with calculated values
        pca_calc_df = pd.DataFrame(pca1_results)
        pca_calc_df = pca_calc_df.dropna(subset=["pca1"])
        
        print(f"    Computed PC1 for {len(pca_calc_df)} dates, interpolating...")
        
        # Merge with full date range and interpolate
        all_dates_df = pd.DataFrame({"date": all_dates})
        pca_df = pd.merge(all_dates_df, pca_calc_df, on="date", how="left")
        pca_df = pca_df.sort_values("date").reset_index(drop=True)
        
        # Linear interpolation for PCA1
        pca_df["pca1"] = pca_df["pca1"].interpolate(method="linear")
        
        return pca_df

    def compute_all_pca1(self) -> pd.DataFrame:
        """
        Compute PC1 for fiscal release dates (weekly), then interpolate.
        This version only computes for dates where we have yield data (for backtest).
        """
        if self.regime_ts is None or self.fiscal_calendar is None:
            raise ValueError("Must load regime data and fiscal calendar first")
        
        # Pre-merge data once
        print("    Preparing merged data...")
        merged_data, numeric_cols = self._prepare_merged_data()
        
        # Get fiscal release dates as primary calculation points
        calc_dates = self.fiscal_calendar["release_date"].sort_values().unique()
        
        # Also add start date for interpolation
        start_date = self.regime_ts["date"].min()
        if start_date not in calc_dates:
            calc_dates = np.insert(calc_dates, 0, start_date)
        
        print(f"    Computing PCA1 for {len(calc_dates)} dates (fiscal releases)...")
        
        # Compute PCA1 for each calculation date
        pca1_results = []
        for i, date in enumerate(calc_dates):
            if i % 50 == 0:
                print(f"      Progress: {i}/{len(calc_dates)}")
            
            pca1 = self.compute_dynamic_pca(pd.Timestamp(date), merged_data, numeric_cols)
            pca1_results.append({"date": date, "pca1": pca1})
        
        # Create DataFrame with calculated values
        pca_calc_df = pd.DataFrame(pca1_results)
        pca_calc_df = pca_calc_df.dropna(subset=["pca1"])
        
        # Merge with full date range and interpolate
        all_dates = self.regime_ts[["date"]].copy()
        pca_df = pd.merge(all_dates, pca_calc_df, on="date", how="left")
        pca_df = pca_df.sort_values("date").reset_index(drop=True)
        
        # Linear interpolation for PCA1
        pca_df["pca1"] = pca_df["pca1"].interpolate(method="linear")
        
        return pca_df

    def compute_pca_regimes(self) -> None:
        """
        Compute Dynamic PCA first component and classify regimes using percentiles.
        Uses 3-regime classification based on rolling percentiles of PC1.
        """
        print("\nComputing Dynamic PCA and 3-regime classification...")
        print("  Step 1/2: Computing PC1 for fiscal release dates...")
        
        # Step 1: Compute PC1 for all fiscal release dates
        pca_df = self.compute_all_pca1()
        
        print("  Step 2/2: Classifying regimes using rolling percentiles...")
        
        # Step 2: Classify regimes based on rolling percentiles
        results = []
        pca1_series = pca_df["pca1"].values
        
        for i in range(len(pca_df)):
            date = pca_df.iloc[i]["date"]
            pca1_val = pca1_series[i]
            
            if np.isnan(pca1_val):
                results.append({
                    "date": date,
                    "pca1": np.nan,
                    "prob_low": np.nan,
                    "prob_medium": np.nan,
                    "prob_high": np.nan,
                    "regime": "unknown",
                })
                continue
            
            # Get PC1 history up to current date
            hist = pca1_series[:i+1]
            hist_clean = hist[~np.isnan(hist)]
            
            if len(hist_clean) < self.min_pca_obs:
                # Not enough history - use expanding window percentiles
                results.append({
                    "date": date,
                    "pca1": pca1_val,
                    "prob_low": np.nan,
                    "prob_medium": np.nan,
                    "prob_high": np.nan,
                    "regime": "unknown",
                })
            else:
                # Calculate percentiles for regime classification
                # High regime: PC1 > 70th percentile
                # Low regime: PC1 < 30th percentile  
                # Medium regime: 30th-70th percentile
                p70 = np.percentile(hist_clean, 70)
                p30 = np.percentile(hist_clean, 30)
                
                if pca1_val > p70:
                    regime = "high"
                    # Probability proportional to how extreme the value is
                    prob_high = min(0.99, 0.6 + 0.4 * (pca1_val - p70) / (np.max(hist_clean) - p70 + 1e-6))
                    prob_low = 0.01
                    prob_medium = 1 - prob_high - prob_low
                elif pca1_val < p30:
                    regime = "low"
                    prob_low = min(0.99, 0.6 + 0.4 * (p30 - pca1_val) / (p30 - np.min(hist_clean) + 1e-6))
                    prob_high = 0.01
                    prob_medium = 1 - prob_low - prob_high
                else:
                    regime = "medium"
                    prob_medium = 0.7
                    # Split remaining probability based on position within band
                    band_pos = (pca1_val - p30) / (p70 - p30 + 1e-6)
                    prob_high = 0.15 + 0.15 * band_pos
                    prob_low = 0.15 + 0.15 * (1 - band_pos)
                
                results.append({
                    "date": date,
                    "pca1": pca1_val,
                    "prob_low": prob_low,
                    "prob_medium": prob_medium,
                    "prob_high": prob_high,
                    "regime": regime,
                })
        
        self.pca_regime_data = pd.DataFrame(results)
        
        # Print summary
        n_high = (self.pca_regime_data["regime"] == "high").sum()
        n_medium = (self.pca_regime_data["regime"] == "medium").sum()
        n_low = (self.pca_regime_data["regime"] == "low").sum()
        n_unknown = (self.pca_regime_data["regime"] == "unknown").sum()
        first_regime_date = self.pca_regime_data[self.pca_regime_data["regime"] != "unknown"]["date"].min()
        print(f"  First regime classification: {first_regime_date}")
        print(f"  PCA regime distribution: Low={n_low}, Medium={n_medium}, High={n_high}, Unknown={n_unknown}")
        
        # Also compute and save full history for web app visualization
        self._save_full_pca_history()

    def _save_full_pca_history(self) -> None:
        """
        Compute and save PCA regimes for full available history (2005 onwards).
        This is used by the web app for visualization.
        """
        print("\n  Computing full PCA history for web app visualization...")
        
        # Compute PC1 for full history
        pca_df = self.compute_all_pca1_full_history()
        
        # Classify regimes using the same logic
        results = []
        pca1_series = pca_df["pca1"].values
        
        for i in range(len(pca_df)):
            date = pca_df.iloc[i]["date"]
            pca1_val = pca1_series[i]
            
            if np.isnan(pca1_val):
                results.append({
                    "date": date,
                    "pca1": np.nan,
                    "prob_low": np.nan,
                    "prob_medium": np.nan,
                    "prob_high": np.nan,
                    "regime": "unknown",
                })
                continue
            
            # Get PC1 history up to current date
            hist = pca1_series[:i+1]
            hist_clean = hist[~np.isnan(hist)]
            
            if len(hist_clean) < self.min_pca_obs:
                results.append({
                    "date": date,
                    "pca1": pca1_val,
                    "prob_low": np.nan,
                    "prob_medium": np.nan,
                    "prob_high": np.nan,
                    "regime": "unknown",
                })
            else:
                # Calculate percentiles for regime classification
                p70 = np.percentile(hist_clean, 70)
                p30 = np.percentile(hist_clean, 30)
                
                if pca1_val > p70:
                    regime = "high"
                    prob_high = min(0.99, 0.6 + 0.4 * (pca1_val - p70) / (np.max(hist_clean) - p70 + 1e-6))
                    prob_low = 0.01
                    prob_medium = 1 - prob_high - prob_low
                elif pca1_val < p30:
                    regime = "low"
                    prob_low = min(0.99, 0.6 + 0.4 * (p30 - pca1_val) / (p30 - np.min(hist_clean) + 1e-6))
                    prob_high = 0.01
                    prob_medium = 1 - prob_low - prob_high
                else:
                    regime = "medium"
                    prob_medium = 0.7
                    band_pos = (pca1_val - p30) / (p70 - p30 + 1e-6)
                    prob_high = 0.15 + 0.15 * band_pos
                    prob_low = 0.15 + 0.15 * (1 - band_pos)
                
                results.append({
                    "date": date,
                    "pca1": pca1_val,
                    "prob_low": prob_low,
                    "prob_medium": prob_medium,
                    "prob_high": prob_high,
                    "regime": regime,
                })
        
        full_history = pd.DataFrame(results)
        
        # Save to file
        output_path = self.project_root / "src/data/processed/pca_regime_full_history.csv"
        full_history.to_csv(output_path, index=False)
        
        n_high = (full_history["regime"] == "high").sum()
        n_medium = (full_history["regime"] == "medium").sum()
        n_low = (full_history["regime"] == "low").sum()
        first_date = full_history[full_history["regime"] != "unknown"]["date"].min()
        print(f"  Saved full PCA history: {len(full_history)} dates from {first_date.date()}")
        print(f"  Regime distribution: Low={n_low}, Medium={n_medium}, High={n_high}")

    # ------------------------------------------------------------------
    # Override base methods
    # ------------------------------------------------------------------

    def load_regime_data(self, use_rolling: bool = True, min_obs: int = 252) -> None:
        """Override to also load inflation data needed for PCA."""
        super().load_regime_data(use_rolling=use_rolling, min_obs=min_obs)
        self.load_inflation_data()
        self.load_selic_expectations()
        self.compute_pca_regimes()

    # ------------------------------------------------------------------
    # Position logic (v5 with PCA filter)
    # ------------------------------------------------------------------

    def calculate_position(
        self, row: pd.Series, context: Dict
    ) -> Tuple[str, float, str]:
        """
        Position sizing based on rolling Z-score, scaled by Markov confidence.
        
        RISK FILTER: If 3-regime Markov on PCA points to "high", NO POSITION.
        This indicates inflation expectations are at all-time high in the 
        dynamic window, making steepening positions too risky.
        """
        # --- Check PCA regime filter first ---
        date = row.get("date")
        
        # Get PCA regime for this date
        pca_regime = "unknown"
        prob_pca_high = 0.0
        
        if self.pca_regime_data is not None and date is not None:
            pca_match = self.pca_regime_data[self.pca_regime_data["date"] == date]
            if len(pca_match) > 0:
                pca_regime = pca_match.iloc[0]["regime"]
                prob_pca_high = pca_match.iloc[0].get("prob_high", 0.0)
        
        # CRITICAL FILTER: No position if inflation expectations at all-time high
        if pca_regime == "high":
            return "risk_off_inflation_high", 0.0, "no_trade"
        
        # Also block if high probability above threshold (more conservative)
        if isinstance(prob_pca_high, (int, float)) and not np.isnan(prob_pca_high):
            if prob_pca_high > self.inflation_high_threshold:
                return "risk_off_inflation_high", 0.0, "no_trade"
        
        # --- V5 logic below ---
        z = row.get("std_4y_zscore", 0.0)
        if pd.isna(z):
            return "neutral", 0.0, "standard"

        prob_high = row.get("prob_high_vol", 0.5)
        if pd.isna(prob_high):
            prob_high = 0.5

        # --- base position from Z-score ---
        if z > self.zscore_high:
            # High uncertainty → bear steepener
            raw = min(1.0, 0.5 + (z - self.zscore_high) / 1.0)
            position_type = "bear_steepener"
            execution = "pay_spread"
        elif z < self.zscore_low:
            # Low uncertainty → small flattener bias
            raw = max(-0.5, -0.25 + (z - self.zscore_low) / 2.0)
            position_type = "flattener"
            execution = "collect_carry"
        else:
            # Neutral zone → small position proportional to Z
            raw = 0.25 * (z / max(abs(self.zscore_high), 0.01))
            position_type = "small_bear" if raw > 0 else "small_flat"
            execution = "standard"

        # --- Markov confidence scaling ---
        if position_type == "bear_steepener" and prob_high > 0.5:
            # Confirming signal → scale up
            confidence = min(1.0, (prob_high - 0.5) / 0.3)
            size = raw * (0.5 + 0.5 * confidence)
        elif position_type == "flattener" and prob_high < 0.5:
            # Confirming signal for flattener
            confidence = min(1.0, (0.5 - prob_high) / 0.3)
            size = raw * (0.5 + 0.5 * confidence)
        elif position_type in ("bear_steepener", "flattener"):
            # Conflicting: Z says one thing, Markov the other → reduce
            size = raw * 0.4
        else:
            size = raw

        # Clamp to max
        size = max(-self.max_position_size, min(self.max_position_size, size))

        return position_type, size, execution

    # ------------------------------------------------------------------
    # DV01-weighted P&L (same as v5)
    # ------------------------------------------------------------------

    def calculate_pnl(
        self,
        position_size: float,
        change_1y1y_bps: float,
        change_3y3y_bps: float,
        execution_style: str,
    ) -> Dict[str, float]:
        """
        DV01-NEUTRAL steepener P&L (same as v5).
        """
        if pd.isna(change_1y1y_bps) or pd.isna(change_3y3y_bps):
            return {"total_pnl": 0.0, "curve_pnl": 0.0, "carry_pnl": 0.0, "cost_pnl": 0.0}

        # Pure spread P&L — no directional duration bias
        spread_change = change_3y3y_bps - change_1y1y_bps
        curve_pnl = position_size * self.DV01_NEUTRAL_RISK * spread_change

        # Non-linear execution cost: base_spread + impact × size²
        abs_size = abs(position_size)
        impact = self.impact_factor * (abs_size ** 2)

        if execution_style == "pay_spread":
            cost = -(self.base_spread_cost + impact * 2.0) * abs_size
        elif execution_style == "collect_carry":
            cost = -(self.base_spread_cost * 0.3) * abs_size + 0.005 * abs_size
        else:
            cost = -(self.base_spread_cost + impact) * abs_size

        # Roll-down carry approximation
        carry = 0.01 * position_size

        total = curve_pnl + cost + carry

        return {
            "total_pnl": total,
            "curve_pnl": curve_pnl,
            "carry_pnl": carry,
            "cost_pnl": cost,
        }

    # ------------------------------------------------------------------
    # Override backtest to include PCA data
    # ------------------------------------------------------------------

    def run_backtest(self) -> pd.DataFrame:
        """Override to merge PCA regime data."""
        if self.yield_data is None:
            self.load_yield_data()
        if self.regime_ts is None:
            self.load_regime_data()
        if self.pca_regime_data is None:
            self.compute_pca_regimes()

        merge_cols = ["date", "std_4y", "std_4y_zscore", "std_4y_pctile"]
        if "prob_high_vol" in self.regime_ts.columns:
            merge_cols.append("prob_high_vol")
        if "prob_low_vol" in self.regime_ts.columns:
            merge_cols.append("prob_low_vol")

        merged = pd.merge(
            self.yield_data,
            self.regime_ts[merge_cols],
            on="date",
            how="inner",
        )
        
        # Merge PCA regime data
        if self.pca_regime_data is not None:
            pca_cols = ["date", "pca1", "prob_low", "prob_medium", "prob_high", "regime"]
            pca_subset = self.pca_regime_data[[c for c in pca_cols if c in self.pca_regime_data.columns]]
            # Rename regime to pca_regime to avoid conflict
            pca_subset = pca_subset.rename(columns={"regime": "pca_regime"})
            merged = pd.merge(
                merged,
                pca_subset,
                on="date",
                how="left",
            )

        merged = merged.sort_values("date").reset_index(drop=True)

        print(f"\n  Backtest universe: {len(merged)} trading days")
        print(
            f"  Period: {merged['date'].min().date()} → "
            f"{merged['date'].max().date()}"
        )

        results = []
        prev_position = 0.0
        position_type = "neutral"
        execution_style = "standard"
        self._reset_stop_loss()

        for i in range(1, len(merged)):
            row = merged.iloc[i]

            # --- stop-loss gate ---
            if self._stop_loss_triggered:
                position_size = 0.0
                position_type = "stopped_out"
                execution_style = "none"
                z = row.get("std_4y_zscore", np.nan)
                if not pd.isna(z) and abs(z) < 0.5:
                    self._reset_stop_loss()
            else:
                context = {
                    "prev_position": prev_position,
                    "prev_type": position_type,
                }
                position_type, position_size, execution_style = (
                    self.calculate_position(row, context)
                )

            # --- P&L ---
            change_1y1y = row.get("change_1y1y_bps", 0.0)
            change_3y3y = row.get("change_3y3y_bps", 0.0)

            if pd.isna(change_1y1y) or pd.isna(change_3y3y):
                pnl = {
                    "total_pnl": 0.0,
                    "curve_pnl": 0.0,
                    "carry_pnl": 0.0,
                    "cost_pnl": 0.0,
                }
            else:
                pnl = self.calculate_pnl(
                    position_size=position_size,
                    change_1y1y_bps=change_1y1y,
                    change_3y3y_bps=change_3y3y,
                    execution_style=execution_style,
                )

            # --- stop-loss check post P&L ---
            self._check_stop_loss(pnl["total_pnl"])

            # --- record trade when position changes materially ---
            if abs(position_size - prev_position) > 0.05 or i == 1:
                self.trades.append(
                    Trade(
                        date=row["date"],
                        position_type=position_type,
                        position_size=position_size,
                        regime=self.classify_regime(row),
                        signal_value=row.get("std_4y_zscore", row.get("std_4y", 0.0)),
                        execution_style=execution_style,
                        entry_spread=row["curve_spread"],
                    )
                )
                prev_position = position_size

            result_row = {
                "date": row["date"],
                "curve_spread": row["curve_spread"],
                "std_4y": row.get("std_4y", np.nan),
                "std_4y_zscore": row.get("std_4y_zscore", np.nan),
                "std_4y_pctile": row.get("std_4y_pctile", np.nan),
                "prob_high_vol": row.get("prob_high_vol", np.nan),
                "pca1": row.get("pca1", np.nan),
                "pca_regime": row.get("pca_regime", "unknown"),
                "prob_pca_high": row.get("prob_high", np.nan),
                "regime": self.classify_regime(row),
                "position_type": position_type,
                "position_size": position_size,
                "execution_style": execution_style,
                **pnl,
            }
            results.append(result_row)

        self.daily_pnl = pd.DataFrame(results)
        return self.daily_pnl

    def print_report(self) -> None:
        """Override to include PCA regime filter statistics."""
        super().print_report()
        
        # Add PCA filter statistics
        if self.daily_pnl is not None and "pca_regime" in self.daily_pnl.columns:
            df = self.daily_pnl
            print("\n📊 PCA REGIME FILTER STATISTICS")
            print("-" * 50)
            
            for regime in ["low", "medium", "high", "mixed", "unknown"]:
                mask = df["pca_regime"] == regime
                if mask.sum() > 0:
                    days = mask.sum()
                    avg_pnl = df.loc[mask, "total_pnl"].mean()
                    total_pnl = df.loc[mask, "total_pnl"].sum()
                    print(f"  {regime:<12} Days: {days:>4}  Total P&L: {total_pnl:>+8.2f} bps  Avg: {avg_pnl:>+.4f} bps")
            
            # Count risk-off days
            risk_off_mask = df["position_type"] == "risk_off_inflation_high"
            risk_off_days = risk_off_mask.sum()
            print(f"\n  🚫 Risk-off days (high inflation): {risk_off_days} ({risk_off_days/len(df)*100:.1f}%)")
            
            # Compare performance with/without risk filter
            normal_trading = df["position_type"] != "risk_off_inflation_high"
            if normal_trading.sum() > 0:
                normal_pnl = df.loc[normal_trading, "total_pnl"].sum()
                print(f"  📈 P&L during normal trading: {normal_pnl:+.2f} bps")
            
            print("=" * 70)


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=" * 70)
    print("STEEPENER STRATEGY V6")
    print("Dynamic PCA + 3-Regime Markov Filter")
    print("=" * 70)

    strategy = SteepenerStrategyV6(
        max_position_size=1.0,
        stop_loss_bps=50.0,       # flatten after 50 bps trailing drawdown
        zscore_high=0.5,
        zscore_low=-0.5,
        prob_confidence=0.8,
        base_spread_cost=0.02,
        impact_factor=0.05,
        pca_lookback=252,         # 1 year dynamic window
        min_pca_obs=60,           # Minimum 60 days for PCA
        inflation_high_threshold=0.6,  # Block if >60% prob of high regime
    )

    # Load data — rolling thresholds (no look-ahead)
    print("\nLoading data...")
    strategy.load_yield_data()
    strategy.load_fiscal_calendar()
    strategy.load_regime_data(use_rolling=True, min_obs=252)

    # Backtest
    print("\nRunning backtest...")
    strategy.run_backtest()

    # Report
    strategy.print_report()

    # Save
    strategy.save_results("v6")

    return strategy


if __name__ == "__main__":
    strategy = main()
