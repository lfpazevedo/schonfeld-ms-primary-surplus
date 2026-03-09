import json
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

# Cache file path (in project root)
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "vix_cache.csv")
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"


def fetch_vix_data_from_api(api_key, start_date=None, end_date=None):
    """
    Fetches raw VIXCLS data from the St. Louis FRED API.

    Args:
        api_key (str): Your FRED API key.
        start_date (str, optional): Start date in 'YYYY-MM-DD' format. Defaults to None.
        end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to None.

    Returns:
        dict: JSON response from the API containing VIXCLS data or None if an error occurs.
    """
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'VIXCLS',
        'api_key': api_key,
        'file_type': 'json',
    }

    if start_date:
        params['observation_start'] = start_date
    if end_date:
        params['observation_end'] = end_date

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
    else:
        raise ValueError(f"API request failed with status {response.status_code}: {response.text[:200]}")


def fetch_vix_from_fred_csv(timeout=30, max_retries=3):
    """
    Fetches VIX data from FRED CSV endpoint with retries.
    
    Args:
        timeout (int): Request timeout in seconds.
        max_retries (int): Maximum number of retry attempts.
        
    Returns:
        pd.DataFrame: DataFrame with 'date' and 'VIX' columns, or None if failed.
    """
    for attempt in range(max_retries):
        try:
            df = pd.read_csv(FRED_CSV_URL, timeout=timeout)
            df['date'] = pd.to_datetime(df['observation_date'])
            df = df[df['VIXCLS'] != '.']
            df['VIX'] = pd.to_numeric(df['VIXCLS'])
            df = df[['date', 'VIX']].dropna().sort_values('date')
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            return None
    return None


def load_cached_vix():
    """
    Load VIX data from local cache file.
    
    Returns:
        pd.DataFrame: DataFrame with 'date' and 'VIX' columns, or None if no cache exists.
    """
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception:
            return None
    return None


def save_vix_cache(df):
    """
    Save VIX data to local cache file.
    
    Args:
        df (pd.DataFrame): DataFrame with 'date' and 'VIX' columns.
    """
    try:
        df.to_csv(CACHE_FILE, index=False)
    except Exception:
        pass


def load_vix_data(use_cache=True, cache_max_age_days=7, timeout=30):
    """
    Load VIX data with caching and fallback.
    
    This function will:
    1. Try to fetch fresh data from FRED
    2. If successful, update the cache and return the data
    3. If failed, fall back to cached data (if available and not too old)
    4. If no valid cache, raise an error
    
    Args:
        use_cache (bool): Whether to use cache as fallback.
        cache_max_age_days (int): Maximum age of cache in days before warning.
        timeout (int): Timeout for FRED request in seconds.
        
    Returns:
        pd.DataFrame: DataFrame with 'date' and 'VIX' columns.
        
    Raises:
        RuntimeError: If unable to fetch data and no valid cache exists.
    """
    # Try to fetch fresh data from FRED
    fresh_df = fetch_vix_from_fred_csv(timeout=timeout)
    
    if fresh_df is not None and len(fresh_df) > 0:
        # Save to cache
        save_vix_cache(fresh_df)
        return fresh_df
    
    # Fetch failed - try to use cache
    if use_cache:
        cached_df = load_cached_vix()
        if cached_df is not None and len(cached_df) > 0:
            # Check cache age
            if os.path.exists(CACHE_FILE):
                cache_mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
                cache_age_days = (datetime.now() - cache_mtime).days
                if cache_age_days > cache_max_age_days:
                    print(f"Warning: Using cached VIX data ({cache_age_days} days old)")
            return cached_df
    
    # No data available
    raise RuntimeError(
        "Unable to fetch VIX data from FRED and no cache available. "
        "Please check your internet connection or populate the cache manually."
    )


def load_vix_data_with_fallback(fallback_to_sample=False):
    """
    Load VIX data with multiple fallback options.
    
    This is the recommended function for notebooks - it will:
    1. Try FRED first
    2. Fall back to cache
    3. Optionally fall back to empty/sample data if requested
    
    Args:
        fallback_to_sample (bool): If True, return empty DataFrame on total failure instead of raising.
        
    Returns:
        pd.DataFrame: DataFrame with 'date' and 'VIX' columns.
    """
    try:
        return load_vix_data()
    except RuntimeError as e:
        if fallback_to_sample:
            print(f"Warning: {e}")
            print("Returning empty DataFrame - analysis may be incomplete")
            return pd.DataFrame(columns=['date', 'VIX'])
        raise
