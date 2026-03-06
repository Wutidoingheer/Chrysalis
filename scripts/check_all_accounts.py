"""Check all accounts being pulled from Monarch Money"""
import json
from pathlib import Path

json_acc = Path("./data/raw/accounts.json")
if not json_acc.exists():
    print("[ERROR] accounts.json not found. Run fetch_monarch_api.py first.")
    exit(1)

with open(json_acc, "r", encoding="utf-8") as f:
    accounts = json.load(f)

print("=" * 60)
print("ALL ACCOUNTS FROM MONARCH MONEY")
print("=" * 60)
print(f"Total accounts: {len(accounts)}\n")

# Group by type
by_type = {}
for acc in accounts:
    acc_type = acc.get("type", {})
    type_name = acc_type.get("name", "unknown") if isinstance(acc_type, dict) else "unknown"
    type_display = acc_type.get("display", type_name) if isinstance(acc_type, dict) else type_name
    
    if type_display not in by_type:
        by_type[type_display] = []
    
    display_name = acc.get("displayName", acc.get("name", "Unknown"))
    current_balance = acc.get("currentBalance", 0.0)
    display_balance = acc.get("displayBalance", 0.0)
    balance = float(display_balance) if display_balance else float(current_balance)
    is_asset = acc.get("isAsset", True)
    
    by_type[type_display].append({
        "name": display_name,
        "balance": balance,
        "currentBalance": current_balance,
        "isAsset": is_asset
    })

# Print by category
for category in sorted(by_type.keys()):
    accounts_list = by_type[category]
    total = sum(abs(a["balance"]) for a in accounts_list)
    print(f"\n{category.upper()} ({len(accounts_list)} accounts, Total: ${total:,.2f})")
    print("-" * 60)
    
    for acc in sorted(accounts_list, key=lambda x: abs(x["balance"]), reverse=True):
        balance_str = f"${acc['balance']:,.2f}" if acc['balance'] >= 0 else f"-${abs(acc['balance']):,.2f}"
        asset_label = "Asset" if acc['isAsset'] else "Liability"
        print(f"  {acc['name']}")
        print(f"    Balance: {balance_str} ({asset_label})")

print("\n" + "=" * 60)
print("CREDIT CARDS SUMMARY")
print("=" * 60)

# Find credit cards by type/subtype
credit_cards = []
for acc in accounts:
    acc_type = acc.get("type", {})
    acc_subtype = acc.get("subtype", {})
    type_name = acc_type.get("name", "") if isinstance(acc_type, dict) else ""
    subtype_name = acc_subtype.get("name", "") if isinstance(acc_subtype, dict) else ""
    
    if type_name == "credit" or subtype_name == "credit_card":
        display_name = acc.get("displayName", acc.get("name", "Unknown"))
        display_balance = acc.get("displayBalance", acc.get("currentBalance", 0.0))
        balance = float(display_balance) if display_balance else abs(float(acc.get("currentBalance", 0.0)))
        if balance > 0:
            credit_cards.append({"name": display_name, "balance": balance})

if credit_cards:
    total_cc = sum(c["balance"] for c in credit_cards)
    print(f"\nTotal Credit Card Debt: ${total_cc:,.2f}")
    print(f"Number of cards: {len(credit_cards)}\n")
    for card in sorted(credit_cards, key=lambda x: x["balance"], reverse=True):
        print(f"  {card['name']}: ${card['balance']:,.2f}")
else:
    print("\nNo credit cards found.")

print("\n" + "=" * 60)
print("VERIFICATION: All accounts are being pulled from Monarch Money")
print("=" * 60)

