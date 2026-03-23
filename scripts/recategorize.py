"""
recategorize.py

Applies merchant-based recategorization rules to this month's transactions.
Previews changes before applying them.

Usage:
    python scripts/recategorize.py           # preview only
    python scripts/recategorize.py --apply   # apply changes

Add your rules to the RULES list below. Each rule matches on merchant name
(case-insensitive substring) and assigns a target category ID.

Run `get_transaction_categories()` or check config/categories.yml for IDs.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from monarchmoney import MonarchMoney, LoginFailedException, SessionExpiredError

load_dotenv()

SESSION_FILE = Path(".mm/mm_session.pickle")

# ── Rules ────────────────────────────────────────────────────────────────────
# Each rule: (merchant substring, target category ID, label)
# Matching is case-insensitive. First matching rule wins.

RULES: list[tuple[str, str, str]] = [
    ("costco",     "225515046838784483", "Groceries"),
    ("walmart",    "225515046838784483", "Groceries"),
    ("icpayment",  "225515046838784469", "Auto Payment"),
]

# ── Auth ─────────────────────────────────────────────────────────────────────

async def get_client() -> MonarchMoney:
    mm = MonarchMoney(session_file=str(SESSION_FILE))
    if SESSION_FILE.exists():
        try:
            mm.load_session(str(SESSION_FILE))
            return mm
        except Exception:
            print("Session invalid or expired, re-authenticating...")
    await mm.interactive_login()
    mm.save_session(str(SESSION_FILE))
    return mm


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(apply: bool = False):
    try:
        mm = await get_client()
    except (LoginFailedException, SessionExpiredError):
        print("Authentication failed. Check your credentials in .env")
        sys.exit(1)

    now = datetime.now()
    start = now.strftime("%Y-%m-01")
    end = now.strftime("%Y-%m-%d")

    print(f"Scanning transactions for {now.strftime('%B %Y')}...\n")

    txns_data = await mm.get_transactions(start_date=start, end_date=end, limit=500)
    txns = txns_data.get("allTransactions", {}).get("results", [])

    # Match transactions against rules
    changes: list[dict] = []
    for t in txns:
        merchant = (t.get("merchant") or {}).get("name") or t.get("description", "")
        current_cat = (t.get("category") or {}).get("name", "Uncategorized")
        current_cat_id = (t.get("category") or {}).get("id")

        for pattern, target_id, target_label in RULES:
            if pattern.lower() in merchant.lower():
                # Skip if already in the target category
                if current_cat_id == target_id:
                    break
                changes.append({
                    "id": t["id"],
                    "date": (t.get("date") or "")[:10],
                    "merchant": merchant,
                    "amount": t.get("amount", 0),
                    "from_cat": current_cat,
                    "to_cat": target_label,
                    "to_id": target_id,
                })
                break  # first matching rule wins

    if not changes:
        print("No transactions matched the recategorization rules.")
        return

    # Preview
    print(f"  {'DATE':<12} {'MERCHANT':<32} {'AMOUNT':>9}  {'FROM':<22}  {'TO'}")
    print("  " + "-" * 90)
    for c in sorted(changes, key=lambda x: x["date"]):
        print(
            f"  {c['date']:<12}"
            f" {c['merchant']:<32}"
            f" ${abs(c['amount']):>8.2f}"
            f"  {c['from_cat']:<22}"
            f"  -> {c['to_cat']}"
        )

    print(f"\n  {len(changes)} transaction(s) would be recategorized.")

    if not apply:
        print("\n  Run with --apply to commit these changes.")
        return

    # Group by target category for bulk update
    by_category: dict[str, list[str]] = {}
    for c in changes:
        by_category.setdefault(c["to_id"], []).append(c["id"])

    print("\nApplying changes...")
    total = 0
    for cat_id, ids in by_category.items():
        result = await mm.bulk_update_transactions(
            transaction_ids=ids,
            updates={"categoryId": cat_id},
        )
        affected = result.get("bulkUpdateTransactions", {}).get("affectedCount", len(ids))
        total += affected

    print(f"Done. {total} transaction(s) updated.")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply=apply))
