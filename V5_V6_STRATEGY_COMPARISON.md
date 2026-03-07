# Steepener Strategy V5 vs V6: Detailed Comparison Report

**Date:** March 7, 2026  
**Author:** Kimi Code Analysis  
**Purpose:** Technical comparison of strategy versions V5 (Advanced Dynamic Size) and V6 (PCA Inflation Filter)

---

## Executive Summary

| Aspect | V5 | V6 |
|--------|-----|-----|
| **Primary Signal** | Z-score of fiscal uncertainty (std_4y) | Same as V5 |
| **Secondary Signal** | 2-regime Markov (trend confirmation) | 2-regime Markov + **3-regime PCA filter** |
| **Regime System** | Single: Fiscal uncertainty | **Dual:** Fiscal + Inflation/SELIC PCA |
| **Trade Blocking** | ❌ No | ✅ Yes (inflation high) |
| **Combined Regimes** | ❌ No | ✅ 4-quadrant classification |
| **Protection Type** | Fiscal only | Fiscal + **Inflation/Selic macro filter** |

---

## 1. Signal Architecture

### 1.1 V5: Two-Layer Signal System

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Primary Signal (Z-Score)                          │
│  ─────────────────────────────────                          │
│  std_4y_zscore = (std_4y - expanding_mean) / expanding_std  │
│                                                             │
│  • Z > +0.5  →  Bear steepener (raw size 0.5 to 1.0)        │
│  • Z < -0.5  →  Flattener (raw size -0.25 to -0.5)          │
│  • |Z| ≤ 0.5 →  Neutral/small position                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Confidence Scaling (Markov 2-Regime)              │
│  ─────────────────────────────────────────────              │
│  Runs on: diff(std_4y) — daily changes in uncertainty       │
│                                                             │
│  • prob_high_vol > 0.5 + agrees with Z → size × 1.0         │
│  • prob_high_vol < 0.5 + agrees with Z → size × 1.0         │
│  • Conflict (Z says ↑, Markov says ↓) → size × 0.4          │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:** V5's Markov model is used for **sizing**, not for **blocking**. A trade can proceed even if Markov probability is 0% (the position is just sized smaller).

### 1.2 V6: Three-Layer Signal System with Risk Filter

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 0: CRITICAL RISK FILTER (PCA 3-Regime)               │
│  ─────────────────────────────────────────────              │
│  Runs on: PC1 of IPCA (median, std) + SELIC (median, std)   │
│                                                             │
│  • Regime = "high" → **BLOCK TRADE** (return size = 0)      │
│  • prob_pca_high > threshold → **BLOCK TRADE**              │
│  • Otherwise → proceed to Layer 1                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Combined Regime Classification                    │
│  ─────────────────────────────────────                      │
│  Inputs: std_4y_zscore + ts_vol_4y_zscore                   │
│                                                             │
│  • active_crisis:       High fiscal + High instability      │
│  • chronic_disagreement: High fiscal + Low instability      │
│  • consensus_shock:     Low fiscal + High instability       │
│  • calm:                Low fiscal + Low instability        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Position Sizing (Same as V5)                      │
│  ─────────────────────────────────                          │
│  Base size from combined regime + Z-score scaling           │
│  Markov confidence scaling (same 2-regime model as V5)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Regime Classification Systems

### 2.1 V5: Single 3-Regime System (Z-Score Based)

The `std_4y` (cross-sectional standard deviation of 4-year primary surplus forecasts) is classified into 3 regimes based on expanding-window Z-score:

```python
def classify_regime(row: pd.Series) -> str:
    z = row.get("std_4y_zscore", np.nan)
    if z > 0.5:
        return "high_uncertainty"      # Upper tail
    if z < -0.5:
        return "low_uncertainty"       # Lower tail
    return "medium_uncertainty"       # Middle 50%
```

**Visualization:**

```
Z-Score Distribution
      │
   2  │      ██
   1  │     ████
   0  │    ██████
  -1  │   ████████
  -2  │  ██████████
      └──────────────────
         Low   Med   High
        ←─0.5─→←─+0.5─→
```

### 2.2 V6: Dual Regime System

#### 2.2.1 Fiscal Regime (2-Regime Markov on Changes)

Same as V5 — runs on `diff(std_4y)` to detect whether fiscal uncertainty is **accelerating** or **stable**.

| State | Characteristic | Interpretation |
|-------|---------------|----------------|
| Regime 1 (high_vol) | Positive mean in differenced series | Uncertainty is **rising** |
| Regime 0 (low_vol) | Negative mean in differenced series | Uncertainty is **stable/falling** |

#### 2.2.2 PCA Regime (3-Regime Markov on Levels)

**Critical Innovation in V6:** A completely separate regime system based on **inflation and SELIC expectations**.

**Input Variables:**
- IPCA median 12M forecast
- IPCA std dev 12M forecast  
- SELIC median 1Y forecast
- SELIC std dev 1Y forecast

**PCA Computation (Point-in-Time):**
```python
def compute_dynamic_pca(effective_date, merged_data, numeric_cols):
    # Use data STRICTLY before effective_date (no look-ahead)
    hist_data = merged_data[merged_data["date"] < effective_date]
    
    # Standardize and extract PC1
    X = scaler.fit_transform(hist_data[numeric_cols])
    pca = PCA(n_components=1)
    pca.fit(X)
    
    # Project current values onto PC1
    pca1 = pca.transform(current_values)
    return pca1
```

**3-Regime Classification:**

| Regime | PC1 Level | Risk Interpretation | Action |
|--------|-----------|---------------------|--------|
| Low | Low PC1 | Low inflation expectations | ✅ Safe to trade |
| Medium | Medium PC1 | Normal environment | ✅ Safe to trade |
| High | High PC1 | **High inflation expectations** | ❌ **BLOCK TRADE** |

**Why Block on High PC1?**

PC1 loadings typically show:
- Positive loading on IPCA median (higher inflation expected)
- Positive loading on IPCA std (more inflation uncertainty)
- Positive loading on SELIC median (higher rates expected)
- Positive loading on SELIC std (more policy uncertainty)

When PC1 is at **all-time highs**, it indicates:
1. Inflation expectations are elevated
2. The market expects aggressive SELIC hikes
3. **Steepening positions become dangerous** — the short end can rise dramatically

#### 2.2.3 Combined 4-Quadrant Classification

```python
def _classify_combined_regime(std_4y_zscore, ts_vol_4y, threshold=0.5):
    high_cross_sec = std_4y_zscore > threshold
    high_ts_vol = ts_vol_4y > threshold
    
    if high_cross_sec and high_ts_vol:
        return "active_crisis"           # Maximum conviction
    elif high_cross_sec and not high_ts_vol:
        return "chronic_disagreement"    # Bleeding carry
    elif not high_cross_sec and high_ts_vol:
        return "consensus_shock"         # Trend following
    else:
        return "calm"                    # Carry mode
```

| | High Time-Series Vol | Low Time-Series Vol |
|---|:---:|:---:|
| **High Cross-Sectional** | Active Crisis | Chronic Disagreement |
| **Low Cross-Sectional** | Consensus Shock | Calm |

---

## 3. Position Sizing Logic

### 3.1 V5 Sizing Formula

```python
def calculate_position(self, row, context):
    z = row.get("std_4y_zscore", 0.0)
    prob_high = row.get("prob_high_vol", 0.5)
    
    # Step 1: Base position from Z-score
    if z > self.zscore_high:           # z > +0.5
        raw = min(1.0, 0.5 + (z - 0.5) / 1.0)
        position_type = "bear_steepener"
    elif z < self.zscore_low:          # z < -0.5
        raw = max(-0.5, -0.25 + (z + 0.5) / 2.0)
        position_type = "flattener"
    else:                              # |z| ≤ 0.5
        raw = 0.25 * (z / 0.5)
        position_type = "small_bear" if raw > 0 else "small_flat"
    
    # Step 2: Markov confidence scaling
    if position_type == "bear_steepener" and prob_high > 0.5:
        confidence = min(1.0, (prob_high - 0.5) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)  # 0.5x to 1.0x
    elif position_type == "flattener" and prob_high < 0.5:
        confidence = min(1.0, (0.5 - prob_high) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)
    elif position_type in ("bear_steepener", "flattener"):
        size = raw * 0.4  # Conflicting signals → reduce
    else:
        size = raw
    
    return position_type, size, execution_style
```

**Position Size Range:**
- Steepener: 0 to +1.0 (or +1.2 for active_crisis in V6)
- Flattener: -0.5 to 0
- Neutral: -0.25 to +0.25

### 3.2 V6 Sizing Formula

```python
def calculate_position(self, row, context):
    # STEP 0: PCA Risk Filter (NEW IN V6)
    pca_regime = get_pca_regime(row["date"])
    prob_pca_high = get_pca_prob_high(row["date"])
    
    if pca_regime == "high" or prob_pca_high > self.inflation_high_threshold:
        return "risk_off_inflation_high", 0.0, "no_trade"  # BLOCKED
    
    # STEP 1: Combined regime (different from V5)
    z = row.get("std_4y_zscore", 0.0)
    ts_vol = row.get("ts_vol_63d_4y_zscore", None)
    combined_regime = self._classify_combined_regime(z, ts_vol)
    
    # STEP 2: Base position from combined regime
    if combined_regime == "active_crisis":
        raw = min(1.0, 0.5 + (z - 0.5) / 1.0) * 1.2  # 20% boost
        position_type = "bear_steepener"
    elif combined_regime == "chronic_disagreement":
        raw = min(0.5, 0.25 + (z - 0.5) / 2.0) if z > 0.5 else 0.0
        position_type = "small_bear" if raw > 0 else "neutral"
    # ... (other regimes similar to V5)
    
    # STEP 3: Markov scaling (same as V5)
    # ... same confidence scaling logic
    
    return position_type, size, execution_style
```

---

## 4. Risk Management Differences

### 4.1 V5 Risk Controls

| Risk Type | Mechanism | Implementation |
|-----------|-----------|----------------|
| Fiscal Uncertainty | Z-score thresholds | Enter when \|Z\| > 0.5 |
| Trend Confirmation | 2-regime Markov | Scale position 0.4x to 1.0x |
| Position Limit | max_position_size | Hard cap at ±1.0 |
| Stop Loss | Trailing stop | Flatten after 50 bps drawdown |
| Convexity | Gamma P&L attribution | Track convexity bleed |
| Execution Cost | Non-linear slippage | base_cost + impact × size² |

### 4.2 V6 Risk Controls (Additional)

| Risk Type | Mechanism | Implementation |
|-----------|-----------|----------------|
| **Inflation Risk** | **3-regime PCA filter** | **Block trade if PC1 = "high"** |
| **Macro Regime** | **4-quadrant classification** | Distinguish active crisis vs chronic disagreement |
| Time-Series Vol | ts_vol_4y_zscore | Don't size up if fiscal uncertainty is "stale" |
| Same as V5 | — | All V5 controls inherited |

---

## 5. Data Sources and Processing

### 5.1 Common Data (Both V5 and V6)

| Data | Source | Frequency | Use |
|------|--------|-----------|-----|
| DI Swap Rates | B3 Pre-DI | Daily | FRA construction, curve spread |
| FRA 1y1y, 3y3y | Derived from DI swaps | Daily | Tradeable spread |
| FOCUS Fiscal | BCB Focus Survey | Monthly | std_4y, median forecasts |
| Fiscal Calendar | BCB release dates | Monthly | Point-in-time regime data |

### 5.2 V6 Additional Data

| Data | Source | Frequency | Use |
|------|--------|-----------|-----|
| IPCA 12M Median | BCB Focus Survey | Daily | PCA input |
| IPCA 12M Std Dev | BCB Focus Survey | Daily | PCA input |
| SELIC 1Y Median | BCB Focus Survey | Daily | PCA input |
| SELIC 1Y Std Dev | BCB Focus Survey | Daily | PCA input |

### 5.3 Point-in-Time Processing

**Critical for Both Versions:** All regime calculations use **expanding windows** to avoid look-ahead bias.

```python
# Expanding window Z-score (no future data)
expanding = combined["std_4y"].expanding(min_periods=252)
combined["rolling_mean"] = expanding.mean()  # Mean up to date t
combined["rolling_std"] = expanding.std()    # Std dev up to date t

# Point-in-time PCA (V6)
for date in dates:
    hist_data = data[data["date"] < date]  # Strictly before
    pca.fit(hist_data)                      # Fit on history only
    pc1_today = pca.transform(current)      # Project today
```

---

## 6. P&L Attribution

Both versions use identical P&L decomposition:

```python
{
    "total_pnl": curve_pnl + gamma_pnl + carry_pnl + cost_pnl,
    "curve_pnl": position_size * DV01_NEUTRAL_RISK * spread_change,
    "gamma_pnl": convexity_attribution,  # Second-order effects
    "carry_pnl": 0.01 * position_size,   # Roll-down approximation
    "cost_pnl": -(base_cost + impact * size²) * |size|
}
```

**DV01-Neutral Construction:**
- Long 1y1y (shorter duration) → Larger notional
- Short 3y3y (longer duration) → Smaller notional
- Position sized so DV01_1y1y = DV01_3y3y (neutral to parallel shifts)

---

## 7. When to Use Each Version

### 7.1 Use V5 When...

- **Pure fiscal signal** is the primary concern
- You want **maximum exposure** to fiscal uncertainty episodes
- You believe **inflation risk is secondary** or managed separately
- You want a **simpler, more interpretable** strategy
- **Backtesting** fiscal scenarios without macro noise

### 7.2 Use V6 When...

- **Macro protection is critical** — you want to avoid steepening when inflation is spiking
- You want to **distinguish** between "active crisis" (tradeable) and "chronic disagreement" (bleeding carry)
- You're concerned about **inflation/SELIC regime changes** impacting the curve
- You want the **most conservative** implementation
- **Live trading** where macro surprises can be catastrophic

---

## 8. Summary Table

| Feature | V5 | V6 |
|--------|-----|-----|
| **Fiscal Signal** | Z-score (expanding window) | Same |
| **Fiscal Trend** | 2-regime Markov (diff) | Same |
| **Combined Regimes** | ❌ No | ✅ 4-quadrant |
| **Time-Series Vol** | ❌ Not used | ✅ Used in classification |
| **PCA Filter** | ❌ No | ✅ 3-regime on IPCA+SELIC |
| **Trade Blocking** | ❌ No | ✅ Yes (inflation high) |
| **Position Boost** | ❌ No | ✅ +20% for active_crisis |
| **Risk-Off Label** | ❌ No | ✅ "risk_off_inflation_high" |
| **Max Position** | 1.0 | 1.2 (active_crisis) |
| **Look-Ahead Bias** | ✅ None | ✅ None |
| **Code Complexity** | Medium | Higher |

---

## 9. Key Code References

### V5 Files
- `src/steepener_strategy_v5.py` — Main strategy implementation
- `src/base_strategy.py` — Parent class with `classify_regime()`
- `src/markov_regime_analysis.py` — 2-regime Markov fitting

### V6 Files
- `src/steepener_strategy_v6.py` — Main strategy with PCA filter
- `src/base_strategy.py` — Inherited methods
- `src/data/processed/regime_analysis/` — Fiscal regime probabilities

### Critical Functions

| Function | File | Purpose |
|----------|------|---------|
| `calculate_position()` | v5.py, v6.py | Core position logic |
| `classify_regime()` | base_strategy.py | Z-score → regime label |
| `fit_3regime_markov()` | v6.py | PCA 3-regime fitting |
| `compute_pca_regimes()` | v6.py | Point-in-time PC1 |
| `_classify_combined_regime()` | v6.py | 4-quadrant logic |

---

## 10. Visual Comparison

### V5 Signal Flow

```
FOCUS Survey ──→ std_4y ──→ Z-score ──→ Position Type
                              ↓
                         2-Regime Markov ──→ Size Scaling
                              (diff)
```

### V6 Signal Flow

```
FOCUS Survey ──→ std_4y ──→ Z-score ──┐
                                      ├──→ Combined Regime ──→ Position
              ts_vol_4y ──→ Z-score ──┘          ↑
                                                 │
IPCA+SELIC ──→ PCA ──→ 3-Regime Markov ──→ FILTER (can block)
                         (levels)
```

---

**End of Report**

*For questions or updates to this analysis, refer to the source code in `/src/steepener_strategy_v5.py` and `/src/steepener_strategy_v6.py`.*
