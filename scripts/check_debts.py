"""Quick script to check what debts are being detected from accounts.json"""
import json
from pathlib import Path

json_acc = Path("./data/raw/accounts.json")
if not json_acc.exists():
    print("[ERROR] accounts.json not found. Run fetch_monarch_api.py first.")
    exit(1)

with open(json_acc, "r", encoding="utf-8") as f:
    accounts = json.load(f)

print("=" * 60)
print("CREDIT CARD ACCOUNTS FOUND IN MONARCH MONEY")
print("=" * 60)

credit_cards = []
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
        
        credit_cards.append({
            "name": display_name,
            "balance": balance,
            "currentBalance": current_balance,
            "displayBalance": display_balance
        })

if credit_cards:
    print(f"\nFound {len(credit_cards)} credit card account(s):\n")
    for card in sorted(credit_cards, key=lambda x: x["balance"], reverse=True):
        print(f"  {card['name']}")
        print(f"    Balance: ${card['balance']:,.2f}")
        print(f"    (currentBalance: {card['currentBalance']}, displayBalance: {card['displayBalance']})")
        print()
else:
    print("\nNo credit card accounts found.")

print("=" * 60)
print("These balances are pulled LIVE from Monarch Money")
print("APR and payment amounts come from config/debts.yml")
print("=" * 60)



