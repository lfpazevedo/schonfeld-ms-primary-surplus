import pandas as pd
import os


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = "src/data/processed/b3/predi_252_pivot.csv"
OUTPUT_DIR = "src/data/processed/b3"
OUTPUT_FILE = "predi_fra_1y1y_3y3y.csv"

# Forward rate definitions: (name, short_du, long_du)
# 1y1y: 1-year rate, 1 year forward (252d to 504d)
# 3y3y: 3-year rate, 3 years forward (756d to 1512d)
FRA_DEFINITIONS = [
    ("1y1y", 252, 504),      # 1y rate, 1y forward
    ("3y3y", 756, 1512),     # 3y rate, 3y forward
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
        du1: Short leg business days
        r2: Long leg rate in decimal
        du2: Long leg business days
    
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


def calculate_fra_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate FRA rates for the defined forward periods.
    
    Args:
        df: DataFrame with date index and predi_XXX columns
    
    Returns:
        DataFrame with fra_XXX columns added
    """
    df = df.copy()
    
    for fra_name, du_short, du_long in FRA_DEFINITIONS:
        col_short = f"predi_{du_short}"
        col_long = f"predi_{du_long}"
        fra_col = f"fra_{fra_name}"
        
        if col_short in df.columns and col_long in df.columns:
            df[fra_col] = df.apply(
                lambda row: calculate_b3_forward(
                    row[col_short], du_short,
                    row[col_long], du_long
                ),
                axis=1
            )
        else:
            missing = []
            if col_short not in df.columns:
                missing.append(col_short)
            if col_long not in df.columns:
                missing.append(col_long)
            print(f"Warning: Missing columns for {fra_name}: {missing}")
    
    return df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Extract 1y1y and 3y3y FRA rates from PRE-DI curve data."""
    
    print("=" * 60)
    print("FRA Rates Extraction: 1y1y and 3y3y")
    print("=" * 60)
    
    # Check input file exists
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")
    
    # Load data
    print(f"\n[1/3] Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE, index_col="date", parse_dates=True)
    print(f"      Loaded {len(df):,} rows with {len(df.columns)} columns")
    
    # Calculate FRA rates
    print("\n[2/3] Calculating FRA rates...")
    print(f"      Definitions: {[f[0] for f in FRA_DEFINITIONS]}")
    df_with_fra = calculate_fra_rates(df)
    
    # Extract only FRA columns
    fra_cols = [f"fra_{f[0]}" for f in FRA_DEFINITIONS]
    fra_df = df_with_fra[fra_cols].copy()
    
    # Rename to cleaner column names
    fra_df.columns = ["1y1y", "3y3y"]
    
    # Display sample
    print("\n      Sample FRA rates (latest 5 dates):")
    print(fra_df.tail().to_string())
    
    # Save output
    print("\n[3/3] Saving results...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    fra_df.to_csv(output_path)
    print(f"      Saved: {output_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Date range: {fra_df.index[0].strftime('%Y-%m-%d')} to {fra_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"Total dates: {len(fra_df)}")
    print(f"\nFRA 1y1y (1-year forward, 1 year out):")
    print(f"  Latest: {fra_df['1y1y'].iloc[-1]:.4%}")
    print(f"  Mean:   {fra_df['1y1y'].mean():.4%}")
    print(f"  Min:    {fra_df['1y1y'].min():.4%}")
    print(f"  Max:    {fra_df['1y1y'].max():.4%}")
    print(f"\nFRA 3y3y (3-year forward, 3 years out):")
    print(f"  Latest: {fra_df['3y3y'].iloc[-1]:.4%}")
    print(f"  Mean:   {fra_df['3y3y'].mean():.4%}")
    print(f"  Min:    {fra_df['3y3y'].min():.4%}")
    print(f"  Max:    {fra_df['3y3y'].max():.4%}")
    
    print("\n" + "=" * 60)
    print("Extraction complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
