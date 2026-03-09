# CELL: Optimized 3-Regime Markov-Switching PCA (V7)
# Replace the existing compute_pca_regimes cell with this implementation

from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from sklearn.decomposition import IncrementalPCA
import numpy as np
import pandas as pd

def compute_pca_regimes_v7(ipca_df, selic_df, min_obs=252, smooth_window=20):
    """
    OPTIMIZED 3-REGIME MS FOR INCREMENTAL PCA:
    
    1. Incremental PCA on 4 series (IPCA median/std, Selic median/std)
    2. 3-regime Markov-Switching with PARAMETER SEEDING (warm-start)
    3. Automatic regime sorting by mean level (Low < Mid < High)
    4. Returns high-regime probability for trade blocking
    
    Parameters:
    -----------
    ipca_df : DataFrame with ['date', 'median_forecast', 'std_forecast']
    selic_df : DataFrame with ['date', 'median_forecast', 'std_forecast']
    min_obs : Minimum observations before starting PCA (default: 252 = 1 year)
    smooth_window : Rolling window for smoothing PC1 before MS (default: 20 days)
    
    Returns:
    --------
    DataFrame with ['date', 'pca1', 'prob_pca_high', 'prob_pca_mid', 'prob_pca_low', 'pca_regime']
    """
    # 1. Data Preparation
    merged = pd.merge(ipca_df, selic_df, on='date', suffixes=('_ipca', '_selic'))
    merged = merged.sort_values('date').reset_index(drop=True)
    
    numeric_cols = ['median_forecast_ipca', 'std_forecast_ipca',
                   'median_forecast_selic', 'std_forecast_selic']
    
    # Forward fill any NaN values
    for col in numeric_cols:
        merged[col] = merged[col].ffill()
    
    data = merged[numeric_cols].values
    dates = merged['date'].values
    n = len(merged)
    n_features = len(numeric_cols)
    
    # Pre-allocate results
    pca1_values = np.full(n, np.nan)
    prob_high = np.full(n, np.nan)
    prob_mid = np.full(n, np.nan)
    prob_low = np.full(n, np.nan)
    regimes = ['unknown'] * n
    
    # Welford's algorithm for running mean and variance
    running_mean = np.zeros(n_features)
    running_m2 = np.zeros(n_features)
    
    # PCA Setup
    ipca_model = IncrementalPCA(n_components=1, batch_size=min_obs)
    
    # Markov-Switching Seeding (key optimization!)
    last_params = None
    last_regime_order = None  # To track regime flipping
    
    print(f"Starting incremental 3-regime MS for {n} days...")
    
    for i in range(n):
        x = data[i]
        
        # Skip if any value is NaN
        if np.isnan(x).any():
            continue
        
        # Update running statistics using Welford's algorithm
        delta = x - running_mean
        running_mean += delta / (i + 1)
        delta2 = x - running_mean
        running_m2 += delta * delta2
        
        if i < min_obs:
            continue
        
        # Compute running std
        running_var = running_m2 / i
        running_std = np.sqrt(running_var)
        running_std[running_std == 0] = 1  # Avoid division by zero
        
        # Standardize current observation
        x_scaled = (x - running_mean) / running_std
        
        # Update IncrementalPCA
        if i == min_obs:
            # Initial fit on first min_obs observations
            hist_data = data[:i]
            hist_scaled = (hist_data - running_mean) / running_std
            ipca_model.fit(hist_scaled)
        elif i > min_obs:
            # Partial fit with new observation
            ipca_model.partial_fit(x_scaled.reshape(1, -1))
        
        # Transform current observation to get PC1
        pca1 = ipca_model.transform(x_scaled.reshape(1, -1))[0, 0]
        pca1_values[i] = pca1
        
        # 2. Daily 3-Regime Markov-Switching
        # Need enough PC1 history + smoothing window
        if i >= min_obs + smooth_window + 10:
            # Get PC1 history up to current point
            pc1_history = pca1_values[~np.isnan(pca1_values)]
            
            # Smooth the PC1 series (reduces noise for MS)
            pc1_series = pd.Series(pc1_history)
            smooth_pc1 = pc1_series.rolling(window=smooth_window, min_periods=smooth_window//2).mean()
            smooth_values = smooth_pc1.dropna().values
            
            # Need enough smoothed observations
            if len(smooth_values) >= min_obs // 2:
                try:
                    # Fit 3-regime Markov with switching variance
                    model = MarkovRegression(
                        smooth_values,
                        k_regimes=3,
                        switching_variance=True,
                        trend='n'  # No trend for stationary PC1
                    )
                    
                    # OPTIMIZATION 1: Parameter Seeding (Warm-Start)
                    # Use previous day's params to seed today's optimization
                    if last_params is not None and len(last_params) == model.nparams:
                        res = model.fit(
                            start_params=last_params,
                            disp=False,
                            cov_type='none',  # OPTIMIZATION 2: Skip Hessian calculation
                            maxiter=50  # Limit iterations (warm start helps convergence)
                        )
                    else:
                        # First fit - use default initialization
                        res = model.fit(
                            disp=False,
                            cov_type='none',
                            maxiter=100
                        )
                    
                    # Save params for tomorrow's warm-start
                    last_params = res.params.copy()
                    
                    # OPTIMIZATION 3: Regime Sorting by Mean Level
                    # Markov regimes are unordered - sort by mean to ensure consistency
                    # Parameters: [p00, p01, p10, p11, mu0, mu1, mu2, sigma0, sigma1, sigma2]
                    # For 3 regimes: means are at indices 4, 5, 6 (k_regimes + 1 to 2*k_regimes)
                    means = np.array([
                        res.params[4],  # mu0
                        res.params[5],  # mu1
                        res.params[6]   # mu2
                    ])
                    
                    # Sort regimes by mean: Low < Mid < High
                    order = np.argsort(means)  # Indices that sort ascending
                    # order[0] = index of lowest mean regime
                    # order[1] = index of middle mean regime  
                    # order[2] = index of highest mean regime
                    
                    # Get smoothed probabilities for all 3 regimes
                    smoothed_probs = res.smoothed_marginal_probabilities
                    
                    # Reorder probabilities by sorted regime means
                    prob_low_val = smoothed_probs[-1, order[0]]
                    prob_mid_val = smoothed_probs[-1, order[1]]
                    prob_high_val = smoothed_probs[-1, order[2]]
                    
                    # Store probabilities
                    prob_low[i] = prob_low_val
                    prob_mid[i] = prob_mid_val
                    prob_high[i] = prob_high_val
                    
                    # Classify regime based on highest probability
                    if prob_high_val > 0.5:
                        regimes[i] = 'high'
                    elif prob_low_val > 0.5:
                        regimes[i] = 'low'
                    else:
                        regimes[i] = 'neutral'
                    
                except Exception as e:
                    # Reset seeding on failure
                    last_params = None
                    # Keep previous regime classification if available
                    if i > 0 and regimes[i-1] != 'unknown':
                        regimes[i] = regimes[i-1]
        
        # Progress reporting
        if i % 500 == 0:
            print(f"  Processed day {i}/{n} ({100*i/n:.1f}%)")
    
    print(f"Complete! Processed {n} days.")
    
    return pd.DataFrame({
        'date': dates,
        'pca1': pca1_values,
        'prob_pca_low': prob_low,
        'prob_pca_mid': prob_mid,
        'prob_pca_high': prob_high,
        'pca_regime': regimes
    })


# ============================================================================
# V7 Position Calculation with 3-Regime MS Block
# ============================================================================

# Configuration for V7
INFLATION_HIGH_THRESHOLD = 0.6  # Block if prob_pca_high > 60%

def calculate_position_v7(row, context):
    """
    V7 position sizing with 3-Regime MS PCA filter.
    Uses prob_pca_high for trade blocking (not just regime label).
    
    Returns: (position_type, position_size, execution_style)
    """
    z = row.get('std_4y_zscore', 0.0)
    prob_high_vol = row.get('prob_high_vol', 0.5)
    prob_pca_high = row.get('prob_pca_high', 0.0)
    
    if pd.isna(z):
        return 'neutral', 0.0, 'standard'
    
    # STEP 0: 3-Regime MS PCA Filter - BLOCK if high inflation probability
    # This uses the continuous probability, not just discrete regime
    if isinstance(prob_pca_high, (int, float)) and not pd.isna(prob_pca_high):
        if prob_pca_high > INFLATION_HIGH_THRESHOLD:
            return 'risk_off_high_inflation', 0.0, 'no_trade'
    
    # STEP 1: Standard V5/V6 signal logic (reused)
    # (Copy your existing signal logic here)
    if z > 2.0:
        raw = min(1.0, 0.5 + (z - 2.0) / 1.0)
        position_type = 'bear_steepener'
        execution = 'pay_spread'
    elif z < -1.5:
        raw = max(-0.5, -0.25 + (z - (-1.5)) / 2.0)
        position_type = 'flattener'
        execution = 'collect_carry'
    else:
        raw = 0.25 * (z / 2.0)
        position_type = 'small_bear' if raw > 0 else 'small_flat'
        execution = 'standard'
    
    # STEP 2: Markov confidence scaling
    if position_type == 'bear_steepener' and prob_high_vol > 0.5:
        confidence = min(1.0, (prob_high_vol - 0.5) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)
    elif position_type == 'flattener' and prob_high_vol < 0.5:
        confidence = min(1.0, (0.5 - prob_high_vol) / 0.3)
        size = raw * (0.5 + 0.5 * confidence)
    else:
        size = raw * 0.4
    
    size = max(-1.0, min(1.0, size))
    
    return position_type, size, execution


# ============================================================================
# Usage Example (replace your existing PCA cell with this)
# ============================================================================

pca_cache_file_v7 = 'pca_regimes_v7_3regime.pkl'

if os.path.exists(pca_cache_file_v7):
    pca_regimes_v7 = pd.read_pickle(pca_cache_file_v7)
    print(f"Loaded V7 PCA regimes from cache: {pca_cache_file_v7}")
else:
    print("Computing V7 3-regime MS PCA (optimized with warm-start)...")
    print("This may take 2-5 minutes depending on your data length...")
    
    pca_regimes_v7 = compute_pca_regimes_v7(ipca_df, selic_df)
    pca_regimes_v7.to_pickle(pca_cache_file_v7)
    print(f"Saved V7 PCA regimes to cache: {pca_cache_file_v7}")

print(f"\nV7 PCA regimes calculated for: {len(pca_regimes_v7)} dates")
print(f"\nRegime distribution:")
print(pca_regimes_v7['pca_regime'].value_counts())
print(f"\nHigh regime probability stats:")
print(pca_regimes_v7['prob_pca_high'].describe())
