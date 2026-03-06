import glob
import pandas as pd

def read_cdi_data():
    """
    Read CDI data from the raw data directory.

    Returns:
    - pd.DataFrame: DataFrame containing CDI data.
    """
    # Find all files in the raw data directory
    files = glob.glob('src/data/raw/cdi/*.xls') + glob.glob('src/data/raw/cdi/*.xlsx')

    dfs = []

    for file in files:
        try:
            print(f"📂 Processing: {file}")

            # First, attempt to read as an Excel file
            try:
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, skiprows=1, skipfooter=2, engine=engine)
                print(f"✅ Successfully read {file} as Excel")
                dfs.append(df)
                continue  # If successful, move to the next file

            except Exception as e:
                print(f"⚠️ Excel read error: {e}. Attempting to read as a raw text file.")

            # If Excel reading fails, treat it as a text file (most likely case)
            try:
                with open(file, 'r', encoding="latin1") as f:
                    lines = f.readlines()
                
                # Print first few lines for debugging
                print("📄 First 5 lines of file:", "".join(lines[:5]))

                # Identify correct start of data (skip metadata)
                data_lines = [line.strip().split("\t") for line in lines if line.strip()]

                # Convert to DataFrame
                df = pd.DataFrame(data_lines)

                # Rename columns based on expected structure (adjust if needed)
                df.columns = [
                    "Data", 
                    "Nr. Operacoes", 
                    "Volume", 
                    "Media", 
                    "Fator Diario", 
                    "Taxa SELIC"
                ]

                # Convert date column
                df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

                # Convert numeric columns, handling Portuguese decimal format
                df["Volume"] = pd.to_numeric(df["Volume"].str.replace(",", "."), errors="coerce")
                df["Taxa SELIC"] = pd.to_numeric(df["Taxa SELIC"].str.replace(",", "."), errors="coerce")
                df["Fator Diario"] = pd.to_numeric(df["Fator Diario"].str.replace(",", "."), errors="coerce")

                # Drop rows where 'Data' is missing (likely extra metadata)
                df.dropna(subset=["Data"], inplace=True)

                dfs.append(df)
                print(f"✅ Successfully read {file} as a text file")

            except Exception as txt_e:
                print(f"❌ Failed to read {file} as text: {txt_e}")

        except Exception as e:
            print(f"❌ Unexpected error processing {file}: {e}")

    # Combine all valid DataFrames into one
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # rename to English
        df.columns = [
            "date", 
            "Number of Operations", 
            "Volume", 
            "Average", 
            "Daily Factor", 
            "SELIC Rate"
        ]

        return df
    else:
        return pd.DataFrame()

