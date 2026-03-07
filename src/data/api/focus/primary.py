#!/usr/bin/env python
"""
Focus API client for fetching Primary Result (Resultado primário) forecasts.

API Documentation:
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais

Available indicators:
- Resultado primário (Primary surplus/deficit)
- Various other macroeconomic indicators

Usage:
    from src.data.api.focus.primary import fetch_primary_median_data, fetch_primary_std_data
    
    median_df = fetch_primary_median_data()
    std_df = fetch_primary_std_data()
"""

import pandas as pd
import requests
import urllib.parse
import json


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais'
INDICATOR = 'Resultado primário'
BASE_CALCULO = 0  # 0 = annual calendar year, 1 = 12-month rolling


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def fetch_primary_median_data(top=50000):
    """
    Fetch median (Mediana) forecasts for 'Resultado primário' from Focus API.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with columns: Indicador, Data, DataReferencia, Mediana
    """
    filter_condition = f"baseCalculo eq {BASE_CALCULO} and (Indicador eq '{INDICATOR}')"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$select': 'Indicador,Data,DataReferencia,Mediana',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    url = f'{BASE_URL}?{encoded_params}'
    
    print(f'Fetching median data from Focus API...')
    
    response = requests.get(url, timeout=180)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
        
        if 'value' in data:
            records = data['value']
            df = pd.DataFrame(records)
            print(f'Fetched {len(df)} median rows.')
            print(f'Date range: {df["Data"].min()} to {df["Data"].max()}')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


def fetch_primary_std_data(top=50000):
    """
    Fetch standard deviation (DesvioPadrao) forecasts for 'Resultado primário' from Focus API.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with columns: Indicador, Data, DataReferencia, DesvioPadrao
    """
    filter_condition = f"baseCalculo eq {BASE_CALCULO} and (Indicador eq '{INDICATOR}')"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$select': 'Indicador,Data,DataReferencia,DesvioPadrao',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    url = f'{BASE_URL}?{encoded_params}'
    
    print(f'Fetching standard deviation data from Focus API...')
    
    response = requests.get(url, timeout=180)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
        
        if 'value' in data:
            records = data['value']
            df = pd.DataFrame(records)
            print(f'Fetched {len(df)} std dev rows.')
            print(f'Date range: {df["Data"].min()} to {df["Data"].max()}')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


def fetch_primary_full_data(top=50000):
    """
    Fetch both median and standard deviation data in a single request.
    
    Args:
        top: Maximum number of records to fetch (default: 50000)
        
    Returns:
        DataFrame with columns: Indicador, Data, DataReferencia, Mediana, DesvioPadrao
    """
    filter_condition = f"baseCalculo eq {BASE_CALCULO} and (Indicador eq '{INDICATOR}')"
    
    query_params = {
        '$filter': filter_condition,
        '$format': 'json',
        '$select': 'Indicador,Data,DataReferencia,Mediana,DesvioPadrao',
        '$top': str(top),
        '$orderby': 'Data asc'
    }
    
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    url = f'{BASE_URL}?{encoded_params}'
    
    print(f'Fetching full data from Focus API...')
    
    response = requests.get(url, timeout=180)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
        
        if 'value' in data:
            records = data['value']
            df = pd.DataFrame(records)
            print(f'Fetched {len(df)} rows.')
            print(f'Date range: {df["Data"].min()} to {df["Data"].max()}')
            return df
        else:
            raise ValueError("No 'value' key in API response")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Focus API - Primary Result (Resultado primário)")
    print("=" * 60)
    
    # Fetch median data
    print("\n[1/2] Fetching median forecasts...")
    median_df = fetch_primary_median_data()
    print(f"\nSample median data:")
    print(median_df.head(10).to_string())
    
    # Fetch std dev data
    print("\n[2/2] Fetching standard deviation...")
    std_df = fetch_primary_std_data()
    print(f"\nSample std dev data:")
    print(std_df.head(10).to_string())
    
    print("\n" + "=" * 60)
    print("Fetch complete!")
    print("=" * 60)
