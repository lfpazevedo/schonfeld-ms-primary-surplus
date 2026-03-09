import pandas as pd
import numpy as np
import pickle
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
import warnings
warnings.filterwarnings('ignore')

try:
    # Try to load focus_primary_cache.csv
    df = pd.read_csv('focus_primary_cache.csv')
    
    # We need the 'date' column. It might be named 'Data' or 'date'
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    elif 'Data' in df.columns:
        df['date'] = pd.to_datetime(df['Data'])
        
    df = df.sort_values('date')
    series = df[df['date'] <= '2021-04-30']['DesvioPadrao'].dropna() # is std_4y called DesvioPadrao?
    
    print(f"Loaded {len(series)} data points.")
    
    # Actually, in the notebook, focus_data['std_4y'] comes from focus_primary_cache.csv but how?
    # Let's check how the notebook creates backtest_data.
except Exception as e:
    print(f"Failed: {e}")
