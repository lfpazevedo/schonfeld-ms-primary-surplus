# Critical Study: Look-Ahead Bias in V1–V4 and the Focus Std Dev Misinterpretation

## Executive Summary

Three critical methodological flaws have been identified:

1. **Look-Ahead Bias**: V1–V4 use full-sample statistics (2001–2026) to compute regime thresholds
2. **Cross-Sectional vs. Time-Series Confusion**: Focus `std_4y` measures **forecaster disagreement**, not **forecast uncertainty**
3. **Missing Flow Signal**: The strategy can't distinguish between "active crisis" and "chronic disagreement"

---

## Part 1: Look-Ahead Bias in V1–V4

### Severity: **CRITICAL** — All V1–V4 results are statistically invalid

### The Problem

```python
# V3/V4 CODE (INVALID - Look-ahead bias)
low_threshold = np.percentile(self.regime_ts['std_4y'], 25)   # Uses 2001-2026!
high_threshold = np.percentile(self.regime_ts['std_4y'], 75)  # Future data included
```

When "trading" on January 15, 2012, the model knows what uncertainty will be in 2020.

### Invalidated Results

| Version | Reported P&L | True Estimate | Status |
|---------|--------------|---------------|--------|
| V3 | −35.59 bps | −60 to −120 bps | **INVALID** |
| V4 | −183.87 bps | −200 to −300 bps | **INVALID** |

---

## Part 2: Cross-Sectional vs. Time-Series Confusion

### The Core Distinction

**Cross-sectional std** (Focus `DesvioPadrao`): How much do forecasters disagree TODAY?

```
Jan 15, 2024:
  Hedge Fund A: 2.0%      │
  Hedge Fund B: 3.0%      │  Disagreement
  Bank C:       4.0%      │  among forecasters
  → Std = 0.82%
```

**Time-series volatility**: How fast is the CONSENSUS changing over TIME?

```
Jan: Median = 3.0%        │
Feb: Median = 3.5%        │  Median moving
Mar: Median = 4.0%        │  rapidly
→ Volatility = HIGH
```

### Why This Matters — The Four Scenarios

| Cross-Sec Std | Time-Series Vol | Scenario | Strategy Action |
|---------------|-----------------|----------|-----------------|
| High | **High** | **Active crisis** — disagreement + movement | **Maximum conviction** |
| High | **Low** | **Chronic disagreement** — stale, nothing moving | **Reduce/sit out** ← Key fix |
| Low | High | Consensus shock — everyone agrees but view changed | Enter aggressively |
| Low | Low | Calm markets — stable agreement | Carry mode |

**The V1–V6 Problem**: Can't distinguish rows 1 and 2. Both show high `std_4y`, but only row 1 deserves full sizing.

### Real-World Example

**Brazil 2015–2016**: High `std_4y` for months (forecasters disagreed on fiscal trajectory), but median stable at ~−2.5%. Strategy kept sizing up, bleeding carry.

**COVID March 2020**: High `std_4y` + median moved from −1% to −5% in weeks. Active crisis — this is when you want full size.

---

## Part 3: Implementation Fixes

### Fix 1: Expanding Window (V5+)

```python
# V5+ CODE (VALID - Expanding window)
for i in range(len(series)):
    historical = series.iloc[:i]  # Only past data
    z = (series.iloc[i] - historical.mean()) / historical.std()
```

### Fix 2: Combined Regime Signal (V6+ Updated)

```python
# NEW: Combined cross-sectional + time-series
def _classify_combined_regime(std_4y_zscore, ts_vol_4y):
    high_cross_sec = std_4y_zscore > 0.5
    high_ts_vol = ts_vol_4y > 0.5
    
    if high_cross_sec and high_ts_vol:
        return "active_crisis"        # Full size
    elif high_cross_sec and not high_ts_vol:
        return "chronic_disagreement" # Reduce to 0.25x
    # ... etc
```

**Implementation**: Added to `primary_interp.py`:

```python
# Time-series volatility (flow signal)
merged['ts_vol_21d_4y'] = (
    merged['median_4y'].diff().rolling(21).std() * np.sqrt(252)
)
merged['ts_vol_63d_4y'] = (
    merged['median_4y'].diff().rolling(63).std() * np.sqrt(252)
)
```

---

## Part 4: Version Status

| Version | Look-Ahead | Combined Signal | Status |
|---------|------------|-----------------|--------|
| V1–V4 | ❌ Full sample | ❌ No | **INVALID** |
| V5 | ✅ Expanding | ❌ No | Deprecated |
| V6 (original) | ✅ Expanding | ❌ No | Superseded |
| **V6 (updated)** | ✅ Expanding | ✅ Yes | **Current** |

---

## Key Insight

> High `std_4y` can persist for years in a structurally ambiguous environment where nothing is actually happening to the curve. The strategy keeps sizing up its steepener based on the level of disagreement, but the curve isn't moving because the disagreement is stable.

The combined signal fixes this by requiring **both** high disagreement AND high median movement for maximum conviction sizing.

---

*Document Version: 2.0*
*Last Updated: March 6, 2026*
