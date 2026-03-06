"""
Steepener Strategy V5 — Production-Grade Implementation.

Key improvements over v1–v4:
  1. Rolling Z-score signal on std_4y (no look-ahead bias)
  2. Markov probability scaling (using fixed differenced-input model)
  3. Proper DV01-weighted P&L per leg (not spread × flat factor)
  4. Non-linear slippage model  (base + impact × size²)
  5. Trailing stop-loss with regime-normalisation reset
"""

import sys
from pathlib import Path

# Allow importing from src/
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np
from typing import Dict, Tuple

from base_strategy import BaseSteepenerStrategy


class SteepenerStrategyV5(BaseSteepenerStrategy):
    """
    V5: Rolling Z-Score + Markov Enhancement + Proper Risk Management.

    Signal Architecture
    -------------------
    Primary:   Expanding-window Z-score of std_4y
    Secondary: Markov smoothed probability of "rising uncertainty" regime
    Sizing:    Continuous, scaled by signal strength × Markov confidence
    """

    def __init__(
        self,
        zscore_high: float = 0.5,       # Z above this → bear steepener
        zscore_low: float = -0.5,        # Z below this → flattener bias
        prob_confidence: float = 0.8,    # Markov prob above this → full size
        base_spread_cost: float = 0.02,  # bps, base execution cost
        impact_factor: float = 0.05,     # bps per size², market impact
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.zscore_high = zscore_high
        self.zscore_low = zscore_low
        self.prob_confidence = prob_confidence
        self.base_spread_cost = base_spread_cost
        self.impact_factor = impact_factor

    # ------------------------------------------------------------------
    # Position logic
    # ------------------------------------------------------------------

    def calculate_position(
        self, row: pd.Series, context: Dict
    ) -> Tuple[str, float, str]:
        """
        Position sizing based on rolling Z-score, scaled by Markov confidence.

        Z > +0.5  →  Bear steepener  (uncertainty above historical norm)
        Z < −0.5  →  Small flattener (uncertainty below norm)
        |Z| ≤ 0.5 →  Medium / neutral

        The Markov prob of "rising uncertainty" regime amplifies or dampens
        the base size:
          - prob > 0.8 and in steepener  →  full conviction
          - prob < 0.5 but Z says steep   →  reduce (conflicting signals)
        """
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
    # DV01-weighted P&L
    # ------------------------------------------------------------------

    def calculate_pnl(
        self,
        position_size: float,
        change_1y1y_bps: float,
        change_3y3y_bps: float,
        execution_style: str,
    ) -> Dict[str, float]:
        """
        DV01-NEUTRAL steepener P&L.

        We weight notionals so  N_1y × DV01_1y = N_3y × DV01_3y = R.
        This neutralises parallel yield shifts.  P&L becomes:

          curve_pnl = position_size × R × (Δ3y3y − Δ1y1y)
                    = position_size × R × Δ(spread)

        Positive position_size = bear steepener (profit when spread widens).
        Negative position_size = flattener      (profit when spread narrows).
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


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=" * 70)
    print("STEEPENER STRATEGY V5")
    print("=" * 70)

    strategy = SteepenerStrategyV5(
        max_position_size=1.0,
        stop_loss_bps=50.0,       # flatten after 50 bps trailing drawdown
        zscore_high=0.5,
        zscore_low=-0.5,
        prob_confidence=0.8,
        base_spread_cost=0.02,
        impact_factor=0.05,
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
    strategy.save_results("v5")

    return strategy


if __name__ == "__main__":
    strategy = main()
