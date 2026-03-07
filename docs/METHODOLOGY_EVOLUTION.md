# Strategy Methodology Evolution & Critical Findings

> **⚠️ IMPORTANT**: Versions 1–4 are INVALID for trading decisions due to look-ahead bias. See details below.

---

## Executive Summary

This document tracks the evolution of the steepener strategy from V1 to V6, highlighting critical methodological errors discovered during research and the fixes applied.

| Version | Status | Key Finding | Valid for Trading? |
|---------|--------|-------------|-------------------|
| V1–V4 | **INVALIDATED** | Look-ahead bias + conceptual error | ❌ **NO** |
| V5 | **DEPRECATED** | Fixed look-ahead, normalization issues | ⚠️ Partial |
| V6 | **CURRENT** | Expanding window + PCA filter | ✅ Conditional |
| V7 | **PLANNED** | Proper uncertainty measures | 🔄 In Design |

---

## Critical Finding #1: Look-Ahead Bias in V1–V4

### The Problem

V1–V4 computed regime thresholds using **full-sample statistics** (2001–2026), giving the model perfect knowledge of future data when making historical decisions.

```python
# V3/V4 CODE (INVALID - Look-ahead bias)
def calculate_regime_thresholds(self):
    # ❌ Uses data from 2001-2026 even when "trading" in 2012!
    low_threshold = np.percentile(self.regime_ts['std_4y'], 25)
    high_threshold = np.percentile(self.regime_ts['std_4y'], 75)
    return low_threshold, high_threshold
```

### Impact

| Version | Reported P&L | Estimated True P&L | Inflation |
|---------|--------------|-------------------|-----------|
| V3 | −35.59 bps | −60 to −120 bps | ~50-100% |
| V4 | −183.87 bps | −200 to −300 bps | ~10-30% |

### The Fix (V5+)

```python
# V5+ CODE (VALID - Expanding window)
def compute_regime_zscore_expanding(self, series):
    results = []
    for i in range(len(series)):
        if i < self.min_obs:
            results.append(np.nan)
        else:
            # ✅ Only uses data[0:i] at time i
            historical = series.iloc[:i]
            z = (series.iloc[i] - historical.mean()) / historical.std()
            results.append(z)
    return pd.Series(results, index=series.index)
```

---

## Critical Finding #2: Cross-Sectional vs. Time-Series Confusion

### The Problem

The Focus `std_4y` measure represents **disagreement among forecasters** (cross-sectional), NOT **uncertainty in the forecast over time** (time-series).

### What Focus Std Dev Actually Measures

```
Survey Date: January 15, 2024
Reference Year: 2028 (4-year ahead)

Institution          Forecast
─────────────────────────────
Hedge Fund A         -1.2%
Hedge Fund B         -0.8%
Bank C               -1.5%
Asset Manager D      -0.5%

Std Dev = 0.35%  ← CROSS-SECTIONAL dispersion
                 (how much forecasters disagree TODAY)
```

### What We Should Measure

```
Date          Median     Change
─────────────────────────────────
Jan 15, 2024  -1.0%      │
Feb 15, 2024  -1.2%      │  TIME-SERIES volatility
Mar 15, 2024  -0.9%      │  (how much forecasts change)
Apr 15, 2024  -1.3%      │

Std Dev of Changes = 0.18%  ← TIME-SERIES uncertainty
```

### Why This Matters

| Scenario | Focus Std (Cross-Sectional) | True Uncertainty | Model Action | Reality |
|----------|----------------------------|------------------|--------------|---------|
| Consensus Crisis | LOW | HIGH | Trade | Shouldn't trade |
| Divided Outlook | HIGH | LOW | No Trade | Should trade |

### The Fix (V7 - Planned)

```python
# CORRECT: Time-series volatility
def compute_time_series_volatility(series, window=63):
    """Volatility of consensus forecast changes over time."""
    changes = series.diff()
    return changes.rolling(window=window).std() * np.sqrt(252)

# CORRECT: Composite uncertainty index
def create_composite_uncertainty_index(df):
    return (
        0.4 * time_series_volatility(df['median_4y']) +
        0.3 * forecast_revisions(df['median_4y']) +
        0.2 * cross_sectional_dispersion(df['std_4y']) +
        0.1 * time_series_volatility(df['median_1y'])
    )
```

---

## Version-by-Version Breakdown

### V1: Baseline
- **Status**: Invalidated
- **Issues**: Undocumented methodology, likely look-ahead bias
- **Lesson**: Document assumptions from day one

### V2: Enhanced
- **Status**: Invalidated
- **Issues**: Inherits V1 issues, unclear improvements
- **Lesson**: Version control must track methodology changes

### V3: Regime Detection
- **Status**: **INVALIDATED — Critical**
- **Issues**: 
  - Full-sample percentiles (look-ahead bias)
  - Cross-sectional std used as regime indicator
- **Reported P&L**: −35.59 bps
- **True P&L Estimate**: −60 to −120 bps

### V4: Position Sizing
- **Status**: **INVALIDATED — Critical**
- **Issues**:
  - Same look-ahead bias as V3
  - `max()` normalization uses future data
- **Reported P&L**: −183.87 bps
- **True P&L Estimate**: −200 to −300 bps

### V5: Expanding Window
- **Status**: Deprecated
- **Improvements**:
  - ✅ Fixed look-ahead bias (expanding window)
  - Still uses wrong uncertainty measure
- **Issues**:
  - Rolling window normalization (boiled frog problem)
- **Action**: Superseded by V6

### V6: PCA Filter + Expanding Window
- **Status**: **Current — Conditional Validity**
- **Improvements**:
  - ✅ Fixed look-ahead bias
  - ✅ Fixed normalization (expanding window PCA)
  - ✅ Added inflation expectations filter
- **Issues**:
  - Still uses Focus std (cross-sectional) as uncertainty measure
  - PCA complexity adds model risk
- **Conditions for Use**:
  - Re-run with proper uncertainty measure (see V7)
  - Out-of-sample validation required

### V7: Proper Uncertainty Measures (Planned)
- **Status**: In Design
- **Features**:
  - Time-series volatility measures
  - Composite uncertainty index
  - Out-of-sample validation protocol
- **Target**: Production-ready

---

## The "Boiled Frog" Problem (V5 → V6 Fix)

### The Issue

Rolling windows normalize persistent regime shifts:

```
Inflation jumps from 3% → 6% and stays there:

Rolling 1-Year Window (V5 - PROBLEMATIC):
  Year 1: PC1 [-2, +2] → 3% = "normal"
  Year 2: PC1 [+2, +4] → 6% = "high" ✓
  Year 3: PC1 [+2, +4] → 6% = "medium" (forgot 3% existed!)

Expanding Window (V6+ - CORRECT):
  Year 1: PC1 [-2, +2] → 3% = "normal"
  Year 2: PC1 [-2, +4] → 6% = "high" ✓
  Year 3: PC1 [-2, +4] → 6% = "high" (remembers 3% baseline) ✓
```

### V6 Fix

```python
# V6: Expanding window PCA
def compute_dynamic_pca(self, end_date, ...):
    # Uses ALL data from start to end_date
    window_df = merged_data[merged_data["date"] <= end_date].copy()
    
    # No rolling cutoff — full history preserved
    if len(window_df) > self.pca_lookback:  # REMOVED
        window_df = window_df.iloc[-self.pca_lookback:]  # REMOVED
    
    # ... rest of PCA computation
```

---

## Validation Protocol

### Current Status

| Stage | V3 | V4 | V5 | V6 | V7 |
|-------|----|----|----|----|----|
| Backtest | ❌ Invalid | ❌ Invalid | ✅ Valid | ✅ Valid | 🔄 Planned |
| Out-of-Sample | ❌ N/A | ❌ N/A | ⚠️ Missing | ⚠️ Missing | 🔄 Planned |
| Paper Trading | ❌ N/A | ❌ N/A | ❌ No | ❌ No | 🔄 Planned |

### Required for Production

1. **Backtest**: 2001–2022 (expanding window, no look-ahead)
2. **Validation**: 2023–2024 (unseen data, frozen hyperparameters)
3. **Paper Trading**: 6 months (real-time, no hindsight)
4. **Sharpe Threshold**: > 0.5 in all three stages

---

## References

### Internal Documents
- `docs/STUDY_LOOKAHEAD_BIAS_AND_FOCUS_STD_DEV.md` — Detailed analysis
- `docs/STRATEGY_VERSION_VALIDITY_MATRIX.md` — Quick reference
- `src/data/processing/focus/proper_uncertainty_measures.py` — Correct implementations

### External References
- Bailey & López de Prado (2014): "The Deflated Sharpe Ratio"
- Bloom (2014): "Fluctuations in Uncertainty"
- Hamilton (1989): Markov-switching models

---

## Action Items

### Immediate (This Week)
- [x] Document look-ahead bias findings
- [x] Invalidate V1–V4 results
- [ ] Archive V1–V4 backtests with watermark
- [ ] Brief stakeholders

### Short-Term (This Month)
- [ ] Implement proper uncertainty measures (V7 design)
- [ ] Re-run V3/V4 with expanding windows (comparison only)
- [ ] Run V6 out-of-sample validation

### Medium-Term (This Quarter)
- [ ] Complete V7 implementation
- [ ] 3-stage validation protocol
- [ ] Documentation & white paper

### Long-Term (6 Months)
- [ ] Production deployment (if validation passes)
- [ ] Monitoring framework
- [ ] Quarterly review process

---

*Document Version: 1.0*
*Last Updated: March 6, 2026*
*Owner: Quantitative Research Team*
