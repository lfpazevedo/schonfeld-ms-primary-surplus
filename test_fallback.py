import pandas as pd
import numpy as np
import warnings
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
warnings.filterwarnings('ignore')

# Generate some dummy data that looks like std_4y
np.random.seed(42)
# Create regime 0 (low vol) and regime 1 (high vol)
regimes = np.random.choice([0, 1], size=500, p=[0.7, 0.3])
data = np.zeros(500)
for i in range(500):
    if regimes[i] == 0:
        data[i] = np.random.normal(0.2, 0.05)
    else:
        data[i] = np.random.normal(0.6, 0.2)

model = MarkovRegression(data, k_regimes=2, switching_variance=True, trend='c')

try:
    res = model.fit(disp=False)
    print("Normal fit worked. AIC:", res.aic)
except Exception as e:
    print("Normal fit failed:", e)

# Test the fallback explicitly
print("\nTesting fallback...")
try:
    res_fb = model.fit(disp=False, em_iter=0, search_reps=20)
    print("Fallback fit worked. AIC:", res_fb.aic)
    probs = res_fb.smoothed_marginal_probabilities
    print(f"Fallback probs shape: {probs.shape}")
    print(f"Fallback max prob R0: {probs[:,0].max():.3f}, min: {probs[:,0].min():.3f}")
    print(f"Fallback max prob R1: {probs[:,1].max():.3f}, min: {probs[:,1].min():.3f}")
except Exception as e:
    print("Fallback failed:", e)

