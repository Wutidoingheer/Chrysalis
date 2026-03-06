import pandas as pd

def utilization_by_account(balances: dict, limits: dict) -> pd.DataFrame:
    rows = []
    for acc, bal in balances.items():
        limit = limits.get(acc)
        if not limit: 
            continue
        util = max(0.0, -bal) / float(limit)  # negative = debt
        rows.append({"account_id": acc, "limit": limit, "balance": bal, "utilization": util})
    df = pd.DataFrame(rows)
    if df.empty:
        return df, 0.0
    overall = max(0.0, -df["balance"].sum()) / df["limit"].sum()
    return df.sort_values("utilization", ascending=False), overall
