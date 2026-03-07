import json

import requests

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
    