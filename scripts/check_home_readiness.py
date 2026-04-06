"""
check_home_readiness.py

Quick console check for Home Purchase Readiness.
Reads cached data from data/raw/ — run fetch_monarch_api.py first for fresh data.

Usage:
    python scripts/check_home_readiness.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports.generate_report import load_any
from src.analytics.home_purchase_readiness import (
    load_config,
    spending_vs_targets,
    monthly_savings_progress,
    milestone_status,
    dti_readiness,
)

DIVIDER = "-" * 66


def bar(pct: float, width: int = 30) -> str:
    filled = int(min(pct, 100) / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:.0f}%"


def main():
    cfg = load_config()
    if not cfg:
        print("[WARN] config/home_purchase.yml not found. See config/home_purchase.yml for setup.")
        sys.exit(1)

    print("\n" + "=" * 66)
    print("  HOME PURCHASE READINESS TRACKER")
    print(f"  Target: ~$650k home by {cfg.get('target_move_date', 'TBD')}")
    print(f"  Est. proceeds: ${cfg.get('estimated_net_proceeds', 0):,.0f}  |  "
          f"New PITI: ${cfg.get('new_payment_piti_low', 0):,.0f}–"
          f"${cfg.get('new_payment_piti_high', 0):,.0f}/mo")
    print("=" * 66)

    # ── Load transaction data ─────────────────────────────────────────────────
    try:
        df = load_any()
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("Run python src/ingest/fetch_monarch_api.py first.")
        sys.exit(1)

    # ── Load accounts ─────────────────────────────────────────────────────────
    accounts = []
    acc_path = Path("./data/raw/accounts.json")
    if acc_path.exists():
        with open(acc_path, encoding="utf-8") as f:
            accounts = json.load(f)

    # ── 1. Spending vs. Targets ───────────────────────────────────────────────
    print("\n── 1. SPENDING CATEGORY TARGETS (last 3 months) " + "-" * 19)
    spending = spending_vs_targets(df, cfg, months=3)
    if not spending:
        print("  No spending targets configured.")
    else:
        header = f"  {'CATEGORY':<30} {'TARGET':>8}  {'AVG ACTUAL':>10}  {'AVG DIFF':>10}"
        print(header)
        print("  " + DIVIDER)
        for row in spending:
            diff_str = ("+" if row["avg_over_by"] > 0 else "") + f"${row['avg_over_by']:,.0f}"
            flag = "  OVER" if row["avg_over_by"] > 0 else "  ok"
            print(f"  {row['label']:<30} ${row['target']:>7,.0f}  ${row['avg_actual']:>9,.0f}"
                  f"  {diff_str:>10}{flag}")
        print()
        # Month-by-month detail
        for row in spending:
            print(f"  {row['label']}  (target ${row['target']:,.0f}/mo)")
            for m in row["months"]:
                diff_str = ("+" if m["over_by"] > 0 else "") + f"${m['over_by']:,.0f}"
                flag = " <-- OVER" if m["over_by"] > 0 else ""
                print(f"    {m['month']}  actual ${m['actual']:>8,.0f}  {diff_str:>9}{flag}")
            print()

    # ── 2. Monthly Savings Progress ───────────────────────────────────────────
    print("── 2. SAVINGS PROGRESS vs. $500/mo GOAL " + "-" * 25)
    savings = monthly_savings_progress(df, cfg, months=6)
    goal = savings.get("goal", 500)
    combined_target = savings.get("combined_target", 0)
    print(f"  Combined target ceiling: ${combined_target:,.0f}/mo  |  Goal: ${goal:,.0f}/mo saved\n")

    months_data = savings.get("months", [])
    if months_data:
        print(f"  {'MONTH':<10} {'ACTUAL':>10} {'SAVED':>9} {'vs GOAL':>9} {'CUMULATIVE':>12}")
        print("  " + DIVIDER)
        for r in months_data:
            vs_str = ("+" if r["vs_goal"] >= 0 else "") + f"${r['vs_goal']:,.0f}"
            on_track = " ok" if r["vs_goal"] >= 0 else " below"
            print(f"  {r['month']:<10} ${r['total_actual']:>9,.0f} ${r['saved']:>8,.0f}"
                  f"  {vs_str:>9}  ${r['cumulative']:>10,.0f}{on_track}")

    cum_saved = savings.get("cumulative_saved", 0)
    cum_goal  = savings.get("cumulative_goal", 0)
    on_track  = savings.get("on_track", False)
    pct = cum_saved / cum_goal * 100 if cum_goal else 0
    print(f"\n  Cumulative: ${cum_saved:,.0f} of ${cum_goal:,.0f} goal  {bar(pct, 24)}")
    print(f"  Status: {'ON TRACK' if on_track else 'BEHIND — tighten spending to hit $500/mo'}\n")

    # ── 3. Milestone Tracker ──────────────────────────────────────────────────
    print("── 3. MILESTONE TRACKER " + "-" * 42)
    milestones = milestone_status(cfg)
    if not milestones:
        print("  No milestones configured.")
    else:
        print(f"  {'MILESTONE':<38} {'TARGET':>12} {'DAYS':>6}  PROGRESS")
        print("  " + DIVIDER)
        for ms in milestones:
            days_str = "DONE" if ms["days_away"] < 0 else f"{ms['days_away']}d"
            print(f"  {ms['label']:<38} {ms['target_date']:>12} {days_str:>6}  {bar(ms['pct_elapsed'], 18)}")
    print()

    # ── 4. DTI Readiness ──────────────────────────────────────────────────────
    print("── 4. DTI READINESS " + "-" * 46)
    dti = dti_readiness(accounts, cfg)
    gross = dti.get("gross_monthly_income", 0)
    print(f"  Gross monthly income: ${gross:,.0f}  |  Thresholds: <36% ideal, <43% max\n")

    scenarios = [
        ("Current (CC pmts + existing mortgage)",
         dti.get("current_total_payments", 0), dti.get("current_dti", 0)),
        (f"Projected Low  (CC pmts + PITI ${dti.get('piti_low', 0):,.0f})",
         dti.get("projected_total_low", 0), dti.get("projected_dti_low", 0)),
        (f"Projected High (CC pmts + PITI ${dti.get('piti_high', 0):,.0f})",
         dti.get("projected_total_high", 0), dti.get("projected_dti_high", 0)),
    ]
    print(f"  {'SCENARIO':<46} {'PAYMENTS':>10}  {'DTI':>6}  STATUS")
    print("  " + DIVIDER)
    for label, payments, pct in scenarios:
        status = "OK (<36%)" if pct < 36 else "CAUTION (<43%)" if pct < 43 else "HIGH (>43%)"
        print(f"  {label:<46} ${payments:>9,.0f}  {pct:>5.1f}%  {status}")

    # CC breakdown
    cc_obs = dti.get("cc_obligations", [])
    if cc_obs:
        print(f"\n  Credit card obligations included:")
        for o in cc_obs:
            print(f"    {o['name']:<40}  bal ${o['balance']:>9,.0f}  pmt ${o['payment']:>7,.0f}/mo")
    print(f"\n  Tip: paying down CC balances before closing reduces projected DTI.")
    print()
    print("=" * 66 + "\n")


if __name__ == "__main__":
    main()
