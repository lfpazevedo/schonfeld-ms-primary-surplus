#!/usr/bin/env python
"""
Focus API client for fetching SELIC (interest rate) expectations.

API Documentation:
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoSelic

Available endpoints:
- ExpectativasMercadoSelic: SELIC rate expectations for specific Copom meetings
- ExpectativasMercadoTop5Selic: Top 5 institutions' SELIC forecasts

The SELIC endpoint provides expectations for specific Copom meetings (e.g., R1/2028 = first meeting of 2028).

Usage:
    from src.data.api.focus.selic import fetch_selic_data, fetch_selic_median_data
    
    # Fetch all SELIC expectations
    df = fetch_selic_data()
    
    # Fetch median values only
    median_df = fetch_selic_median_data()
    
    # Fetch for a specific meeting
    r1_2028_df = fetch_selic_data(reuniao='R1/2028')
"""

import pandas as pd
import requests
import urllib.parse


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoSelic'
INDICATOR = 'Selic'


def _build_url(base_url, query_params):
    """Helper function to build properly encoded URL."""
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote, safe="$'")
    return f'{base_url}?{encoded_params}'


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def fetch_selic_data(top=50000, reuniao=None):
    """
    Fetch SELIC rate expectations from Focus API.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        reuniao: Specific Copom meeting to filter (e.g., 'R1/2028'), or None for all
        
    Returns:
        DataFrame with columns: Indicador, Data, Reuniao, Media, Mediana, 
                               DesvioPadrao, Minimo, Maximo, numeroRespondentes, baseCalculo
    """
    if reuniao:
        filter_condition = f"Indicador eq '{INDICATOR}' and Reuniao eq '{reuniao}'"
    else:
        filter_condition = f"Indicador eq '{INDICATOR}'"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    url = _build_url(BASE_URL, query_params)
    
    print(f'Fetching SELIC expectations from Focus API...')
    
    response = requests.get(url, timeout=180)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        data = response.json()
        
        if 'value' in data:
            records = data['value']
            df = pd.DataFrame(records)
            print(f'Fetched {len(df)} rows.')
            if len(df) > 0:
                print(f'Date range: {df["Data"].min()} to {df["Data"].max()}')
                if 'Reuniao' in df.columns and reuniao is None:
                    reunioes = sorted(df["Reuniao"].unique())
                    print(f'Meetings: {reunioes if len(reunioes) <= 10 else reunioes[:10]}...')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


def fetch_selic_median_data(top=50000, reuniao=None):
    """
    Fetch SELIC expectations with Median values.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        reuniao: Specific Copom meeting to filter (e.g., 'R1/2028'), or None for all
        
    Returns:
        DataFrame with key columns: Data, Reuniao, Mediana, Media, DesvioPadrao, Minimo, Maximo
    """
    df = fetch_selic_data(top=top, reuniao=reuniao)
    # Return relevant columns
    key_cols = ['Data', 'Reuniao', 'Mediana', 'Media', 'DesvioPadrao', 'Minimo', 'Maximo']
    available_cols = [c for c in key_cols if c in df.columns]
    return df[available_cols].copy()


def fetch_selic_full_data(top=50000, reuniao=None):
    """
    Fetch all available statistics for SELIC expectations.
    
    Includes: Mediana, Media, DesvioPadrao, Minimo, Maximo, numeroRespondentes, baseCalculo, Reuniao
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        reuniao: Specific Copom meeting to filter (e.g., 'R1/2028'), or None for all
        
    Returns:
        DataFrame with all available columns
    """
    return fetch_selic_data(top=top, reuniao=reuniao)


def fetch_selic_by_meeting(reuniao, top=50000):
    """
    Fetch SELIC expectations for a specific Copom meeting.
    
    Args:
        reuniao: Copom meeting code (e.g., 'R1/2028', 'R2/2028')
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with SELIC expectations for the specified meeting
    """
    return fetch_selic_data(top=top, reuniao=reuniao)


def fetch_selic_top5(top=50000):
    """
    Fetch Top 5 SELIC expectations (forecasts from top 5 institutions).
    
    Note: The Top5 endpoint returns data with lowercase column names and 
    doesn't support $filter parameter.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with Top 5 SELIC expectations
    """
    base_url = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoTop5Selic'
    
    # Top5 endpoint doesn't support $filter
    query_params = {
        '$format': 'json',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    url = _build_url(base_url, query_params)
    
    print(f'Fetching SELIC Top 5 expectations from Focus API...')
    
    response = requests.get(url, timeout=180)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        data = response.json()
        
        if 'value' in data:
            records = data['value']
            df = pd.DataFrame(records)
            print(f'Fetched {len(df)} rows.')
            if len(df) > 0:
                print(f'Date range: {df["Data"].min()} to {df["Data"].max()}')
                # Filter for SELIC only since the endpoint returns all indicators
                if 'indicador' in df.columns:
                    df = df[df['indicador'].str.lower() == 'selic'].copy()
                    print(f'After filtering for SELIC: {len(df)} rows')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}")


def fetch_selic_current_meetings(top=50000, latest_only=True):
    """
    Fetch SELIC expectations focusing on current/near-term meetings.
    
    This returns expectations for upcoming Copom meetings.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        latest_only: If True, return only the most recent forecast date (default: True)
        
    Returns:
        DataFrame with current SELIC expectations by meeting
    """
    df = fetch_selic_data(top=top)
    
    if latest_only and len(df) > 0:
        # Get the most recent date
        latest_date = df['Data'].max()
        df = df[df['Data'] == latest_date].copy()
        print(f"Filtered to latest date: {latest_date}")
    
    return df


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Focus API - SELIC Rate Expectations")
    print("=" * 60)
    
    # Fetch all SELIC data
    print("\n[1/3] Fetching all SELIC expectations...")
    df_all = fetch_selic_data(top=5000)
    print(f"\nColumns: {list(df_all.columns)}")
    print(f"\nSample data:")
    print(df_all.head(10).to_string())
    
    # Fetch for a specific meeting
    print("\n[2/3] Fetching SELIC expectations for R1/2028...")
    df_meeting = fetch_selic_data(reuniao='R1/2028', top=1000)
    print(f"\nFetched {len(df_meeting)} rows for R1/2028")
    if len(df_meeting) > 0:
        print(f"\nSample R1/2028 data:")
        print(df_meeting.head(10).to_string())
    
    # Fetch Top 5 data
    print("\n[3/3] Fetching SELIC Top 5 expectations...")
    df_top5 = fetch_selic_top5(top=1000)
    print(f"\nColumns: {list(df_top5.columns)}")
    print(f"\nSample Top 5 data:")
    print(df_top5.head(10).to_string())
    
    print("\n" + "=" * 60)
    print("Fetch complete!")
    print("=" * 60)
