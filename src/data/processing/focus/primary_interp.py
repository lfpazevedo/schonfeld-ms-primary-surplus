#!/usr/bin/env python
"""
Process Focus Primary Result forecasts into interpolated time series.

Builds 1y and 4y ahead interpolated curves for both median forecasts
and standard deviation (forecast uncertainty).

Output: src/data/processed/focus/primary_1y_4y_interp.csv

Usage:
    python src/data/processing/focus/primary_interp.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.api.focus.primary import fetch_primary_median_data, fetch_primary_std_data


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("src/data/processed/focus")
OUTPUT_FILE = OUTPUT_DIR / "primary_1y_4y_interp.csv"


# =============================================================================
# INTERPOLATION FUNCTIONS
# =============================================================================

def build_interpolated_curves(df, value_column):
    """
    Build 1-year and 4-year ahead interpolated curves.
    
    For each date, interpolate between consecutive years based on day of year:
    - 1y ahead: Interpolates between Y and Y+1
    - 4y ahead: Interpolates between Y+3 and Y+4
    
    Args:
        df: DataFrame with columns Data, DataReferencia, and value_column
        value_column: Name of column ('Mediana' or 'DesvioPadrao')
        
    Returns:
        DataFrame with daily interpolated values
    """
    print(f"\nBuilding {value_column} interpolated curves...")
    
    # Convert dates
    df = df.copy()
    df['Data'] = pd.to_datetime(df['Data'])
    df['DataReferencia'] = df['DataReferencia'].astype(int)
    df[value_column] = pd.to_numeric(df[value_column], errors='coerce')
    
    # Get date range
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    
    # Create daily business days
    daily_dates = pd.date_range(start=min_date, end=max_date, freq='B')
    
    result = []
    
    for current_date in daily_dates:
        current_year = current_date.year
        
        # Years for interpolation
        year_1y_current = current_year
        year_1y_next = current_year + 1
        year_4y_current = current_year + 3
        year_4y_next = current_year + 4
        
        # Get survey data for this date
        date_data = df[df['Data'] == current_date]
        
        if date_data.empty:
            continue
        
        # Get values for each horizon
        data_1y_curr = date_data[date_data['DataReferencia'] == year_1y_current]
        data_1y_next = date_data[date_data['DataReferencia'] == year_1y_next]
        data_4y_curr = date_data[date_data['DataReferencia'] == year_4y_current]
        data_4y_next = date_data[date_data['DataReferencia'] == year_4y_next]
        
        # Skip if missing data
        if (data_1y_curr.empty or data_1y_next.empty or 
            data_4y_curr.empty or data_4y_next.empty):
            continue
        
        val_1y_curr = data_1y_curr[value_column].values[0]
        val_1y_next = data_1y_next[value_column].values[0]
        val_4y_curr = data_4y_curr[value_column].values[0]
        val_4y_next = data_4y_next[value_column].values[0]
        
        # Calculate weight based on day of year
        day_of_year = current_date.timetuple().tm_yday
        days_in_year = 366 if (current_year % 4 == 0 and current_year % 100 != 0) or (current_year % 400 == 0) else 365
        weight = day_of_year / days_in_year
        
        # Linear interpolations
        interp_1y = val_1y_curr * (1 - weight) + val_1y_next * weight
        interp_4y = val_4y_curr * (1 - weight) + val_4y_next * weight
        
        result.append({
            'date': current_date,
            f'{value_column}_1y_interp': interp_1y,
            f'{value_column}_4y_interp': interp_4y,
        })
    
    result_df = pd.DataFrame(result)
    if not result_df.empty:
        result_df = result_df.set_index('date')
        result_df = result_df.sort_index()
        
    return result_df


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    """Main processing pipeline."""
    print("=" * 70)
    print("Focus Primary Result - Interpolated Curves Processor")
    print("=" * 70)
    
    # Fetch data from Focus API
    print("\n[1/4] Fetching median data...")
    median_raw = fetch_primary_median_data()
    
    print("\n[2/4] Fetching standard deviation data...")
    std_raw = fetch_primary_std_data()
    
    # Build interpolated curves
    print("\n[3/4] Building interpolated curves...")
    median_interp = build_interpolated_curves(median_raw, 'Mediana')
    std_interp = build_interpolated_curves(std_raw, 'DesvioPadrao')
    
    # Merge data
    print("\n[4/4] Merging and saving...")
    merged = median_interp.join(std_interp, how='inner')
    
    # Rename columns for clarity
    merged.columns = [
        'median_1y', 'median_4y',
        'std_1y', 'std_4y'
    ]
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    merged.to_csv(OUTPUT_FILE)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"Total rows: {len(merged)}")
    print(f"Date range: {merged.index.min().strftime('%Y-%m-%d')} to {merged.index.max().strftime('%Y-%m-%d')}")
    
    print("\nColumns:")
    for col in merged.columns:
        print(f"  - {col}")
    
    print("\nSample data (last 5 rows):")
    print(merged.tail().to_string())
    
    print("\nSummary statistics:")
    print(merged.describe().to_string())
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
