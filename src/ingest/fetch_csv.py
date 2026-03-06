import pandas as pd
from pathlib import Path

def load_transactions(csv_path: str) -> pd.DataFrame:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"{csv_path} not found.")
    df = pd.read_csv(p)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    if "date" in df.columns and "posted_at" not in df.columns:
        df.rename(columns={"date": "posted_at"}, inplace=True)
    if "description" in df.columns and "description_raw" not in df.columns:
        df.rename(columns={"description": "description_raw"}, inplace=True)
    if "account" in df.columns and "account_name" not in df.columns:
        df.rename(columns={"account": "account_name"}, inplace=True)
    return df

if __name__ == "__main__":
    print(load_transactions("./data/raw/sample_transactions.csv").head())
