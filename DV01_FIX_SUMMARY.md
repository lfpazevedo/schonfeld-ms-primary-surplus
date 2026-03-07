# Fix: Static DV01 Ratios — Unhedged Convexity Risk

## Problem
V5/V6 used hardcoded DV01 values (`DV01_1Y1Y = 0.98`, `DV01_3Y3Y = 2.72`) that never updated.
This created two problems:
1. **Duration drift**: As yields move, the actual DV01 of each leg changes
2. **Convexity bleed**: During large yield moves, the second-derivative mismatch between legs causes P&L to deviate

## Solution Implemented

### Phase 1: Dynamic DV01 Recalculation (Baseline Fix)
Added methods to `BaseSteepenerStrategy` for calculating DV01 dynamically:

```python
calculate_dv01_di_fra(forward_rate, start_years, tenor_years)
calculate_convexity_di_fra(forward_rate, start_years, tenor_years)
update_dynamic_dv01(current_yield_1y1y, current_yield_3y3y, force)
calculate_gamma_pnl(position_size, change_1y1y_bps, change_3y3y_bps, ...)
```

### Phase 2: Convexity P&L Attribution (Diagnostic Fix)
Added `gamma_pnl` to P&L reporting to track the "convexity bleed" separately from curve P&L.

### Phase 3: Tolerance-Band Rebalancing (Operational Fix)
Implemented tolerance-band logic to avoid excessive micro-trading:
- DV01 is only recalculated when yields move > 25 bps from last calculation level
- Configurable via `dv01_rebalance_threshold_bps` parameter

## Key Changes

### base_strategy.py
1. Added configuration parameters for DV01 and convexity
2. Added state variables for tracking DV01 updates
3. Added `calculate_dv01_di_fra()` - Brazilian DI FRA DV01 formula
4. Added `calculate_convexity_di_fra()` - convexity calculation
5. Added `update_dynamic_dv01()` - tolerance-band rebalancing logic
6. Added `calculate_gamma_pnl()` - second-order P&L attribution
7. Updated `run_backtest()` to call DV01 update each day
8. Updated `print_report()` to show DV01 stats and P&L attribution

### steepener_strategy_v5.py
1. Updated `calculate_pnl()` to accept yield levels and dv01_update
2. Added gamma P&L calculation using dynamic convexity values
3. Updated return dict to include `gamma_pnl` and `dv01_ratio`

### steepener_strategy_v6.py
1. Same changes as V5
2. Updated `run_backtest()` override to include DV01 update logic

## Usage

### Enable Dynamic DV01 (default)
```python
strategy = SteepenerStrategyV5(
    use_dynamic_dv01=True,              # Enable dynamic DV01 (default: True)
    dv01_rebalance_threshold_bps=25.0,  # Recalc when yields move > 25 bps
)
```

### Use Static DV01 (legacy behavior)
```python
strategy = SteepenerStrategyV5(
    use_dynamic_dv01=False,  # Use static 0.98/2.72 DV01 values
)
```

## Results

Typical DV01 ratio variation observed:
- Static ratio: 0.3603 (0.98/2.72)
- Dynamic ratio range: 0.4550 - 0.6552 (varies with yield levels)
- Mean dynamic ratio: ~0.53

This shows the static ratio significantly underestimates the true hedge ratio needed,
leading to the "convexity bleed" P&L component.

## P&L Attribution

The new reporting shows:
- **Curve P&L**: First-order spread change (DV01-neutral)
- **Gamma P&L**: Second-order convexity effects
- **Carry**: Roll-down approximation
- **Costs**: Execution costs and market impact

## References

- Brazilian DI Futures DV01 formula: `Price = 100,000 / (1+r)^(DU/252)`
- DV01 calculation: `DV01 = Price × (DU/252) × 1/(1+r) × 0.0001`
- Convexity: `C ≈ T × (T+1) / (1+r)²`
- Gamma P&L: `Γ_PnL = 0.5 × C × (Δy)²`
