import pandas as pd
import glob
import os


# =============================================================================
# CONFIGURATION - Define vertices and output paths
# =============================================================================

# Path to the historical data folder
FOLDER_PATH = "src/data/raw/b3/predi/*.csv"
OUTPUT_DIR = "src/data/processed/b3"

# Vertices (in business days) to extract from the curve
# Extended list for more comprehensive analysis including 2520 (10y)
VERTICES = [
    21,      # 1m
    63,      # 3m  
    126,     # 6m
    252,     # 1y
    378,     # 1.5y
    504,     # 2y
    630,     # 2.5y
    756,     # 3y
    882,     # 3.5y
    1008,    # 4y
    1260,    # 5y
    1512,    # 6y
    1764,    # 7y
    2016,    # 8y
    2268,    # 9y
    2520,    # 10y
]

# Forward rate definitions: (name, short_du, long_du)
# Uses B3 PRE-DI convention with 252 business days
FORWARD_DEFINITIONS = [
    ("1y1y", 252, 504),     # 1-year rate, 1 year forward
    ("2y1y", 504, 756),     # 1-year rate, 2 years forward  
    ("3y1y", 756, 1008),    # 1-year rate, 3 years forward
    ("5y5y", 1260, 2520),   # 5-year rate, 5 years forward
]


# =============================================================================
# B3 FORWARD RATE CALCULATION
# =============================================================================

def calculate_b3_forward(r1: float, du1: int, r2: float, du2: int) -> float:
    """
    Calculate forward rate using B3 PRE-DI geometric/exponential convention.
    
    Formula: f = [(1 + r2)^(DU2/252) / (1 + r1)^(DU1/252)]^(252/(DU2-DU1)) - 1
    
    Args:
        r1: Short leg rate in decimal (e.g., 0.10 for 10%)
        du1: Short leg business days (e.g., 252 for 1y)
        r2: Long leg rate in decimal (e.g., 0.115 for 11.5%)
        du2: Long leg business days (e.g., 504 for 2y)
    
    Returns:
        Forward rate in decimal
    """
    if pd.isna(r1) or pd.isna(r2) or r1 <= -1 or r2 <= -1:
        return float('nan')
    
    factor_long = (1 + r2) ** (du2 / 252)
    factor_short = (1 + r1) ** (du1 / 252)
    
    period_days = du2 - du1
    if period_days <= 0:
        return float('nan')
    
    forward_rate = (factor_long / factor_short) ** (252 / period_days) - 1
    return forward_rate


def calculate_forward_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all defined forward rates for the given DataFrame.
    
    Args:
        df: DataFrame with date index and columns like 'predi_252', 'predi_504', etc.
    
    Returns:
        DataFrame with forward rate columns added
    """
    df = df.copy()
    
    for fwd_name, du_short, du_long in FORWARD_DEFINITIONS:
        col_short = f"predi_{du_short}"
        col_long = f"predi_{du_long}"
        fwd_col = f"fwd_{fwd_name}"
        
        if col_short in df.columns and col_long in df.columns:
            df[fwd_col] = df.apply(
                lambda row: calculate_b3_forward(
                    row[col_short], du_short,
                    row[col_long], du_long
                ),
                axis=1
            )
        else:
            print(f"Warning: Missing columns for {fwd_name} forward calculation")
    
    return df


# =============================================================================
# DATA LOADING AND PROCESSING
# =============================================================================

def load_raw_data(folder_path: str) -> pd.DataFrame:
    """Load and concatenate all raw CSV files."""
    file_list = glob.glob(folder_path)
    
    if not file_list:
        raise ValueError(f"No files found in {folder_path}")
    
    df_list = []
    
    for file in file_list:
        df = pd.read_csv(file, delimiter=",")
        # Expected columns: Date, Dias Corridos, 252(2)(4), 360(1)
        df.columns = ["date", "days", "predi_252", "predi_360"]
        
        # Convert decimal comma to dot
        df["predi_252"] = df["predi_252"].astype(str).str.replace(",", ".").astype(float) / 100
        df["predi_360"] = df["predi_360"].astype(str).str.replace(",", ".").astype(float) / 100
        
        # Convert date format
        df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
        
        df_list.append(df)
    
    merged_df = pd.concat(df_list, ignore_index=True)
    
    # Remove duplicates - keep last occurrence (most recent data)
    merged_df = merged_df.drop_duplicates(subset=["date", "days"], keep="last")
    
    return merged_df


def process_curve_data(df: pd.DataFrame, curve_type: str = "252") -> pd.DataFrame:
    """
    Process curve data: melt, pivot, interpolate, and select vertices.
    
    Args:
        df: Merged DataFrame with raw data
        curve_type: '252' or '360'
    
    Returns:
        Pivoted DataFrame with selected vertices
    """
    value_col = f"predi_{curve_type}"
    
    # Melt data
    melted = df.melt(
        id_vars=["date", "days"],
        value_vars=[value_col],
        var_name="type",
        value_name="value"
    ).sort_values(by=["date", "days"])
    
    # Pivot to have dates as rows and days as columns
    pivoted = melted.pivot(index="date", columns="days", values="value")
    
    # Interpolate horizontally to fill any missing vertices
    pivoted = pivoted.interpolate(method="linear", axis=1)
    
    # Select only the configured vertices
    available_vertices = [v for v in VERTICES if v in pivoted.columns]
    missing_vertices = [v for v in VERTICES if v not in pivoted.columns]
    
    if missing_vertices:
        print(f"Warning: Vertices not available in data: {missing_vertices}")
    
    pivoted = pivoted.loc[:, available_vertices]
    
    # Add prefix to column names
    pivoted.columns = [f"predi_{col}" for col in pivoted.columns]
    
    # Sort by date
    pivoted.index = pd.to_datetime(pivoted.index)
    pivoted = pivoted.sort_index()
    
    return pivoted


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main processing pipeline."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("B3 PRE-DI Curve Processing")
    print("=" * 60)
    
    # Step 1: Load raw data
    print("\n[1/3] Loading raw data...")
    merged_df = load_raw_data(FOLDER_PATH)
    print(f"      Loaded {len(merged_df):,} rows from {merged_df['date'].nunique()} dates")
    
    # Step 2: Process PRE-DI 252 curve
    print("\n[2/3] Processing PRE-DI 252 curve...")
    predi_252_pivot = process_curve_data(merged_df, curve_type="252")
    print(f"      Vertices: {list(predi_252_pivot.columns)}")
    
    # Step 3: Calculate forward rates
    print("\n[3/3] Calculating forward rates...")
    print(f"      Definitions: {[f[0] for f in FORWARD_DEFINITIONS]}")
    
    predi_252_with_forwards = calculate_forward_rates(predi_252_pivot)
    
    # Display forward rate columns
    fwd_cols = [c for c in predi_252_with_forwards.columns if c.startswith("fwd_")]
    print(f"      Calculated forwards: {fwd_cols}")
    
    # Save final output
    output_file = os.path.join(OUTPUT_DIR, "predi_252_pivot.csv")
    predi_252_with_forwards.to_csv(output_file)
    print(f"\n      Saved: {output_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Date range: {predi_252_with_forwards.index[0].strftime('%Y-%m-%d')} to {predi_252_with_forwards.index[-1].strftime('%Y-%m-%d')}")
    print(f"Total dates: {len(predi_252_with_forwards)}")
    print(f"Spot columns: {len([c for c in predi_252_with_forwards.columns if c.startswith('predi_')])}")
    print(f"Forward columns: {len([c for c in predi_252_with_forwards.columns if c.startswith('fwd_')])}")
    
    # Show sample forward rates
    print("\nSample Forward Rates (latest date):")
    latest = predi_252_with_forwards.iloc[-1]
    for col in fwd_cols:
        if not pd.isna(latest[col]):
            print(f"  {col}: {latest[col]:.4%}")
    
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
