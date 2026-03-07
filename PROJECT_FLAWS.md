# Project Flaws Report

> Consolidated analysis from four independent strategy reviews (Gemini Deep, Gemini Web, Kimi, Opus).  
> Focus: **flaws only** — what is broken, missing, or dangerous in the current codebase.

---

## 1. Fundamental Thesis Flaw — The High-Uncertainty Paradox

**Severity: CRITICAL** · *Identified by: All 4 reports*

The core thesis — "high fiscal uncertainty → curve steepening" — is a developed-market heuristic that **does not hold in Brazil** during sustained crises. When fiscal uncertainty rises in Brazil:

1. **BRL depreciates** → inflation expectations de-anchor
2. **BCB hikes Selic aggressively** → short-end rises faster than long-end
3. **Curve flattens**, not steepens — the opposite of the strategy's bet

**Evidence from V5 backtest:**
- High-uncertainty regime: **−95.8 bps, 19.8% win rate** (1,375 days)
- Low/medium-uncertainty regimes: **+71.7 bps combined**

The signal correctly identifies fiscal risk, but the **directional mapping is inverted**. The strategy's primary signal is also its primary loss driver. V6's PCA filter partially addresses this by blocking trades, but never inverts the position — it leaves alpha on the table during the most volatile periods.

---

## 2. Static DV01 Ratios — Unhedged Convexity Risk

**Severity: HIGH** · *Identified by: Gemini Deep, Kimi*

V5/V6 use hardcoded DV01 values (`DV01_1Y1Y = 0.98`, `DV01_3Y3Y = 2.72`) that never update. This creates two problems:

- **Duration drift:** As yields move, the actual DV01 of each leg changes. The 3y3y leg's duration falls faster than the 1y1y during a sell-off (higher convexity), re-introducing directional risk into the "neutral" portfolio.
- **Convexity bleed:** During large yield moves (precisely when the strategy is most active), the second-derivative mismatch between legs causes P&L to deviate significantly from the spread-only model.

The portfolio is only DV01-neutral at a single theoretical yield level. In practice, it carries **unhedged convexity exposure** that grows with market volatility.

---

## 3. Missing Funding Costs — Phantom P&L

**Severity: HIGH** · *Identified by: Gemini Deep, Kimi, Gemini Web*

The entire P&L framework across **all six versions** ignores the funding cost differential between legs. A bear steepener (pay fixed on long-end, receive fixed on short-end) in an environment where the BCB is hiking the Selic creates **deep negative carry**:

- The cost of financing the short-end position exceeds the yield on the long-end
- The portfolio bleeds capital daily even if the spread is unchanged
- This phantom carry cost is **not reflected** in any version's total P&L

The reported performance metrics are therefore **systematically overstated**. Actual live P&L would be worse than backtested P&L by the cumulative funding differential.

---

<!-- ## 4. Look-Ahead Bias in V1–V4

**Severity: HIGH** · *Identified by: All 4 reports*

Versions 1–4 compute `std_4y` percentile thresholds using the **entire sample** (2001–2026), including future data. Specific violations:

| Version | Look-Ahead Source |
|---------|-------------------|
| V3 | `np.percentile(self.regime_ts['std_4y'], 25)` on full dataset |
| V4 | Same — inherits V3's full-sample percentiles |
| V3/V4 | `self.regime_ts['std_4y'].max()` used in position sizing normalization |

V5 fixed this with expanding windows, but **V1–V4 backtest results are invalid** for any predictive or comparative purpose. The V3 result of −35.59 bps and V4 result of −183.87 bps cannot be trusted as indicators of true out-of-sample performance. -->

---

## 5. Stop-Loss Death Spiral

**Severity: HIGH** · *Identified by: Gemini Deep, Opus, Gemini Web*

The V5/V6 trailing stop-loss (50 bps drawdown, reset when `|Z| < 0.5`) has a **fatal design flaw** during sustained regime shifts:

**Case study — 2016 Dilma impeachment:**
- Jan 29 – Feb 10: Bear steepener loses 54.76 bps → stop triggered
- Feb 10 – Jul 1: **Strategy flat for 100+ consecutive days**
- Z-score stayed 1.65–3.98 (never crossed 0.5 to reset)
- Missed the entire Temer rally — massive steepening in May 2016

**The problem:** The reset condition (`|Z| < 0.5`) is too strict for Brazil, where `std_4y` can remain structurally elevated for months/years (post-2015 structural break). The stop-loss correctly protects capital but **permanently removes the strategy from the market** during the exact periods where opportunities emerge post-crisis.

Additionally, the fixed 50 bps threshold is **regime-blind**: too tight in high-vol environments (whipsaw), too loose in low-vol (excessive drawdown before trigger).

---

<!-- ## 6. Expanding Z-Score Anchoring Problem

**Severity: MEDIUM** · *Identified by: Opus, Gemini Deep*

The V5/V6 expanding-window Z-score anchors to **all history from 2001**. Due to the structural break in `std_4y` (~0.05 pre-2015 → ~0.45+ post-2015):

- By 2016+, even a "moderate" `std_4y` of 0.5 reads as z ≈ 2+ relative to the 2001–2010 baseline
- The Z-score is **permanently elevated** in the post-break regime
- This overwhelms the Markov confidence scaling, keeping the strategy at maximum steepener conviction precisely when flattening pressure is strongest

The expanding window means the signal can **never fully adapt** to the post-break reality. A rolling window (e.g., 252-day) would fix this but was not implemented. -->

---

## 7. Unrealistic Transaction Cost Model

**Severity: MEDIUM** · *Identified by: Gemini Deep, Kimi, Gemini Web*

The slippage model uses hardcoded parameters that don't reflect B3 market realities:

| Parameter | Current Value | Reality |
|-----------|---------------|---------|
| `base_spread_cost` | 0.02 bps | Likely 0.05–0.50 bps during stress |
| `impact_factor` | 0.05 × size² | No empirical calibration to DI liquidity |
| Liquidity scaling | None | DI market depth varies dramatically by tenor and date |
| Calendar effects | None | Year-end, election periods, Copom meetings have wider spreads |
| B3 exchange fees | Not modeled | Missing brokerage and exchange settlement costs |

The cost model is **scale-invariant** — it doesn't account for the fact that 3y3y FRAs are substantially less liquid than front-month DI futures. During stress events (exactly when "pay the spread" is triggered), the actual execution cost can be **orders of magnitude** higher than the model assumes.

---

<!-- ## 8. PCA Sign Instability (V6)

**Severity: MEDIUM** · *Identified by: Kimi, Gemini Web*

V6's Dynamic PCA uses a 252-day rolling window to extract PC1. Two problems:

1. **Sign flips:** PCA eigenvectors can flip sign between windows. PC1 might point toward "inflationary stress" in one window and toward "deflationary risk" in the next, without any underlying economic change. The code doesn't enforce sign consistency.

2. **Window too short for structural regimes:** Inflation expectation regimes in Brazil can persist for 2+ years. A 1-year window may **normalize an elevated regime**, causing the filter to prematurely re-enable trading. Conversely, it may be slow to recognize a genuine regime shift.

The 3-regime Markov model on PC1 was implemented but then **abandoned in favor of simpler percentiles** — suggesting the Markov fit on PCA was numerically unstable. This was a pragmatic fix but left the underlying instability unaddressed. -->

---

## 9. No Liquidity-Adjusted Position Sizing

**Severity: MEDIUM** · *Identified by: Gemini Deep, Kimi*

Position sizing is purely signal-driven (Z-score × Markov confidence). There is **no adjustment for market liquidity**:

- Maximum-notional steepeners are executed during stress events when order book depth is thinnest
- The strategy assumes continuous pricing — in reality, Brazilian DI markets can gap significantly during political crises or Copom surprises
- The "pay the spread" execution style acknowledges higher costs but doesn't reduce size to compensate

This is the **inverse** of prudent execution: the strategy takes its largest positions exactly when liquidity is poorest.

---

## 10. Markov Model Fragility

**Severity: MEDIUM** · *Identified by: Gemini Deep, Kimi, Opus*

The 2-regime Markov-Switching model has several embedded fragilities:

- **Constant transition probabilities:** Real-world regime persistence varies with macro conditions, but the model assumes stationary transition matrices
- **Sensitivity to smoothing window:** The 20-day smoothing window was chosen to fix the "barcode" problem, but no sensitivity analysis was performed — other window lengths may produce very different regime classifications
- **Short-history instability:** For early fiscal releases with limited history, the model can produce degenerate results (near-singular covariance, persistent EM convergence failures)
- **No model confidence metric:** The strategy uses smoothed probabilities as-is, with no measure of whether the underlying model fit was trustworthy (e.g., checking AIC/BIC convergence, regime separation quality)

---

## 11. No Walk-Forward Validation

**Severity: MEDIUM** · *Identified by: All 4 reports*

Every tunable parameter across V5/V6 is **hardcoded without out-of-sample validation**:

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `zscore_high` | 0.5 | None documented |
| `zscore_low` | −0.5 | None documented |
| `prob_confidence` | 0.8 | None documented |
| `stop_loss_bps` | 50.0 | None documented |
| `base_spread_cost` | 0.02 | None documented |
| `impact_factor` | 0.05 | None documented |
| `pca_lookback` | 252 | None documented |
| `inflation_high_threshold` | 0.6 | None documented |

There is no walk-forward optimization, no cross-validation, no sensitivity analysis. The risk of **overfitting to specific historical episodes** (2016 crisis, COVID, 2022 election) is high. Parameters may perform well on the backtest sample but fail catastrophically on unseen data.

---

## 12. Roll Mechanics Completely Ignored

**Severity: LOW-MEDIUM** · *Identified by: Kimi*

The strategy trades synthetic FRA spreads constructed from DI futures, but the code completely ignores:

- **Roll risk:** As DI contracts approach maturity, the portfolio must roll to maintain the target FRA exposure. Roll timing and roll cost are not modeled.
- **Roll yield:** The carry component of the P&L doesn't account for the actual yield pickup (or shortfall) from rolling contracts.
- **Contract liquidity shifting:** As contracts roll from front-month to back-month, liquidity profiles change — this affects actual execution quality.

The `carry_pnl = 0.01 * position_size` approximation in V5/V6 has **no economic justification** and likely understates the true carry dynamics.

---

## 13. Cross-Asset Signals Completely Absent

**Severity: LOW-MEDIUM** · *Identified by: Gemini Deep, Kimi, Gemini Web*

The strategy operates in a single-instrument vacuum. Critical correlated signals are ignored:

- **USD/BRL:** Currency depreciation is the primary transmission mechanism from fiscal stress to BCB reaction. Not tracking FX removes the most direct early-warning signal for flattening pressure.
- **Brazil 5y CDS:** Offshore sovereign risk pricing often leads onshore DI curve moves. Divergence between CDS and local uncertainty signals → false positive risk.
- **US rates / MOVE index:** Global rate volatility (especially the US 2s10s and UST MOVE index) can dominate local curve dynamics via foreign capital flows. The strategy has zero global macro awareness.

---

## 14. V4 `calculate_position` Returns Wrong Tuple

**Severity: LOW** · *Identified by: Opus (code analysis)*

V4's `calculate_position()` returns a 4-tuple `(position_type, position_size, execution_style, regime)` but the base class and other versions expect a 3-tuple `(position_type, position_size, execution_style)`. This breaks the interface contract and would fail if V4 were run through the `BaseSteepenerStrategy` backtest engine.

---

## 15. V1/V2 Bull Steepener Direction Error

**Severity: LOW** · *Identified by: Opus, Gemini Deep*

During low-uncertainty regimes, V1 and V2 take a **bull steepener** (long short-end, betting on rate cuts). In Brazil, low fiscal uncertainty often coincides with solid growth → BCB keeps rates elevated or hikes → curve flattens. The bull steepener is the **wrong directional bet** in this environment. Combined with V2's broken DV01 model (0.01/0.03 instead of 0.98/2.72), this created massive unhedged directional exposure and drove V2's catastrophic −810 bps loss.

---

## Summary: Flaw Severity Matrix

| # | Flaw | Severity | Affects | Fix Complexity |
|---|------|----------|---------|----------------|
| 1 | Thesis inversion (high uncertainty → flattening) | 🔴 Critical | All versions | Medium |
| 2 | Static DV01 / convexity risk | 🔴 High | V5, V6 | Low |
| 3 | Missing funding costs | 🔴 High | All versions | Low |
<!-- | 4 | Look-ahead bias | 🔴 High | V1–V4 | Fixed in V5 | -->
| 5 | Stop-loss death spiral | 🔴 High | V5, V6 | Medium |
| 6 | Expanding Z-score anchoring | 🟡 Medium | V5, V6 | Low |
| 7 | Unrealistic transaction costs | 🟡 Medium | All versions | Medium |
<!-- | 8 | PCA sign instability | 🟡 Medium | V6 | Medium | -->
| 9 | No liquidity-adjusted sizing | 🟡 Medium | All versions | Medium |
| 10 | Markov model fragility | 🟡 Medium | All versions | High |
| 11 | No walk-forward validation | 🟡 Medium | V5, V6 | Medium |
| 12 | Roll mechanics ignored | 🟡 Low-Med | All versions | Medium |
| 13 | No cross-asset signals | 🟡 Low-Med | All versions | High |
| 14 | V4 tuple mismatch | 🟢 Low | V4 only | Trivial |
| 15 | V1/V2 bull steepener error | 🟢 Low | V1, V2 | Deprecated |
