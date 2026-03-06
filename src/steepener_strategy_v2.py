"""
Steepener Trading Strategy v2 - Enhanced Implementation

This version:
1. Uses the actual regime probabilities for each trading date
2. Implements position sizing based on regime probability strength
3. Creates proper regime classification using the full probability history
4. Provides more realistic P&L attribution

Strategy Framework (from Fiscal Uncertainty Steepening Strategy):
- HIGH FISCAL UNCERTAINTY (prob_high_vol > threshold):
    "Pay the Spread" execution
    Position: Bear Steepener (long short-end, short long-end)
    Rationale: Fiscal uncertainty drives term premium expansion
    
- LOW FISCAL UNCERTAINTY (prob_low_vol >= threshold):
    "Collect the Carry" execution
    Position: Bull Steepener or Flatten for carry
    Rationale: Stable environment favors roll-down and carry optimization
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class Regime(Enum):
    """Regime classification based on fiscal uncertainty."""
    HIGH_UNCERTAINTY = "high_uncertainty"
    LOW_UNCERTAINTY = "low_uncertainty"


@dataclass
class Trade:
    """Represents a trade execution."""
    date: datetime
    position_type: str  # "bear_steepener", "bull_steepener", "neutral"
    regime: Regime
    prob_high_vol: float
    position_size: float  # 0.0 to 1.0
    execution_style: str  # "pay_spread" or "collect_carry"
    entry_spread: float


class SteepenerStrategyV2:
    """
    Enhanced Steepener Strategy using Markov-Switching Regime Probabilities.
    
    Key Improvements:
    - Uses actual regime probabilities for each date from the model output
    - Position sizing scales with regime confidence
    - Proper handling of holding periods between recalculation dates
    """
    
    def __init__(
        self,
        regime_threshold: float = 0.5,
        high_confidence_threshold: float = 0.8,
        short_tenor: str = "1y1y",
        long_tenor: str = "3y3y",
        notional: float = 1_000_000,  # 1M notional per leg
        transaction_cost_bps: float = 0.5,
    ):
        """
        Initialize strategy.
        
        Args:
            regime_threshold: Threshold for regime classification (0.5 = 50%)
            high_confidence_threshold: Threshold for maximum position sizing
            short_tenor: Short leg tenor
            long_tenor: Long leg tenor
            notional: Notional amount per leg
            transaction_cost_bps: Transaction cost in basis points
        """
        self.regime_threshold = regime_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.short_tenor = short_tenor
        self.long_tenor = long_tenor
        self.notional = notional
        self.transaction_cost_bps = transaction_cost_bps
        
        self.project_root = Path("/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus")
        self.regime_dir = self.project_root / "src/data/processed/regime_analysis"
        
        # Data containers
        self.yield_data: Optional[pd.DataFrame] = None
        self.fiscal_calendar: Optional[pd.DataFrame] = None
        self.regime_ts: Optional[pd.DataFrame] = None  # Time series of regime probs
        self.trades: List[Trade] = []
        self.daily_pnl: Optional[pd.DataFrame] = None
        
    def load_data(self) -> None:
        """Load all required data sources."""
        print("Loading strategy data...")
        
        # Load yield curve data
        fra_file = self.project_root / "src/data/processed/b3/predi_fra_1y1y_3y3y.csv"
        self.yield_data = pd.read_csv(fra_file, parse_dates=['date'])
        self.yield_data = self.yield_data.sort_values('date').reset_index(drop=True)
        print(f"  Yield data: {len(self.yield_data)} obs from {self.yield_data['date'].min().date()} to {self.yield_data['date'].max().date()}")
        
        # Calculate curve spread (steepness measure)
        self.yield_data['curve_spread'] = self.yield_data[self.long_tenor] - self.yield_data[self.short_tenor]
        self.yield_data['spread_change_bps'] = self.yield_data['curve_spread'].diff() * 10000
        
        # Load fiscal calendar
        calendar_file = self.project_root / "src/data/processed/calendar/fiscal_release_dates.csv"
        self.fiscal_calendar = pd.read_csv(calendar_file, parse_dates=['release_date'])
        self.fiscal_calendar = self.fiscal_calendar.sort_values('release_date').reset_index(drop=True)
        
        # Build complete regime time series
        self._build_regime_time_series()
        
    def _build_regime_time_series(self) -> None:
        """
        Build a complete time series of regime probabilities.
        For each date, use the regime probabilities from the most recent model run.
        """
        print("\nBuilding regime time series...")
        
        # Collect all regime probability data
        all_regime_data = []
        
        for _, row in self.fiscal_calendar.iterrows():
            release_date = row['release_date']
            date_str = release_date.strftime('%Y%m%d')
            regime_file = self.regime_dir / f"regime_probs_{date_str}.csv"
            
            if regime_file.exists():
                df = pd.read_csv(regime_file, parse_dates=['date'])
                df['model_release_date'] = release_date
                all_regime_data.append(df[['date', 'prob_high_vol', 'prob_low_vol', 'std_4y', 'model_release_date']])
        
        if not all_regime_data:
            raise ValueError("No regime data found!")
        
        # Combine all data
        combined = pd.concat(all_regime_data, ignore_index=True)
        combined = combined.sort_values(['date', 'model_release_date'])
        
        # For each date, keep only the regime probabilities from the most recent model run
        # (as of that date - model_release_date must be >= date)
        self.regime_ts = combined[combined['model_release_date'] >= combined['date']]
        self.regime_ts = self.regime_ts.drop_duplicates(subset=['date'], keep='last')
        self.regime_ts = self.regime_ts.sort_values('date').reset_index(drop=True)
        
        # Classify regime
        self.regime_ts['regime'] = np.where(
            self.regime_ts['prob_high_vol'] > self.regime_threshold,
            'high_uncertainty',
            'low_uncertainty'
        )
        
        print(f"  Regime time series: {len(self.regime_ts)} dates")
        high_unc_count = (self.regime_ts['regime'] == 'high_uncertainty').sum()
        low_unc_count = (self.regime_ts['regime'] == 'low_uncertainty').sum()
        print(f"    High uncertainty: {high_unc_count} ({high_unc_count/len(self.regime_ts):.1%})")
        print(f"    Low uncertainty: {low_unc_count} ({low_unc_count/len(self.regime_ts):.1%})")
        
        # Show regime probability distribution
        print(f"\n  Prob High Vol statistics:")
        print(self.regime_ts['prob_high_vol'].describe())
        
    def calculate_position_size(self, prob_high_vol: float) -> Tuple[str, float, str]:
        """
        Calculate position size and type based on regime probability.
        
        Returns:
            (position_type, position_size, execution_style)
        """
        if prob_high_vol > self.regime_threshold:
            # High uncertainty regime - "Pay the Spread"
            # Position: Bear Steepener (long short-end, short long-end)
            # We profit when the curve steepens due to long-end sell-off
            regime_strength = min(1.0, (prob_high_vol - self.regime_threshold) / 
                                 (self.high_confidence_threshold - self.regime_threshold))
            position_size = 0.5 + 0.5 * regime_strength  # Scale from 50% to 100%
            return "bear_steepener", position_size, "pay_spread"
        else:
            # Low uncertainty regime - "Collect the Carry"
            # Position: Bull Steepener or neutral for carry optimization
            regime_strength = min(1.0, (self.regime_threshold - prob_high_vol) / 
                                 (self.regime_threshold - 0.0))
            position_size = 0.5 + 0.5 * regime_strength
            return "bull_steepener", position_size, "collect_carry"
    
    def calculate_daily_pnl(
        self,
        spread_change_bps: float,
        position_type: str,
        position_size: float,
        execution_style: str
    ) -> Dict[str, float]:
        """
        Calculate daily P&L in basis points.
        
        P&L Attribution:
        - Curve P&L: From changes in the yield curve spread
        - Carry P&L: From holding the position (positive for collecting, negative for paying)
        - Cost P&L: Transaction costs
        """
        dv01_short = 0.01  # Simplified DV01 for short leg
        dv01_long = 0.03   # Simplified DV01 for long leg (3x duration)
        
        if position_type == "bear_steepener":
            # Long short-end (profit when short yields fall)
            # Short long-end (profit when long yields rise)
            # Overall: profit when spread increases (curve steepens)
            curve_pnl = spread_change_bps * position_size * (dv01_short + dv01_long) * 100
        elif position_type == "bull_steepener":
            # Position for curve steepening via short-end rally
            curve_pnl = -spread_change_bps * position_size * (dv01_short + dv01_long) * 100
        else:  # neutral
            curve_pnl = 0.0
        
        # Carry/cost component
        if execution_style == "pay_spread":
            # Paying the spread costs money (negative carry)
            carry_pnl = -0.1 * position_size  # -0.1 bps per day cost
        else:
            # Collecting carry earns money
            carry_pnl = 0.05 * position_size  # +0.05 bps per day benefit
        
        # Transaction cost (amortized - only charged on rebalance days)
        cost_pnl = 0.0
        
        total_pnl = curve_pnl + carry_pnl + cost_pnl
        
        return {
            'total_pnl': total_pnl,
            'curve_pnl': curve_pnl,
            'carry_pnl': carry_pnl,
            'cost_pnl': cost_pnl,
        }
    
    def run_backtest(self) -> pd.DataFrame:
        """Run the complete backtest."""
        print("\n" + "="*70)
        print("RUNNING STEEPENER STRATEGY BACKTEST v2")
        print("="*70)
        
        # Merge yield data with regime data
        merged = pd.merge(
            self.yield_data,
            self.regime_ts[['date', 'prob_high_vol', 'prob_low_vol', 'std_4y', 'regime']],
            on='date',
            how='inner'
        )
        merged = merged.sort_values('date').reset_index(drop=True)
        
        print(f"\nMerged dataset: {len(merged)} trading days")
        
        daily_results = []
        
        for i in range(1, len(merged)):
            row = merged.iloc[i]
            prev_row = merged.iloc[i-1]
            
            date = row['date']
            prob_high_vol = row['prob_high_vol']
            spread_change_bps = row['spread_change_bps']
            
            # Determine position
            position_type, position_size, execution_style = self.calculate_position_size(prob_high_vol)
            
            # Calculate P&L
            pnl = self.calculate_daily_pnl(
                spread_change_bps,
                position_type,
                position_size,
                execution_style
            )
            
            # Record trade on first day or regime change
            if i == 1 or merged.iloc[i-1]['regime'] != row['regime']:
                trade = Trade(
                    date=date,
                    position_type=position_type,
                    regime=Regime.HIGH_UNCERTAINTY if row['regime'] == 'high_uncertainty' else Regime.LOW_UNCERTAINTY,
                    prob_high_vol=prob_high_vol,
                    position_size=position_size,
                    execution_style=execution_style,
                    entry_spread=row['curve_spread'],
                )
                self.trades.append(trade)
            
            daily_results.append({
                'date': date,
                'curve_spread': row['curve_spread'],
                'spread_change_bps': spread_change_bps,
                'prob_high_vol': prob_high_vol,
                'prob_low_vol': row['prob_low_vol'],
                'std_4y': row['std_4y'],
                'regime': row['regime'],
                'position_type': position_type,
                'position_size': position_size,
                'execution_style': execution_style,
                'daily_pnl': pnl['total_pnl'],
                'curve_pnl': pnl['curve_pnl'],
                'carry_pnl': pnl['carry_pnl'],
            })
        
        self.daily_pnl = pd.DataFrame(daily_results)
        
        # Print trade summary
        print(f"\n{'='*70}")
        print("TRADE SUMMARY")
        print(f"{'='*70}")
        for i, trade in enumerate(self.trades[:10], 1):
            print(f"{i}. {trade.date.date()} | {trade.position_type.upper()} | "
                  f"Regime: {trade.regime.value} | Size: {trade.position_size:.0%} | "
                  f"Prob HighVol: {trade.prob_high_vol:.1%}")
        if len(self.trades) > 10:
            print(f"... and {len(self.trades)-10} more trades")
        
        return self.daily_pnl
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if self.daily_pnl is None or len(self.daily_pnl) == 0:
            raise ValueError("No backtest results available")
        
        df = self.daily_pnl.copy()
        
        # Calculate cumulative metrics
        df['cumulative_pnl'] = df['daily_pnl'].cumsum()
        
        # Overall metrics
        total_pnl = df['daily_pnl'].sum()
        total_days = len(df)
        years = total_days / 252
        
        # Regime-specific
        high_mask = df['regime'] == 'high_uncertainty'
        low_mask = df['regime'] == 'low_uncertainty'
        
        # Calculate max drawdown
        running_max = df['cumulative_pnl'].expanding().max()
        drawdown = df['cumulative_pnl'] - running_max
        max_drawdown = drawdown.min()
        
        report = {
            'overall': {
                'total_pnl_bps': total_pnl,
                'total_pnl_per_year_bps': total_pnl / years if years > 0 else 0,
                'trading_days': total_days,
                'years': years,
                'avg_daily_pnl_bps': df['daily_pnl'].mean(),
                'pnl_volatility_bps': df['daily_pnl'].std(),
                'sharpe_ratio': df['daily_pnl'].mean() / df['daily_pnl'].std() * np.sqrt(252) if df['daily_pnl'].std() > 0 else 0,
                'max_drawdown_bps': max_drawdown,
                'win_rate': (df['daily_pnl'] > 0).mean(),
            },
            'high_uncertainty': {
                'total_pnl_bps': df.loc[high_mask, 'daily_pnl'].sum(),
                'days': high_mask.sum(),
                'avg_daily_pnl_bps': df.loc[high_mask, 'daily_pnl'].mean() if high_mask.sum() > 0 else 0,
                'win_rate': (df.loc[high_mask, 'daily_pnl'] > 0).mean() if high_mask.sum() > 0 else 0,
                'curve_pnl_bps': df.loc[high_mask, 'curve_pnl'].sum(),
                'carry_pnl_bps': df.loc[high_mask, 'carry_pnl'].sum(),
            },
            'low_uncertainty': {
                'total_pnl_bps': df.loc[low_mask, 'daily_pnl'].sum(),
                'days': low_mask.sum(),
                'avg_daily_pnl_bps': df.loc[low_mask, 'daily_pnl'].mean() if low_mask.sum() > 0 else 0,
                'win_rate': (df.loc[low_mask, 'daily_pnl'] > 0).mean() if low_mask.sum() > 0 else 0,
                'curve_pnl_bps': df.loc[low_mask, 'curve_pnl'].sum(),
                'carry_pnl_bps': df.loc[low_mask, 'carry_pnl'].sum(),
            },
            'trades': len(self.trades),
        }
        
        return report
    
    def print_report(self) -> None:
        """Print formatted performance report."""
        report = self.generate_performance_report()
        
        print("\n" + "="*70)
        print("STEEPENER STRATEGY PERFORMANCE REPORT v2")
        print("="*70)
        
        print("\n📊 OVERALL PERFORMANCE")
        print("-" * 50)
        print(f"Total P&L:          {report['overall']['total_pnl_bps']:>12.2f} bps")
        print(f"P&L per Year:       {report['overall']['total_pnl_per_year_bps']:>12.2f} bps")
        print(f"Trading Days:       {report['overall']['trading_days']:>12}")
        print(f"Avg Daily P&L:      {report['overall']['avg_daily_pnl_bps']:>12.4f} bps")
        print(f"P&L Volatility:     {report['overall']['pnl_volatility_bps']:>12.4f} bps")
        print(f"Sharpe Ratio:       {report['overall']['sharpe_ratio']:>12.2f}")
        print(f"Max Drawdown:       {report['overall']['max_drawdown_bps']:>12.2f} bps")
        print(f"Win Rate:           {report['overall']['win_rate']*100:>11.1f}%")
        
        print("\n🔴 HIGH UNCERTAINTY REGIME (Pay the Spread)")
        print("-" * 50)
        print(f"Total P&L:          {report['high_uncertainty']['total_pnl_bps']:>12.2f} bps")
        print(f"Days:               {report['high_uncertainty']['days']:>12}")
        print(f"Avg Daily P&L:      {report['high_uncertainty']['avg_daily_pnl_bps']:>12.4f} bps")
        print(f"Win Rate:           {report['high_uncertainty']['win_rate']*100:>11.1f}%")
        print(f"  Curve P&L:        {report['high_uncertainty']['curve_pnl_bps']:>12.2f} bps")
        print(f"  Carry P&L:        {report['high_uncertainty']['carry_pnl_bps']:>12.2f} bps")
        
        print("\n🟢 LOW UNCERTAINTY REGIME (Collect the Carry)")
        print("-" * 50)
        print(f"Total P&L:          {report['low_uncertainty']['total_pnl_bps']:>12.2f} bps")
        print(f"Days:               {report['low_uncertainty']['days']:>12}")
        print(f"Avg Daily P&L:      {report['low_uncertainty']['avg_daily_pnl_bps']:>12.4f} bps")
        print(f"Win Rate:           {report['low_uncertainty']['win_rate']*100:>11.1f}%")
        print(f"  Curve P&L:        {report['low_uncertainty']['curve_pnl_bps']:>12.2f} bps")
        print(f"  Carry P&L:        {report['low_uncertainty']['carry_pnl_bps']:>12.2f} bps")
        
        print("\n📈 TRADE SUMMARY")
        print("-" * 50)
        print(f"Total Trades:       {report['trades']:>12}")
        
        print("\n" + "="*70)
    
    def save_results(self, output_dir: Optional[str] = None) -> None:
        """Save backtest results to CSV files."""
        if output_dir is None:
            output_dir = self.project_root / "src/data/processed/strategy_results_v2"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.daily_pnl is not None:
            self.daily_pnl.to_csv(output_dir / "daily_pnl.csv", index=False)
            print(f"\nSaved daily P&L to: {output_dir / 'daily_pnl.csv'}")
        
        if self.trades:
            trades_df = pd.DataFrame([
                {
                    'date': t.date,
                    'position_type': t.position_type,
                    'regime': t.regime.value,
                    'prob_high_vol': t.prob_high_vol,
                    'position_size': t.position_size,
                    'execution_style': t.execution_style,
                    'entry_spread': t.entry_spread,
                }
                for t in self.trades
            ])
            trades_df.to_csv(output_dir / "trades.csv", index=False)
            print(f"Saved trades to: {output_dir / 'trades.csv'}")


def main():
    """Main execution function."""
    strategy = SteepenerStrategyV2(
        regime_threshold=0.5,
        high_confidence_threshold=0.8,
        notional=1_000_000,
        transaction_cost_bps=0.5,
    )
    
    # Load data
    strategy.load_data()
    
    # Run backtest
    strategy.run_backtest()
    
    # Print report
    strategy.print_report()
    
    # Save results
    strategy.save_results()
    
    return strategy


if __name__ == "__main__":
    strategy = main()
