"""
Steepener Trading Strategy v3 - Continuous Regime-Based Sizing

This version uses a continuous approach to fiscal uncertainty:
- Position size scales with the level of std_4y (fiscal uncertainty)
- Higher uncertainty -> Larger bear steepener position ("Pay the Spread")
- Lower uncertainty -> Smaller position / flattener bias ("Collect the Carry")

Strategy Framework:
1. Use std_4y percentile to determine regime intensity
2. Position sizing: 0% to 100% based on uncertainty level
3. Execution style: Costs scale with position size (larger = more impact)

This approach better captures the "Fiscal Uncertainty Steepening" thesis where
the magnitude of uncertainty drives the steepening pressure.
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


@dataclass
class Trade:
    """Represents a trade execution."""
    date: datetime
    position_type: str
    position_size: float  # -1.0 to 1.0 (negative = flattener)
    uncertainty_level: float  # normalized 0-1
    execution_style: str
    entry_spread: float
    entry_std_4y: float


class SteepenerStrategyV3:
    """
    Steepener Strategy with Continuous Position Sizing based on Fiscal Uncertainty.
    
    Core Thesis:
    - High fiscal uncertainty increases term premium demand
    - This drives long-end yields higher relative to short-end (bear steepening)
    - Position size should scale with uncertainty magnitude
    
    Position Sizing:
    - std_4y < 25th percentile: Flatten or small bear (uncertainty is low)
    - std_4y 25-75th percentile: Medium bear steepener
    - std_4y > 75th percentile: Full bear steepener (pay the spread for immediacy)
    """
    
    def __init__(
        self,
        low_threshold_percentile: float = 25,  # Below this = low uncertainty
        high_threshold_percentile: float = 75,  # Above this = high uncertainty
        short_tenor: str = "1y1y",
        long_tenor: str = "3y3y",
        max_position_size: float = 1.0,
    ):
        self.low_threshold_pct = low_threshold_percentile
        self.high_threshold_pct = high_threshold_percentile
        self.short_tenor = short_tenor
        self.long_tenor = long_tenor
        self.max_position_size = max_position_size
        
        self.project_root = Path("/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus")
        
        # Data containers
        self.yield_data: Optional[pd.DataFrame] = None
        self.regime_ts: Optional[pd.DataFrame] = None
        self.trades: List[Trade] = []
        self.daily_pnl: Optional[pd.DataFrame] = None
        
        # Thresholds (set during data loading)
        self.low_threshold: Optional[float] = None
        self.high_threshold: Optional[float] = None
        
    def load_data(self) -> None:
        """Load and prepare all data."""
        print("Loading strategy data...")
        
        # Load yield curve data
        fra_file = self.project_root / "src/data/processed/b3/predi_fra_1y1y_3y3y.csv"
        self.yield_data = pd.read_csv(fra_file, parse_dates=['date'])
        self.yield_data = self.yield_data.sort_values('date').reset_index(drop=True)
        print(f"  Yield data: {len(self.yield_data)} obs from {self.yield_data['date'].min().date()} to {self.yield_data['date'].max().date()}")
        
        # Calculate curve spread
        self.yield_data['curve_spread'] = self.yield_data[self.long_tenor] - self.yield_data[self.short_tenor]
        self.yield_data['spread_change_bps'] = self.yield_data['curve_spread'].diff() * 10000
        
        # Load regime data with std_4y
        self._build_regime_time_series()
        
    def _build_regime_time_series(self) -> None:
        """Build regime time series with std_4y."""
        print("\nBuilding regime time series...")
        
        regime_dir = self.project_root / "src/data/processed/regime_analysis"
        calendar_file = self.project_root / "src/data/processed/calendar/fiscal_release_dates.csv"
        calendar = pd.read_csv(calendar_file, parse_dates=['release_date'])
        
        all_regime_data = []
        for _, row in calendar.iterrows():
            release_date = row['release_date']
            date_str = release_date.strftime('%Y%m%d')
            regime_file = regime_dir / f"regime_probs_{date_str}.csv"
            
            if regime_file.exists():
                df = pd.read_csv(regime_file, parse_dates=['date'])
                df['model_release_date'] = release_date
                all_regime_data.append(df[['date', 'prob_high_vol', 'std_4y', 'model_release_date']])
        
        combined = pd.concat(all_regime_data, ignore_index=True)
        combined = combined.sort_values(['date', 'model_release_date'])
        combined = combined[combined['model_release_date'] >= combined['date']]
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        combined = combined.sort_values('date').reset_index(drop=True)
        
        self.regime_ts = combined
        
        # Calculate thresholds based on std_4y distribution
        self.low_threshold = np.percentile(self.regime_ts['std_4y'], self.low_threshold_pct)
        self.high_threshold = np.percentile(self.regime_ts['std_4y'], self.high_threshold_pct)
        
        print(f"  Regime time series: {len(self.regime_ts)} dates")
        print(f"\n  Std_4y Distribution:")
        print(self.regime_ts['std_4y'].describe())
        print(f"\n  Thresholds:")
        print(f"    Low uncertainty (<{self.low_threshold_pct}th pctile): std_4y < {self.low_threshold:.4f}")
        print(f"    High uncertainty (>{self.high_threshold_pct}th pctile): std_4y > {self.high_threshold:.4f}")
        
    def calculate_position(self, std_4y: float) -> Tuple[str, float, str]:
        """
        Calculate position type and size based on fiscal uncertainty level.
        
        Returns:
            (position_type, position_size, execution_style)
            position_size: -1.0 to 1.0
                Positive = Bear steepener (long short, short long)
                Negative = Flattener (short short, long long)
        """
        if std_4y <= self.low_threshold:
            # Low uncertainty - small position or flattener bias
            # In very stable periods, the curve might flatten as risk premium compresses
            normalized = std_4y / self.low_threshold if self.low_threshold > 0 else 0
            position_size = 0.25 * normalized  # 0% to 25% bear steepener
            execution_style = "collect_carry"
            
        elif std_4y >= self.high_threshold:
            # High uncertainty - full bear steepener, pay for immediacy
            # Normalize between high_threshold and max
            max_std = self.regime_ts['std_4y'].max()
            normalized = min(1.0, (std_4y - self.high_threshold) / (max_std - self.high_threshold))
            position_size = 0.75 + 0.25 * normalized  # 75% to 100%
            execution_style = "pay_spread"
            
        else:
            # Medium uncertainty - linear scaling
            normalized = (std_4y - self.low_threshold) / (self.high_threshold - self.low_threshold)
            position_size = 0.25 + 0.50 * normalized  # 25% to 75%
            execution_style = "standard"
        
        position_type = "bear_steepener" if position_size > 0 else "flattener"
        return position_type, position_size, execution_style
    
    def calculate_daily_pnl(
        self,
        spread_change_bps: float,
        position_size: float,
        execution_style: str,
    ) -> Dict[str, float]:
        """
        Calculate daily P&L.
        
        Bear Steepener P&L:
        - Profit when spread increases (long-end rises more than short-end)
        - Curve P&L = spread_change * position_size * dv01_factor
        
        Execution Cost:
        - "pay_spread": Higher cost for immediacy (larger positions in volatile periods)
        - "collect_carry": Lower cost, patient execution
        """
        dv01_factor = 2.0  # Simplified combined DV01
        
        # Curve P&L - profit when spread widens (bear steepener)
        curve_pnl = spread_change_bps * position_size * dv01_factor
        
        # Carry/Cost based on execution style
        if execution_style == "pay_spread":
            # Paying the spread costs more
            cost_factor = -0.15 * position_size
        elif execution_style == "collect_carry":
            # Collecting carry earns a bit
            cost_factor = 0.02 * position_size
        else:
            cost_factor = -0.05 * position_size
        
        total_pnl = curve_pnl + cost_factor
        
        return {
            'total_pnl': total_pnl,
            'curve_pnl': curve_pnl,
            'carry_pnl': cost_factor,
        }
    
    def run_backtest(self) -> pd.DataFrame:
        """Run backtest with continuous position sizing."""
        print("\n" + "="*70)
        print("RUNNING STEEPENER STRATEGY BACKTEST v3")
        print("="*70)
        print("\nStrategy: Continuous position sizing based on fiscal uncertainty (std_4y)")
        
        # Merge data
        merged = pd.merge(
            self.yield_data,
            self.regime_ts[['date', 'prob_high_vol', 'std_4y']],
            on='date',
            how='inner'
        )
        merged = merged.sort_values('date').reset_index(drop=True)
        
        print(f"\nMerged dataset: {len(merged)} trading days")
        
        daily_results = []
        prev_position_size = 0.0
        
        for i in range(1, len(merged)):
            row = merged.iloc[i]
            prev_row = merged.iloc[i-1]
            
            date = row['date']
            std_4y = row['std_4y']
            spread_change_bps = row['spread_change_bps']
            
            # Calculate position
            position_type, position_size, execution_style = self.calculate_position(std_4y)
            
            # Calculate P&L
            pnl = self.calculate_daily_pnl(spread_change_bps, position_size, execution_style)
            
            # Record trade if position changes significantly (>10%)
            if abs(position_size - prev_position_size) > 0.1 or i == 1:
                trade = Trade(
                    date=date,
                    position_type=position_type,
                    position_size=position_size,
                    uncertainty_level=(std_4y - self.low_threshold) / (self.high_threshold - self.low_threshold),
                    execution_style=execution_style,
                    entry_spread=row['curve_spread'],
                    entry_std_4y=std_4y,
                )
                self.trades.append(trade)
                prev_position_size = position_size
            
            daily_results.append({
                'date': date,
                'curve_spread': row['curve_spread'],
                'spread_change_bps': spread_change_bps,
                'std_4y': std_4y,
                'prob_high_vol': row['prob_high_vol'],
                'position_type': position_type,
                'position_size': position_size,
                'execution_style': execution_style,
                'daily_pnl': pnl['total_pnl'],
                'curve_pnl': pnl['curve_pnl'],
                'carry_pnl': pnl['carry_pnl'],
            })
        
        self.daily_pnl = pd.DataFrame(daily_results)
        
        # Print sample of trades
        print(f"\n{'='*70}")
        print("SAMPLE TRADES (showing position adjustments)")
        print(f"{'='*70}")
        print(f"{'Date':<12} {'Type':<18} {'Size':>8} {'Uncert':>8} {'Std_4y':>8} {'Exec Style':<15}")
        print("-" * 70)
        for trade in self.trades[:15]:
            print(f"{trade.date.strftime('%Y-%m-%d'):<12} {trade.position_type:<18} "
                  f"{trade.position_size:>7.1%} {trade.uncertainty_level:>7.2f} "
                  f"{trade.entry_std_4y:>8.4f} {trade.execution_style:<15}")
        if len(self.trades) > 15:
            print(f"... and {len(self.trades)-15} more position adjustments")
        
        return self.daily_pnl
    
    def generate_performance_report(self) -> Dict:
        """Generate performance report."""
        df = self.daily_pnl.copy()
        df['cumulative_pnl'] = df['daily_pnl'].cumsum()
        
        total_days = len(df)
        years = total_days / 252
        
        # Segment by uncertainty level
        low_mask = df['std_4y'] <= self.low_threshold
        mid_mask = (df['std_4y'] > self.low_threshold) & (df['std_4y'] <= self.high_threshold)
        high_mask = df['std_4y'] > self.high_threshold
        
        # Max drawdown
        running_max = df['cumulative_pnl'].expanding().max()
        drawdown = df['cumulative_pnl'] - running_max
        max_drawdown = drawdown.min()
        
        total_pnl = df['daily_pnl'].sum()
        
        report = {
            'overall': {
                'total_pnl_bps': total_pnl,
                'trading_days': total_days,
                'years': years,
                'pnl_per_year_bps': total_pnl / years if years > 0 else 0,
                'avg_daily_pnl_bps': df['daily_pnl'].mean(),
                'pnl_volatility_bps': df['daily_pnl'].std(),
                'sharpe_ratio': df['daily_pnl'].mean() / df['daily_pnl'].std() * np.sqrt(252) if df['daily_pnl'].std() > 0 else 0,
                'max_drawdown_bps': max_drawdown,
                'win_rate': (df['daily_pnl'] > 0).mean(),
            },
            'low_uncertainty': {
                'days': low_mask.sum(),
                'avg_std_4y': df.loc[low_mask, 'std_4y'].mean() if low_mask.sum() > 0 else 0,
                'total_pnl_bps': df.loc[low_mask, 'daily_pnl'].sum(),
                'avg_pnl_bps': df.loc[low_mask, 'daily_pnl'].mean() if low_mask.sum() > 0 else 0,
            },
            'medium_uncertainty': {
                'days': mid_mask.sum(),
                'avg_std_4y': df.loc[mid_mask, 'std_4y'].mean() if mid_mask.sum() > 0 else 0,
                'total_pnl_bps': df.loc[mid_mask, 'daily_pnl'].sum(),
                'avg_pnl_bps': df.loc[mid_mask, 'daily_pnl'].mean() if mid_mask.sum() > 0 else 0,
            },
            'high_uncertainty': {
                'days': high_mask.sum(),
                'avg_std_4y': df.loc[high_mask, 'std_4y'].mean() if high_mask.sum() > 0 else 0,
                'total_pnl_bps': df.loc[high_mask, 'daily_pnl'].sum(),
                'avg_pnl_bps': df.loc[high_mask, 'daily_pnl'].mean() if high_mask.sum() > 0 else 0,
            },
            'trades': len(self.trades),
        }
        
        return report
    
    def print_report(self) -> None:
        """Print formatted report."""
        report = self.generate_performance_report()
        
        print("\n" + "="*70)
        print("STEEPENER STRATEGY PERFORMANCE REPORT v3")
        print("(Continuous Position Sizing based on Fiscal Uncertainty)")
        print("="*70)
        
        print("\n📊 OVERALL PERFORMANCE")
        print("-" * 50)
        print(f"Total P&L:          {report['overall']['total_pnl_bps']:>12.2f} bps")
        print(f"P&L per Year:       {report['overall']['pnl_per_year_bps']:>12.2f} bps")
        print(f"Trading Days:       {report['overall']['trading_days']:>12}")
        print(f"Avg Daily P&L:      {report['overall']['avg_daily_pnl_bps']:>12.4f} bps")
        print(f"P&L Volatility:     {report['overall']['pnl_volatility_bps']:>12.4f} bps")
        print(f"Sharpe Ratio:       {report['overall']['sharpe_ratio']:>12.2f}")
        print(f"Max Drawdown:       {report['overall']['max_drawdown_bps']:>12.2f} bps")
        print(f"Win Rate:           {report['overall']['win_rate']*100:>11.1f}%")
        print(f"Trades:             {report['trades']:>12}")
        
        print("\n🔴 HIGH UNCERTAINTY (Pay the Spread)")
        print(f"   Std_4y > {self.high_threshold:.4f}")
        print("-" * 50)
        print(f"Days:               {report['high_uncertainty']['days']:>12}")
        print(f"Avg Std_4y:         {report['high_uncertainty']['avg_std_4y']:>12.4f}")
        print(f"Total P&L:          {report['high_uncertainty']['total_pnl_bps']:>12.2f} bps")
        print(f"Avg Daily P&L:      {report['high_uncertainty']['avg_pnl_bps']:>12.4f} bps")
        
        print("\n🟡 MEDIUM UNCERTAINTY (Standard Execution)")
        print(f"   Std_4y between {self.low_threshold:.4f} and {self.high_threshold:.4f}")
        print("-" * 50)
        print(f"Days:               {report['medium_uncertainty']['days']:>12}")
        print(f"Avg Std_4y:         {report['medium_uncertainty']['avg_std_4y']:>12.4f}")
        print(f"Total P&L:          {report['medium_uncertainty']['total_pnl_bps']:>12.2f} bps")
        print(f"Avg Daily P&L:      {report['medium_uncertainty']['avg_pnl_bps']:>12.4f} bps")
        
        print("\n🟢 LOW UNCERTAINTY (Collect the Carry)")
        print(f"   Std_4y < {self.low_threshold:.4f}")
        print("-" * 50)
        print(f"Days:               {report['low_uncertainty']['days']:>12}")
        print(f"Avg Std_4y:         {report['low_uncertainty']['avg_std_4y']:>12.4f}")
        print(f"Total P&L:          {report['low_uncertainty']['total_pnl_bps']:>12.2f} bps")
        print(f"Avg Daily P&L:      {report['low_uncertainty']['avg_pnl_bps']:>12.4f} bps")
        
        print("\n" + "="*70)
        
        # Best and worst periods
        df = self.daily_pnl
        print("\n📈 BEST MONTHS (by total P&L)")
        print("-" * 50)
        df['year_month'] = df['date'].dt.to_period('M')
        monthly_pnl = df.groupby('year_month')['daily_pnl'].sum().sort_values(ascending=False)
        for month, pnl in monthly_pnl.head(5).items():
            print(f"  {month}: {pnl:>10.2f} bps")
        
        print("\n📉 WORST MONTHS (by total P&L)")
        print("-" * 50)
        for month, pnl in monthly_pnl.tail(5).sort_values().items():
            print(f"  {month}: {pnl:>10.2f} bps")
        
        print("\n" + "="*70)
    
    def save_results(self, output_dir: Optional[str] = None) -> None:
        """Save results."""
        if output_dir is None:
            output_dir = self.project_root / "src/data/processed/strategy_results_v3"
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
                    'position_size': t.position_size,
                    'uncertainty_level': t.uncertainty_level,
                    'execution_style': t.execution_style,
                    'entry_spread': t.entry_spread,
                    'entry_std_4y': t.entry_std_4y,
                }
                for t in self.trades
            ])
            trades_df.to_csv(output_dir / "trades.csv", index=False)
            print(f"Saved trades to: {output_dir / 'trades.csv'}")


def main():
    """Main execution."""
    strategy = SteepenerStrategyV3(
        low_threshold_percentile=25,
        high_threshold_percentile=75,
        max_position_size=1.0,
    )
    
    strategy.load_data()
    strategy.run_backtest()
    strategy.print_report()
    strategy.save_results()
    
    return strategy


if __name__ == "__main__":
    strategy = main()
