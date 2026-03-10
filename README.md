# Schonfeld Primary Surplus Strategy Dashboard

A comprehensive Dash web application for analyzing and visualizing the Brazilian Interest Rate Steepener/Flattener Strategy based on fiscal uncertainty regimes.

## Overview

This dashboard provides interactive analytics for a quantitative trading strategy that:
- Takes **steepener** positions (long back leg, short front leg) when fiscal uncertainty is high
- Takes **flattener** positions (short back leg, long front leg) when fiscal uncertainty is low
- Uses Markov regime-switching models to identify uncertainty periods
- Implements PCA-based inflation filters (V6) to block trades during accelerating inflation

## Features

### 1. Performance Tab
- **Cumulative P&L Chart**: Total returns with regime background shading
- **Position Sizing**: Dynamic position visualization
- **Spread Analysis**: 1y1y-3y3y FRA spread tracking
- **Fiscal Uncertainty**: 4Y Primary Surplus Std Dev with rolling Z-score
- **Regime Probability**: Markov regime probability time series
- **Trading Details Explorer**: Date picker for point-in-time analysis

### 2. Market Variables Tab
- DI Swap rates (1Y, 2Y, 3Y, 6Y)
- FRA rates (1y1y vs 3y3y)
- Steepening spread visualization
- Mathematical formulas for rate calculations

### 3. Macro Variables Tab
- Primary surplus median forecasts (1Y vs 4Y)
- Standard deviation forecasts (uncertainty measure)
- Temporal interpolation methodology

### 4. Strategy Tab
- Steepening spread analysis
- Fiscal Uncertainty vs EPU (Economic Policy Uncertainty)
- VIX comparison (rhetorical risk factor)
- Focus Survey Expectations (IPCA & SELIC)
- PCA Analysis (full sample and dynamic)

### 5. V5 vs V6 Comparison
- Side-by-side cumulative P&L comparison
- P&L attribution comparison (Curve, Gamma, Carry, Cost)
- Drawdown comparison
- Risk-off period highlighting (V6)
- Comprehensive metrics table

### 6. Risk Management Tab
- **3D Yield Curve Surface**: Weekly DI swap curve evolution
- **Swap Curve PCA**: Level, slope, curvature factors
- **DV01 Analysis**: Portfolio-scaled risk exposure
- **VaR/ES Charts**: Position-weighted Value at Risk and Expected Shortfall
- **Carry & Roll-Down**: Position-scaled carry attribution
- **Rolling Correlation**: FRA 1y1y vs 3y3y correlation analysis
- **Portfolio Exposure**: Gross/net exposure breakdown

### 7. P&L Attribution Tab
- Cumulative attribution (Curve, Gamma, Carry, Cost)
- Monthly waterfall charts
- Total attribution summary
- Daily decomposition

### 8. Performance Attribution Tab
- Drawdown analysis from peak
- Rolling Sharpe ratio
- Monthly P&L heatmap
- Regime-conditional performance

## File Structure

```
├── web/
│   ├── app.py              # Main Dash application (~4200 lines)
│   ├── __init__.py
│   └── assets/
│       └── style.css       # Schonfeld-themed styling
├── src/
│   ├── data/
│   │   ├── processed/      # Generated data files (NOT in git)
│   │   │   ├── b3/
│   │   │   │   ├── predi_252_pivot.csv
│   │   │   │   └── predi_fra_1y1y_3y3y.csv
│   │   │   ├── calendar/
│   │   │   │   ├── copom_meetings.csv
│   │   │   │   └── fiscal_release_dates.csv
│   │   │   ├── focus/
│   │   │   │   ├── primary_1y_3y_4y_interp.csv
│   │   │   │   ├── ipca_12m_forecast.csv
│   │   │   │   └── selic_1y_forecast.csv
│   │   │   ├── regime_analysis/    # Point-in-time regime files
│   │   │   ├── strategy_results_v5/  # V5 backtest results
│   │   │   │   ├── daily_pnl.csv
│   │   │   │   └── trades.csv
│   │   │   └── strategy_results_v6/  # V6 backtest results
│   │   │       ├── daily_pnl.csv
│   │   │       └── trades.csv
│   │   ├── api/            # Data fetching modules
│   │   └── processing/     # Data processing scripts
│   └── steepener_strategy_v*.py  # Strategy implementations
├── notebook/
│   ├── schonfeld_fiscal_regime_steepening_strategy.ipynb  # Main notebook
│   └── v5_v6_strategy_comparison.ipynb
└── [root cache files - see below]
```

## Critical: Required Data Files

### ⚠️ IMPORTANT - Git Repository Status

**After cloning this repository, the app will NOT run immediately.** The processed data files in `src/data/processed/` are **NOT tracked in git** (they are in `.gitignore`) because they are large generated files.

### Tracked Cache Files (Included in Git)

These root-level cache files ARE tracked and will be available after cloning:

| File | Description | Size |
|------|-------------|------|
| `b3_predi_cache.csv` | B3 Pre-DI swap rates raw data | ~32 MB |
| `focus_primary_cache.csv` | FOCUS primary surplus forecasts | ~2 MB |
| `epu_cache.csv` | Brazil Economic Policy Uncertainty data | ~12 KB |
| `selic_raw_cache.csv` | SELIC rate forecasts raw data | ~4 MB |
| `vix_cache.csv` | VIX volatility index (auto-updates) | ~150 KB |
| `ipca_12m_cache.csv` | IPCA inflation forecasts | ~115 KB |
| `copom_meetings_cache.json` | COPOM meeting dates | ~15 KB |
| `markov_regime_probs_cache.pkl` | Pre-computed Markov regime probabilities | ~280 KB |
| `pca_regimes_cache.pkl` | PCA regime classification cache | ~150 KB |

### Required Generated Files (NOW in Git)

These files are now tracked in git and will be available after clone:

**B3 Market Data (~1.4 MB):**
- `src/data/processed/b3/predi_252_pivot.csv` - DI swap rates pivot table
- `src/data/processed/b3/predi_fra_1y1y_3y3y.csv` - Forward rate agreements

**Calendar Data (~36 KB):**
- `src/data/processed/calendar/copom_meetings.csv` - COPOM meeting schedule
- `src/data/processed/calendar/fiscal_release_dates.csv` - FOCUS release dates

**FOCUS Forecasts (~1.2 MB):**
- `src/data/processed/focus/primary_1y_3y_4y_interp.csv` - Interpolated fiscal forecasts
- `src/data/processed/focus/ipca_12m_forecast.csv` - IPCA 12M forecasts
- `src/data/processed/focus/selic_1y_forecast.csv` - SELIC 1Y forecasts

**Strategy Results (~2.4 MB):**
- `src/data/processed/strategy_results_v5/daily_pnl.csv` - V5 daily P&L
- `src/data/processed/strategy_results_v5/trades.csv` - V5 trade log
- `src/data/processed/strategy_results_v6/daily_pnl.csv` - V6 daily P&L
- `src/data/processed/strategy_results_v6/trades.csv` - V6 trade log

**Note:** Regime analysis files (`regime_analysis/regime_probs_*.csv`) are NOT tracked (~141 MB) but are optional - the app uses `prob_high_vol` from the strategy CSVs instead.

## Installation

### Prerequisites
- Python 3.13+
- uv (recommended) or pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd schonfeld-ms-primary-surplus

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

## Running the Application

### Quick Start (No Data Generation Required)

The processed data files are now tracked in git, so you can run the app immediately after cloning:

```bash
# Clone and setup
git clone <repository-url>
cd schonfeld-ms-primary-surplus
uv sync  # or: pip install -e .

# Run the dashboard directly
python web/app.py
```

The app will be available at `http://localhost:8050`

### Optional: Regenerate Data from Notebook

If you want to run the full pipeline or modify the strategy:

```bash
jupyter notebook notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb
```
Execute all cells to regenerate processed data files.

### Optional: Run Strategy Scripts Directly

```bash
python src/steepener_strategy_v5.py
python src/steepener_strategy_v6.py
```

```bash
# From the project root
python web/app.py
```

The app will start on `http://localhost:8050`

## Data Sources

| Source | Data | URL |
|--------|------|-----|
| B3 | DI Futures (Pre-DI) | https://www.b3.com.br |
| BCB Focus | Economic forecasts | https://www3.bcb.gov.br/expectativas |
| PolicyUncertainty.com | Brazil EPU | https://www.policyuncertainty.com |
| FRED | VIX Index | https://fred.stlouisfed.org |

## Strategy Versions

### V5 (Advanced Dynamic Size)
- Dynamic position sizing based on fiscal uncertainty
- 3-regime classification (high/medium/low uncertainty)
- No inflation filter

### V6 (PCA Inflation Filter)
- All V5 features PLUS
- PCA-based inflation acceleration detection
- Risk-off periods during accelerating inflation
- Enhanced Sharpe ratio through regime filtering

## Key Metrics Displayed

- **Total Return**: Cumulative strategy return in basis points
- **Sharpe Ratio**: Risk-adjusted return metric
- **Win Rate**: Percentage of positive P&L days
- **Number of Trades**: Total position changes
- **Max Drawdown**: Largest peak-to-trough decline
- **VaR/ES**: Value at Risk and Expected Shortfall

## P&L Attribution Components

1. **Curve PnL**: First-order spread changes (DV01-neutral)
2. **Gamma PnL**: Second-order convexity effects
3. **Carry PnL**: Roll-down and carry earnings
4. **Cost PnL**: Execution costs and market impact

## Styling

The dashboard uses Schonfeld's brand colors:
- Primary Accent: `#00acac` (Teal)
- Soft Black: `#282828`
- Soft Grey: `#f2ece3`
- Gold/Khaki: `#b4a680`

Font: Unica77LLSub (with Verdana fallback)

## Troubleshooting

### App fails to start with "File not found" errors
This should not happen if you cloned the repository correctly. The processed data files are now tracked in git.
- If you manually deleted `src/data/processed/` files, restore them: `git checkout src/data/processed/`
- Check that all cache files exist in the root directory

### VIX data not loading
- The app will use cached VIX data if available
- If cache is stale (>7 days), it attempts to fetch from FRED
- Check internet connection for auto-updates

### Regime shading not appearing
- Ensure `strategy_results_v5/` or `strategy_results_v6/` directories exist
- Check that `daily_pnl.csv` contains `prob_high_vol` column

## Development

### Adding New Tabs
1. Create chart functions in `web/app.py`
2. Define tab content HTML in the appropriate section
3. Add callback for interactivity

### Modifying Data Pipeline
- Edit files in `src/data/processing/` for data transformations
- Update API modules in `src/data/api/` for new data sources
- Regenerate processed files by re-running the notebook

## License

This project is for educational and demonstration purposes as part of a quantitative research case study.

## Contact

For questions about the strategy or dashboard, refer to the project documentation in the repository.
