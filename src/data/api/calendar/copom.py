#!/usr/bin/env python
"""
COPOM Meeting Calendar - Meeting Date Extractor

Fetches and extracts COPOM (Monetary Policy Committee) meeting dates
from the Brazilian Central Bank (BCB) API.

Data source:
- https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados

The meeting date is derived from:
- The meeting number (nro_reuniao)
- The reference date (dataReferencia) which is the publication date
- The title containing meeting summary

Usage:
    from src.data.api.calendar.copom import fetch_copom_meetings, save_copom_meetings_csv
    
    df = fetch_copom_meetings()  # Fetch all COPOM meetings
    save_copom_meetings_csv(df)  # Save to processed folder
    
    # Or run as script to auto-generate:
    python src/data/api/calendar/copom.py
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import pandas as pd
import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

API_URL = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados"
DETAIL_URL = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes"
BASE_WEB_URL = "https://www.bcb.gov.br/controleinflacao/comunicadoscopom"

# Output path for processed CSV
SCRIPT_DIR = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR.parent.parent / "processed" / "calendar"
DEFAULT_CSV_FILENAME = "copom_meetings.csv"

# Regex patterns
REUNIAO_PATTERN = re.compile(r"(\d+)[ªº°]?\s*reuni[ãa]o", re.IGNORECASE)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CopomMeeting:
    """Represents a COPOM meeting."""

    meeting_number: int
    meeting_year: int
    meeting_month: int
    publication_date: datetime
    decision: str
    url: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _parse_meeting_number(text: str) -> Optional[int]:
    """Extract meeting number from text like '276ª reunião'."""
    match = REUNIAO_PATTERN.search(text)
    if match:
        return int(match.group(1))
    return None


def _fetch_comunicados(quantidade: int = 1000) -> List[dict]:
    """
    Fetch comunicados from BCB API.
    
    Args:
        quantidade: Number of records to fetch (max 1000)
        
    Returns:
        List of comunicado dictionaries
    """
    url = f"{API_URL}?quantidade={quantidade}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
    return data.get("conteudo", [])


def _fetch_detalhe_publication_date(nro_reuniao: int) -> Optional[datetime]:
    """
    Fetch detailed information including publication date for a specific meeting.
    
    Args:
        nro_reuniao: Meeting number
        
    Returns:
        Publication date or None if not found
    """
    url = f"{DETAIL_URL}?nro_reuniao={nro_reuniao}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}. Response content: {response.text[:200]}")
        conteudo = data.get("conteudo", {})
        
        # Try to get the publication date from detalhe
        if conteudo:
            # The API returns the same dataReferencia which is the publication date
            data_referencia = conteudo.get("dataReferencia")
            if data_referencia:
                return datetime.strptime(data_referencia, "%Y-%m-%d")
                
    except Exception:
        pass
    
    return None


def _extract_meeting_from_comunicado(item: dict) -> Optional[CopomMeeting]:
    """
    Extract meeting information from a comunicado API response item.
    
    Args:
        item: Dictionary with comunicado data
        
    Returns:
        CopomMeeting object or None if extraction fails
    """
    nro_reuniao = item.get("nro_reuniao")
    data_referencia = item.get("dataReferencia")
    titulo = item.get("titulo", "")
    
    if not nro_reuniao or not data_referencia:
        return None
    
    # Parse publication date
    try:
        publication_date = datetime.strptime(data_referencia, "%Y-%m-%d")
    except ValueError:
        return None
    
    # The meeting month/year is typically the month/year of the publication
    # (since COPOM meetings happen and are published in the same month)
    meeting_year = publication_date.year
    meeting_month = publication_date.month
    
    # Build URL for the web page
    # The web URL pattern seems to be based on an ID, but we can construct a search URL
    url = f"{BASE_WEB_URL}/{nro_reuniao}"
    
    return CopomMeeting(
        meeting_number=nro_reuniao,
        meeting_year=meeting_year,
        meeting_month=meeting_month,
        publication_date=publication_date,
        decision=titulo,
        url=url,
    )


# =============================================================================
# MAIN API FUNCTION
# =============================================================================

def fetch_copom_meetings(quantidade: int = 1000) -> pd.DataFrame:
    """
    Fetch all COPOM meeting dates from BCB API.
    
    Args:
        quantidade: Number of records to fetch (default: 1000, which should cover all history)
        
    Returns:
        DataFrame with columns:
        - meeting_number: COPOM meeting number (e.g., 276)
        - meeting_year: Year of the meeting
        - meeting_month: Month of the meeting (1-12)
        - publication_date: Date when the decision was published
        - decision: Brief description of the decision
        - url: Link to the full announcement
    """
    print(f"Fetching COPOM meetings from BCB API...")
    print(f"API URL: {API_URL}")
    print("=" * 60)
    
    comunicados = _fetch_comunicados(quantidade)
    
    if not comunicados:
        print("No meetings found.")
        return pd.DataFrame(columns=[
            "meeting_number", "meeting_year", "meeting_month", 
            "publication_date", "decision", "url"
        ])
    
    print(f"Fetched {len(comunicados)} comunicados from API")
    print("Processing...")
    
    meetings = []
    for item in comunicados:
        meeting = _extract_meeting_from_comunicado(item)
        if meeting:
            meetings.append(meeting)
    
    print(f"Successfully extracted {len(meetings)} meetings")
    print("=" * 60)
    
    if not meetings:
        return pd.DataFrame(columns=[
            "meeting_number", "meeting_year", "meeting_month", 
            "publication_date", "decision", "url"
        ])
    
    # Create DataFrame
    df = pd.DataFrame([
        {
            "meeting_number": m.meeting_number,
            "meeting_year": m.meeting_year,
            "meeting_month": m.meeting_month,
            "publication_date": m.publication_date,
            "decision": m.decision,
            "url": m.url,
        }
        for m in meetings
    ])
    
    # Sort by meeting number (descending - newest first)
    df = df.sort_values("meeting_number", ascending=False).reset_index(drop=True)
    
    return df


# =============================================================================
# CSV SAVE FUNCTION
# =============================================================================

def save_copom_meetings_csv(
    df: pd.DataFrame,
    filename: str = DEFAULT_CSV_FILENAME,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Save COPOM meetings DataFrame to CSV in the processed folder.
    
    Args:
        df: DataFrame with meeting dates
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
    print("COPOM Meeting Calendar - Date Extractor")
    print("=" * 60)
    print()
    
    # Fetch all COPOM meetings
    df = fetch_copom_meetings()
    
    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"\nTotal records: {len(df)}")
    
    if len(df) > 0:
        print(f"Meeting range: #{df['meeting_number'].min()} to #{df['meeting_number'].max()}")
        print(f"Date range: {df['publication_date'].min()} to {df['publication_date'].max()}")
        print()
        print("Sample data (first 10):")
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
        save_copom_meetings_csv(df)
    else:
        print("\nNo meetings found.")
