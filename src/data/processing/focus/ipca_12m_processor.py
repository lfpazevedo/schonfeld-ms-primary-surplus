#!/usr/bin/env python
"""
Process Focus IPCA 12-month ahead forecasts into a clean time-series.

Output: src/data/processed/focus/ipca_12m_forecast.csv

Usage:
    python src/data/processing/focus/ipca_12m_processor.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.api.focus.ipca import fetch_ipca_data


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("src/data/processed/focus")
OUTPUT_FILE = OUTPUT_DIR / "ipca_12m_forecast.csv"


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def process_ipca_forecasts(df):
    """
    Process IPCA 12-month forecasts to extract median and std dev.
    
    Args:
        df: DataFrame with IPCA forecasts from Focus API
        
    Returns:
        DataFrame with daily median and std dev forecasts
    """
    print("\nProcessing IPCA 12-month forecasts...")
    
    # Convert dates
    df = df.copy()
    df['Data'] = pd.to_datetime(df['Data'])
    
    # Convert numeric columns
    for col in ['Mediana', 'DesvioPadrao', 'Media']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter for baseCalculo=0 (calendar year) if available, otherwise use all
    if 'baseCalculo' in df.columns:
        df = df[df['baseCalculo'] == 0].copy()
    
    # Group by date and get the first entry (or average if multiple)
    daily_data = df.groupby('Data').agg({
        'Mediana': 'first',
        'Media': 'first',
        'DesvioPadrao': 'first',
        'Minimo': 'first',
        'Maximo': 'first',
        'numeroRespondentes': 'first'
    }).reset_index()
    
    daily_data = daily_data.rename(columns={
        'Data': 'date',
        'Mediana': 'median_forecast',
        'Media': 'mean_forecast',
        'DesvioPadrao': 'std_forecast',
        'Minimo': 'min_forecast',
        'Maximo': 'max_forecast',
        'numeroRespondentes': 'num_respondents'
    })
    
    daily_data = daily_data.set_index('date').sort_index()
    
    return daily_data


def interpolate_to_business_days(df):
    """
    Interpolate the time-series to all business days.
    
    Args:
        df: DataFrame with irregular date index
        
    Returns:
        DataFrame with daily business day index and interpolated values
    """
    print("\nInterpolating to business days...")
    
    if df.empty:
        return df
    
    # Create business day index
    min_date = df.index.min()
    max_date = df.index.max()
    daily_index = pd.date_range(start=min_date, end=max_date, freq='B')
    
    # Reindex and interpolate
    df_daily = df.reindex(daily_index)
    
    # Interpolate numeric columns only
    numeric_cols = ['median_forecast', 'mean_forecast', 'std_forecast', 'min_forecast', 'max_forecast']
    for col in numeric_cols:
        if col in df_daily.columns:
            df_daily[col] = df_daily[col].interpolate(method='linear')
    
    # Forward fill num_respondents
    if 'num_respondents' in df_daily.columns:
        df_daily['num_respondents'] = df_daily['num_respondents'].ffill()
    
    return df_daily


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    """Main processing pipeline."""
    print("=" * 70)
    print("Focus IPCA - 12-Month Ahead Forecast Processor")
    print("=" * 70)
    
    # Fetch IPCA 12-month data from Focus API
    print("\n[1/3] Fetching IPCA 12-month forecasts from Focus API...")
    df_raw = fetch_ipca_data(top=100000, months_ahead=12)
    print(f"Fetched {len(df_raw)} forecast records")
    print(f"Date range: {df_raw['Data'].min()} to {df_raw['Data'].max()}")
    
    # Process forecasts
    print("\n[2/3] Processing forecasts...")
    df_processed = process_ipca_forecasts(df_raw)
    print(f"Created {len(df_processed)} daily forecast points")
    
    if df_processed.empty:
        print("\nERROR: No forecasts could be generated!")
        return
    
    # Interpolate to business days
    print("\n[3/3] Interpolating to business days...")
    df_daily = interpolate_to_business_days(df_processed)
    print(f"Interpolated to {len(df_daily)} business days")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    df_daily.to_csv(OUTPUT_FILE)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"Total rows: {len(df_daily)}")
    print(f"Date range: {df_daily.index.min().strftime('%Y-%m-%d')} to {df_daily.index.max().strftime('%Y-%m-%d')}")
    
    print("\nColumns:")
    for col in df_daily.columns:
        print(f"  - {col}")
    
    print("\nSample data (first 5 rows):")
    print(df_daily.head().to_string())
    
    print("\nSample data (last 5 rows):")
    print(df_daily.tail().to_string())
    
    print("\nSummary statistics:")
    print(df_daily[['median_forecast', 'std_forecast']].describe().to_string())
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
