#!/usr/bin/env python
"""
BCB Fiscal Statistics Calendar - Release Date Extractor

Fetches and extracts release dates of monthly fiscal statistics reports
from the Brazilian Central Bank (BCB) since January 2012.

Data sources:
- TXT files (older): https://www.bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/YYYYMM_Texto_de_estatisticas_fiscais.txt
- PDF files (newer): https://www.bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/YYYYMM_Texto_de_estatisticas_fiscais.pdf

The release date is found:
- TXT: First line, format "NOTA PARA A IMPRENSA   -   DD.M.YYYY" or "NOTA PARA A IMPRENSA - DD.M.YYYY"
- PDF: First page, first text element, format "DD.M.YYYY" or "DD.MM.YYYY"

Usage:
    from src.data.api.calendar.fiscal import fetch_release_dates, save_release_dates_csv
    
    df = fetch_release_dates()  # Fetch all dates since Jan 2012
    save_release_dates_csv(df)  # Save to processed folder
    
    # Or run as script to auto-generate:
    python src/data/api/calendar/fiscal.py
"""

import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd
import pdfplumber
import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.bcb.gov.br/content/estatisticas/hist_estatisticasfiscais"
START_YEAR = 2012
START_MONTH = 1

# Output path for processed CSV
SCRIPT_DIR = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR.parent.parent / "processed" / "calendar"
DEFAULT_CSV_FILENAME = "fiscal_release_dates.csv"

# Regex patterns for date extraction
TXT_DATE_PATTERN = re.compile(
    r"NOTA\s+PARA\s+A\s+IMPRENSA\s+-\s*(\d{1,2})[.](\d{1,2})[.](\d{4})",
    re.IGNORECASE
)
PDF_DATE_PATTERN = re.compile(r"(\d{1,2})[.](\d{1,2})[.](\d{4})")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_file_url(year: int, month: int, extension: str) -> str:
    """Construct the URL for a fiscal statistics file."""
    yyyymm = f"{year}{month:02d}"
    return f"{BASE_URL}/{yyyymm}_Texto_de_estatisticas_fiscais.{extension}"


def _extract_date_from_txt(content: str) -> Optional[datetime]:
    """
    Extract release date from TXT file content.
    
    The date is in the first line, format:
    "NOTA PARA A IMPRENSA   -   DD.M.YYYY"
    """
    # Look for the pattern in the first 500 characters
    first_chunk = content[:500]
    
    match = TXT_DATE_PATTERN.search(first_chunk)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def _extract_date_from_pdf(pdf_bytes: bytes) -> Optional[datetime]:
    """
    Extract release date from PDF file content.
    
    The date is on the first page, typically the first text element.
    """
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                return None
            
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            
            if not text:
                return None
            
            # Look for date pattern in first 500 characters
            first_chunk = text[:500]
            match = PDF_DATE_PATTERN.search(first_chunk)
            
            if match:
                day, month, year = match.groups()
                try:
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    return None
    except Exception:
        return None
    
    return None


def _fetch_release_date(year: int, month: int) -> Optional[datetime]:
    """
    Fetch and extract the release date for a specific year/month.
    
    Tries TXT first (for older files), then PDF (for newer files).
    
    Args:
        year: The year of the report
        month: The month of the report (1-12)
        
    Returns:
        datetime object with the release date, or None if not found
    """
    # Try TXT first
    txt_url = _get_file_url(year, month, "txt")
    try:
        response = requests.get(txt_url, timeout=30)
        if response.status_code == 200:
            # Decode with latin-1 as these are old Brazilian files
            content = response.content.decode('latin-1', errors='ignore')
            date = _extract_date_from_txt(content)
            if date:
                return date
    except Exception:
        pass
    
    # Try PDF if TXT fails
    pdf_url = _get_file_url(year, month, "pdf")
    try:
        response = requests.get(pdf_url, timeout=30)
        if response.status_code == 200:
            date = _extract_date_from_pdf(response.content)
            if date:
                return date
    except Exception:
        pass
    
    return None


# =============================================================================
# MAIN API FUNCTION
# =============================================================================

def fetch_release_dates(
    start_year: int = START_YEAR,
    start_month: int = START_MONTH,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch release dates of fiscal statistics reports from BCB.
    
    Args:
        start_year: Starting year (default: 2012)
        start_month: Starting month (default: 1)
        end_year: Ending year (default: current year)
        end_month: Ending month (default: current month)
        
    Returns:
        DataFrame with columns:
        - report_year: Year of the fiscal report
        - report_month: Month of the fiscal report (1-12)
        - release_date: Date when the report was published
    """
    now = datetime.now()
    end_year = end_year or now.year
    end_month = end_month or now.month
    
    results = []
    total_months = 0
    found_dates = 0
    
    print(f"Fetching fiscal report release dates from {start_year}-{start_month:02d} to {end_year}-{end_month:02d}...")
    print("=" * 60)
    
    for year in range(start_year, end_year + 1):
        month_start = start_month if year == start_year else 1
        month_end = end_month if year == end_year else 12
        
        for month in range(month_start, month_end + 1):
            total_months += 1
            release_date = _fetch_release_date(year, month)
            
            if release_date:
                found_dates += 1
                results.append({
                    "report_year": year,
                    "report_month": month,
                    "release_date": release_date
                })
                print(f"✓ {year}-{month:02d}: Released on {release_date.strftime('%Y-%m-%d')}")
            else:
                print(f"✗ {year}-{month:02d}: Date not found")
    
    print("=" * 60)
    print(f"Found {found_dates}/{total_months} release dates")
    
    if not results:
        return pd.DataFrame(columns=["report_year", "report_month", "release_date"])
    
    df = pd.DataFrame(results)
    df = df.sort_values(["report_year", "report_month"]).reset_index(drop=True)
    return df


# =============================================================================
# CSV SAVE FUNCTION
# =============================================================================

def save_release_dates_csv(
    df: pd.DataFrame,
    filename: str = DEFAULT_CSV_FILENAME,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Save release dates DataFrame to CSV in the processed folder.
    
    Args:
        df: DataFrame with release dates
        filename: Name of the output CSV file
        output_dir: Directory to save the file (default: src/data/processed/calendar)
        
    Returns:
        Path to the saved CSV file
    """
    output_dir = output_dir or PROCESSED_DIR
    
    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    
    df.to_csv(output_path, index=False)
    print(f"\nSaved CSV to: {output_path}")
    print(f"Total records: {len(df)}")
    
    return output_path


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BCB Fiscal Statistics - Release Date Extractor")
    print("=" * 60)
    print()
    
    # Fetch all release dates since Jan 2012
    df = fetch_release_dates()
    
    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"\nTotal records: {len(df)}")
    print(f"Date range: {df['release_date'].min()} to {df['release_date'].max()}")
    print()
    print("Sample data:")
    print(df.head(10).to_string(index=False))
    
    if len(df) > 10:
        print()
        print("...")
        print()
        print("Last records:")
        print(df.tail(5).to_string(index=False))
    
    # Auto-generate CSV in processed folder
    print()
    print("=" * 60)
    print("Generating CSV")
    print("=" * 60)
    save_release_dates_csv(df)
