#!/usr/bin/env python3
"""
Script to populate the VIX cache from FRED.
Run this when you have network access to update the local cache.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.api.vix.vix import fetch_vix_from_fred_csv, save_vix_cache, CACHE_FILE


def main():
    print("Fetching VIX data from FRED...")
    df = fetch_vix_from_fred_csv(timeout=60, max_retries=5)
    
    if df is not None and len(df) > 0:
        save_vix_cache(df)
        print(f"✓ Cached {len(df)} VIX observations to {CACHE_FILE}")
        print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        return 0
    else:
        print("✗ Failed to fetch VIX data from FRED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
