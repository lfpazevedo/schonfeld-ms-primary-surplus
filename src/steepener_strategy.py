"""
Steepener Trading Strategy Based on Markov-Switching Regime Probabilities

This module implements a regime-dependent steepener trading strategy that:
1. Uses Markov-switching model probabilities to identify fiscal uncertainty regimes
2. Applies "Pay the Spread" execution in high fiscal uncertainty (high vol regime)
   - Bear steepener: long short-end, short long-end (bet on curve steepening via long-end sell-off)
3. Applies "Collect the Carry" execution in low fiscal uncertainty (low vol regime)
   - Bull steepener/flattener: optimize for carry and roll-down

Positions are held between regime recalculation dates (fiscal release dates).
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
    HIGH_UNCERTAINTY = "high_uncertainty"  # High fiscal uncertainty - "Pay the Spread"
    LOW_UNCERTAINTY = "low_uncertainty"    # Low fiscal uncertainty - "Collect the Carry"


class SteepenerPosition(Enum):
    """Type of steepener position."""
    BEAR_STEEPENER = "bear_steepener"      # Long short-end, short long-end (pay long-end)
    BULL_STEEPENER = "bull_steepener"      # Long short-end ( benefiting from rate cuts)
    FLATTENER = "flattener"                # Short short-end, long long-end
    NEUTRAL = "neutral"                    # No position


@dataclass
class Trade:
    """Represents a trade execution."""
    date: datetime
    position: SteepenerPosition
    regime: Regime
    prob_high_vol: float
    prob_low_vol: float
    entry_spread: float
    execution_style: str  # "pay_spread" or "collect_carry"
    notional: float = 1.0


@dataclass
class PositionHolding:
    """Represents a position held over a period."""
    entry_date: datetime
    exit_date: datetime
    position: SteepenerPosition
    regime: Regime
    entry_spread: float
    exit_spread: float
    pnl: float
    carry_pnl: float
    curve_pnl: float


class SteepenerStrategy:
    """
    Steepener trading strategy based on Markov-switching regime probabilities.
    
    Strategy Logic:
    ----------------
    - HIGH UNCERTAINTY (prob_high_vol > threshold): 
        "Pay the Spread" mode - Bear steepener
        Rationale: In high fiscal uncertainty, long-end yields rise faster (term premium expansion)
    
    - LOW UNCERTAINTY (prob_low_vol >= threshold):
        "Collect the Carry" mode - Bull steepener / carry optimization
        Rationale: In stable periods, optimize for carry and roll-down
    
    Position Holding:
    -----------------
    Positions are established on each fiscal release date (regime recalculation)
    and held until the next recalculation date.
    """
    
    def __init__(
        self,
        regime_threshold: float = 0.5,
        short_tenor: str = "1y1y",
        long_tenor: str = "3y3y",
        short_dv01: float = 1.0,
        long_dv01: float = 1.0,
        transaction_cost_bps: float = 1.0,  # 1bp cost for "paying the spread"
        carry_cost_bps: float = 0.5,        # 0.5bp benefit for "collecting carry"
    ):
        """
        Initialize the strategy.
        
        Args:
            regime_threshold: Probability threshold for regime classification
            short_tenor: Short-end tenor for steepener (e.g., "1y1y")
            long_tenor: Long-end tenor for steepener (e.g., "3y3y")
            short_dv01: DV01 weight for short leg
            long_dv01: DV01 weight for long leg
            transaction_cost_bps: Cost in bps when "paying the spread"
            carry_cost_bps: Benefit in bps when "collecting carry"
        """
        self.regime_threshold = regime_threshold
        self.short_tenor = short_tenor
        self.long_tenor = long_tenor
        self.short_dv01 = short_dv01
        self.long_dv01 = long_dv01
        self.transaction_cost_bps = transaction_cost_bps
        self.carry_cost_bps = carry_cost_bps
        
        self.project_root = Path("/home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus")
        self.regime_dir = self.project_root / "src/data/processed/regime_analysis"
        
        # Data containers
        self.yield_data: Optional[pd.DataFrame] = None
        self.fiscal_calendar: Optional[pd.DataFrame] = None
        self.regime_history: Optional[pd.DataFrame] = None
        self.trades: List[Trade] = []
        self.position_holdings: List[PositionHolding] = []
        self.daily_pnl: Optional[pd.DataFrame] = None
        
    def load_data(self) -> None:
        """Load all required data sources."""
        print("Loading strategy data...")
        
        # Load yield curve data (forward rates)
        fra_file = self.project_root / "src/data/processed/b3/predi_fra_1y1y_3y3y.csv"
        self.yield_data = pd.read_csv(fra_file, parse_dates=['date'])
        self.yield_data = self.yield_data.sort_values('date').reset_index(drop=True)
        print(f"  Yield data: {len(self.yield_data)} observations from {self.yield_data['date'].min().date()} to {self.yield_data['date'].max().date()}")
        
        # Calculate 2s10s steepener proxy (1y1y vs 3y3y spread)
        self.yield_data['curve_spread'] = self.yield_data[self.long_tenor] - self.yield_data[self.short_tenor]
        self.yield_data['spread_change'] = self.yield_data['curve_spread'].diff()
        
        # Load fiscal release calendar
        calendar_file = self.project_root / "src/data/processed/calendar/fiscal_release_dates.csv"
        self.fiscal_calendar = pd.read_csv(calendar_file, parse_dates=['release_date'])
        self.fiscal_calendar = self.fiscal_calendar.sort_values('release_date').reset_index(drop=True)
        print(f"  Fiscal calendar: {len(self.fiscal_calendar)} release dates")
        
        # Build regime history from all regime probability files
        self._build_regime_history()
        
    def _build_regime_history(self) -> None:
        """Build regime history from all regime probability files."""
        regime_snapshots = []
        
        for _, row in self.fiscal_calendar.iterrows():
            release_date = row['release_date']
            date_str = release_date.strftime('%Y%m%d')
            regime_file = self.regime_dir / f"regime_probs_{date_str}.csv"
            
            if regime_file.exists():
                # Load the regime probabilities for this release date
                df = pd.read_csv(regime_file, parse_dates=['date'])
                
                # Get the latest probabilities (last row)
                latest = df.iloc[-1]
                
                regime_snapshots.append({
                    'release_date': release_date,
                    'prob_high_vol': latest['prob_high_vol'],
                    'prob_low_vol': latest['prob_low_vol'],
                    'regime': Regime.HIGH_UNCERTAINTY if latest['prob_high_vol'] > self.regime_threshold else Regime.LOW_UNCERTAINTY,
                    'model_n_obs': latest.get('model_n_obs', np.nan),
                })
        
        self.regime_history = pd.DataFrame(regime_snapshots)
        print(f"  Regime history: {len(self.regime_history)} regime classifications")
        print(f"    High uncertainty periods: {(self.regime_history['regime'] == Regime.HIGH_UNCERTAINTY).sum()}")
        print(f"    Low uncertainty periods: {(self.regime_history['regime'] == Regime.LOW_UNCERTAINTY).sum()}")
        
    def classify_regime(self, prob_high_vol: float) -> Regime:
        """Classify regime based on high volatility probability."""
        if prob_high_vol > self.regime_threshold:
            return Regime.HIGH_UNCERTAINTY
        return Regime.LOW_UNCERTAINTY
    
    def determine_position(self, regime: Regime, current_spread: float) -> SteepenerPosition:
        """
        Determine position based on regime.
        
        HIGH UNCERTAINTY -> BEAR STEEPENER
            Rationale: Fiscal uncertainty pushes long-end yields up (term premium)
            Position: Long short-end (1y1y), Short long-end (3y3y)
            Execution: "Pay the spread" - use market orders for immediacy
        
        LOW UNCERTAINTY -> BULL STEEPENER / CARRY
            Rationale: Stable environment favors carry and roll-down
            Position: Optimize for positive carry
            Execution: "Collect the carry" - use limit orders, be patient
        """
        if regime == Regime.HIGH_UNCERTAINTY:
            return SteepenerPosition.BEAR_STEEPENER
        else:
            # In low uncertainty, we could also go neutral if carry is unfavorable
            # For simplicity, we'll use a bull steepener bias
            return SteepenerPosition.BULL_STEEPENER
    
    def calculate_position_pnl(
        self, 
        position: SteepenerPosition,
        spread_change: float,
        days_held: int,
        execution_style: str
    ) -> Tuple[float, float, float]:
        """
        Calculate P&L for a position.
        
        Returns:
            (total_pnl, curve_pnl, carry_pnl)
        """
        # Curve P&L: Change in spread * DV01-weighted position
        # For bear steepener: we win when spread increases (long-end rises more)
        if position == SteepenerPosition.BEAR_STEEPENER:
            # Long short-end, Short long-end
            # We profit when: short-end yields fall OR long-end yields rise
            # Spread = Long - Short -> profit when spread increases
            curve_pnl = spread_change * (self.short_dv01 + self.long_dv01) * 100  # in bps
        elif position == SteepenerPosition.BULL_STEEPENER:
            # Position for falling rates at short-end
            # We profit when short-end yields fall more than long-end
            curve_pnl = -spread_change * (self.short_dv01 + self.long_dv01) * 100
        else:
            curve_pnl = 0.0
        
        # Carry P&L: daily accrual based on execution style
        if execution_style == "pay_spread":
            # Paying the spread costs us
            carry_pnl = -self.transaction_cost_bps * days_held / 252
        else:
            # Collecting carry benefits us
            carry_pnl = self.carry_cost_bps * days_held / 252
        
        total_pnl = curve_pnl + carry_pnl
        return total_pnl, curve_pnl, carry_pnl
    
    def run_backtest(self) -> pd.DataFrame:
        """
        Run the complete backtest.
        
        Strategy rebalancing occurs on each fiscal release date.
        Positions are held until the next release date.
        """
        print("\n" + "="*70)
        print("RUNNING STEEPENER STRATEGY BACKTEST")
        print("="*70)
        
        if self.regime_history is None or len(self.regime_history) == 0:
            raise ValueError("No regime history available. Run load_data() first.")
        
        daily_results = []
        
        # Iterate through each regime period (between fiscal release dates)
        for i in range(len(self.regime_history) - 1):
            current_regime_row = self.regime_history.iloc[i]
            next_regime_row = self.regime_history.iloc[i + 1]
            
            entry_date = current_regime_row['release_date']
            exit_date = next_regime_row['release_date']
            
            # Get regime classification
            prob_high_vol = current_regime_row['prob_high_vol']
            prob_low_vol = current_regime_row['prob_low_vol']
            regime = current_regime_row['regime']
            
            # Determine position and execution style
            execution_style = "pay_spread" if regime == Regime.HIGH_UNCERTAINTY else "collect_carry"
            
            # Get yield data for this period
            period_mask = (self.yield_data['date'] >= entry_date) & (self.yield_data['date'] <= exit_date)
            period_data = self.yield_data[period_mask].copy()
            
            if len(period_data) < 2:
                continue
            
            # Get entry spread
            entry_spread = period_data.iloc[0]['curve_spread']
            position = self.determine_position(regime, entry_spread)
            
            # Record trade
            trade = Trade(
                date=entry_date,
                position=position,
                regime=regime,
                prob_high_vol=prob_high_vol,
                prob_low_vol=prob_low_vol,
                entry_spread=entry_spread,
                execution_style=execution_style,
            )
            self.trades.append(trade)
            
            # Calculate daily P&L for this holding period
            period_pnl = self._calculate_period_pnl(
                period_data, position, execution_style, entry_date, exit_date
            )
            daily_results.extend(period_pnl)
            
            # Record position holding summary
            if len(period_data) > 0:
                exit_spread = period_data.iloc[-1]['curve_spread']
                total_pnl = sum([d['daily_pnl'] for d in period_pnl])
                total_curve_pnl = sum([d['curve_pnl'] for d in period_pnl])
                total_carry_pnl = sum([d['carry_pnl'] for d in period_pnl])
                
                holding = PositionHolding(
                    entry_date=entry_date,
                    exit_date=exit_date,
                    position=position,
                    regime=regime,
                    entry_spread=entry_spread,
                    exit_spread=exit_spread,
                    pnl=total_pnl,
                    carry_pnl=total_carry_pnl,
                    curve_pnl=total_curve_pnl,
                )
                self.position_holdings.append(holding)
                
                # Print summary for this period
                print(f"\n[{i+1}/{len(self.regime_history)-1}] {entry_date.date()} to {exit_date.date()}")
                print(f"  Regime: {regime.value} (HighVol: {prob_high_vol:.2%}, LowVol: {prob_low_vol:.2%})")
                print(f"  Position: {position.value} | Execution: {execution_style}")
                print(f"  Spread: {entry_spread:.4%} -> {exit_spread:.4%} ({(exit_spread-entry_spread)*10000:.1f}bps)")
                print(f"  P&L: {total_pnl:.2f}bps (Curve: {total_curve_pnl:.2f}, Carry: {total_carry_pnl:.2f})")
        
        # Create daily P&L DataFrame
        self.daily_pnl = pd.DataFrame(daily_results)
        
        return self.daily_pnl
    
    def _calculate_period_pnl(
        self,
        period_data: pd.DataFrame,
        position: SteepenerPosition,
        execution_style: str,
        entry_date: datetime,
        exit_date: datetime,
    ) -> List[Dict]:
        """Calculate daily P&L for a holding period."""
        results = []
        
        for i in range(1, len(period_data)):
            current_row = period_data.iloc[i]
            prev_row = period_data.iloc[i-1]
            
            date = current_row['date']
            spread_change = current_row['curve_spread'] - prev_row['curve_spread']
            days_held = 1  # Assuming daily data
            
            total_pnl, curve_pnl, carry_pnl = self.calculate_position_pnl(
                position, spread_change, days_held, execution_style
            )
            
            results.append({
                'date': date,
                'position': position.value,
                'regime': 'high_uncertainty' if execution_style == 'pay_spread' else 'low_uncertainty',
                'execution_style': execution_style,
                'curve_spread': current_row['curve_spread'],
                'spread_change': spread_change,
                'daily_pnl': total_pnl,
                'curve_pnl': curve_pnl,
                'carry_pnl': carry_pnl,
                'holding_period_start': entry_date,
                'holding_period_end': exit_date,
            })
        
        return results
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if self.daily_pnl is None or len(self.daily_pnl) == 0:
            raise ValueError("No backtest results available. Run run_backtest() first.")
        
        df = self.daily_pnl.copy()
        
        # Overall metrics
        total_pnl = df['daily_pnl'].sum()
        total_days = len(df)
        
        # Regime-specific performance
        high_unc_mask = df['regime'] == 'high_uncertainty'
        low_unc_mask = df['regime'] == 'low_uncertainty'
        
        report = {
            'overall': {
                'total_pnl_bps': total_pnl,
                'total_days': total_days,
                'avg_daily_pnl_bps': df['daily_pnl'].mean(),
                'pnl_volatility_bps': df['daily_pnl'].std(),
                'sharpe_ratio': df['daily_pnl'].mean() / df['daily_pnl'].std() * np.sqrt(252) if df['daily_pnl'].std() > 0 else 0,
                'max_drawdown_bps': self._calculate_max_drawdown(df['daily_pnl']),
                'win_rate': (df['daily_pnl'] > 0).mean(),
            },
            'high_uncertainty_regime': {
                'total_pnl_bps': df.loc[high_unc_mask, 'daily_pnl'].sum(),
                'days': high_unc_mask.sum(),
                'avg_daily_pnl_bps': df.loc[high_unc_mask, 'daily_pnl'].mean() if high_unc_mask.sum() > 0 else 0,
                'win_rate': (df.loc[high_unc_mask, 'daily_pnl'] > 0).mean() if high_unc_mask.sum() > 0 else 0,
            },
            'low_uncertainty_regime': {
                'total_pnl_bps': df.loc[low_unc_mask, 'daily_pnl'].sum(),
                'days': low_unc_mask.sum(),
                'avg_daily_pnl_bps': df.loc[low_unc_mask, 'daily_pnl'].mean() if low_unc_mask.sum() > 0 else 0,
                'win_rate': (df.loc[low_unc_mask, 'daily_pnl'] > 0).mean() if low_unc_mask.sum() > 0 else 0,
            },
            'trades': len(self.trades),
            'position_holdings': len(self.position_holdings),
        }
        
        return report
    
    def _calculate_max_drawdown(self, pnl_series: pd.Series) -> float:
        """Calculate maximum drawdown in bps."""
        cumulative = pnl_series.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        return drawdown.min()
    
    def print_report(self) -> None:
        """Print formatted performance report."""
        report = self.generate_performance_report()
        
        print("\n" + "="*70)
        print("STEEPENER STRATEGY PERFORMANCE REPORT")
        print("="*70)
        
        print("\n📊 OVERALL PERFORMANCE")
        print("-" * 50)
        print(f"Total P&L:          {report['overall']['total_pnl_bps']:>10.2f} bps")
        print(f"Trading Days:       {report['overall']['total_days']:>10}")
        print(f"Avg Daily P&L:      {report['overall']['avg_daily_pnl_bps']:>10.4f} bps")
        print(f"P&L Volatility:     {report['overall']['pnl_volatility_bps']:>10.4f} bps")
        print(f"Sharpe Ratio:       {report['overall']['sharpe_ratio']:>10.2f}")
        print(f"Max Drawdown:       {report['overall']['max_drawdown_bps']:>10.2f} bps")
        print(f"Win Rate:           {report['overall']['win_rate']*100:>9.1f}%")
        
        print("\n🔴 HIGH UNCERTAINTY REGIME (Pay the Spread)")
        print("-" * 50)
        print(f"Total P&L:          {report['high_uncertainty_regime']['total_pnl_bps']:>10.2f} bps")
        print(f"Days:               {report['high_uncertainty_regime']['days']:>10}")
        print(f"Avg Daily P&L:      {report['high_uncertainty_regime']['avg_daily_pnl_bps']:>10.4f} bps")
        print(f"Win Rate:           {report['high_uncertainty_regime']['win_rate']*100:>9.1f}%")
        
        print("\n🟢 LOW UNCERTAINTY REGIME (Collect the Carry)")
        print("-" * 50)
        print(f"Total P&L:          {report['low_uncertainty_regime']['total_pnl_bps']:>10.2f} bps")
        print(f"Days:               {report['low_uncertainty_regime']['days']:>10}")
        print(f"Avg Daily P&L:      {report['low_uncertainty_regime']['avg_daily_pnl_bps']:>10.4f} bps")
        print(f"Win Rate:           {report['low_uncertainty_regime']['win_rate']*100:>9.1f}%")
        
        print("\n📈 TRADE SUMMARY")
        print("-" * 50)
        print(f"Total Trades:       {report['trades']:>10}")
        print(f"Position Holds:     {report['position_holdings']:>10}")
        
        print("\n" + "="*70)
    
    def save_results(self, output_dir: Optional[str] = None) -> None:
        """Save backtest results to CSV files."""
        if output_dir is None:
            output_dir = self.project_root / "src/data/processed/strategy_results"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save daily P&L
        if self.daily_pnl is not None:
            self.daily_pnl.to_csv(output_dir / "daily_pnl.csv", index=False)
            print(f"\nSaved daily P&L to: {output_dir / 'daily_pnl.csv'}")
        
        # Save trades
        if self.trades:
            trades_df = pd.DataFrame([
                {
                    'date': t.date,
                    'position': t.position.value,
                    'regime': t.regime.value,
                    'prob_high_vol': t.prob_high_vol,
                    'prob_low_vol': t.prob_low_vol,
                    'entry_spread': t.entry_spread,
                    'execution_style': t.execution_style,
                }
                for t in self.trades
            ])
            trades_df.to_csv(output_dir / "trades.csv", index=False)
            print(f"Saved trades to: {output_dir / 'trades.csv'}")
        
        # Save position holdings
        if self.position_holdings:
            holdings_df = pd.DataFrame([
                {
                    'entry_date': h.entry_date,
                    'exit_date': h.exit_date,
                    'position': h.position.value,
                    'regime': h.regime.value,
                    'entry_spread': h.entry_spread,
                    'exit_spread': h.exit_spread,
                    'pnl': h.pnl,
                    'carry_pnl': h.carry_pnl,
                    'curve_pnl': h.curve_pnl,
                }
                for h in self.position_holdings
            ])
            holdings_df.to_csv(output_dir / "position_holdings.csv", index=False)
            print(f"Saved position holdings to: {output_dir / 'position_holdings.csv'}")


def main():
    """Main execution function."""
    # Initialize strategy with default parameters
    strategy = SteepenerStrategy(
        regime_threshold=0.5,  # 50% threshold for high uncertainty
        short_tenor="1y1y",
        long_tenor="3y3y",
        short_dv01=1.0,
        long_dv01=1.0,
        transaction_cost_bps=1.0,  # Cost of "paying the spread"
        carry_cost_bps=0.5,        # Benefit of "collecting carry"
    )
    
    # Load all data
    strategy.load_data()
    
    # Run backtest
    daily_pnl = strategy.run_backtest()
    
    # Print performance report
    strategy.print_report()
    
    # Save results
    strategy.save_results()
    
    return strategy


if __name__ == "__main__":
    strategy = main()
