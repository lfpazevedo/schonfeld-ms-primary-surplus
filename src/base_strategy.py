"""
Abstract Base Class for Steepener Strategies.

Handles boilerplate data loading, expanding-window regime thresholds,
DV01-weighted P&L, stop-loss, performance analytics, and result persistence.

All versioned strategies inherit from this class and only override
calculate_position() and calculate_pnl().
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """Trade execution record."""
    date: datetime
    position_type: str      # e.g. "bear_steepener", "flattener", "neutral"
    position_size: float     # -1 … +1
    regime: str              # "high_uncertainty" / "medium" / "low"
    signal_value: float      # the z-score or probability that drove the trade
    execution_style: str     # "pay_spread" / "collect_carry" / "standard"
    entry_spread: float      # curve_spread at entry


# ---------------------------------------------------------------------------
# Base strategy
# ---------------------------------------------------------------------------

class BaseSteepenerStrategy(ABC):
    """
    Abstract base for regime-dependent steepener strategies.

    Concrete sub-classes must implement:
      * calculate_position(row, context) -> (type, size, exec_style)
      * calculate_pnl(size, Δ1y1y, Δ3y3y, exec_style) -> dict
    """

    # DV01 per 1bp move per unit notional (BRL DI FRA market).
    # 1y1y forward-starting: ~1 yr modified duration
    # 3y3y forward-starting: ~3 yr modified duration
    DV01_1Y1Y = 0.98
    DV01_3Y3Y = 2.72

    # For a DV01-NEUTRAL steepener, notionals are weighted so that
    #   N_1y × DV01_1y = N_3y × DV01_3y = R  (target risk per leg)
    # Then:  PnL = R × (Δ3y3y − Δ1y1y)  = R × ΔSpread
    # This isolates curve moves and neutralises parallel shifts.
    # Set R = 1.0 so P&L is in "bps per 1 bp DV01 per leg".
    DV01_NEUTRAL_RISK = 1.0

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_position_size: float = 1.0,
        stop_loss_bps: Optional[float] = None,
    ):
        if project_root is None:
            self.project_root = Path(
                "/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus"
            )
        else:
            self.project_root = Path(project_root)

        self.max_position_size = max_position_size
        self.stop_loss_bps = stop_loss_bps

        # Data containers
        self.yield_data: Optional[pd.DataFrame] = None
        self.fiscal_calendar: Optional[pd.DataFrame] = None
        self.regime_ts: Optional[pd.DataFrame] = None
        self.trades: List[Trade] = []
        self.daily_pnl: Optional[pd.DataFrame] = None

        # Stop-loss state
        self._peak_pnl = 0.0
        self._current_pnl = 0.0
        self._stop_loss_triggered = False

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_yield_data(self) -> None:
        """Load FRA yield data and compute spreads / daily changes."""
        fra_file = self.project_root / "src/data/processed/b3/predi_fra_1y1y_3y3y.csv"
        self.yield_data = pd.read_csv(fra_file, parse_dates=["date"])
        self.yield_data = self.yield_data.sort_values("date").reset_index(drop=True)

        # Curve spread (3y3y – 1y1y)
        self.yield_data["curve_spread"] = (
            self.yield_data["3y3y"] - self.yield_data["1y1y"]
        )
        # Daily rate changes per leg (in bps)
        self.yield_data["change_1y1y_bps"] = self.yield_data["1y1y"].diff() * 10_000
        self.yield_data["change_3y3y_bps"] = self.yield_data["3y3y"].diff() * 10_000
        # Legacy field kept for backwards compat with old strategies
        self.yield_data["spread_change_bps"] = (
            self.yield_data["curve_spread"].diff() * 10_000
        )

        print(
            f"  Yield data: {len(self.yield_data)} obs  "
            f"({self.yield_data['date'].min().date()} → "
            f"{self.yield_data['date'].max().date()})"
        )

    def load_fiscal_calendar(self) -> None:
        """Load fiscal release calendar."""
        cal_file = (
            self.project_root
            / "src/data/processed/calendar/fiscal_release_dates.csv"
        )
        self.fiscal_calendar = pd.read_csv(cal_file, parse_dates=["release_date"])
        self.fiscal_calendar = (
            self.fiscal_calendar.sort_values("release_date").reset_index(drop=True)
        )
        print(f"  Fiscal calendar: {len(self.fiscal_calendar)} release dates")

    def load_regime_data(
        self,
        use_rolling: bool = True,
        min_obs: int = 252,
    ) -> None:
        """
        Build a daily regime time-series from per-release Markov probability
        CSV files.

        When *use_rolling* is True (default), percentile thresholds and
        z-scores are computed on an **expanding** window so that every date
        only uses data up to that point.  This avoids the look-ahead bias
        present in v3/v4.

        Parameters
        ----------
        use_rolling : bool
            True  → expanding-window percentiles (no look-ahead)
            False → full-sample percentiles (for comparison / debugging only)
        min_obs : int
            Minimum observations before calculating rolling stats.
        """
        regime_dir = self.project_root / "src/data/processed/regime_analysis"
        cal_file = (
            self.project_root
            / "src/data/processed/calendar/fiscal_release_dates.csv"
        )
        calendar = pd.read_csv(cal_file, parse_dates=["release_date"])

        all_data: list[pd.DataFrame] = []
        for _, row in calendar.iterrows():
            release_date = row["release_date"]
            date_str = release_date.strftime("%Y%m%d")
            regime_file = regime_dir / f"regime_probs_{date_str}.csv"

            if regime_file.exists():
                df = pd.read_csv(regime_file, parse_dates=["date"])
                df["model_release_date"] = release_date
                cols = ["date", "std_4y", "model_release_date"]
                if "prob_high_vol" in df.columns:
                    cols.append("prob_high_vol")
                if "prob_low_vol" in df.columns:
                    cols.append("prob_low_vol")
                all_data.append(df[cols])

        if not all_data:
            raise ValueError("No regime probability files found!")

        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values(["date", "model_release_date"])

        # For each date keep the probabilities from the most recent model
        # run that was available on or after that date.
        combined = combined[combined["model_release_date"] >= combined["date"]]
        combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)

        # ----- rolling / expanding statistics -----
        if use_rolling:
            expanding = combined["std_4y"].expanding(min_periods=min_obs)
            combined["rolling_mean"] = expanding.mean()
            combined["rolling_std"] = expanding.std()

            combined["std_4y_zscore"] = (
                (combined["std_4y"] - combined["rolling_mean"])
                / combined["rolling_std"].replace(0, np.nan)
            )

            # Rolling percentile: rank of current value within the
            # expanding window (0 → 1).
            combined["std_4y_pctile"] = combined["std_4y"].expanding(
                min_periods=min_obs
            ).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1],
                raw=False,
            )
        else:
            # Full-sample (look-ahead) – for debug / comparison only
            combined["std_4y_zscore"] = (
                (combined["std_4y"] - combined["std_4y"].mean())
                / combined["std_4y"].std()
            )
            combined["std_4y_pctile"] = combined["std_4y"].rank(pct=True)

        # Ensure prob columns exist even if the legacy files lack them
        if "prob_high_vol" not in combined.columns:
            combined["prob_high_vol"] = np.nan
        if "prob_low_vol" not in combined.columns:
            combined["prob_low_vol"] = np.nan

        self.regime_ts = combined
        print(f"  Regime time-series: {len(self.regime_ts)} dates")
        n_valid = combined["std_4y_zscore"].notna().sum()
        print(f"  Dates with valid z-score: {n_valid}")

    # ------------------------------------------------------------------
    # Abstract interface – subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def calculate_position(
        self, row: pd.Series, context: Dict
    ) -> Tuple[str, float, str]:
        """
        Return (position_type, position_size, execution_style) for *row*.

        Parameters
        ----------
        row : pd.Series
            Merged row with yield + regime data.
        context : dict
            Previous position info, etc.
        """
        ...

    @abstractmethod
    def calculate_pnl(
        self,
        position_size: float,
        change_1y1y_bps: float,
        change_3y3y_bps: float,
        execution_style: str,
    ) -> Dict[str, float]:
        """
        Return dict with at least 'total_pnl', 'curve_pnl', 'carry_pnl',
        'cost_pnl'.
        """
        ...

    # ------------------------------------------------------------------
    # Stop-loss
    # ------------------------------------------------------------------

    def _check_stop_loss(self, daily_pnl: float) -> bool:
        """Return True if the trailing stop-loss has been breached."""
        if self.stop_loss_bps is None:
            return False

        self._current_pnl += daily_pnl
        if self._current_pnl > self._peak_pnl:
            self._peak_pnl = self._current_pnl

        drawdown = self._peak_pnl - self._current_pnl
        if drawdown >= self.stop_loss_bps:
            self._stop_loss_triggered = True
            return True
        return False

    def _reset_stop_loss(self) -> None:
        self._peak_pnl = 0.0
        self._current_pnl = 0.0
        self._stop_loss_triggered = False

    # ------------------------------------------------------------------
    # Regime classification (for reporting)
    # ------------------------------------------------------------------

    @staticmethod
    def classify_regime(row: pd.Series) -> str:
        """Classify regime from z-score for reporting purposes."""
        z = row.get("std_4y_zscore", np.nan)
        if pd.isna(z):
            return "unknown"
        if z > 0.5:
            return "high_uncertainty"
        if z < -0.5:
            return "low_uncertainty"
        return "medium_uncertainty"

    # ------------------------------------------------------------------
    # Backtest engine
    # ------------------------------------------------------------------

    def run_backtest(self) -> pd.DataFrame:
        """
        Walk-forward backtest.

        Merges yield + regime data and iterates daily, calling the
        sub-class's calculate_position() and calculate_pnl() on each row.
        """
        if self.yield_data is None:
            self.load_yield_data()
        if self.regime_ts is None:
            self.load_regime_data()

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
        ).sort_values("date").reset_index(drop=True)

        print(f"\n  Backtest universe: {len(merged)} trading days")
        print(
            f"  Period: {merged['date'].min().date()} → "
            f"{merged['date'].max().date()}"
        )

        results: list[dict] = []
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

            results.append(
                {
                    "date": row["date"],
                    "curve_spread": row["curve_spread"],
                    "std_4y": row.get("std_4y", np.nan),
                    "std_4y_zscore": row.get("std_4y_zscore", np.nan),
                    "std_4y_pctile": row.get("std_4y_pctile", np.nan),
                    "prob_high_vol": row.get("prob_high_vol", np.nan),
                    "regime": self.classify_regime(row),
                    "position_type": position_type,
                    "position_size": position_size,
                    "execution_style": execution_style,
                    **pnl,
                }
            )

        self.daily_pnl = pd.DataFrame(results)
        return self.daily_pnl

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_performance_report(self) -> Dict:
        """Compute comprehensive performance metrics."""
        if self.daily_pnl is None or len(self.daily_pnl) == 0:
            raise ValueError("No backtest results. Run run_backtest() first.")

        df = self.daily_pnl.copy()
        df["cumulative"] = df["total_pnl"].cumsum()

        total = df["total_pnl"].sum()
        days = len(df)
        years = days / 252

        # Drawdown
        peak = df["cumulative"].expanding().max()
        dd = df["cumulative"] - peak
        max_dd = dd.min()

        # Sharpe
        std = df["total_pnl"].std()
        sharpe = (
            df["total_pnl"].mean() / std * np.sqrt(252) if std > 0 else 0.0
        )

        # Regime attribution
        regime_stats: Dict[str, Dict] = {}
        if "regime" in df.columns:
            for regime in sorted(df["regime"].dropna().unique()):
                mask = df["regime"] == regime
                regime_stats[regime] = {
                    "days": int(mask.sum()),
                    "total_pnl": float(df.loc[mask, "total_pnl"].sum()),
                    "avg_pnl": float(df.loc[mask, "total_pnl"].mean()),
                    "win_rate": float(
                        (df.loc[mask, "total_pnl"] > 0).mean()
                    ),
                }

        # Monthly P&L
        df["month"] = df["date"].dt.to_period("M")
        monthly = df.groupby("month")["total_pnl"].sum()
        best_months = monthly.nlargest(5)
        worst_months = monthly.nsmallest(5)

        return {
            "overall": {
                "total_pnl_bps": total,
                "trading_days": days,
                "years": years,
                "pnl_per_year": total / years if years > 0 else 0,
                "sharpe": sharpe,
                "max_drawdown_bps": max_dd,
                "win_rate": float((df["total_pnl"] > 0).mean()),
                "avg_daily_pnl": float(df["total_pnl"].mean()),
                "std_daily_pnl": float(std),
            },
            "regime_stats": regime_stats,
            "trades": len(self.trades),
            "best_months": best_months.to_dict(),
            "worst_months": worst_months.to_dict(),
        }

    def print_report(self) -> None:
        """Print formatted performance report."""
        report = self.generate_performance_report()
        o = report["overall"]

        print("\n" + "=" * 70)
        print(f"PERFORMANCE REPORT: {self.__class__.__name__}")
        print("=" * 70)

        print("\n📊 OVERALL")
        print("-" * 50)
        print(f"  Total P&L:        {o['total_pnl_bps']:>10.2f} bps")
        print(f"  P&L / Year:       {o['pnl_per_year']:>10.2f} bps")
        print(f"  Sharpe Ratio:     {o['sharpe']:>10.2f}")
        print(f"  Max Drawdown:     {o['max_drawdown_bps']:>10.2f} bps")
        print(f"  Win Rate:         {o['win_rate'] * 100:>9.1f}%")
        print(f"  Trading Days:     {o['trading_days']:>10}")
        print(f"  Trades:           {report['trades']:>10}")

        if report["regime_stats"]:
            print("\n📈 PERFORMANCE BY REGIME")
            print("-" * 50)
            print(
                f"  {'Regime':<22} {'Days':>6} {'Total (bps)':>12} "
                f"{'Avg (bps)':>10} {'Win%':>7}"
            )
            for regime, s in report["regime_stats"].items():
                print(
                    f"  {regime:<22} {s['days']:>6} {s['total_pnl']:>12.1f} "
                    f"{s['avg_pnl']:>10.4f} {s['win_rate'] * 100:>6.1f}%"
                )

        print("\n🏆 BEST MONTHS")
        print("-" * 50)
        for period, pnl in report["best_months"].items():
            print(f"  {period}  {pnl:>+10.2f} bps")

        print("\n💀 WORST MONTHS")
        print("-" * 50)
        for period, pnl in report["worst_months"].items():
            print(f"  {period}  {pnl:>+10.2f} bps")

        print("\n" + "=" * 70)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_results(self, version: str) -> None:
        """Save daily P&L and trades to CSV."""
        out_dir = (
            self.project_root / f"src/data/processed/strategy_results_{version}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        if self.daily_pnl is not None:
            self.daily_pnl.to_csv(out_dir / "daily_pnl.csv", index=False)
            print(f"\n  daily_pnl.csv  → {out_dir}")

        if self.trades:
            trades_df = pd.DataFrame(
                [
                    {
                        "date": t.date,
                        "position_type": t.position_type,
                        "position_size": t.position_size,
                        "regime": t.regime,
                        "signal": t.signal_value,
                        "execution_style": t.execution_style,
                        "entry_spread": t.entry_spread,
                    }
                    for t in self.trades
                ]
            )
            trades_df.to_csv(out_dir / "trades.csv", index=False)
            print(f"  trades.csv     → {out_dir}")
