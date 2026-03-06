"""
Steepener Trading Strategy v4 - Final Refined Implementation

Key Features:
1. Regime-based position sizing (std_4y percentiles)
2. Trend/momentum filter for entry timing
3. Proper risk management with position limits
4. Dual execution styles: "Pay the Spread" vs "Collect the Carry"
5. P&L attribution: Curve, Carry, and Cost components

Strategy Logic:
- Uses fiscal uncertainty (std_4y) as primary signal
- Combines with momentum filter to avoid false signals
- Position sizing: 0% to 100% based on uncertainty level
- Execution costs vary by regime (high uncertainty = higher costs)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class Trade:
    """Trade record."""
    date: datetime
    position_type: str
    position_size: float
    std_4y: float
    spread_level: float
    spread_ma: float
    execution_style: str
    regime: str


class SteepenerStrategyV4:
    """
    Final Steepener Strategy Implementation.
    
    Signal Generation:
    - Primary: Fiscal uncertainty level (std_4y percentile)
    - Secondary: Spread momentum (avoid entries against trend)
    
    Position Sizing:
    - Base size determined by uncertainty percentile
    - Adjusted by momentum alignment
    - Capped at max_position_size
    
    Execution:
    - High uncertainty (>75%): "Pay the Spread" - accept higher costs for immediacy
    - Low uncertainty (<25%): "Collect the Carry" - patient execution, earn carry
    - Medium: Standard execution
    """
    
    def __init__(
        self,
        low_threshold_pct: float = 25,
        high_threshold_pct: float = 75,
        max_position_size: float = 1.0,
        momentum_lookback: int = 20,
        momentum_threshold: float = 0.5,  # Minimum momentum alignment
    ):
        self.low_threshold_pct = low_threshold_pct
        self.high_threshold_pct = high_threshold_pct
        self.max_position_size = max_position_size
        self.momentum_lookback = momentum_lookback
        self.momentum_threshold = momentum_threshold
        
        self.project_root = Path("/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus")
        
        # Data
        self.yield_data: Optional[pd.DataFrame] = None
        self.regime_ts: Optional[pd.DataFrame] = None
        self.trades: List[Trade] = []
        self.daily_pnl: Optional[pd.DataFrame] = None
        
        self.low_threshold: Optional[float] = None
        self.high_threshold: Optional[float] = None
        
    def load_data(self) -> None:
        """Load all data."""
        print("Loading data...")
        
        # Yield data
        fra_file = self.project_root / "src/data/processed/b3/predi_fra_1y1y_3y3y.csv"
        self.yield_data = pd.read_csv(fra_file, parse_dates=['date'])
        self.yield_data = self.yield_data.sort_values('date').reset_index(drop=True)
        
        # Calculate spread and momentum
        self.yield_data['curve_spread'] = self.yield_data['3y3y'] - self.yield_data['1y1y']
        self.yield_data['spread_change_bps'] = self.yield_data['curve_spread'].diff() * 10000
        self.yield_data['spread_ma'] = self.yield_data['curve_spread'].rolling(self.momentum_lookback).mean()
        self.yield_data['spread_vs_ma'] = self.yield_data['curve_spread'] - self.yield_data['spread_ma']
        
        print(f"  Yield data: {len(self.yield_data)} obs")
        
        # Regime data
        self._load_regime_data()
        
    def _load_regime_data(self) -> None:
        """Load regime time series."""
        regime_dir = self.project_root / "src/data/processed/regime_analysis"
        calendar_file = self.project_root / "src/data/processed/calendar/fiscal_release_dates.csv"
        calendar = pd.read_csv(calendar_file, parse_dates=['release_date'])
        
        all_data = []
        for _, row in calendar.iterrows():
            release_date = row['release_date']
            date_str = release_date.strftime('%Y%m%d')
            regime_file = regime_dir / f"regime_probs_{date_str}.csv"
            
            if regime_file.exists():
                df = pd.read_csv(regime_file, parse_dates=['date'])
                df['model_release_date'] = release_date
                all_data.append(df[['date', 'std_4y', 'model_release_date']])
        
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values(['date', 'model_release_date'])
        combined = combined[combined['model_release_date'] >= combined['date']]
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        combined = combined.sort_values('date').reset_index(drop=True)
        
        self.regime_ts = combined
        
        # Calculate thresholds
        self.low_threshold = np.percentile(self.regime_ts['std_4y'], self.low_threshold_pct)
        self.high_threshold = np.percentile(self.regime_ts['std_4y'], self.high_threshold_pct)
        
        print(f"  Regime data: {len(self.regime_ts)} dates")
        print(f"  Thresholds: Low={self.low_threshold:.4f}, High={self.high_threshold:.4f}")
        
    def calculate_position(self, std_4y: float, spread_vs_ma: float) -> Tuple[str, float, str]:
        """
        Calculate position based on uncertainty and momentum.
        
        Returns:
            (position_type, position_size, execution_style)
        """
        # Base position size from uncertainty level
        if std_4y <= self.low_threshold:
            base_size = 0.25 * (std_4y / self.low_threshold)
            execution_style = "collect_carry"
            regime = "low_uncertainty"
        elif std_4y >= self.high_threshold:
            max_std = self.regime_ts['std_4y'].max()
            normalized = min(1.0, (std_4y - self.high_threshold) / (max_std - self.high_threshold))
            base_size = 0.75 + 0.25 * normalized
            execution_style = "pay_spread"
            regime = "high_uncertainty"
        else:
            normalized = (std_4y - self.low_threshold) / (self.high_threshold - self.low_threshold)
            base_size = 0.25 + 0.50 * normalized
            execution_style = "standard"
            regime = "medium_uncertainty"
        
        # Momentum adjustment: reduce size if fighting the trend
        # For bear steepener, we want spread to be widening (positive momentum)
        # If spread is below MA (compressed), it's a better entry for bear steepener
        momentum_factor = 1.0
        if spread_vs_ma < -0.005:  # Spread compressed vs MA
            momentum_factor = 1.1  # Slight increase - potential mean reversion
        elif spread_vs_ma > 0.01:  # Spread extended vs MA
            momentum_factor = 0.7  # Reduce - extended already
        
        position_size = min(self.max_position_size, base_size * momentum_factor)
        position_type = "bear_steepener"
        
        return position_type, position_size, execution_style, regime
    
    def calculate_pnl(self, spread_change_bps: float, position_size: float, execution_style: str) -> Dict:
        """Calculate P&L components."""
        # Curve P&L
        dv01_factor = 2.0
        curve_pnl = spread_change_bps * position_size * dv01_factor
        
        # Carry/Cost
        if execution_style == "pay_spread":
            carry_pnl = -0.10 * position_size  # Higher cost for immediacy
        elif execution_style == "collect_carry":
            carry_pnl = 0.03 * position_size   # Small carry benefit
        else:
            carry_pnl = -0.04 * position_size
        
        return {
            'total_pnl': curve_pnl + carry_pnl,
            'curve_pnl': curve_pnl,
            'carry_pnl': carry_pnl,
        }
    
    def run_backtest(self) -> pd.DataFrame:
        """Run backtest."""
        print("\n" + "="*70)
        print("RUNNING STEEPENER STRATEGY BACKTEST v4")
        print("="*70)
        
        # Merge data
        merged = pd.merge(
            self.yield_data,
            self.regime_ts[['date', 'std_4y']],
            on='date',
            how='inner'
        )
        merged = merged.sort_values('date').reset_index(drop=True)
        merged = merged.dropna()  # Remove rows with NaN from MA calculation
        
        print(f"Backtest period: {merged['date'].min().date()} to {merged['date'].max().date()}")
        print(f"Trading days: {len(merged)}")
        
        results = []
        prev_position = 0.0
        
        for i in range(1, len(merged)):
            row = merged.iloc[i]
            prev_row = merged.iloc[i-1]
            
            date = row['date']
            std_4y = row['std_4y']
            spread_change = row['spread_change_bps']
            spread_vs_ma = row['spread_vs_ma']
            
            # Calculate position
            pos_type, pos_size, exec_style, regime = self.calculate_position(std_4y, spread_vs_ma)
            
            # Calculate P&L
            pnl = self.calculate_pnl(spread_change, pos_size, exec_style)
            
            # Record trade if position changes meaningfully
            if abs(pos_size - prev_position) > 0.05 or i == 1:
                self.trades.append(Trade(
                    date=date, position_type=pos_type, position_size=pos_size,
                    std_4y=std_4y, spread_level=row['curve_spread'],
                    spread_ma=row['spread_ma'], execution_style=exec_style, regime=regime
                ))
                prev_position = pos_size
            
            results.append({
                'date': date,
                'std_4y': std_4y,
                'curve_spread': row['curve_spread'],
                'spread_change_bps': spread_change,
                'position_size': pos_size,
                'execution_style': exec_style,
                'regime': regime,
                'daily_pnl': pnl['total_pnl'],
                'curve_pnl': pnl['curve_pnl'],
                'carry_pnl': pnl['carry_pnl'],
            })
        
        self.daily_pnl = pd.DataFrame(results)
        
        # Print trade summary
        print(f"\nPosition adjustments: {len(self.trades)}")
        print(f"\n{'Date':<12} {'Regime':<18} {'Size':>8} {'Std_4y':>8} {'Exec':<12}")
        print("-" * 60)
        for t in self.trades[:10]:
            print(f"{t.date.strftime('%Y-%m-%d'):<12} {t.regime:<18} {t.position_size:>7.1%} {t.std_4y:>8.4f} {t.execution_style:<12}")
        
        return self.daily_pnl
    
    def print_report(self) -> None:
        """Print performance report."""
        df = self.daily_pnl
        df['cumulative'] = df['daily_pnl'].cumsum()
        
        # Overall
        total_pnl = df['daily_pnl'].sum()
        days = len(df)
        years = days / 252
        
        # Max drawdown
        running_max = df['cumulative'].expanding().max()
        max_dd = (df['cumulative'] - running_max).min()
        
        # By regime
        regime_stats = df.groupby('regime').agg({
            'daily_pnl': ['count', 'sum', 'mean'],
            'std_4y': 'mean',
        }).round(4)
        
        print("\n" + "="*70)
        print("FINAL PERFORMANCE REPORT")
        print("="*70)
        
        print("\n📊 OVERALL")
        print("-" * 50)
        print(f"Total P&L:          {total_pnl:>12.2f} bps")
        print(f"P&L/Year:           {total_pnl/years:>12.2f} bps")
        print(f"Sharpe:             {df['daily_pnl'].mean()/df['daily_pnl'].std()*np.sqrt(252):>12.2f}")
        print(f"Max DD:             {max_dd:>12.2f} bps")
        print(f"Win Rate:           {(df['daily_pnl']>0).mean()*100:>11.1f}%")
        
        print("\n📈 BY REGIME")
        print("-" * 50)
        for regime in ['high_uncertainty', 'medium_uncertainty', 'low_uncertainty']:
            if regime in regime_stats.index:
                stats = regime_stats.loc[regime]
                print(f"\n{regime.upper().replace('_', ' ')}")
                print(f"  Days:    {int(stats['daily_pnl']['count']):>6}")
                print(f"  Total:   {stats['daily_pnl']['sum']:>10.2f} bps")
                print(f"  Daily:   {stats['daily_pnl']['mean']:>10.4f} bps")
                print(f"  Avg Std: {stats['std_4y']['mean']:>10.4f}")
        
        # Best/worst months
        df['ym'] = df['date'].dt.to_period('M')
        monthly = df.groupby('ym')['daily_pnl'].sum().sort_values(ascending=False)
        
        print("\n📅 BEST MONTHS")
        print("-" * 50)
        for m, pnl in monthly.head(5).items():
            print(f"  {m}: {pnl:>10.2f} bps")
        
        print("\n📅 WORST MONTHS")
        print("-" * 50)
        for m, pnl in monthly.tail(5).sort_values().items():
            print(f"  {m}: {pnl:>10.2f} bps")
        
        print("\n" + "="*70)
    
    def save_results(self) -> None:
        """Save results."""
        output_dir = self.project_root / "src/data/processed/strategy_results_v4"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_pnl.to_csv(output_dir / "daily_pnl.csv", index=False)
        
        trades_df = pd.DataFrame([
            {
                'date': t.date,
                'position_type': t.position_type,
                'position_size': t.position_size,
                'std_4y': t.std_4y,
                'spread_level': t.spread_level,
                'execution_style': t.execution_style,
                'regime': t.regime,
            }
            for t in self.trades
        ])
        trades_df.to_csv(output_dir / "trades.csv", index=False)
        
        print(f"\nResults saved to: {output_dir}")


def main():
    strategy = SteepenerStrategyV4()
    strategy.load_data()
    strategy.run_backtest()
    strategy.print_report()
    strategy.save_results()
    return strategy


if __name__ == "__main__":
    strategy = main()
