#!/usr/bin/env python
"""
Process Focus SELIC forecasts into 1-year ahead time-series.

Maps Copom meeting codes (e.g., R1/2028) to actual meeting dates from the calendar
and constructs a 1-year ahead forecast time-series (median and std dev).

Output: src/data/processed/focus/selic_1y_forecast.csv

Usage:
    python src/data/processing/focus/selic_1y_processor.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.api.focus.selic import fetch_selic_data


# =============================================================================
# CONFIGURATION
# =============================================================================

CALENDAR_FILE = Path("src/data/processed/calendar/copom_meetings.csv")
OUTPUT_DIR = Path("src/data/processed/focus")
OUTPUT_FILE = OUTPUT_DIR / "selic_1y_forecast.csv"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_meeting_calendar():
    """
    Load and process Copom meeting calendar.
    
    Returns:
        DataFrame with columns: reuniao_code, meeting_date, meeting_year, meeting_in_year
    """
    cal = pd.read_csv(CALENDAR_FILE)
    cal['publication_date'] = pd.to_datetime(cal['publication_date'])
    
    # Sort by date and create meeting codes like R1/2028
    cal = cal.sort_values('publication_date').reset_index(drop=True)
    cal['meeting_in_year'] = cal.groupby('meeting_year').cumcount() + 1
    cal['reuniao_code'] = 'R' + cal['meeting_in_year'].astype(str) + '/' + cal['meeting_year'].astype(str)
    
    # Select relevant columns
    result = cal[['reuniao_code', 'publication_date', 'meeting_year', 'meeting_in_year']].copy()
    result.columns = ['reuniao_code', 'meeting_date', 'meeting_year', 'meeting_in_year']
    
    return result


def find_meeting_1y_ahead(survey_date, calendar_df):
    """
    Find the Copom meeting that is approximately 1-year ahead from the survey date.
    
    Finds the meeting closest to (survey_date + 365 days), ensuring it's at least
    30 days ahead to avoid using the immediate next meeting.
    
    Args:
        survey_date: The date of the survey/forecast
        calendar_df: DataFrame with meeting dates
        
    Returns:
        reuniao_code of the meeting closest to 1-year ahead, or None if not found
    """
    target_date = survey_date + pd.Timedelta(days=365)
    
    # Find meetings after the survey date
    future_meetings = calendar_df[calendar_df['meeting_date'] > survey_date].copy()
    
    if future_meetings.empty:
        return None
    
    # Find the meeting closest to the target date (1 year ahead)
    future_meetings['date_diff'] = (future_meetings['meeting_date'] - target_date).abs()
    closest_meeting = future_meetings.loc[future_meetings['date_diff'].idxmin()]
    
    return closest_meeting['reuniao_code']


def process_selic_forecasts(selic_df, calendar_df):
    """
    Process SELIC forecasts to create 1-year ahead time-series.
    
    For each unique survey date, find the meeting that is ~1-year ahead and
    extract the median forecast and std dev for that meeting.
    
    Args:
        selic_df: DataFrame with SELIC forecasts from Focus API
        calendar_df: DataFrame with meeting calendar
        
    Returns:
        DataFrame with 1-year ahead forecast time-series
    """
    print("\nProcessing 1-year ahead forecasts...")
    
    # Convert dates
    selic_df = selic_df.copy()
    selic_df['Data'] = pd.to_datetime(selic_df['Data'])
    
    # Convert numeric columns
    for col in ['Mediana', 'DesvioPadrao', 'Media']:
        if col in selic_df.columns:
            selic_df[col] = pd.to_numeric(selic_df[col], errors='coerce')
    
    # Get unique survey dates
    survey_dates = sorted(selic_df['Data'].unique())
    
    results = []
    
    for survey_date in survey_dates:
        # Find the meeting that is ~1-year ahead
        target_meeting = find_meeting_1y_ahead(survey_date, calendar_df)
        
        if target_meeting is None:
            continue
        
        # Get forecasts for this survey date and target meeting
        forecasts = selic_df[
            (selic_df['Data'] == survey_date) & 
            (selic_df['Reuniao'] == target_meeting)
        ]
        
        if forecasts.empty:
            continue
        
        # Get the first row (should be only one per baseCalculo, but we want baseCalculo=0)
        forecast = forecasts[forecasts['baseCalculo'] == 0] if 'baseCalculo' in forecasts.columns else forecasts
        
        if forecast.empty:
            forecast = forecasts.iloc[0]
        else:
            forecast = forecast.iloc[0]
        
        # Get meeting date
        meeting_info = calendar_df[calendar_df['reuniao_code'] == target_meeting]
        if meeting_info.empty:
            meeting_date = None
        else:
            meeting_date = meeting_info.iloc[0]['meeting_date']
        
        results.append({
            'date': survey_date,
            'target_meeting': target_meeting,
            'target_meeting_date': meeting_date,
            'median_forecast': forecast['Mediana'] if 'Mediana' in forecast else None,
            'mean_forecast': forecast['Media'] if 'Media' in forecast else None,
            'std_forecast': forecast['DesvioPadrao'] if 'DesvioPadrao' in forecast else None,
            'min_forecast': forecast['Minimo'] if 'Minimo' in forecast else None,
            'max_forecast': forecast['Maximo'] if 'Maximo' in forecast else None,
            'num_respondents': forecast['numeroRespondentes'] if 'numeroRespondentes' in forecast else None,
        })
    
    result_df = pd.DataFrame(results)
    
    if not result_df.empty:
        result_df = result_df.set_index('date').sort_index()
    
    return result_df


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
    
    # Forward fill non-numeric columns
    if 'target_meeting' in df_daily.columns:
        df_daily['target_meeting'] = df_daily['target_meeting'].ffill()
    if 'target_meeting_date' in df_daily.columns:
        df_daily['target_meeting_date'] = df_daily['target_meeting_date'].ffill()
    
    return df_daily


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    """Main processing pipeline."""
    print("=" * 70)
    print("Focus SELIC - 1-Year Ahead Forecast Processor")
    print("=" * 70)
    
    # Load meeting calendar
    print("\n[1/4] Loading meeting calendar...")
    calendar_df = load_meeting_calendar()
    print(f"Loaded {len(calendar_df)} meetings from calendar")
    print(f"Date range: {calendar_df['meeting_date'].min()} to {calendar_df['meeting_date'].max()}")
    
    # Fetch SELIC data from Focus API
    print("\n[2/4] Fetching SELIC forecasts from Focus API...")
    selic_df = fetch_selic_data(top=100000)
    print(f"Fetched {len(selic_df)} forecast records")
    print(f"Date range: {selic_df['Data'].min()} to {selic_df['Data'].max()}")
    print(f"Unique meetings: {selic_df['Reuniao'].nunique()}")
    
    # Process 1-year ahead forecasts
    print("\n[3/4] Building 1-year ahead time-series...")
    forecasts_1y = process_selic_forecasts(selic_df, calendar_df)
    print(f"Created {len(forecasts_1y)} 1-year ahead forecast points")
    
    if forecasts_1y.empty:
        print("\nERROR: No 1-year ahead forecasts could be generated!")
        return
    
    # Interpolate to business days
    print("\n[4/4] Interpolating to business days...")
    forecasts_daily = interpolate_to_business_days(forecasts_1y)
    print(f"Interpolated to {len(forecasts_daily)} business days")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    forecasts_daily.to_csv(OUTPUT_FILE)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"Total rows: {len(forecasts_daily)}")
    print(f"Date range: {forecasts_daily.index.min().strftime('%Y-%m-%d')} to {forecasts_daily.index.max().strftime('%Y-%m-%d')}")
    
    print("\nColumns:")
    for col in forecasts_daily.columns:
        print(f"  - {col}")
    
    print("\nSample data (first 5 rows):")
    print(forecasts_daily.head().to_string())
    
    print("\nSample data (last 5 rows):")
    print(forecasts_daily.tail().to_string())
    
    print("\nSummary statistics:")
    print(forecasts_daily[['median_forecast', 'std_forecast']].describe().to_string())
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
