# Proposed Improvements & New Features

> Roadmap for enhancing the Fiscal Uncertainty Steepener project.  
> Synthesized from four independent strategy reviews and the consolidated flaws analysis.  
> **No code changes included** — this document is a specification and design reference only.

---

## Table of Contents

1. [Signal Architecture Improvements](#1-signal-architecture-improvements)
2. [Risk Management Overhaul](#2-risk-management-overhaul)
3. [Execution & Cost Realism](#3-execution--cost-realism)
4. [New Data Sources & Cross-Asset Integration](#4-new-data-sources--cross-asset-integration)
5. [Machine Learning & Advanced Modeling](#5-machine-learning--advanced-modeling)
6. [Backtesting Framework Upgrades](#6-backtesting-framework-upgrades)
7. [Web Dashboard Enhancements](#7-web-dashboard-enhancements)
8. [Architecture & Code Quality](#8-architecture--code-quality)
9. [Priority Matrix](#9-priority-matrix)

---

## 1. Signal Architecture Improvements

### 1.1 — Signal Inversion for Extreme Regimes

**Problem it solves:** The high-uncertainty regime is the dominant loss driver (−95.8 bps in V5) because the BCB flattens the curve during fiscal crises.

**Proposed design:**

Introduce a **Z-score threshold** above which the strategy **inverts** from bear steepener to flattener:

| Z-Score Range | Position | Rationale |
|---------------|----------|-----------|
| Z > 1.5 (AND Markov prob > 0.8) | Flattener | BCB is almost certainly hiking → curve will flatten |
| 0.5 < Z ≤ 1.5 | Bear steepener | Standard thesis: term premium expands |
| −0.5 ≤ Z ≤ 0.5 | Small / neutral | Insufficient signal conviction |
| Z < −0.5 | Carry / flattener bias | Low uncertainty, collect roll-down |

The key insight is that the **same signal** (high `std_4y`) predicts **different curve moves** depending on its magnitude. Moderate fiscal stress → steepening. Extreme fiscal stress → BCB intervention → flattening. The inversion threshold should be calibrated via walk-forward validation (see §6).

### 1.2 — BCB Reaction Function Filter

**Problem it solves:** The strategy doesn't account for the monetary policy channel that dominates curve dynamics.

**Proposed design:**

Track the **Selic rate trajectory** as a conditioning variable:

| Fiscal Signal | Selic Direction | Strategy Action |
|---------------|-----------------|-----------------|
| `std_4y` rising | Selic rising (hiking cycle) | **Flatten or sit out** — BCB is fighting inflation |
| `std_4y` rising | Selic flat or falling | **Steepen** — fiscal stress without monetary tightening |
| `std_4y` falling | Selic rising | Small steepener — demand-driven hikes |
| `std_4y` falling | Selic falling or flat | Carry — stable environment |

Data source: Selic target rate from BCB (already in the Focus survey pipeline). Compute the 60-day Selic change to classify direction.

### 1.3 — Rolling Z-Score (Replace Expanding)

**Problem it solves:** The expanding Z-score is permanently anchored to pre-2015 data, making most post-break readings "high."

**Proposed design:**

Replace the expanding window with a **252-day rolling window** for the Z-score calculation. This makes the signal responsive to the *current* macro regime rather than the full 20+ year history. The rolling window naturally handles the 2015 structural break without requiring explicit break detection.

Trade-off: A rolling window forgets long-term context. A **hybrid approach** — rolling Z-score for signal generation, expanding percentile for regime labeling — could capture both local and structural information.

### 1.4 — Composite Multi-Factor Score

**Problem it solves:** V5/V6 use a cascaded filter architecture (Z-score → Markov → PCA), which is rigid and can miss non-linear interactions.

**Proposed design:**

Combine all signals into a **single weighted composite**:

```
composite = w₁ × z_score_norm + w₂ × markov_prob + w₃ × pca_score + w₄ × selic_momentum + w₅ × fx_vol
```

- Normalize each signal to [−1, +1]
- Weights optimized via walk-forward cross-validation (§6)
- Position sign and size derived directly from composite: positive → steepener, negative → flattener, magnitude → sizing
- Eliminates the need for sequential filter logic and percentile thresholds

---

## 2. Risk Management Overhaul

### 2.1 — Time-Decaying Stop-Loss (Replace Z-Score Reset)

**Problem it solves:** The current stop-loss kept the strategy flat for 100+ consecutive days during the 2016 crisis because the Z-score never crossed 0.5.

**Proposed design:**

When the 50 bps trailing stop is triggered:

1. **Hard blackout:** 20 trading days — no positions
2. **Linear ramp-up:** Over the next 20 trading days, gradually re-enable position sizing from 0% to 100% of the signal-implied size
3. **No Z-score dependency** for re-entry

This ensures capital protection during the immediate post-crisis period while preventing permanent market exclusion.

### 2.2 — Volatility-Targeted Position Sizing

**Problem it solves:** Position sizing is signal-based without regard for absolute P&L volatility, causing massive variance swings between calm and stressed regimes.

**Proposed design:**

Target a **constant daily P&L standard deviation** (e.g., 1.0 bps):

```
vol_scalar = target_vol / trailing_60d_vol(daily_pnl)
position_size = signal_implied_size × vol_scalar
```

This automatically deleverages during high-vol regimes (where losses concentrate) and levers up during calm, trending periods. It replaces the current approach of using signal magnitude alone for sizing.

### 2.3 — Dynamic Stop-Loss Threshold

**Problem it solves:** The fixed 50 bps stop is too tight in high-vol environments (whipsaw) and too loose in low-vol (excessive drawdown).

**Proposed design:**

Replace the fixed stop with a **volatility-indexed threshold**:

```
stop_level = 2 × ATR_20d(curve_spread)
```

Where ATR is the 20-day Average True Range of the 1y1y–3y3y spread. This automatically widens the stop during volatile periods and tightens it during calm markets.

### 2.4 — Maximum Monthly Loss Limit

**Problem it solves:** Catastrophic months (e.g., March 2016: −249 bps) are uncapped.

**Proposed design:**

Add a hard monthly drawdown limit (e.g., −50 bps cumulative for the month). Once hit, the strategy goes flat until the first trading day of the next calendar month. Simple but effective tail-risk truncation.

### 2.5 — Carry-to-Risk Gate

**Problem it solves:** The "collect the carry" mode activates based on fiscal uncertainty alone, without checking whether the actual carry is worth the risk.

**Proposed design:**

Calculate the **carry/volatility ratio** before activating carry mode:

```
carry_per_day = estimated_roll_down + spread_yield
carry_vol_ratio = carry_per_day / 20d_realized_vol(spread)
```

Only activate "collect the carry" if `carry_vol_ratio > threshold` (e.g., 0.1). If carry is thin relative to ambient volatility, the risk/reward doesn't justify the position.

---

## 3. Execution & Cost Realism

### 3.1 — Dynamic DV01 Recalibration

**Problem it solves:** Static DV01 ratios (0.98/2.72) drift as yields move, re-introducing directional risk.

**Proposed design:**

Recalculate DV01 values **daily** from the prevailing DI curve:

```
DV01(tenor, yield) = modified_duration(tenor, yield) × notional / 10_000
```

The hedge ratio `N_1y / N_3y = DV01_3y / DV01_1y` updates each day. This eliminates convexity bleed and maintains true neutrality through large yield moves.

### 3.2 — Funding Cost Integration

**Problem it solves:** The P&L model ignores the carry cost of financing the position, overstating performance.

**Proposed design:**

Add a **daily funding cost component** to the P&L:

```
funding_cost = position_size × (overnight_DI_rate − spread_yield) × (1/252)
```

Where `overnight_DI_rate` is the CDI (CETIP deposit rate) and `spread_yield` is the implied yield differential between legs. During BCB hiking cycles, this will be meaningfully negative, reflecting the true cost of maintaining a bear steepener.

### 3.3 — Liquidity-Adjusted Position Sizing

**Problem it solves:** The strategy takes maximum positions during stress events when liquidity is thinnest.

**Proposed design:**

Introduce a **liquidity scalar** based on trailing DI futures volume:

```
liquidity_scalar = min(1.0, (trailing_5d_volume / volume_threshold) ^ 0.5)
position_size = signal_size × liquidity_scalar
```

Data source: B3 daily volume data for the relevant DI futures contracts. The square root dampening prevents violent sizing changes on volume drops while still providing meaningful protection.

### 3.4 — Realistic Spread Cost Model

**Problem it solves:** The fixed `base_spread_cost = 0.02 bps` is unrealistically low during stress periods.

**Proposed design:**

Replace the static cost with a **regime-conditioned model**:

| Regime | Base Spread (bps) | Impact Model |
|--------|-------------------|--------------|
| Low uncertainty (VIX-BRL < 20) | 0.03 | Linear: 0.02 × size |
| Medium | 0.06 | Quadratic: 0.04 × size^1.5 |
| High uncertainty (VIX-BRL > 30) | 0.15 | Quadratic: 0.08 × size² |
| Crisis (VIX-BRL > 50) | 0.30 | Concave: 0.15 × size^1.3 |

If actual B3 bid-ask data is available, calibrate directly from historical spreads by tenor, date, and time-of-day.

### 3.5 — Roll Cost Modeling

**Problem it solves:** The strategy ignores the mechanics and costs of rolling FRA positions as underlying DI contracts expire.

**Proposed design:**

Track the actual DI contracts underlying each FRA leg. When a contract approaches maturity (T−5 days), model:

- Roll spread (cost of closing the expiring contract and opening the next)
- Roll yield impact on carry P&L
- Liquidity differential between front-month and back-month contracts

The carry P&L component (`carry_pnl = 0.01 × position_size` in V5) should be replaced with an **actual roll-down estimate** computed from the current curve shape.

---

## 4. New Data Sources & Cross-Asset Integration

### 4.1 — USD/BRL FX Signal

**Rationale:** Currency depreciation is the primary transmission mechanism from fiscal stress to BCB rate hikes. FX moves often *lead* DI curve moves by hours to days.

**Proposed usage:**

- **Confirming filter:** If `std_4y` rising AND BRL weakening → high confidence steepener (or flattener, per §1.1 inversion)
- **Divergence signal:** If `std_4y` rising BUT BRL stable → possible false positive; reduce position
- **Data:** USD/BRL spot rate and 1-month implied volatility from B3 or Bloomberg

### 4.2 — Brazil 5-Year CDS

**Rationale:** Sovereign CDS captures offshore institutional positioning on Brazil risk. Divergence between onshore DI uncertainty and offshore CDS pricing indicates cross-border flow risk.

**Proposed usage:**

- CDS widening + `std_4y` rising → corroborated risk signal → higher conviction
- CDS tightening + `std_4y` rising → onshore/offshore divergence → reduce size (offshore may be better informed)
- **Data:** 5y Brazil CDS mid-spread from ICE/Bloomberg

### 4.3 — US Treasuries / MOVE Index

**Rationale:** Emerging market curves are heavily influenced by global rate volatility and capital flows. A steepening US curve or spiking MOVE index can dominate local dynamics.

**Proposed usage:**

- US 2s10s steepening → global term premium rising → supports Brazil steepener thesis
- MOVE index > 120 → global rates vol regime → reduce Brazil steepener sizing (risk of disorderly capital outflows)
- **Data:** US Treasury yields from FRED; MOVE index from ICE

### 4.4 — B3 Order Flow / VPIN

**Rationale:** Microstructure data captures informed trading before macro data is released.

**Proposed usage:**

- VPIN (Volume-synchronized Probability of Informed Trading) on DI futures
- High VPIN + fiscal uncertainty → stronger signal (informed participants are trading aggressively)
- **Data:** Tick-level DI futures data from B3 (requires significant infrastructure)
- **Priority:** Low — high implementation cost, marginal improvement over macro signals

### 4.5 — Tesouro Nacional Issuance Calendar

**Rationale:** Government bond supply directly impacts curve dynamics. Heavy issuance at the long end steepens the curve; Treasury buybacks flatten it.

**Proposed usage:**

- Upcoming long-end auctions (NTN-F or NTN-B) → potential steepening pressure
- Treasury buyback announcements → flattening pressure
- **Data:** Tesouro Nacional monthly issuance plan (publicly available)

---

## 5. Machine Learning & Advanced Modeling

### 5.1 — Gradient-Boosted Regime Classifier

**Problem it solves:** Hand-tuned Z-score thresholds may miss non-linear interactions between signals.

**Proposed design:**

Train a gradient-boosted classifier (XGBoost/LightGBM) on:

- **Features:** `std_4y`, Z-score, Markov probability, PCA components, Selic rate/change, IPCA forecasts, USD/BRL, CDS spread
- **Target:** Forward 30-day curve spread direction (binary: steepen vs flatten)
- **Training:** Walk-forward (3-year train, 1-year test, rolling quarterly)
- **Output:** Probability used for position direction and sizing

Feature importance analysis would reveal which signals actually drive curve moves and which are noise.

### 5.2 — Meta-Labeling (López de Prado Framework)

**Problem it solves:** The primary model generates too many false signals — it correctly identifies regimes but the curve doesn't always respond as expected.

**Proposed design:**

Keep the existing V5/V6 signal as the **primary model** (direction generator). Train a **secondary ML model** to predict *whether the primary model's current signal will be correct*:

- **Features:** Volatility regime, trend strength, macro surprise index, recent win rate, signal age
- **Target:** Binary — did the primary model's signal produce positive P&L over the next 5 days?
- **Action:** Only trade when meta-model probability > 0.6

This preserves the economic interpretability of the primary model while adding a data-driven confidence overlay.

### 5.3 — HMM Ensemble for Regime Detection

**Problem it solves:** The single 2-regime Markov model is fragile and assumes constant transition probabilities.

**Proposed design:**

Replace the single Markov model with an **ensemble** of three models:

1. **2-regime Markov-Switching** (current) — captures the rising/falling fiscal uncertainty dynamic
2. **3-regime Hidden Markov Model** — adds a "crisis" regime distinct from regular high uncertainty
3. **Gaussian Mixture Model with time-varying weights** — provides a non-parametric alternative

Combine regime classifications via **majority voting** or **probability averaging**. Only trade with full conviction when all three agree. This dramatically reduces false regime classifications from any single model.

### 5.4 — LSTM Regime Persistence Predictor

**Problem it solves:** The Markov model tells you the *current* regime but not how long it will last.

**Proposed design:**

Train an LSTM on regime-labeled sequences to predict:

- Probability of regime change within the next 5/10/20 days
- Expected remaining duration of the current regime

Use the persistence forecast to **scale position sizing**: if the model predicts the regime is ending soon, reduce size to avoid the transition period. If it predicts persistence, maintain or increase conviction.

---

## 6. Backtesting Framework Upgrades

### 6.1 — Walk-Forward Optimization Engine

**Problem it solves:** All parameters are hand-tuned with no out-of-sample validation framework.

**Proposed design:**

Build a `WalkForwardOptimizer` class that:

1. Takes a strategy class and a parameter grid as input
2. Iterates through the historical data in rolling blocks (e.g., 3-year train / 1-year test)
3. For each block, optimizes parameters on the train set (maximizing Sharpe or minimizing drawdown)
4. Records out-of-sample performance on the test set
5. Reports aggregate out-of-sample metrics and parameter stability across windows

Parameters to optimize: `zscore_high`, `zscore_low`, `prob_confidence`, `stop_loss_bps`, `pca_lookback`, `inflation_high_threshold`.

### 6.2 — Synthetic Stress Testing

**Problem it solves:** The backtest only covers one path of history. The strategy has never been tested against extreme but plausible scenarios.

**Proposed scenarios:**

| Scenario | Design | What It Tests |
|----------|--------|---------------|
| Taper Tantrum replay | Apply 2013-style US selloff to current Brazilian curve levels | Global contagion risk |
| COVID front-end freeze | Simulate 5 days of zero short-end liquidity | Liquidity assumptions |
| Double BCB hike | Simulate a 300 bps emergency hike | Stop-loss and DV01 resilience |
| Election shock | Simulate 2018/2022-scale volatility with random timing | Position sizing under surprise |
| Stagflation | Sustained high `std_4y` + high IPCA + Selic at 15%+ | Funding cost drag |

Generate scenarios by bootstrapping historical returns with imposed conditions, or by applying multiplicative shocks to the actual time series.

### 6.3 — Monte Carlo Confidence Intervals

**Problem it solves:** Single-path backtesting gives false precision — one +193 bps month (Dec 2022) dominates the entire P&L profile.

**Proposed design:**

Run 10,000 bootstrap simulations:

- Resample daily returns with replacement (block bootstrap, 20-day blocks to preserve autocorrelation)
- Compute P&L, Sharpe, max drawdown distribution
- Report 5th/50th/95th percentile outcomes

This reveals whether the strategy's performance is robust or driven by a few outlier events.

### 6.4 — Sensitivity Analysis Dashboard

**Problem it solves:** No understanding of how sensitive performance is to parameter choices.

**Proposed design:**

For each key parameter, run a sweep across a reasonable range and plot:

- Total P&L vs parameter value
- Sharpe ratio vs parameter value
- Max drawdown vs parameter value

If performance is a sharp peak at the current parameter value, the strategy is overfit. If it's a broad plateau, the parameter is robust.

---

## 7. Web Dashboard Enhancements

### 7.1 — Live Parameter Tuning Interface

Add interactive controls that let the user adjust strategy parameters (Z-score thresholds, stop-loss, PCA lookback) and see the backtest results update in real-time. This enables rapid iteration without modifying code.

### 7.2 — Cross-Asset Overlay Charts

Add panels showing:

- USD/BRL alongside the curve spread and regime classification
- Brazil 5y CDS alongside `std_4y`
- Selic target rate overlaid on the position sizing chart

This visual correlation analysis helps identify which cross-asset signals would have best predicted curve moves.

### 7.3 — Drawdown Attribution View

A new chart breaking down cumulative P&L by component:

- Curve P&L (spread moves)
- Carry P&L (once implemented)
- Cost P&L (slippage and impact)
- Funding cost (once implemented)

With regime-colored backgrounds showing when the strategy was in high/medium/low uncertainty or risk-off mode.

### 7.4 — Strategy Comparison Mode

Side-by-side comparison of V5 vs V6 (and future versions):

- Dual cumulative P&L curves
- Venn diagram of trading days: when do they agree/disagree?
- Performance attribution for agreement vs disagreement periods

### 7.5 — Scenario Simulator

Interactive UI where the user defines a hypothetical scenario (e.g., "Selic +200 bps over 3 months") and sees the projected P&L impact on the current portfolio, using the DV01 model and cost assumptions.

---

## 8. Architecture & Code Quality

### 8.1 — Strategy Config Dataclass

Replace the growing `__init__` argument lists in V5/V6 with a typed `StrategyConfig` dataclass:

- All parameters in one place with defaults and validation
- Serializable to JSON/YAML for reproducibility
- Enables easy parameter sweeps in the walk-forward optimizer

### 8.2 — Archive V1–V4

Move `steepener_strategy.py`, `steepener_strategy_v2.py`, `steepener_strategy_v3.py`, and `steepener_strategy_v4.py` to an `archive/` directory. They contain look-ahead bias, broken DV01 models, and wrong directional bets. Keeping them alongside production code (V5/V6) risks confusion.

### 8.3 — Unified Data Pipeline

Create a `DataLoader` class that:

- Loads all data sources once (yield data, fiscal calendar, regime data, IPCA, Selic, FX, CDS)
- Handles date alignment, forward-filling, and frequency conversion
- Returns a single merged DataFrame to the strategy
- Caches processed data to avoid repeated I/O during walk-forward runs

Currently, each strategy version loads data independently with slightly different merging logic — a source of subtle bugs.

### 8.4 — Event-Driven Backtest Engine

Replace the current for-loop backtest with an **event-driven** architecture:

- Events: market data tick, fiscal release, Copom meeting, roll date, stop-loss trigger
- The strategy subscribes to relevant events and produces position updates
- This naturally supports the fiscal release calendar, Copom-aware trading, and roll mechanics

This is a significant refactor but dramatically improves testability and facilitates live trading integration.

### 8.5 — Logging & Audit Trail

Add structured logging to the backtest engine:

- Every position change: date, signal values, position before/after, reason
- Every stop-loss trigger/reset: date, drawdown level, reset condition
- Every PCA regime change: date, PC1 value, percentiles, regime label

Export to CSV alongside the daily P&L for post-hoc analysis. Currently, debugging requires re-running the backtest with print statements.

---

## 9. Priority Matrix

| Priority | Feature | Expected Impact | Complexity | Dependencies |
|----------|---------|----------------|------------|--------------|
| **P0** | Signal inversion for extreme regimes (§1.1) | 🔴 High — directly fixes dominant loss driver | Medium | Walk-forward validation |
| **P0** | Funding cost integration (§3.2) | 🔴 High — corrects phantom P&L | Low | CDI data |
| **P0** | Dynamic DV01 recalibration (§3.1) | 🔴 High — eliminates convexity risk | Low | None |
| **P1** | Time-decaying stop-loss (§2.1) | 🟠 High — prevents 100-day flatline | Low | None |
| **P1** | BCB reaction function filter (§1.2) | 🟠 High — disentangles fiscal vs monetary | Low | Selic data (already available) |
| **P1** | Rolling Z-score (§1.3) | 🟠 Medium — fixes anchoring bias | Low | None |
| **P1** | Vol-targeted sizing (§2.2) | 🟠 Medium — stabilizes risk profile | Low | None |
| **P1** | Walk-forward optimizer (§6.1) | 🟠 Medium — validates all parameters | Medium | None |
| **P2** | USD/BRL FX signal (§4.1) | 🟡 Medium — best cross-asset leading indicator | Medium | FX data |
| **P2** | Liquidity-adjusted sizing (§3.3) | 🟡 Medium — prevents stress-period overexposure | Medium | B3 volume data |
| **P2** | Realistic spread costs (§3.4) | 🟡 Medium — improves P&L accuracy | Medium | B3 bid-ask data |
| **P2** | Archive V1–V4 (§8.2) | 🟢 Low — reduces confusion | Trivial | None |
| **P2** | Strategy config dataclass (§8.1) | 🟢 Low — improves code quality | Low | None |
| **P3** | Gradient-boosted classifier (§5.1) | 🟡 Medium — potentially large alpha | High | Multiple data sources |
| **P3** | Meta-labeling (§5.2) | 🟡 Medium — improves signal-to-noise | High | Primary model stable |
| **P3** | HMM ensemble (§5.3) | 🟡 Low-Medium — robustness improvement | High | None |
| **P3** | Brazil 5y CDS (§4.2) | 🟡 Low-Medium — offshore confirmation | Medium | CDS data |
| **P3** | Monte Carlo confidence intervals (§6.3) | 🟢 Low — improves understanding | Medium | None |
| **P3** | Scenario simulator (§7.5) | 🟢 Low — research tool | High | Dashboard infra |
| **P4** | LSTM persistence predictor (§5.4) | 🟡 Speculative | High | Labeled regime data |
| **P4** | Event-driven backtest engine (§8.4) | 🟢 Architecture improvement | Very High | Full refactor |
| **P4** | VPIN microstructure signal (§4.4) | 🟡 Speculative | Very High | Tick data infrastructure |
