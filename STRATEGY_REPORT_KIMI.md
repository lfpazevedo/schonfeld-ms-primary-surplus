I'll analyze the evolution of these steepener strategies from V1 through V6 and provide actionable improvement recommendations.

---

# Steepener Strategy Evolution Report
## Fiscal Uncertainty-Based Curve Trading Framework

### Executive Summary

This codebase represents a sophisticated evolution of a **Brazilian DI Futures steepener strategy** (1y1y vs 3y3y) that trades based on fiscal uncertainty regimes derived from Markov-switching models. The progression shows a maturation from simple binary regime classification to a multi-factor, risk-managed system with macro-economic filtering.

**Core Thesis**: High fiscal uncertainty (measured by forecast dispersion of Brazil's primary surplus) drives term premium expansion, causing bear steepening (long-end sells off relative to short-end). The strategy scales exposure based on regime confidence while protecting against inflationary tail risks.

---

## Strategy Evolution Analysis

### V1: Foundation (Binary Regime Classification)
**Innovation**: Basic Markov-switching integration
- **Signal**: Binary classification (High/Low uncertainty) using `prob_high_vol > 0.5`
- **Execution**: 
  - High uncertainty → "Pay the Spread" (Bear steepener, market orders)
  - Low uncertainty → "Collect the Carry" (Bull steepener/carry optimization)
- **Limitations**: Discrete jumps, no position sizing granularity, static holding periods between fiscal releases

### V2: Probabilistic Position Sizing
**Innovation**: Continuous position scaling
- **Signal**: Position size scales 50%→100% based on regime strength
  - `position_size = 0.5 + 0.5 * regime_strength`
- **Improvement**: Smoother transitions, confidence-weighted exposure
- **Limitations**: Still reactive rather than predictive; no dynamic risk management

### V3: Uncertainty Percentile-Based Sizing
**Innovation**: Direct fiscal uncertainty (std_4y) percentile mapping
- **Signal**: 
  - <25th percentile: 0-25% size (flattener bias)
  - 25-75th percentile: 25-75% size (linear scaling)
  - >75th percentile: 75-100% size (full bear steepener)
- **Logic**: Magnitude of uncertainty drives steepening pressure intensity
- **Limitations**: Static thresholds, no trend/momentum confirmation

### V4: Momentum Filtering
**Innovation**: Trend confirmation layer
- **Addition**: Spread vs 20-day moving average momentum filter
- **Logic**: 
  - Spread compressed vs MA (+10% size) → mean reversion opportunity
  - Spread extended vs MA (-30% size) → avoid chasing
- **Execution**: Different cost structures by regime (high uncertainty = higher slippage)
- **Limitations**: Look-ahead bias in percentile calculations (uses full-sample stats)

### V5: Production-Grade Risk Management ⭐
**Major Leap**: Institutional-quality implementation
- **Rolling Statistics**: Expanding-window Z-scores (no look-ahead bias)
- **DV01-Neutral Construction**: Properly weighted 1y1y vs 3y3y legs
  - DV01_1Y1Y = 0.98, DV01_3Y3Y = 2.72
  - Isolates curve steepening from parallel shifts
- **Non-Linear Costs**: `cost = base_spread + impact_factor × size²`
- **Trailing Stop-Loss**: 50bps trailing drawdown with regime-normalized reset
- **Markov Scaling**: Z-score primary signal, Markov probability for confidence adjustment

### V6: Macro Regime Filtering (Current State-of-Art) ⭐⭐
**Innovation**: Inflation expectations PCA overlay
- **Dynamic PCA**: Rolling 252-day PCA on:
  - IPCA 12-month forecasts (inflation)
  - Selic 1-year expectations (monetary policy)
  - Fiscal uncertainty (std_4y)
- **3-Regime Markov**: Low/Medium/High inflation expectations
- **Risk Filter**: **NO POSITION** when PCA indicates "high" inflation regime (>60% probability)
  - Prevents steepening positions when inflation is at extremes (Central Bank hawkishness risk)
- **Smart Sampling**: Computes Markov only on fiscal release dates for efficiency

---

## Technical Architecture Assessment

### Strengths

1. **Data Handling Excellence**
   - Proper expanding-window calculations (V5+) eliminate look-ahead bias
   - Fiscal calendar integration (Anbima release dates)
   - Forward-fill methodology for regime probabilities

2. **Risk-Adjusted Position Sizing**
   - DV01-neutral construction removes directional duration risk
   - Non-linear impact model accounts for market depth constraints
   - Dual stop-loss regime (hard stop + normalized reset)

3. **Multi-Layer Signal Architecture**
   - Primary: Fiscal uncertainty Z-score
   - Secondary: Markov regime persistence
   - Tertiary (V6): Inflation macro filter

### Critical Vulnerabilities

1. **Model Risk Concentration**
   - Heavy reliance on Markov-switching assumptions (constant transition probabilities)
   - PCA components may flip signs across windows (interpretability risk)
   - Single-factor signal (fiscal) dominates; vulnerable to regime changes in fiscal-monetary interaction

2. **Execution Assumptions**
   - Static DV01 ratios (0.98/2.72) ignore convexity and term structure changes
   - No liquidity scaling (Brazilian DI market depth varies significantly by contract)
   - Assumes continuous pricing; ignores roll timing and calendar effects

3. **Cost Structure Realism**
   - `base_spread_cost = 0.02bps` likely optimistic for Brazilian FRAs during stress
   - No funding cost differential (short-end vs long-end carry funding)
   - Missing exchange/B3 fees and brokerage

---

## Improvement Recommendations

### 1. Signal Enhancement

**Microstructure Signal Integration**
```python
# Add order flow imbalance from B3 data
def calculate_flow_toxicity(vpin_data, threshold=0.6):
    """
    VPIN (Volume-synchronized Probability of Informed Trading)
    High VPIN + fiscal uncertainty = stronger steepening signal
    """
    return position_size * (1 + vpin_normalized)
```

**Cross-Asset Validation**
- **FX Component**: USD/BRL implied volatility vs fiscal uncertainty spread
  - If fiscal uncertainty high but FX vol low → skepticism of steepening (possible arbitrage)
- **CDS Integration**: Brazil 5y CDS vs local curve steepness
  - Divergence indicates offshore/onshore regime mismatch

**Alternative Fiscal Measures**
- Primary balance revisions (change in consensus mean), not just dispersion
- Revenue vs expenditure uncertainty decomposition
- Real-time Tesouro Nacional issuance calendar (supply risk)

### 2. Execution & Market Microstructure

**Dynamic DV01 Scaling**
```python
def get_dv01_ratio(date, yield_curve):
    """
    Adjust DV01 weights based on curve steepness
    Steeper curve = higher duration risk in long end
    """
    slope = yield_curve['3y3y'] - yield_curve['1y1y']
    adjustment = 1 + (slope - historical_mean_slope) * convexity_factor
    return DV01_3Y3Y * adjustment
```

**Liquidity-Adjusted Sizing**
```python
def apply_liquidity_discount(position_size, contract_volume):
    """
    Reduce size in illiquid periods (year-end, election periods)
    """
    if contract_volume < volume_threshold:
        return position_size * (contract_volume / volume_threshold) ** 0.5
    return position_size
```

**Roll Optimization**
- Current implementation ignores the 1y1y→1y roll and 3y3y→3y3y roll mechanics
- Add roll yield capture: Enter front vs back contracts based on carry/roll matrix

### 3. Advanced Risk Management

**Correlation Regime Switching**
```python
# Add to V6's PCA filter
def check_rates_vol_regime(vix_proxy):
    """
    If rates vol spikes (MOVE index equivalent), 
    disable steepener regardless of fiscal signal
    """
    if rates_vol > percentile_90:
        return "risk_off_vol_spike"
```

**Tail Risk Hedging**
- **Wings**: Cheap payer swaptions on long leg during extreme fiscal stress (>90th percentile std_4y)
- **Skew**: Monitor 25d risk reversal in DI options; if puts expensive, fade steepener

**Drawdown Circuit Breakers**
- Current: 50bps trailing stop
- Proposed: Tiered stops based on volatility regime
  - Low vol regime: 30bps (tight)
  - High vol regime: 80bps (wider to avoid whipshaw)

### 4. Machine Learning Enhancements

**Ensemble Regime Detection**
Replace single Markov model with:
1. **HMM (Hidden Markov Model)**: For robustness to outliers
2. **Random Forest**: Feature importance on macro variables
3. **LSTM**: Sequence modeling for regime persistence prediction

**Meta-Labeling** (from Lopez de Prado)
```python
def meta_labeling(primary_model_predictions, bar_data):
    """
    Use ML to predict when primary model is likely correct
    Train on subsequent return direction vs prediction
    """
    features = [volatility_regime, trend_strength, macro_surprise]
    # Only trade if meta-model probability > 0.6
```

### 5. Operational Improvements

**Transaction Cost Model Refinement**
| Component | Current | Recommended |
|-----------|---------|-------------|
| Base spread | 0.02bps | Dynamic: 0.02-0.10bps based on VIX |
| Impact factor | 0.05 × size² | 0.05 × size^1.5 (concave, not quadratic) |
| Slippage | None | Add 0.01bps per day of holding (time decay) |

**Funding Cost Integration**
```python
def calculate_net_carry(position_size, selic_path, di_curve):
    """
    Bear steepener = long short-end (pay funding), short long-end (receive)
    If Selic > long-end yield, negative carry hurts
    """
    funding_cost = selic - di_curve['3y3y']
    return position_size * funding_cost * holding_days
```

### 6. Robustness Testing

**Synthetic Stress Tests**
- **Taper Tantrum Replay**: 2013-style selloff with current position sizing
- **COVID Shock**: Front-end freeze with long-end illiquidity
- **Election Scenarios**: Historical Brazilian election volatility (2018, 2022)

**Walk-Forward Optimization**
- V5 uses expanding window, but parameters (Z-score thresholds) are static
- Implement quarterly recalibration of `zscore_high`, `zscore_low` using walk-forward CV

---

## Implementation Priority Matrix

| Priority | Improvement | Expected Impact | Complexity |
|----------|-------------|----------------|------------|
| **P0** | Add funding cost model | High (avoid negative carry traps) | Low |
| **P0** | Liquidity-adjusted sizing | High (prevents blow-ups in stress) | Medium |
| **P1** | Cross-asset validation (FX/CDS) | Medium (reduces false signals) | Medium |
| **P1** | Tail risk hedging (swaptions) | High (convexity protection) | High |
| **P2** | Meta-labeling layer | Medium (improves Sharpe) | High |
| **P2** | Roll optimization | Medium (adds carry alpha) | Medium |
| **P3** | HMM ensemble | Low-Medium (robustness) | High |

---

## Conclusion

The evolution from V1→V6 demonstrates institutional maturation: **from a binary signal generator to a risk-managed, multi-factor macro system**. The V6 implementation with PCA-based inflation filtering is particularly sophisticated—it recognizes that fiscal uncertainty steepening only works when monetary policy isn't in aggressive tightening mode.

**Immediate Action Items**:
1. **Validate the PCA sign stability**—ensure PC1 consistently points to "inflationary pressure" across different windows
2. **Add funding cost math**—the current P&L ignores carry cost asymmetry between legs
3. **Implement liquidity scalars**—Brazilian DI market depth is highly variable; position sizing should respect this

The architecture is sound for a quantitative relative value book, but requires the recommended execution and risk overlays before live capital deployment.