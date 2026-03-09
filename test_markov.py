import pandas as pd
import numpy as np
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

import os
if os.path.exists('focus_primary_cache.csv'):
    df = pd.read_csv('focus_primary_cache.csv', parse_dates=['date'])
    series = df[df['date'] <= '2021-04-30']['std_4y'].dropna()
    print("Series length:", len(series))
    
    print("Testing with em_iter=0...")
    model1 = MarkovRegression(series.values, k_regimes=2, switching_variance=True, trend='c')
    res1 = model1.fit(disp=False, em_iter=0)
    print("em_iter=0 P(Regime 1):", res1.smoothed_marginal_probabilities[:, 1].mean())
    print("em_iter=0 P(Regime 0):", res1.smoothed_marginal_probabilities[:, 0].mean())
    print("AIC:", res1.aic)
    
    print("\nTesting with search_reps=20...")
    model2 = MarkovRegression(series.values, k_regimes=2, switching_variance=True, trend='c')
    try:
        res2 = model2.fit(disp=False, search_reps=20)
        print("search_reps=20 P(Regime 1):", res2.smoothed_marginal_probabilities[:, 1].mean())
        print("AIC:", res2.aic)
    except Exception as e:
        print("search_reps=20 failed:", e)

    print("\nTesting with search_iter=10 (to try different init)...")
    model4 = MarkovRegression(series.values, k_regimes=2, switching_variance=True, trend='c')
    try:
        res4 = model4.fit(disp=False, em_iter=5)
        print("em_iter=5 P(Regime 1):", res4.smoothed_marginal_probabilities[:, 1].mean())
        print("AIC:", res4.aic)
    except Exception as e:
        print("em_iter=5 failed:", e)

    print("\nTesting with default...")
    model3 = MarkovRegression(series.values, k_regimes=2, switching_variance=True, trend='c')
    try:
        res3 = model3.fit(disp=False)
        print("default P(Regime 1):", res3.smoothed_marginal_probabilities[:, 1].mean())
        print("AIC:", res3.aic)
    except Exception as e:
        print("default failed:", e)
