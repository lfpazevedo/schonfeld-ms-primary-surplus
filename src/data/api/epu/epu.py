import pandas as pd


def load_epu_data():
    df = pd.read_excel('https://www.policyuncertainty.com/media/Brazil_Policy_Uncertainty_Data.xlsx')
    return df