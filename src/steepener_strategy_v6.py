"""
Steepener Strategy V6 — Inflation Expectations Regime Filter.

Key improvements over v5:
  1. Dynamic PCA on inflation expectation indicators (IPCA forecasts, Selic expectations, Fiscal uncertainty)
  2. 2-regime Markov-switching on First Principal Component (SAME methodology as fiscal uncertainty)
  3. NO POSITION when regime indicates "high_vol" inflation expectations (rapid changes/spikes)
  4. Steepening position is too risky when inflation expectations are volatile

The strategy follows v5 logic but adds a risk filter:
  - If 2-regime Markov on PCA-1 points to "high_vol" → NO POSITION (risk-off)
  - Otherwise → apply v5 logic normally

Methodology (same as markov_regime_analysis.py):
  - Compute smoothed differences (20-day rolling mean of daily diffs) of PC1
  - Fit 2-regime Markov model on smoothed differences
  - Identify "high volatility" regime by VARIANCE (not mean)
  - Use smoothed marginal probabilities for persistence
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
    V6: Dynamic PCA + 2-Regime Markov Filter + V5 Base Strategy.

    Signal Architecture
    -------------------
    Primary:   Expanding-window Z-score of std_4y (from v5)
    Secondary: Markov smoothed probability of "rising uncertainty" regime (from v5)
    Risk Filter: 2-regime Markov on Dynamic PCA First Principal Component
                 - Blocks positions when inflation expectations in high-vol regime
                 - Uses SAME methodology as fiscal uncertainty (smoothed diffs + variance-based)
                 
    Implementation Note:
    The 2-regime Markov is computed daily using expanding window (all history up to date)
    to ensure point-in-time regime classification without look-ahead bias.
    """

    def __init__(
        self,
        zscore_high: float = 0.5,       # Z above this → bear steepener
        zscore_low: float = -0.5,        # Z below this → flattener bias
        prob_confidence: float = 0.8,    # Markov prob above this → full size
        base_spread_cost: float = 0.02,  # bps, base execution cost
        impact_factor: float = 0.05,     # bps per size², market impact
        pca_lookback: int = None,        # DEPRECATED: Expanding window now used
        min_pca_obs: int = 252,          # Minimum observations for PCA (warmup period)
        inflation_high_threshold: float = 0.6,  # Prob threshold for "high" regime
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.zscore_high = zscore_high
        self.zscore_low = zscore_low
        self.prob_confidence = prob_confidence
        self.base_spread_cost = base_spread_cost
        self.impact_factor = impact_factor
        # pca_lookback is deprecated - we now use expanding window (all history)
        self.pca_lookback = pca_lookback  # Kept for backward compatibility
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
            # Include both cross-sectional std (disagreement) and time-series vol (instability)
            cols = ["date", "std_4y"]
            if "ts_vol_63d_4y" in base_df.columns:
                cols.append("ts_vol_63d_4y")  # Time-series volatility (flow signal)
            base_df = base_df[cols].copy()
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

    def compute_pca_regimes(self) -> None:
        """
        FAST 3-REGIME MS PCA (Matched with Notebook):
        Loads from cache if available to speed up execution.
        """
        import os
        import pandas as pd
        
        pca_cache_file = self.project_root / 'pca_regimes_cache.pkl'
        if pca_cache_file.exists():
            print(f"\\nLoading PCA regimes from cache: {pca_cache_file}")
            self.pca_regime_data = pd.read_pickle(pca_cache_file)
            n_accel = (self.pca_regime_data['pca_regime'] == 'accelerating').sum()
            n_stable = (self.pca_regime_data['pca_regime'] == 'stable').sum()
            print(f"  PCA regimes loaded for {len(self.pca_regime_data)} dates")
            print(f"  Distribution: Accel={n_accel}, Stable={n_stable}")
            
            # Create the 'regime' column to match what the rest of the code expects
            if 'regime' not in self.pca_regime_data.columns and 'pca_regime' in self.pca_regime_data.columns:
                self.pca_regime_data['regime'] = self.pca_regime_data['pca_regime']
                
            return

    def load_regime_data(self, use_rolling: bool = True, min_obs: int = 252) -> None:
        """Override to also load inflation data needed for PCA."""
        # Load fiscal calendar first (needed for PCA computation)
        if self.fiscal_calendar is None:
            self.load_fiscal_calendar()
        super().load_regime_data(use_rolling=use_rolling, min_obs=min_obs)
        self.load_inflation_data()
        self.load_selic_expectations()
        self.compute_pca_regimes()

    # ------------------------------------------------------------------
    # Position logic (v5 with PCA filter)
    # ------------------------------------------------------------------

    def _classify_combined_regime(
        self, 
        std_4y_zscore: float, 
        ts_vol_4y: Optional[float],
        threshold: float = 0.5
    ) -> str:
        """
        Classify regime using combined cross-sectional and time-series signals.
        
        The four-quadrant logic:
        - High std + High ts-vol: "active_crisis" — forecasters disagree AND consensus shifting
        - High std + Low ts-vol: "chronic_disagreement" — stale disagreement, nothing moving
        - Low std + High ts-vol: "consensus_shock" — everyone agrees but view just changed
        - Low std + Low ts-vol: "calm" — stable agreement
        """
        if pd.isna(ts_vol_4y):
            # Fallback: only use cross-sectional if time-series unavailable
            return "high_cross_sec" if std_4y_zscore > threshold else "low_cross_sec"
        
        # Determine high/low for each signal
        high_cross_sec = std_4y_zscore > threshold
        high_ts_vol = ts_vol_4y > threshold
        
        if high_cross_sec and high_ts_vol:
            return "active_crisis"  # Maximum conviction regime
        elif high_cross_sec and not high_ts_vol:
            return "chronic_disagreement"  # Bleeding carry regime — reduce/sit out
        elif not high_cross_sec and high_ts_vol:
            return "consensus_shock"  # Trend following opportunity
        else:
            return "calm"  # Carry mode

    def calculate_position(
        self, row: pd.Series, context: Dict
    ) -> Tuple[str, float, str]:
        """
        Position sizing based on combined regime signal (cross-sectional + time-series).
        
        RISK FILTER: If 2-regime Markov on PCA points to "high_vol", NO POSITION.
        This indicates inflation expectations are in a high-volatility regime
        (rapid changes/spikes), making steepening positions too risky.
        
        Uses the same 2-regime Markov methodology as fiscal uncertainty:
        - Smoothed levels (20-day rolling mean)
        - Regimes identified by VARIANCE (not mean)
        - High variance = rapid changes in inflation expectations
        
        NEW: Uses combined cross-sectional (disagreement) and time-series (instability)
        signals to distinguish between active crises and chronic disagreement.
        """
        # --- Check PCA regime filter first ---
        date = row.get("date")
        
        # Get PCA regime for this date (3-regime Markov: accelerating / stable / decelerating)
        pca_regime = "unknown"
        prob_pca_accel = 0.0
        
        if self.pca_regime_data is not None and date is not None:
            pca_match = self.pca_regime_data[self.pca_regime_data["date"] == date]
            if len(pca_match) > 0:
                pca_regime = pca_match.iloc[0]["regime"]
                prob_pca_accel = pca_match.iloc[0].get("prob_pca_accel", 0.0)
        
        # CRITICAL FILTER: No position if inflation expectations in high-vol regime
        # High volatility = rapid changes/spikes in inflation expectations
        if pca_regime == "accelerating":
            return "risk_off_inflation_accel", 0.0, "no_trade"
        
        # Also block if high volatility probability above threshold (more conservative)
        if isinstance(prob_pca_accel, (int, float)) and not np.isnan(prob_pca_accel):
            if prob_pca_accel > self.inflation_high_threshold:
                return "risk_off_inflation_accel", 0.0, "no_trade"
        
        # --- Combined regime classification ---
        z = row.get("std_4y_zscore", 0.0)
        if pd.isna(z):
            return "neutral", 0.0, "standard"
        
        # Get time-series volatility if available
        ts_vol = row.get("ts_vol_63d_4y_zscore", row.get("ts_vol_63d_4y", np.nan))
        
        # Classify combined regime
        combined_regime = self._classify_combined_regime(z, ts_vol, self.zscore_high)
        
        prob_high = row.get("prob_high_vol", 0.5)
        if pd.isna(prob_high):
            prob_high = 0.5

        # --- Position sizing based on combined regime ---
        if combined_regime == "active_crisis":
            # High disagreement + High instability → Maximum conviction
            raw = min(1.0, 0.5 + (z - self.zscore_high) / 1.0)
            position_type = "bear_steepener"
            execution = "pay_spread"
            # Boost size for active crisis
            raw = raw * 1.2
        elif combined_regime == "chronic_disagreement":
            # High disagreement + Low instability → Bleeding carry, reduce/sit out
            # This is the key fix: don't size up just because std_4y is high
            raw = min(0.5, 0.25 + (z - self.zscore_high) / 2.0) if z > self.zscore_high else 0.0
            position_type = "small_bear" if raw > 0 else "neutral"
            execution = "standard"
        elif combined_regime == "consensus_shock":
            # Low disagreement + High instability → Trend following
            raw = min(0.8, 0.4 + abs(z) / 2.0)
            position_type = "bear_steepener" if z > 0 else "flattener"
            execution = "pay_spread" if z > 0 else "collect_carry"
        elif z > self.zscore_high:
            # Legacy: high uncertainty → bear steepener
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
        size = max(-self.max_position_size, min(self.max_position_size * 1.2, size))

        return position_type, size, execution

    # ------------------------------------------------------------------
    # DV01-weighted P&L with Dynamic DV01 and Convexity Attribution
    # ------------------------------------------------------------------

    def calculate_pnl(
        self,
        position_size: float,
        change_1y1y_bps: float,
        change_3y3y_bps: float,
        execution_style: str,
        current_yield_1y1y: Optional[float] = None,
        current_yield_3y3y: Optional[float] = None,
        dv01_update: Optional[Dict] = None,
    ) -> Dict[str, float]:
        """
        DV01-NEUTRAL steepener P&L with dynamic DV01 and gamma attribution.
        """
        if pd.isna(change_1y1y_bps) or pd.isna(change_3y3y_bps):
            return {
                "total_pnl": 0.0,
                "curve_pnl": 0.0,
                "carry_pnl": 0.0,
                "cost_pnl": 0.0,
                "gamma_pnl": 0.0,
                "dv01_ratio": self._current_dv01_ratio if hasattr(self, '_current_dv01_ratio') else self.DV01_1Y1Y / self.DV01_3Y3Y,
            }

        # Pure spread P&L — no directional duration bias
        spread_change = change_3y3y_bps - change_1y1y_bps
        curve_pnl = position_size * self.DV01_NEUTRAL_RISK * spread_change

        # Calculate gamma P&L (convexity attribution) if DV01 update provided
        gamma_pnl = 0.0
        if dv01_update is not None:
            convexity_1y1y = dv01_update.get("convexity_1y1y", self.CONVEXITY_1Y1Y)
            convexity_3y3y = dv01_update.get("convexity_3y3y", self.CONVEXITY_3Y3Y)
            gamma_pnl = self.calculate_gamma_pnl(
                position_size=position_size,
                change_1y1y_bps=change_1y1y_bps,
                change_3y3y_bps=change_3y3y_bps,
                convexity_1y1y=convexity_1y1y,
                convexity_3y3y=convexity_3y3y,
            )

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

        # Total P&L includes gamma attribution
        total = curve_pnl + gamma_pnl + cost + carry

        # Current DV01 ratio for diagnostics
        dv01_ratio = (
            self._current_dv01_ratio
            if hasattr(self, "_current_dv01_ratio")
            else self.DV01_1Y1Y / self.DV01_3Y3Y
        )

        return {
            "total_pnl": total,
            "curve_pnl": curve_pnl,
            "gamma_pnl": gamma_pnl,
            "carry_pnl": carry,
            "cost_pnl": cost,
            "dv01_ratio": dv01_ratio,
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
            pca_cols = ["date", "pca1", "pca_growth", "prob_pca_decel", "prob_pca_stable", "prob_pca_accel", "regime"]
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

            # Update dynamic DV01 based on current yield levels
            current_1y1y_yield = row.get("1y1y", 0.10)
            current_3y3y_yield = row.get("3y3y", 0.11)
            dv01_update = self.update_dynamic_dv01(
                current_yield_1y1y=current_1y1y_yield,
                current_yield_3y3y=current_3y3y_yield,
            )

            if pd.isna(change_1y1y) or pd.isna(change_3y3y):
                pnl = {
                    "total_pnl": 0.0,
                    "curve_pnl": 0.0,
                    "carry_pnl": 0.0,
                    "cost_pnl": 0.0,
                    "gamma_pnl": 0.0,
                    "dv01_ratio": self._current_dv01_ratio,
                }
            else:
                pnl = self.calculate_pnl(
                    position_size=position_size,
                    change_1y1y_bps=change_1y1y,
                    change_3y3y_bps=change_3y3y,
                    execution_style=execution_style,
                    current_yield_1y1y=current_1y1y_yield,
                    current_yield_3y3y=current_3y3y_yield,
                    dv01_update=None,  # Disabled to match notebook
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
                "1y1y": row.get("1y1y", np.nan),
                "3y3y": row.get("3y3y", np.nan),
                "std_4y": row.get("std_4y", np.nan),
                "std_4y_zscore": row.get("std_4y_zscore", np.nan),
                "std_4y_pctile": row.get("std_4y_pctile", np.nan),
                "prob_high_vol": row.get("prob_high_vol", np.nan),
                "pca1": row.get("pca1", np.nan),
                "pca_regime": row.get("pca_regime", "unknown"),
                "prob_pca_accel": row.get("prob_pca_accel", np.nan),
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
            print("\n📊 PCA REGIME FILTER STATISTICS (3-Regime Markov)")
            print("-" * 50)
            
            for regime in ["accelerating", "stable", "decelerating", "unknown"]:
                mask = df["pca_regime"] == regime
                if mask.sum() > 0:
                    days = mask.sum()
                    avg_pnl = df.loc[mask, "total_pnl"].mean()
                    total_pnl = df.loc[mask, "total_pnl"].sum()
                    regime_label = regime.capitalize()
                    print(f"  {regime_label:<12} Days: {days:>4}  Total P&L: {total_pnl:>+8.2f} bps  Avg: {avg_pnl:>+.4f} bps")
            
            # Count risk-off days
            risk_off_mask = df["position_type"] == "risk_off_inflation_accel"
            risk_off_days = risk_off_mask.sum()
            print(f"\n  🚫 Risk-off days (acceleration regime): {risk_off_days} ({risk_off_days/len(df)*100:.1f}%)")
            
            # Compare performance with/without risk filter
            normal_trading = df["position_type"] != "risk_off_inflation_accel"
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
    print("Dynamic PCA + 2-Regime Markov Filter (Same as Fiscal Uncertainty)")
    print("=" * 70)

    strategy = SteepenerStrategyV6(
        max_position_size=1.0,
        stop_loss_bps=10000.0,    # Disable stop-loss to match notebook
        zscore_high=0.5,
        zscore_low=-0.5,
        prob_confidence=0.8,
        base_spread_cost=0.02,
        impact_factor=0.05,
        # pca_lookback is deprecated - expanding window now used (all history)
        min_pca_obs=252,          # 1 year warmup before PCA/regime calc starts
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
