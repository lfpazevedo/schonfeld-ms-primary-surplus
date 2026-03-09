import numpy as np

def classify_combined_regime_v6(std_4y_zscore, ts_vol, threshold=0.5):
    if np.isnan(ts_vol):
        return 'unknown'
    high_cross = std_4y_zscore > threshold
    high_ts = ts_vol > threshold
    if high_cross and high_ts: return 'active_crisis'
    elif high_cross and not high_ts: return 'chronic_disagreement'
    elif not high_cross and high_ts: return 'consensus_shock'
    else: return 'calm'

MAX_POSITION = 1.0
ZSCORE_HIGH = 0.5
ZSCORE_LOW = -0.5
INFLATION_HIGH_THRESHOLD = 0.6

def calculate_position_v6(z, ts_vol, prob_high, prob_pca_accel):
    if np.isnan(z):
        return 'neutral', 0.0, 'standard'
    
    if isinstance(prob_pca_accel, (int, float)) and not np.isnan(prob_pca_accel):
        if prob_pca_accel > INFLATION_HIGH_THRESHOLD:
            return 'risk_off_inflation_accel', 0.0, 'no_trade'
            
    combined_regime = classify_combined_regime_v6(z, ts_vol, ZSCORE_HIGH)
    
    if combined_regime == 'active_crisis':
        raw = min(1.0, 0.5 + (z - ZSCORE_HIGH) / 1.0) * 1.2
        position_type = 'bear_steepener'
        execution = 'pay_spread'
    elif combined_regime == 'chronic_disagreement':
        raw = min(0.5, 0.25 + (z - ZSCORE_HIGH) / 2.0) if z > ZSCORE_HIGH else 0.0
        position_type = 'small_bear' if raw > 0 else 'neutral'
        execution = 'standard'
    elif combined_regime == 'consensus_shock':
        raw = min(0.8, 0.4 + abs(z) / 2.0)
        position_type = 'bear_steepener' if z > 0 else 'flattener'
        execution = 'pay_spread' if z > 0 else 'collect_carry'
    elif z > ZSCORE_HIGH:
        raw = min(1.0, 0.5 + (z - ZSCORE_HIGH) / 1.0)
        position_type = 'bear_steepener'
        execution = 'pay_spread'
    elif z < ZSCORE_LOW:
        raw = max(-0.5, -0.25 + (z - ZSCORE_LOW) / 2.0)
        position_type = 'flattener'
        execution = 'collect_carry'
    else:
        raw = 0.25 * (z / max(abs(ZSCORE_HIGH), 0.01))
        position_type = 'small_bear' if raw > 0 else 'small_flat'
        execution = 'standard'
        
    if position_type == 'bear_steepener' and prob_high > 0.5:
        confidence = min(1.0, (prob_high - 0.5) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)
    elif position_type == 'flattener' and prob_high < 0.5:
        confidence = min(1.0, (0.5 - prob_high) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)
    elif position_type in ('bear_steepener', 'flattener'):
        size = raw * 0.4
    else:
        size = raw
        
    size = max(-MAX_POSITION, min(MAX_POSITION * 1.2, size))
    return position_type, size, execution, raw, combined_regime

# Simulating April 2021
# From the chart: Fiscal P(High Vol) ~ 0.0
# Inflation P(Accel) ~ 0.55 (so < 0.6)
# Z-score must be high because we have a position. 
# ts_vol must be high too to get 1.2 size.

z = 2.0
ts_vol = 1.0
prob_high = 0.0
prob_pca_accel = 0.55

ptype, size, ex, raw, regime = calculate_position_v6(z, ts_vol, prob_high, prob_pca_accel)
print(f"Type: {ptype}, Size: {size}, Raw: {raw}, Regime: {regime}")

# Try another case where maybe size bypasses the 0.4 scaling
