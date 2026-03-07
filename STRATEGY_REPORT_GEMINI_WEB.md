Here is a detailed report on the evolution, architecture, and mechanics of your fiscal uncertainty steepener strategies, along with actionable tips for improvement.

---

### Strategy Overview

This codebase implements a quantitative fixed-income trading strategy targeting the Brazilian DI FRA curve (specifically the 1y1y vs. 3y3y spread). The core thesis is macroeconomic: **high fiscal uncertainty drives term premium expansion, leading to a steeper yield curve (bear steepening)**, while low uncertainty compresses the term premium, favoring curve flattening and carry collection.

The strategy uses `std_4y` (a proxy for fiscal uncertainty) and evolves from a simple binary regime-switching model into a sophisticated, production-grade system with dynamic PCA risk filtering, non-linear slippage, and momentum alignments.

---

### Evolution of the Strategy (V1 to V6)

#### **V1: The Binary Baseline** (`steepener_strategy.py`)

* **Core Logic:** Trades are established on fiscal release dates and held until the next release.
* **Signal:** Uses a strict 0.5 threshold on the Markov probability of a "high volatility" regime.
* **Execution:** High uncertainty triggers a Bear Steepener ("Pay the Spread"); low uncertainty triggers a Bull Steepener ("Collect Carry").
* **Drawbacks:** Highly static. Fixed transaction costs and rigid holding periods fail to capture intra-period market dynamics.

#### **V2: Continuous Sizing** (`steepener_strategy_v2.py`)

* **Core Logic:** Shifts to daily position management.
* **Signal:** Position size scales linearly based on the strength of the regime probability (e.g., scaling up as probability moves from 50% to 80%).
* **Drawbacks:** Still relies entirely on raw probabilities without normalizing the underlying uncertainty data, leaving it vulnerable to structural breaks in the data.

#### **V3: Percentile-Based Scaling** (`steepener_strategy_v3.py`)

* **Core Logic:** Shifts the primary signal from Markov probabilities to the actual distribution (percentiles) of `std_4y`.
* **Signal:** < 25th percentile = Flattener/Collect Carry. > 75th percentile = Full Bear Steepener/Pay the Spread.
* **Drawbacks:** Uses full-sample percentiles, introducing **look-ahead bias** into the backtest.

#### **V4: Momentum Integration** (`steepener_strategy_v4.py`)

* **Core Logic:** Introduces a trend filter to avoid fighting market momentum.
* **Signal:** Compares the curve spread against a 20-day moving average. If the spread is compressed relative to the MA, it increases the steepener size (mean reversion). If it is extended, it reduces the size.
* **Drawbacks:** Fixed cost assumptions still limit realism.

#### **V5: Production-Grade & Risk Managed** (`steepener_strategy_v5.py` & `base_strategy.py`)

* **Core Logic:** Implements institutional-grade mechanics, removing look-ahead bias completely.
* **Signal:** Primary signal is an **expanding-window Z-score** of `std_4y`. The Markov probability is repurposed as a *confidence multiplier* (confirming or dampening the Z-score signal).
* **Execution & Risk:** * Proper DV01-neutral risk weighting.
* Non-linear execution costs ($Cost = Base + Impact \times Size^2$).
* A trailing stop-loss of 50 bps that flattens the position upon breach.



#### **V6: PCA & Inflation Risk Filter** (`steepener_strategy_v6.py`)

* **Core Logic:** Adds a macro-prudential override based on inflation expectations.
* **Signal:** Computes a Dynamic PCA (First Principal Component) on an expanding window of IPCA forecasts, Selic expectations, and fiscal uncertainty.
* **Execution & Risk:** Fits a 3-regime Markov model  to the PCA. If the regime detects "high inflation expectations" (all-time highs in the dynamic window), it triggers a **hard risk-off block**, halting all steepening positions to avoid catastrophic drawdowns.

---

### Core Architectural Components

**1. The Markov Engine (`markov_regime_analysis.py`)**
A brilliant solution to the "barcode" flipping problem (where models rapidly alternate regimes day-to-day). By applying the Markov model to a 20-day rolling mean of the *daily differences* of `std_4y`, the system effectively captures the *trend* of uncertainty over a month, yielding stable, actionable regimes (Rising vs. Stable).

**2. Dual Execution Styles**
The codebase smartly delineates execution urgency based on the macro environment:

* **Pay the Spread:** Used during high-uncertainty regimes. Accepts higher slippage/costs for immediate execution to capture rapid curve steepening.
* **Collect the Carry:** Used during low-uncertainty regimes. Simulates passive order placement to earn carry and roll-down.

**3. Base Strategy Abstraction (`base_strategy.py`)**
Consolidating the boilerplate (data loading, walk-forward loop, DV01 P&L logic, and performance reporting) into an abstract base class makes V5 and V6 exceptionally clean and easy to iterate upon.

---

### Tips for Improvement

**1. Exogenous Macro Filters (US Treasuries)**
Emerging market yield curves do not steepen or flatten in a vacuum; they are highly sensitive to the US curve.

* *Action:* Integrate the UST 2s10s spread or the MOVE index as a secondary dynamic filter. If the US curve is flattening aggressively, a BRL steepener might face severe headwinds despite local fiscal noise.

**2. Dynamic Stop-Loss Thresholds**
A fixed 50 bps trailing stop-loss in V5/V6 might be too tight in high-volatility regimes and too loose in low-volatility regimes.

* *Action:* Make the stop-loss a function of recent curve volatility (e.g., $Stop Loss = 2 \times 20\text{-day ATR of the spread}$).

**3. Refine the PCA Lookback Window**
In V6, you are using a `pca_lookback` of 252 days (1 year). Inflation expectation regimes can often persist longer than a year, meaning a 1-year window might dynamically normalize a permanently higher inflation baseline, causing the model to re-enter trades prematurely.

* *Action:* Test a slower-moving PCA window (e.g., 504 days / 2 years) or use an expanding window with a half-life decay to give more weight to recent data without entirely forgetting the structural past.

**4. Introduce a Carry-to-Risk Metric**
Currently, the strategy flips to a flattener / carry collection when uncertainty is low. However, if the absolute level of carry is poor, the risk of a sudden regime shift outweighs the yield earned.

* *Action:* Calculate the actual yield pickup (carry) per unit of historical volatility. Only activate "Collect Carry" if the Carry/Vol ratio exceeds a specific threshold.

**5. Hyperparameter Optimization Framework**
Parameters like `zscore_high=0.5`, `prob_confidence=0.8`, and `pca_lookback=252` are currently hardcoded.

* *Action:* Implement a `WalkForwardOptimizer` script to ensure these parameters are robust across different market eras (e.g., pre-COVID vs. post-COVID) and aren't overfitted to the backtest.

---

Would you like me to draft a Python script for the dynamic volatility-based stop-loss implementation?