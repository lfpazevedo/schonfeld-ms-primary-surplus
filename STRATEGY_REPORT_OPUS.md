# Fiscal Uncertainty Steepener — Comprehensive Strategy Report

> **Project:** Schonfeld MS Primary Surplus  
> **Asset Class:** Brazilian Interest Rate Curve (BRL DI FRA)  
> **Instruments:** 1y1y vs 3y3y Forward Rate Agreements  
> **Date:** March 6, 2026

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Thesis & Macro Framework](#thesis--macro-framework)
3. [Signal Pipeline](#signal-pipeline)
4. [Strategy Evolution (v1 → v6)](#strategy-evolution-v1--v6)
5. [Detailed Strategy Analysis](#detailed-strategy-analysis)
6. [Performance Comparison](#performance-comparison)
7. [Key Findings & Open Issues](#key-findings--open-issues)
8. [Tips for Improvement](#tips-for-improvement)

---

## Executive Summary

This project implements a **regime-dependent yield curve steepener** on Brazil's DI forward rate curve, trading the spread between the **1y1y** and **3y3y** FRA tenors. The core thesis is that rising fiscal uncertainty — measured by the cross-sectional standard deviation of 4-year-ahead primary surplus forecasts (`std_4y`) — drives term premium expansion and curve steepening.

Six strategy versions have been developed, evolving from a simple binary regime switch (v1) to a production-grade system with rolling Z-scores, Markov regime scaling, DV01-neutral P&L, non-linear slippage, stop-loss management, and a PCA-based inflation expectation risk filter (v6).

**Key takeaway:** The strategy generates alpha during isolated fiscal uncertainty episodes (COVID-19, post-election, debt ceiling) but **bleeds during sustained high-uncertainty regimes** where BCB rate hikes flatten the curve against the bear steepener. All versions have produced negative total P&L. The path to profitability requires either **inverting the signal during high-uncertainty crises**, **filtering out high-inflation environments** (which v6 begins to address), or **fundamentally rethinking the directional mapping** between fiscal uncertainty and curve shape in Brazil.

---

## Thesis & Macro Framework

### Core Idea

| Regime | Fiscal Uncertainty | Curve Expectation | Position | Execution |
|--------|-------------------|-------------------|----------|-----------|
| High Uncertainty | `std_4y` elevated | Steepening (term premium ↑) | Bear Steepener | "Pay the Spread" — market orders for immediacy |
| Low Uncertainty | `std_4y` subdued | Flattening / Stable | Flattener or Carry | "Collect the Carry" — limit orders for roll-down |

### The Brazilian Twist

In developed markets, fiscal uncertainty typically drives long-end yields higher → curve steepens. In **Brazil**, the dynamic is more nuanced:

- **Acute fiscal shocks**: The curve does steepen (e.g., COVID March 2020: +174 bps, post-election Dec 2022: +193 bps).
- **Sustained fiscal crises**: The BCB responds with aggressive Selic hikes → short-end rises faster than long-end → **curve flattens**. This is the opposite of the thesis and the dominant source of strategy losses.

This asymmetry is the central challenge: the signal correctly identifies fiscal risk, but the **directional mapping** (fiscal uncertainty → steepening) breaks down when the central bank reacts.

---

## Signal Pipeline

### 1. Raw Signal: `std_4y`

The 4-year-ahead primary surplus standard deviation from Focus (BCB market survey). Captures cross-sectional dispersion of analyst forecasts — higher dispersion = higher fiscal uncertainty.

- **Data range:** 2001–2026 (interpolated daily from weekly releases)
- **Structural break:** ~0.05 pre-2015 → ~0.45+ post-2015, requiring transformations for stationarity.

### 2. Markov-Switching Regime Model

| Component | Description |
|-----------|-------------|
| **Input** | 20-day rolling mean of daily `std_4y` diffs (smoothed-differenced series) |
| **Model** | 2-regime Markov-Switching Regression with switching variance |
| **Output** | Smoothed probabilities of "Rising Uncertainty" vs "Stable/Falling" regime |
| **Persistence** | p₀₀ ≈ 0.978, p₁₁ ≈ 0.946 (regimes last ~45 and ~18 days on average) |
| **Execution** | Re-fit on each fiscal release date, using only data up to that date |

**Critical fix (v5):** Raw daily diffs had SNR ≈ 0.002 causing a "barcode" pattern (regimes flipping every day). The 20-day smoothing was essential to produce persistent, tradeable regimes.

### 3. Expanding-Window Z-Score (v5+)

```
z_t = (std_4y_t − mean(std_4y_{1..t})) / std(std_4y_{1..t})
```

Uses an **expanding window** (not fixed rolling) to avoid look-ahead bias. The z-score is the primary sizing signal:

| Z-Score | Regime Label | Position |
|---------|-------------|----------|
| z > +0.5 | High Uncertainty | Bear steepener (50–100%) |
| −0.5 ≤ z ≤ +0.5 | Medium | Small position (proportional) |
| z < −0.5 | Low Uncertainty | Flattener bias (up to 50%) |

### 4. Dynamic PCA + 3-Regime Filter (v6)

V6 introduces an **inflation expectation risk filter**:

- **Inputs:** `std_4y`, IPCA 12-month median/std forecasts, Selic 1-year median/std forecasts
- **Method:** Dynamic PCA (252-day rolling window) → first principal component
- **Regime classification:** Expanding-window percentiles (30th/70th) → Low/Medium/High
- **Action:** If PC1 is in the "High" regime → **NO POSITION** (risk-off)
- **Rationale:** When inflation expectations are at dynamic highs, steepener positions carry excessive risk from BCB reaction.

---

## Strategy Evolution (v1 → v6)

```mermaid
graph LR
    V1[V1: Binary Regime<br/>Simple Threshold] --> V2[V2: Probability Sizing<br/>Regime Confidence]
    V2 --> V3[V3: Continuous Sizing<br/>std_4y Percentiles]
    V3 --> V4[V4: Momentum Filter<br/>Spread vs MA]
    V4 --> V5[V5: Production Grade<br/>Z-Score + DV01 + Stop-Loss]
    V5 --> V6[V6: PCA Risk Filter<br/>Inflation Expectations]
    
    style V5 fill:#1a3a5c,stroke:#4a9eff,color:white
    style V6 fill:#1a5c3a,stroke:#4aff9e,color:white
```

### Version Lineage

| Version | Class | Inherits From | Key Innovation | Signal | P&L Model |
|---------|-------|---------------|----------------|--------|-----------|
| **v1** | `SteepenerStrategy` | None (standalone) | Binary regime (P > 0.5 = high) | `prob_high_vol` | Spread × flat DV01 |
| **v2** | `SteepenerStrategyV2` | None (standalone) | Probability-scaled sizing | `prob_high_vol` | Spread × scaled DV01 |
| **v3** | `SteepenerStrategyV3` | None (standalone) | Continuous sizing via percentiles | `std_4y` vs percentile thresholds | Spread × `dv01_factor` |
| **v4** | `SteepenerStrategyV4` | None (standalone) | Momentum overlay (spread vs 20d MA) | `std_4y` + momentum | Spread × `dv01_factor` |
| **v5** | `SteepenerStrategyV5` | `BaseSteepenerStrategy` | Rolling Z-score, DV01-neutral, non-linear slippage, stop-loss | Expanding Z-score + Markov prob | Per-leg DV01-weighted |
| **v6** | `SteepenerStrategyV6` | `BaseSteepenerStrategy` | PCA inflation filter (blocks high-inflation regimes) | V5 + Dynamic PCA regime | Per-leg DV01-weighted |

---

## Detailed Strategy Analysis

### V1 — Binary Regime Switching

**File:** `src/steepener_strategy.py`

**Logic:**
- `prob_high_vol > 0.5` → Bear steepener with "pay the spread" execution
- `prob_high_vol ≤ 0.5` → Bull steepener with "collect the carry" execution
- Positions held between fiscal release dates (monthly rebalancing)
- Fixed notional (no scaling)

**P&L Model:**
- Curve P&L: `spread_change × (DV01_long + DV01_short) × 100`
- Carry: ±0.5–1.0 bps/day based on execution style (flat, not scaled by size)

**Strengths:**
- Simple, interpretable
- Intuitive regime-driven framework

**Weaknesses:**
- Binary classification loses information from probability granularity
- No position sizing — always 100% on or 100% off
- Bull steepener during low uncertainty is directionally wrong when curve is flat
- DV01 model is overly simplified (equal weights)
- Monthly rebalancing cadence too slow for fast-moving regimes

**Total P&L:** −15.18 bps

---

### V2 — Probability-Scaled Sizing

**File:** `src/steepener_strategy_v2.py`

**Logic:**
- Same regime binary split, but **position size scales with probability confidence**
- High uncertainty: size = 50% + 50% × (prob − 0.5) / (0.8 − 0.5) → 50%–100%
- Low uncertainty: similar inverse scaling
- Added P&L component breakdown (curve / carry / cost)

**Innovations over V1:**
- Built a continuous regime time-series from per-release model files
- Uses most-recent-model lookup (`model_release_date >= date`)
- Position sizing proportional to regime conviction

**Weaknesses:**
- DV01 model still simplified (0.01 short, 0.03 long vs true 0.98/2.72)
- Bull steepener direction still problematic
- No stop-loss or risk management
- Full-sample percentile thresholds (look-ahead bias)

**Total P&L:** −809.96 bps (worst performer — large unhedged directional exposure)

---

### V3 — Continuous Sizing via Percentiles

**File:** `src/steepener_strategy_v3.py`

**Logic:**
- Uses **raw `std_4y` level** with percentile-based thresholds (25th/75th)
- Position sizing:
  - Below 25th pctile: 0–25% bear steepener ("collect the carry")
  - Between 25th–75th: 25–75% bear steepener ("standard")
  - Above 75th pctile: 75–100% bear steepener ("pay the spread")
- Trades recorded when position changes >10%

**Innovations over V2:**
- Three-regime framework (low / medium / high) instead of binary
- Continuous sizing avoids abrupt position flips
- Simplified DV01 factor (2.0 combined)

**Weaknesses:**
- Full-sample percentile thresholds introduce **look-ahead bias**
- `std_4y` has a structural break → percentiles are misleading
- Always bear steepener (never takes a flattener position despite design intent)
- No momentum or trend filters

**Total P&L:** −35.59 bps

---

### V4 — Momentum Filter

**File:** `src/steepener_strategy_v4.py`

**Logic:**
- Same percentile-based sizing as V3
- Adds **spread momentum filter**: 20-day moving average of curve spread
  - Spread below MA → slight size increase (mean-reversion opportunity)
  - Spread well above MA → reduce size (already extended)
- Always bear steepener (never flattener)

**Innovations over V3:**
- Momentum adjustment prevents chasing extended moves
- Returns a 4-tuple (position_type, size, exec_style, regime) vs V3's 3-tuple

**Weaknesses:**
- Still uses full-sample percentile thresholds (look-ahead bias)
- Momentum filter thresholds are hand-tuned (−0.005, +0.01) without justification
- Multiplier values (1.1, 0.7) are arbitrary
- Same structural break problem in `std_4y`

**Total P&L:** −183.87 bps (momentum filter made things worse — possibly overfitting the filter params)

---

### V5 — Production-Grade Architecture

**File:** `src/steepener_strategy_v5.py` + `src/base_strategy.py`

**Logic:**
- **Primary signal:** Expanding-window Z-score of `std_4y` (no look-ahead)
- **Secondary signal:** Markov `prob_high_vol` for confidence scaling
- Dual-signal fusion:
  - Z > 0.5 AND Markov prob > 0.5 → full conviction bear steepener
  - Z > 0.5 BUT Markov prob < 0.5 → reduced position (conflicting signals)
  - Z < −0.5 AND Markov prob < 0.5 → flattener (first version with genuine flattener)
- Allows **negative positions** (flattener, up to −0.5)
- **Stop-loss:** 50 bps trailing drawdown → position flattened; reset when |Z| < 0.5

**DV01-Neutral P&L Model:**
```
Notionals: N_1y × DV01_1y = N_3y × DV01_3y = R (target risk per leg)
          where DV01_1y = 0.98, DV01_3y = 2.72
Curve P&L: position_size × R × (Δ3y3y − Δ1y1y)
```
This isolates **pure spread moves** and neutralizes parallel shifts.

**Non-linear Cost Model:**
```
cost = base_spread + impact_factor × size²
```
- "Pay the spread": 2× impact multiplier
- "Collect the carry": 0.3× base cost − small carry benefit

**Innovations over V4:**
- Eliminated look-ahead bias via expanding-window statistics
- True DV01-neutral construction (0.98/2.72 per leg)
- Non-linear slippage model (market impact grows quadratically)
- Abstract base class enables clean version inheritance
- First version to have a genuine flattener position
- Trailing stop-loss with regime-aware reset

**Weaknesses:**
- High uncertainty regime still loses money (−95.8 bps, 19.8% win rate)
- Stop-loss reset condition (`|Z| < 0.5`) too strict → strategy stuck flat for months during sustained stress (e.g., 100 days flat during 2016 Dilma impeachment, missing the Temer rally)
- Expanding Z-score anchored to full history back to 2002 → moderate `std_4y` levels look "high" relative to ancient data

**Total P&L:** −24.11 bps (best net performance, but still negative)

---

### V6 — PCA Inflation Expectations Filter

**File:** `src/steepener_strategy_v6.py`

**Logic:**
- Inherits all V5 logic (Z-score + Markov scaling + DV01 + stop-loss)
- Adds an **inflation expectation risk filter**:
  1. Merge `std_4y`, IPCA 12-month forecast (median + std), Selic 1-year forecast (median + std)
  2. Dynamic PCA (252-day rolling window) → extract first principal component
  3. Classify PC1 into Low / Medium / High using expanding-window percentiles (30th / 70th)
  4. **If PC1 regime = "High" OR prob_high > 0.6 → NO POSITION** (risk-off)
- Computes PC1 at fiscal release dates, then interpolates daily
- Saves full PCA regime history for web dashboard visualization

**Innovations over V5:**
- Multi-factor risk filter combining fiscal, inflation, and monetary policy expectations
- PCA captures the common "macro stress" factor across all expectation indicators
- Blocks the most dangerous periods where BCB tightening makes steepeners toxic
- Dynamic percentile thresholds avoid look-ahead bias

**Weaknesses:**
- PCA computed only at ~30-day intervals then interpolated (may miss rapid regime shifts)
- 3-regime Markov on PC1 was implemented but then replaced with simpler percentile classification (suggests Markov on PCA was unstable)
- Inflation filter is one-sided (only blocks high) — could also constrain the flattener during deflation risks
- No out-of-sample testing on the filter's effectiveness
- Computationally expensive: ~300 PCA fits during backtest

**Total P&L:** Not recorded in available documentation (still being validated)

---

## Performance Comparison

### Strategy Version Results

| Version | Total P&L | P&L/Year | Sharpe | Max DD | Win Rate | Trades | Key Feature |
|---------|----------|---------|--------|--------|----------|--------|-------------|
| V1 | −15.18 bps | ~−1.1 | — | — | — | Monthly | Binary regime |
| V2 | −809.96 bps | ~−60.5 | — | — | — | ~30 | Prob-scaled sizing |
| V3 | −35.59 bps | ~−2.7 | — | — | — | ~200+ | Std_4y percentile sizing |
| V4 | −183.87 bps | −13.73 | −0.06 | −970.01 | 50.8% | 301 | + Momentum filter |
| **V5** | **−24.11 bps** | **−1.80** | **−0.03** | **−266.88** | **37.6%** | **518** | Z-score + DV01-neutral |
| V6 | TBD | TBD | TBD | TBD | TBD | TBD | + PCA inflation filter |

### V5 Performance by Regime

| Regime | Days | Total P&L | Avg Daily | Win Rate |
|--------|------|-----------|-----------|----------|
| High Uncertainty | 1,375 | −95.8 bps | −0.070 | 19.8% |
| Medium Uncertainty | 1,412 | +3.1 bps | +0.002 | 49.8% |
| Low Uncertainty | 587 | +68.6 bps | +0.117 | 50.1% |

### V5 Best / Worst Months

| Best Months | P&L | Worst Months | P&L |
|-------------|-----|------------|-----|
| 2022-12 (post-election) | +193.41 | 2016-03 (post-volatility flattening) | −249.09 |
| 2020-03 (COVID) | +174.08 | 2016-06 (Brexit flight-to-quality) | −185.38 |
| 2016-11 (election) | +154.31 | 2021-10 (policy normalization) | −156.63 |
| 2023-02 (fiscal concerns) | +94.00 | 2018-06 (trade war) | −149.56 |
| 2018-05 (policy uncertainty) | +85.35 | 2018-10 (risk-off) | −135.85 |

---

## Key Findings & Open Issues

### 1. The High-Uncertainty Paradox

The strategy's thesis is "buy steepeners when fiscal uncertainty is high." But the **high uncertainty regime is the dominant loss driver** (−95.8 bps in V5). The problem is specific to Brazil: when fiscal uncertainty is high, the BCB raises Selic → short-end rises faster → curve **flattens**.

This is not a signal quality issue — the signal correctly identifies fiscal risk. It's a **directional mapping error**: fiscal uncertainty → curve steepening is an EMF/DM framework that doesn't hold in Brazil during sustained crises.

### 2. Stop-Loss Death Spiral

The V5 stop-loss (50 bps trailing drawdown, reset when `|Z| < 0.5`) works well for short-lived crises but creates a **flatline problem** during sustained regime shifts:

- Jan–Feb 2016: Bear steepener loses 54.76 bps → stop triggered
- Feb–Jul 2016: Strategy flat for 100 consecutive days (Z-score stayed 1.65–3.98)
- The strategy missed the entire Temer rally (massive steepening in May 2016)

### 3. Look-Ahead Bias (v1–v4)

Versions 1–4 compute percentile thresholds using the **entire sample** (including future data). This artificially inflates in-sample performance. V5 fixed this with expanding-window Z-scores and rolling percentiles.

### 4. Markov Model Stability

The Markov model input required significant engineering (raw levels → daily diffs → 20-day smoothed diffs) to produce stable regimes. The raw series had a structural break and daily diffs were too noisy. Even with smoothing, the model sometimes produces degenerate results for short history windows.

### 5. V2 Catastrophe

V2 produced the worst results (−810 bps) likely because it combined probability-scaled sizing with a simplified DV01 model and the bull steepener direction during low uncertainty, creating large unhedged directional bets.

---

## Tips for Improvement

### 🔴 Critical — Signal & Direction

#### 1. Invert the High-Uncertainty Signal

The single highest-impact change would be to **go flattener** (not steepener) when the Z-score is very high:

```
Z > 1.5 AND prob_high_vol > 0.8 → FLATTENER (short short-end, long long-end)
```

**Rationale:** In these extreme regimes, BCB is almost certainly hiking → flattening pressure dominates. The high-uncertainty days (1,375 in V5) had −95.8 bps loss; inverting even a fraction could swing the total P&L positive.

**Implementation:** In `calculate_position()`, add a threshold above which the position flips to flattener. Start with Z > 1.5 as a conservative threshold and backtest.

#### 2. Add a BCB Reaction Function Filter

Track the Selic rate trajectory alongside the fiscal signal:

- If `std_4y` rising AND Selic rising → **DO NOT STEEPEN** (the BCB is fighting inflation)
- If `std_4y` rising AND Selic flat/falling → **STEEPEN** (fiscal uncertainty without monetary tightening)

This disentangles the fiscal vs monetary channels and avoids the flattening trap.

#### 3. Use Regime-Conditional Direction

Instead of a single bear steepener for all high-uncertainty regimes, condition on the **type** of uncertainty:

| Condition | Action |
|-----------|--------|
| Fiscal uncertainty ↑ + Inflation expectations ↓ | Bear steepener (term premium thesis holds) |
| Fiscal uncertainty ↑ + Inflation expectations ↑ | Flattener or flat (BCB will hike) |
| Fiscal uncertainty ↓ + Inflation expectations ↓ | Carry (stable environment) |
| Fiscal uncertainty ↓ + Inflation expectations ↑ | Small steepener (demand-driven rate rise) |

V6's PCA filter captures this partially, but a more explicit conditional mapping would be clearer.

---

### 🟡 Important — Risk Management

#### 4. Replace Stop-Loss with Time-Based Cooldown

The Z-score-based stop-loss reset is too strict. Replace with:

```python
# After stop-loss triggered, wait 20 trading days then gradually re-enter
if days_since_stop > 20:
    allowed_size = min(1.0, (days_since_stop - 20) / 20)  # Linear ramp over 20 days
```

This prevents the "100 days flat" problem while still limiting drawdown impact.

#### 5. Implement Volatility Targeting

Instead of fixed position sizing, target a **constant daily P&L volatility**:

```python
target_vol_bps = 1.0  # Target 1 bps daily vol
recent_vol = daily_pnl.rolling(60).std()
vol_scalar = target_vol_bps / recent_vol
position_size = base_size * vol_scalar
```

This automatically reduces exposure during volatile regimes and increases during calm ones — a more robust alternative to the percentile-based sizing.

#### 6. Add a Maximum Monthly Loss Limit

Add a hard monthly loss limit (e.g., −50 bps). After hitting it, the strategy goes flat until the next month. This prevents catastrophic months like March 2016 (−249 bps).

---

### 🟢 Enhancements — Execution & Model

#### 7. Use a Rolling Window Z-Score (Not Expanding)

The expanding Z-score is anchored to history starting from 2002. By 2016, even a "moderate" `std_4y` reads as elevated relative to the 2002–2010 low base. Consider a **252-day rolling window** instead:

```python
rolling_z = (std_4y - std_4y.rolling(252).mean()) / std_4y.rolling(252).std()
```

This makes the signal responsive to the current volatility regime rather than the entire history.

#### 8. Add a Momentum Confirmation Gate

Only enter new positions when the curve spread is moving in the direction of the signal:

- For bear steepener: require `spread_change_5d > 0` (curve already steepening)
- For flattener: require `spread_change_5d < 0` (curve already flattening)

This avoids immediate adverse moves on entry. V4 attempted this but used the wrong metrics (level vs MA instead of directional confirmation).

#### 9. Multi-Factor Signal Combination

Instead of cascading v5 Z-score → Markov prob → PCA filter, combine signals into a **single composite score**:

```python
composite = w1 * z_score_normalized + w2 * markov_prob + w3 * pca_score + w4 * selic_momentum
```

Optimize weights using walk-forward cross-validation to avoid overfitting.

#### 10. Backtest with Realistic Transaction Costs

The current cost model uses fixed parameters (`base_spread_cost = 0.02 bps`). Replace with:

- **Actual bid-ask spreads** from B3 market data (if available)
- **Time-of-day effects**: DI FRA spreads widen at open/close
- **Size-dependent impact**: Use a proper market impact model calibrated to BRL DI liquidity

#### 11. Consider DI Futures Instead of FRAs

BRL DI futures (DI1F) are more liquid than FRA contracts. Implementing the steepener via **calendar spreads** on DI futures would:

- Reduce execution costs
- Improve slippage model accuracy
- Enable intraday rebalancing
- Provide better data for cost calibration

#### 12. Walk-Forward Validation Framework

All V5/V6 parameters (Z thresholds, Markov scaling, stop-loss level, PCA lookback) were hand-tuned. Implement a **walk-forward optimization**:

1. Train on rolling 3-year windows
2. Test on the subsequent 1-year out-of-sample period
3. Report aggregate out-of-sample statistics

This would reveal whether the current parameters are overfit to specific historical episodes.

---

### 📊 Architecture & Code

#### 13. Unify the Strategy Hierarchy

V1–V4 are standalone classes; V5–V6 inherit from `BaseSteepenerStrategy`. Consider:

- Deprecating V1–V4 (move to an `archive/` folder)
- Making V6 the canonical production strategy
- Adding a `StrategyConfig` dataclass to hold all parameters, avoiding the growing `__init__` argument lists

#### 14. Add a Strategy Ensemble

Run V5 and V6 simultaneously with equal weight. If they agree, take full position. If they disagree (e.g., V5 says steepen but V6 filters it), take half position. This provides a built-in sanity check.

#### 15. Implement Point-in-Time Data Joins

The `model_release_date >= date` filter in regime loading is correct for avoiding look-ahead, but it means each date uses the *latest available* model. Consider also testing with *exact* model vintage (each fiscal release only applies to dates *after* that release, not retroactively).

---

### 🧪 Research Extensions

#### 16. Event-Driven Signal Enhancement

Layer fiscal data release dates as an additional signal:

- **Pre-release (T−5 to T):** Reduce position (uncertainty about upcoming release)
- **Post-release (T to T+5):** Increase position in the direction implied by the surprise
- **Between releases:** Carry position at steady size

#### 17. Cross-Market Confirmation

Monitor correlated markets for confirmation:

| Market | Signal | Use |
|--------|--------|-----|
| USD/BRL | Weakening BRL | Confirms fiscal stress → supports steepener |
| Brazil 5y CDS | Widening | Sovereign risk ↑ → steepener |
| Ibovespa | Falling | Risk-off → may flatten curve (caution) |
| US 2s10s | Steepening | Global term premium rising → supports thesis |

#### 18. Machine Learning Regime Classification

Replace the hand-tuned Z-score thresholds with a **gradient boosted classifier** trained on:

- `std_4y`, its lags, and rolling statistics
- Markov regime probabilities
- PCA components
- Macro variables (Selic level, IPCA forecasts, USD/BRL)

**Target:** Forward 30-day curve spread change direction (steepen vs flatten).

This could uncover non-linear interactions between signals that the current cascaded filter architecture misses.

---

## Appendix: File Reference

| File | Description |
|------|-------------|
| `src/base_strategy.py` | Abstract base class with DV01-neutral P&L, stop-loss, expanding-window z-scores, and reporting |
| `src/steepener_strategy.py` | V1: Binary regime switching (standalone) |
| `src/steepener_strategy_v2.py` | V2: Probability-scaled sizing (standalone) |
| `src/steepener_strategy_v3.py` | V3: Continuous sizing via percentiles (standalone) |
| `src/steepener_strategy_v4.py` | V4: + Momentum filter (standalone) |
| `src/steepener_strategy_v5.py` | V5: Z-score + Markov + DV01 + stop-loss (inherits base) |
| `src/steepener_strategy_v6.py` | V6: + PCA inflation filter (inherits base) |
| `src/markov_regime_analysis.py` | Markov-Switching on smoothed-differenced `std_4y` |
| `src/data/processed/b3/predi_fra_1y1y_3y3y.csv` | FRA yield curve data |
| `src/data/processed/focus/primary_1y_3y_4y_interp.csv` | Fiscal expectation data |
| `src/data/processed/calendar/fiscal_release_dates.csv` | Fiscal release calendar |
| `src/data/processed/regime_analysis/` | Per-release Markov probability outputs |
| `web/app.py` | Flask-Dash web dashboard |
