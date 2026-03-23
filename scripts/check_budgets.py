"""
check_budgets.py

Fetches budgets for the current month and lists transactions
for over-budget fixed/non-monthly categories and the full
flexible spending pool breakdown.

Usage:
    python scripts/check_budgets.py

Requires:
    - .env with MONARCH_EMAIL / MONARCH_PASSWORD (for re-auth if session expires)
    - Or an existing session at .mm/mm_session.pickle
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from monarchmoney import MonarchMoney, LoginFailedException, SessionExpiredError

load_dotenv()

SESSION_FILE = Path(".mm/mm_session.pickle")
DIVIDER = "-" * 66


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


def print_txns(txns: list) -> None:
    if not txns:
        print("    (no transactions found)")
        return
    for t in sorted(txns, key=lambda x: x.get("date", ""), reverse=True):
        date = (t.get("date") or "")[:10]
        desc = (t.get("merchant") or {}).get("name") or t.get("description", "")
        amt = t.get("amount", 0)
        print(f"    {date}  {desc:<38}  ${abs(amt):>8.2f}")


async def main():
    try:
        mm = await get_client()
    except (LoginFailedException, SessionExpiredError):
        print("Authentication failed. Check your credentials in .env")
        sys.exit(1)

    now = datetime.now()
    start = now.strftime("%Y-%m-01")
    end = now.strftime("%Y-%m-%d")

    print(f"Fetching budgets for {now.strftime('%B %Y')}...\n")

    budgets_data, txns_data = await asyncio.gather(
        mm.get_budgets(start_date=start, end_date=end),
        mm.get_transactions(start_date=start, end_date=end, limit=500),
    )

    # Build category metadata map from categoryGroups
    cat_meta: dict[str, dict] = {}
    for group in budgets_data.get("categoryGroups", []):
        for cat in group.get("categories", []):
            cat_meta[cat["id"]] = {
                "name": cat["name"],
                "variability": cat.get("budgetVariability"),
                "group_type": group.get("type"),
            }

    # Build category id -> monthly budget amounts
    cat_amounts: dict[str, dict] = {}
    for item in budgets_data.get("budgetData", {}).get("monthlyAmountsByCategory", []):
        cid = item.get("category", {}).get("id")
        amounts = (item.get("monthlyAmounts") or [{}])[0]
        cat_amounts[cid] = amounts

    # Index transactions by category
    txns = txns_data.get("allTransactions", {}).get("results", [])
    by_cat: dict[str, list] = {}
    for t in txns:
        cid = (t.get("category") or {}).get("id")
        if cid:
            by_cat.setdefault(cid, []).append(t)

    # ── Fixed / Non-monthly: show over-budget categories ──────────────────────
    fixed_over = []
    for cid, meta in cat_meta.items():
        if meta["group_type"] != "expense":
            continue
        if meta["variability"] not in ("fixed", "non_monthly"):
            continue
        amounts = cat_amounts.get(cid, {})
        planned = amounts.get("plannedCashFlowAmount") or 0
        actual = amounts.get("actualAmount") or 0
        remaining = amounts.get("remainingAmount") or 0
        if planned > 0 and remaining < 0:
            fixed_over.append({
                "name": meta["name"],
                "id": cid,
                "planned": planned,
                "actual": actual,
                "over_by": abs(remaining),
            })

    print("== OVER-BUDGET FIXED / NON-MONTHLY CATEGORIES ==\n")
    if not fixed_over:
        print("  All fixed categories within budget.\n")
    else:
        fixed_over.sort(key=lambda x: x["over_by"], reverse=True)
        print(f"  {'CATEGORY':<26} {'BUDGET':>10} {'ACTUAL':>10} {'OVER BY':>10}")
        print("  " + DIVIDER)
        for b in fixed_over:
            print(
                f"  {b['name']:<26}"
                f"  ${b['planned']:>8.2f}"
                f"  ${b['actual']:>8.2f}"
                f"  ${b['over_by']:>8.2f}"
            )
        print()
        for b in fixed_over:
            print(f"  {b['name']}  (over by ${b['over_by']:.2f})")
            print_txns(by_cat.get(b["id"], []))
            print()

    # ── Flexible: full pool breakdown ─────────────────────────────────────────
    flex_pool = budgets_data["budgetData"].get("monthlyAmountsForFlexExpense", {})
    flex_amounts = (flex_pool.get("monthlyAmounts") or [{}])[0]
    flex_planned = flex_amounts.get("plannedCashFlowAmount") or 0
    flex_actual = flex_amounts.get("actualAmount") or 0
    flex_remaining = flex_amounts.get("remainingAmount") or 0

    status = f"OVER BY ${abs(flex_remaining):.2f}" if flex_remaining < 0 else f"${flex_remaining:.2f} remaining"
    print(f"== FLEXIBLE BUDGET  -  ${flex_planned:.2f} planned  -  ${flex_actual:.2f} spent  -  {status} ==\n")

    # Collect flex categories with any spending
    flex_cats = []
    for cid, meta in cat_meta.items():
        if meta["group_type"] != "expense" or meta["variability"] != "flexible":
            continue
        amounts = cat_amounts.get(cid, {})
        actual = amounts.get("actualAmount") or 0
        if actual > 0 or by_cat.get(cid):
            flex_cats.append({
                "name": meta["name"],
                "id": cid,
                "planned": amounts.get("plannedCashFlowAmount") or 0,
                "actual": actual,
            })

    flex_cats.sort(key=lambda x: x["actual"], reverse=True)

    if not flex_cats:
        print("  No flexible spending this month.\n")
    else:
        print(f"  {'CATEGORY':<26} {'BUDGET':>10} {'ACTUAL':>10}")
        print("  " + DIVIDER[:48])
        for c in flex_cats:
            budgeted_str = f"${c['planned']:>8.2f}" if c['planned'] > 0 else "       --"
            print(f"  {c['name']:<26}  {budgeted_str}  ${c['actual']:>8.2f}")
        print()

        print("  --- Transactions by Category ---\n")
        for c in flex_cats:
            cat_txns = by_cat.get(c["id"], [])
            if not cat_txns:
                continue
            print(f"  {c['name']}  (${c['actual']:.2f} spent)")
            print_txns(cat_txns)
            print()


if __name__ == "__main__":
    asyncio.run(main())
