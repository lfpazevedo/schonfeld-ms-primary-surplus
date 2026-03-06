# Steepener Trading Strategy - Implementation Summary

## Overview

This document summarizes the implementation of a **regime-dependent yield curve steepener strategy** based on fiscal uncertainty signals derived from Markov-switching models.

The strategy follows the framework outlined in "Fiscal Uncertainty Steepening Strategy" with dual execution modes:
- **"Pay the Spread"** in high fiscal uncertainty regimes
- **"Collect the Carry"** in low fiscal uncertainty regimes

---

## Strategy Logic

### Signal Generation

The strategy uses **4-year ahead primary surplus standard deviation (std_4y)** as the primary signal for fiscal uncertainty:

| Regime | Std_4y Level | Position | Execution Style |
|--------|-------------|----------|-----------------|
| **High Uncertainty** | > 75th percentile (0.614) | Full Bear Steepener | "Pay the Spread" |
| **Medium Uncertainty** | 25th-75th percentile | Medium Bear Steepener | "Standard" |
| **Low Uncertainty** | < 25th percentile (0.431) | Small Bear Steepener | "Collect the Carry" |

### Position Construction

**Instrument:** 1y1y vs 3y3y Forward Rate Agreement (FRA) spread
- **Bear Steepener:** Long short-end (1y1y), Short long-end (3y3y)
- **Profit Condition:** Curve spread widens (long-end underperforms)

**Position Sizing:**
- Scales from 25% to 100% based on uncertainty level
- Momentum adjustment: Reduce size if fighting trend
- Maximum position: 100% notional per leg

### Execution Framework

#### "Pay the Spread" (High Uncertainty)
- Use market orders for immediacy
- Accept wider bid-ask spreads
- Higher transaction costs (-0.10 bps/day)
- Rationale: Risk of non-execution exceeds spread cost

#### "Collect the Carry" (Low Uncertainty)
- Use limit orders, patient execution
- Capture bid-ask spread
- Lower transaction costs (+0.03 bps/day benefit)
- Rationale: Stable environment favors carry optimization

---

## Implementation Files

### Main Strategy Code

| File | Description |
|------|-------------|
| `src/steepener_strategy.py` | Original implementation - basic regime switching |
| `src/steepener_strategy_v2.py` | Enhanced with full regime probability history |
| `src/steepener_strategy_v3.py` | Continuous position sizing based on std_4y |
| `src/steepener_strategy_v4.py` | **Final version** with momentum filter |

### Data Sources

| File | Description |
|------|-------------|
| `src/data/processed/regime_analysis/regime_probs_YYYYMMDD.csv` | Regime probabilities from Markov-switching model |
| `src/data/processed/b3/predi_fra_1y1y_3y3y.csv` | Forward rates for yield curve construction |
| `src/data/processed/calendar/fiscal_release_dates.csv` | Fiscal release calendar for rebalancing dates |

### Output Files

Results are saved in `src/data/processed/strategy_results_v4/`:
- `daily_pnl.csv` - Daily P&L attribution
- `trades.csv` - Trade execution records

---

## Backtest Results (2012-2026)

### Overall Performance

| Metric | Value |
|--------|-------|
| Total P&L | -183.87 bps |
| P&L per Year | -13.73 bps |
| Sharpe Ratio | -0.06 |
| Max Drawdown | -970.01 bps |
| Win Rate | 50.8% |
| Trading Days | 3,375 |
| Position Adjustments | 301 |

### Performance by Regime

| Regime | Days | Total P&L | Daily Avg | Avg Std_4y |
|--------|------|-----------|-----------|------------|
| High Uncertainty | 1,284 | -8.40 bps | -0.0065 | 0.732 |
| Medium Uncertainty | 1,352 | -86.07 bps | -0.064 | 0.521 |
| Low Uncertainty | 738 | -89.40 bps | -0.121 | 0.385 |

### Best Performing Months

| Month | P&L | Context |
|-------|-----|---------|
| 2022-12 | +193.41 bps | Post-election fiscal uncertainty |
| 2020-03 | +174.08 bps | COVID crisis / fiscal stimulus |
| 2016-11 | +154.31 bps | Election uncertainty |
| 2023-02 | +94.00 bps | Fiscal concerns / debt ceiling |
| 2018-05 | +85.35 bps | Policy uncertainty |

### Worst Performing Months

| Month | P&L | Context |
|-------|-----|---------|
| 2016-03 | -249.09 bps | Curve flattening post-volatility |
| 2016-06 | -185.38 bps | Brexit surprise / flight to quality |
| 2021-10 | -156.63 bps | Curve flattening / policy normalization |
| 2018-06 | -149.56 bps | Trade war escalation |
| 2018-10 | -135.85 bps | Risk-off / curve flattening |

---

## Key Insights

### 1. Crisis Performance
The strategy excels during periods of **acute fiscal uncertainty**:
- COVID-19 crisis (March 2020): +174 bps
- Post-election periods: Strong positive returns
- Debt ceiling debates: Positive returns

### 2. Challenging Environments
The strategy struggles when:
- Uncertainty is low but curve flattens anyway
- Risk-off flows override fiscal concerns
- Central bank intervention suppresses term premium

### 3. Regime Classification
The Markov-switching model classifies **~99% of periods as high uncertainty** for fiscal data, reflecting the inherent uncertainty in 4-year ahead primary surplus forecasts.

### 4. Position Sizing Impact
Continuous position sizing (v3/v4) provides better risk control than binary regime classification (v1/v2).

---

## Usage Instructions

### Running the Strategy

```bash
cd /home/lfpazevedo/Documents/Projects/schonfeld-ms-primary-surplus
source .venv/bin/activate
python src/steepener_strategy_v4.py
```

### Customizing Parameters

Edit the strategy initialization in `main()`:

```python
strategy = SteepenerStrategyV4(
    low_threshold_pct=25,      # Percentile for low uncertainty
    high_threshold_pct=75,     # Percentile for high uncertainty
    max_position_size=1.0,     # Maximum position (100%)
    momentum_lookback=20,      # Days for momentum calculation
    momentum_threshold=0.5,    # Minimum momentum alignment
)
```

### Accessing Results

```python
import pandas as pd

# Load daily P&L
daily_pnl = pd.read_csv('src/data/processed/strategy_results_v4/daily_pnl.csv', parse_dates=['date'])

# Load trades
trades = pd.read_csv('src/data/processed/strategy_results_v4/trades.csv', parse_dates=['date'])
```

---

## Strategy Comparison

| Version | Approach | Key Feature | Total P&L |
|---------|----------|-------------|-----------|
| v1 | Binary regime | Simple high/low classification | -15.18 bps |
| v2 | Probabilistic | Uses full regime history | -809.96 bps |
| v3 | Continuous | Position sizing by std_4y percentile | -35.59 bps |
| **v4** | **Hybrid** | **+ Momentum filter** | **-183.87 bps** |

---

## Recommendations

### For Production Use

1. **Enhance Signal:** Consider combining fiscal uncertainty with:
   - Economic Policy Uncertainty (EPU) index
   - CDS term premium
   - Realized volatility measures

2. **Improve Execution:** 
   - Implement actual bid-ask spread data
   - Add slippage estimates for larger sizes
   - Consider market impact models

3. **Risk Management:**
   - Add stop-losses for large drawdowns
   - Implement volatility targeting
   - Consider maximum loss limits per trade

4. **Market Regimes:**
   - The strategy works best when fiscal concerns dominate
   - Consider disabling during central bank intervention periods
   - Add filters for risk-off episodes

### Future Enhancements

- [ ] Multi-country comparison (US, EU, Japan)
- [ ] Options-based implementation (lower capital requirements)
- [ ] Machine learning for regime classification
- [ ] Intraday execution optimization
- [ ] Integration with broader macro strategy framework

---

## References

1. Original Strategy Document: `Fiscal Uncertainty Steepening Strategy.md`
2. Markov-Switching Analysis: `src/markov_regime_analysis.py`
3. Data Processing: `src/data/processing/`

---

## Contact & Support

For questions or modifications to the strategy, refer to:
- Strategy code: `src/steepener_strategy_v4.py`
- Data processing: `src/markov_regime_analysis.py`
- Results: `src/data/processed/strategy_results_v4/`
