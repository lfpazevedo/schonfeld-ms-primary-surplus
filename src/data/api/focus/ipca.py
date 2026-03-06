#!/usr/bin/env python
"""
Focus API client for fetching IPCA (inflation) expectations.

API Documentation:
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoInflacao12Meses

Available endpoints:
- ExpectativasMercadoInflacao12Meses: 12-month ahead inflation expectations
- ExpectativasMercadoInflacao24Meses: 24-month ahead inflation expectations
- ExpectativaMercadoMensais: Monthly expectations for specific reference years

Usage:
    from src.data.api.focus.ipca import fetch_ipca_data, fetch_ipca_median_data
    
    # Fetch 12-month ahead expectations
    df = fetch_ipca_data()
    
    # Fetch median values only
    median_df = fetch_ipca_median_data()
    
    # Fetch monthly expectations for specific years
    monthly_df = fetch_ipca_monthly_expectations()
"""

import pandas as pd
import requests
import urllib.parse


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL_12M = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoInflacao12Meses'
BASE_URL_24M = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoInflacao24Meses'
BASE_URL_MONTHLY = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativaMercadoMensais'
INDICATOR = 'IPCA'


def _build_url(base_url, query_params):
    """Helper function to build properly encoded URL."""
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote, safe="$'")
    return f'{base_url}?{encoded_params}'


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def fetch_ipca_data(top=50000, months_ahead=12):
    """
    Fetch IPCA inflation expectations from Focus API.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        months_ahead: 12 or 24 months ahead expectations (default: 12)
        
    Returns:
        DataFrame with columns: Indicador, Data, Suavizada, Media, Mediana, 
                               DesvioPadrao, Minimo, Maximo, numeroRespondentes, baseCalculo
    """
    base_url = BASE_URL_12M if months_ahead == 12 else BASE_URL_24M
    
    filter_condition = f"Indicador eq '{INDICATOR}'"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    url = _build_url(base_url, query_params)
    
    print(f'Fetching IPCA {months_ahead}M expectations from Focus API...')
    
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
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


def fetch_ipca_median_data(top=50000, months_ahead=12):
    """
    Fetch IPCA expectations with Median values.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        months_ahead: 12 or 24 months ahead expectations (default: 12)
        
    Returns:
        DataFrame with key columns: Data, Mediana, Media, DesvioPadrao, Minimo, Maximo
    """
    df = fetch_ipca_data(top=top, months_ahead=months_ahead)
    # Return relevant columns
    key_cols = ['Data', 'Mediana', 'Media', 'DesvioPadrao', 'Minimo', 'Maximo']
    available_cols = [c for c in key_cols if c in df.columns]
    return df[available_cols].copy()


def fetch_ipca_full_data(top=50000, months_ahead=12):
    """
    Fetch all available statistics for IPCA expectations.
    
    Includes: Mediana, Media, DesvioPadrao, Minimo, Maximo, numeroRespondentes, baseCalculo, Suavizada
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        months_ahead: 12 or 24 months ahead expectations (default: 12)
        
    Returns:
        DataFrame with all available columns
    """
    return fetch_ipca_data(top=top, months_ahead=months_ahead)


def fetch_ipca_monthly_expectations(reference_year=None, top=50000):
    """
    Fetch IPCA expectations from the monthly expectations endpoint.
    
    This endpoint provides expectations for specific calendar years (not 12-month rolling).
    
    Args:
        reference_year: Specific year to filter (e.g., '2025'), or None for all
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with monthly IPCA expectations
    """
    if reference_year:
        filter_condition = f"Indicador eq '{INDICATOR}' and DataReferencia eq '{reference_year}'"
    else:
        filter_condition = f"Indicador eq '{INDICATOR}'"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    url = _build_url(BASE_URL_MONTHLY, query_params)
    
    print(f'Fetching IPCA monthly expectations from Focus API...')
    
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
                if 'DataReferencia' in df.columns:
                    refs = sorted(df["DataReferencia"].unique())
                    print(f'Reference periods: {refs if len(refs) <= 10 else refs[:10]}...')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}")


def fetch_ipca_top5(months_ahead=12, top=50000):
    """
    Fetch Top 5 IPCA expectations (forecasts from top 5 institutions).
    
    Args:
        months_ahead: 12 or 24 months ahead (default: 12)
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with Top 5 expectations
    """
    if months_ahead == 12:
        base_url = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoTop5Inflacao12Meses'
    else:
        base_url = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoTop5Inflacao24Meses'
    
    filter_condition = f"Indicador eq '{INDICATOR}'"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    url = _build_url(base_url, query_params)
    
    print(f'Fetching IPCA Top 5 ({months_ahead}M) expectations from Focus API...')
    
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
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Focus API - IPCA Inflation Expectations")
    print("=" * 60)
    
    # Fetch 12-month ahead data
    print("\n[1/3] Fetching 12-month ahead IPCA expectations...")
    df_12m = fetch_ipca_data(top=5000)
    print(f"\nColumns: {list(df_12m.columns)}")
    print(f"\nSample 12-month ahead data:")
    print(df_12m.head(10).to_string())
    
    # Fetch monthly expectations
    print("\n[2/3] Fetching monthly IPCA expectations...")
    df_monthly = fetch_ipca_monthly_expectations(top=5000)
    print(f"\nColumns: {list(df_monthly.columns)}")
    print(f"\nSample monthly data:")
    print(df_monthly.head(10).to_string())
    
    # Fetch 24-month ahead data
    print("\n[3/3] Fetching 24-month ahead IPCA expectations...")
    df_24m = fetch_ipca_data(top=5000, months_ahead=24)
    print(f"\nColumns: {list(df_24m.columns)}")
    print(f"\nSample 24-month ahead data:")
    print(df_24m.head(10).to_string())
    
    print("\n" + "=" * 60)
    print("Fetch complete!")
    print("=" * 60)
