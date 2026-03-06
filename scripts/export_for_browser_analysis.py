"""
Export financial data to JSON for browser-based analysis.

This creates a comprehensive JSON file with all transaction data,
account summaries, and debt information that can be analyzed in the browser.

Usage:
  python export_for_browser_analysis.py              # previous month
  python export_for_browser_analysis.py --year-in-review 2025   # full 2025 year
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

def export_financial_data(year_in_review=None):
    """Export all financial data to JSON for browser analysis."""
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load transaction data
    json_tx = base_dir / "data" / "raw" / "transactions.json"
    if not json_tx.exists():
        print("[ERROR] No transaction data found. Please run fetch_monarch_api.py first.")
        return
    
    with open(json_tx, "r", encoding="utf-8") as f:
        transactions = json.load(f)
    
    df = pd.DataFrame(transactions)
    
    # Normalize columns
    cols = {c.lower(): c for c in df.columns}
    def pick(*opts):
        for o in opts:
            if o in cols: return cols[o]
        return None
    
    date_c = pick("date","posted_at","transaction_date","posted_date","post_date")
    acct_c = pick("account_name","account","account")
    desc_c = pick("description","description_raw","merchant","payee","name","memo","notes")
    cat_c  = pick("category","category_name")
    amt_c  = pick("amount","amount_usd")
    
    rename = {}
    if date_c: rename[date_c] = "posted_at"
    if acct_c: rename[acct_c] = "account_name"
    if desc_c: rename[desc_c] = "description_raw"
    if cat_c:  rename[cat_c]  = "category"
    if amt_c:  rename[amt_c]  = "amount"
    df = df.rename(columns=rename)
    
    # Extract nested data
    if "category" in df.columns:
        def extract_category_name(cat):
            if pd.isna(cat) or cat is None:
                return None
            if isinstance(cat, dict):
                return cat.get("name", None)
            return str(cat)
        df["category"] = df["category"].apply(extract_category_name)
    
    if "account_name" in df.columns:
        def extract_account_name(acc):
            if pd.isna(acc) or acc is None:
                return None
            if isinstance(acc, dict):
                return acc.get("displayName", acc.get("name", None))
            return str(acc)
        df["account_name"] = df["account_name"].apply(extract_account_name)
    
    if "description_raw" in df.columns:
        def extract_description(desc):
            if pd.isna(desc) or desc is None:
                return None
            if isinstance(desc, dict):
                return desc.get("name", desc.get("displayName", str(desc)))
            return str(desc)
        df["description_raw"] = df["description_raw"].apply(extract_description)
    
    df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
    def to_num(x):
        try: return float(str(x).replace("$","").replace(",",""))
        except: return None
    df["amount"] = df["amount"].apply(to_num)
    df = df.dropna(subset=["posted_at","amount"])
    
    # Calculate date ranges
    current_year = pd.Timestamp.now().year
    year_start = pd.Timestamp(f"{current_year}-01-01")
    today = pd.Timestamp.now().normalize()
    month_start = today.replace(day=1).normalize()
    prev_month_end = month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1).normalize()
    
    # Year-in-review mode: analyze full calendar year
    if year_in_review is not None:
        yir_start = pd.Timestamp(f"{year_in_review}-01-01")
        yir_end = pd.Timestamp(f"{year_in_review}-12-31")
        analysis_month_txns = df[
            (df["posted_at"] >= yir_start) &
            (df["posted_at"] <= yir_end)
        ].copy()
        analysis_label = f"{year_in_review} Year in Review"
        # For YTD summary in year-in-review, use that year
        summary_year_start = yir_start
    else:
        # Monthly data - Use PREVIOUS month for analysis
        analysis_month_txns = df[
            (df["posted_at"] >= prev_month_start) &
            (df["posted_at"] < month_start)
        ].copy()
        analysis_label = prev_month_start.strftime("%B %Y")
        summary_year_start = year_start
    
    # USAA data (YTD for the relevant year)
    usaa_df = df[df["account_name"].str.contains("USAA", case=False, na=False)].copy()
    usaa_income_ytd = usaa_df[(usaa_df["amount"] > 0) & (usaa_df["posted_at"] >= summary_year_start)]["amount"].sum()
    usaa_expenses_ytd = abs(usaa_df[(usaa_df["amount"] < 0) & (usaa_df["posted_at"] >= summary_year_start)]["amount"].sum())
    usaa_net_flow = usaa_income_ytd - usaa_expenses_ytd
    
    # Current/previous month slices (for metadata and optional display)
    current_month_txns = df[
        (df["posted_at"] >= month_start) &
        (df["posted_at"] < (month_start + pd.DateOffset(months=1)))
    ].copy()
    
    prev_month_txns = df[
        (df["posted_at"] >= prev_month_start) &
        (df["posted_at"] < month_start)
    ].copy()
    
    # Load live debt balances from accounts.json
    debts = []
    json_acc = base_dir / "data" / "raw" / "accounts.json"
    if json_acc.exists():
        with open(json_acc, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        
        # Debt configuration for APR and payment (fallback if debts.yml missing)
        # Only cards that carry a balance; Capital One and Verizon are autopay-full, not tracked
        DEBT_CONFIG = {
            "Delta": {"apr": 20.0, "payment": 500.0},   # Delta SkyMiles Amex — primary card
            "Citi": {"apr": 20.0, "payment": 500.0},    # Costco Anywhere Visa — Costco only
            "Amazon": {"apr": 25.0, "payment": 100.0},  # Amazon Store Card — nearly done
        }
        
        # Try to load from config/debts.yml
        debts_yml = base_dir / "config" / "debts.yml"
        if debts_yml.exists():
            try:
                import yaml
                debts_config = yaml.safe_load(debts_yml.read_text(encoding="utf-8"))
                DEBT_CONFIG.update(debts_config.get("debts", {}))
            except:
                pass
        
        # Find credit card accounts
        for acc in accounts:
            acc_type = acc.get("type", {})
            acc_subtype = acc.get("subtype", {})
            type_name = acc_type.get("name", "") if isinstance(acc_type, dict) else ""
            subtype_name = acc_subtype.get("name", "") if isinstance(acc_subtype, dict) else ""
            
            is_credit_card = (type_name == "credit" or subtype_name == "credit_card")
            
            if is_credit_card:
                display_name = acc.get("displayName", acc.get("name", "Unknown"))
                current_balance = acc.get("currentBalance", 0.0)
                display_balance = acc.get("displayBalance", 0.0)
                
                balance = float(display_balance) if display_balance else float(current_balance)
                
                if balance > 0:
                    # Only include cards explicitly listed in DEBT_CONFIG
                    # Cards on autopay-full (Capital One, Verizon, etc.) are excluded by omission
                    matched_config = None
                    for key, config in DEBT_CONFIG.items():
                        if key.lower() in display_name.lower():
                            matched_config = config
                            break

                    if matched_config is not None:
                        debts.append({
                            "name": display_name,
                            "balance": balance,
                            "apr": matched_config.get("apr", 20.0),
                            "payment": matched_config.get("payment", 500.0)
                        })
    
    # Fallback if no debts found
    if not debts:
        debts = [
            {"name": "Delta SkyMiles Amex", "balance": 24469.5, "apr": 20.0, "payment": 500.0},
            {"name": "Costco Citi", "balance": 7895.19, "apr": 20.0, "payment": 500.0},
            {"name": "Amazon Store Card", "balance": 334.86, "apr": 25.0, "payment": 100.0},
        ]
    
    # Credit card spending (PREVIOUS month for analysis)
    credit_card_keywords = ["card", "visa", "mastercard", "amex", "american express", "discover", "capital one", "citi", "chase"]
    credit_card_txns = analysis_month_txns[
        (analysis_month_txns["amount"] < 0) &
        (analysis_month_txns["account_name"].str.contains("|".join(credit_card_keywords), case=False, na=False))
    ].copy()
    
    # Prepare export data
    export_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "current_year": current_year,
            "current_month": month_start.strftime("%B %Y"),
            "previous_month": prev_month_start.strftime("%B %Y"),
            "analysis_month": analysis_label,
        },
        "summary": {
            "usaa_income_ytd": float(usaa_income_ytd),
            "usaa_expenses_ytd": float(usaa_expenses_ytd),
            "usaa_net_flow_ytd": float(usaa_income_ytd - usaa_expenses_ytd),
            "previous_month_total": float(prev_month_txns[prev_month_txns["account_name"].str.contains("USAA", case=False, na=False)]["amount"].sum()),
            "current_month_balance": float(current_month_txns[current_month_txns["account_name"].str.contains("USAA", case=False, na=False)]["amount"].sum()),
        },
        "debts": debts,
        "transactions": {
            "current_month": current_month_txns[[
                "posted_at", "account_name", "category", "description_raw", "amount"
            ]].to_dict(orient="records"),
            "previous_month": prev_month_txns[[
                "posted_at", "account_name", "category", "description_raw", "amount"
            ]].to_dict(orient="records"),
            "credit_cards_analysis_month": credit_card_txns[[
                "posted_at", "account_name", "category", "description_raw", "amount"
            ]].to_dict(orient="records"),
        },
        "spending_by_category": analysis_month_txns[analysis_month_txns["amount"] < 0].groupby("category")["amount"].sum().abs().to_dict(),
        "spending_by_account": credit_card_txns.groupby("account_name")["amount"].sum().abs().to_dict(),
    }
    
    # Convert dates to strings
    for txn_list in ["current_month", "previous_month", "credit_cards_analysis_month"]:
        for txn in export_data["transactions"][txn_list]:
            if isinstance(txn.get("posted_at"), pd.Timestamp):
                txn["posted_at"] = txn["posted_at"].strftime("%Y-%m-%d")
            elif hasattr(txn.get("posted_at"), "isoformat"):
                txn["posted_at"] = txn["posted_at"].isoformat()
    
    # Save to JSON
    output_file = output_dir / "financial_data_for_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"[OK] Exported financial data to: {output_file}")
    print(f"     Total transactions: {len(df)}")
    print(f"     Analysis period: {analysis_label}")
    print(f"     Credit card transactions for analysis: {len(credit_card_txns)}")
    
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export financial data for browser analysis.")
    parser.add_argument("--year-in-review", type=int, default=None,
                        help="Full-year mode, e.g. 2025 for '2025 Year in Review'")
    args = parser.parse_args()
    export_financial_data(year_in_review=args.year_in_review)

