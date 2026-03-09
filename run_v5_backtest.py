import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import pickle
import warnings
warnings.filterwarnings('ignore')

from src.base_strategy import fetch_focus_primary_cached, calculate_zscore, calculate_pnl_attribution
from src.markov_regime_analysis import fit_2regime_markov

def run():
    print("Testing importing and running fit_2regime_markov on test data")
    np.random.seed(42)
    test_data = pd.Series(np.random.randn(252) * 0.5 + 0.1)
    
    # Try the one that was failing due to SVD
    # Actually, let's just make sure we catch LinAlgError from numpy
    try:
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
        model = MarkovRegression(
            test_data.values,
            k_regimes=2,
            switching_variance=True,
            trend='c'
        )
        result = model.fit(disp=False)
        print("Success fitting test model!")
    except Exception as e:
        print(f"Caught exception: {type(e).__name__} - {e}")
    except BaseException as e:
        print(f"Caught BaseException: {type(e).__name__} - {e}")

run()
