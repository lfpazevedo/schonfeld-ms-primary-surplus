# import requests
# from datetime import datetime
# from bs4 import BeautifulSoup

# def fetch_bmf_rates(data: str):
#     """
#     Fetches BMF reference rates from BM&F Bovespa portal for a given date and extracts the table.
    
#     Args:
#         data (str): The date in 'DD/MM/YYYY' format.
    
#     Returns:
#         str: The extracted table HTML content.
#     """
#     try:
#         # Convert date to required formats
#         date_obj = datetime.strptime(data, "%d/%m/%Y")
#         data1 = date_obj.strftime("%Y%m%d")
        
#         # Construct URL
#         url = f"https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp?Data={data}&Data1={data1}&slcTaxa=PRE#"
        
#         # Make GET request
#         response = requests.get(url)
#         response.raise_for_status()  # Raise an error for bad responses
        
#         # Parse HTML
#         soup = BeautifulSoup(response.text, "html.parser")
#         table = soup.find("table", id="tb_principal1")  # Extracting table by ID
        
#         return str(table) if table else "No table found."
#     except Exception as e:
#         return f"Error fetching data: {e}"

# # Example usage
# if __name__ == "__main__":
#     data = "03/02/2025"
#     print(fetch_bmf_rates(data))

import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def fetch_bmf_rates(date_str: str):
    """
    Fetches BMF reference rates from BM&F Bovespa portal for a given date.
    Manually parses the table cells and returns a DataFrame.

    Args:
        date_str (str): The date in 'DD/MM/YYYY' format.

    Returns:
        pd.DataFrame: The extracted table data as a DataFrame with columns:
                      ['Date', 'Dias Corridos', '252(2)(4)', '360(1)'].
    """
    try:
        # Convert date to required formats
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        data1 = date_obj.strftime("%Y%m%d")

        # Construct URL
        url = (
            "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
            f"lum-taxas-referenciais-bmf-ptBR.asp?Data={date_str}&Data1={data1}&slcTaxa=PRE#"
        )

        # Make GET request
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse HTML for the table with the ID tb_principal1
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="tb_principal1")

        if not table:
            print(f"No table found for {date_str}")
            return pd.DataFrame()

        # Extract all <td> from the table
        cells = table.find_all("td")
        # We'll assume each row has exactly 3 columns:
        # [Dias Corridos, 252(2)(4), 360(1)]
        rows = []
        row_data = []
        for i, cell in enumerate(cells, start=1):
            row_data.append(cell.get_text(strip=True))
            # Once we've collected 3 columns, push them as one row
            if i % 3 == 0:
                rows.append(row_data)
                row_data = []

        # If no rows found, there's no numeric data
        if not rows:
            print(f"Table found but no data for {date_str}")
            return pd.DataFrame()

        # Create a DataFrame and add the date
        df = pd.DataFrame(rows, columns=["Dias Corridos", "252(2)(4)", "360(1)"])
        df.insert(0, "Date", date_str)
        return df

    except Exception as e:
        print(f"Error fetching data for {date_str}: {e}")
        return pd.DataFrame()

def save_historical_data(start_date: str, end_date: str, save_dir: str):
    """
    Fetches and saves historical BMF reference rates from the given date range,
    saving one file per day.

    Args:
        start_date (str): Start date in 'DD/MM/YYYY' format.
        end_date (str): End date in 'DD/MM/YYYY' format.
        save_dir (str): Directory to save the daily CSV files.
    """
    start = datetime.strptime(start_date, "%d/%m/%Y")
    end = datetime.strptime(end_date, "%d/%m/%Y")

    os.makedirs(save_dir, exist_ok=True)

    while start <= end:
        date_str = start.strftime("%d/%m/%Y")
        file_name = start.strftime("%Y%m%d") + ".csv"
        save_path = os.path.join(save_dir, file_name)

        if not os.path.exists(save_path):
            df = fetch_bmf_rates(date_str)
            if not df.empty:
                df.to_csv(save_path, index=False)
                print(f"Saved data for {date_str} → {save_path}")
            else:
                print(f"No data available for {date_str}")
        else:
            print(f"File already exists: {save_path}")

        start += timedelta(days=1)

if __name__ == "__main__":
    # Example: from 27/01/2025 to 03/02/2025 
    save_historical_data("01/02/2012", "03/03/2026", "src/data/raw/b3/predi/")
