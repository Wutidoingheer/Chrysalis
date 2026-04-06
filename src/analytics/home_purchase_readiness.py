"""
home_purchase_readiness.py

Analytics for the Home Purchase Readiness tracker.

Provides four functions that operate on the same data structures used throughout
the rest of the app (transactions DataFrame, accounts list, debts.yml config):

  spending_vs_targets(df, config)  — monthly actual vs. target for 3 cut categories
  monthly_savings_progress(df, config) — running $500/mo savings discipline tracking
  milestone_status(config)         — milestone timeline with countdown + status
  dti_readiness(accounts, config)  — current & projected DTI indicator
"""

from pathlib import Path
from datetime import date
import yaml
import pandas as pd

CONFIG_PATH = Path("./config/home_purchase.yml")
DEBTS_YML   = Path("./config/debts.yml")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")).get("home_purchase", {})
    return {}


# ── 1. Spending vs. Targets ───────────────────────────────────────────────────

def _match_transactions(df: pd.DataFrame, target_cfg: dict) -> pd.DataFrame:
    """Return rows from df that match a spending target group (by category or merchant)."""
    cats     = [c.lower() for c in target_cfg.get("categories", [])]
    merchants = [m.lower() for m in target_cfg.get("merchants", [])]

    mask = pd.Series(False, index=df.index)

    if cats and "category" in df.columns:
        cat_col = df["category"].fillna("").str.lower()
        mask |= cat_col.apply(lambda c: any(c == cat or c.startswith(cat) for cat in cats))

    if merchants and "description_raw" in df.columns:
        desc_col = df["description_raw"].fillna("").str.lower()
        mask |= desc_col.apply(lambda d: any(m in d for m in merchants))

    return df[mask]


def spending_vs_targets(df: pd.DataFrame, config: dict, months: int = 3) -> list:
    """
    For each spending target group, compute actual monthly spend vs. target
    over the last `months` complete months.

    Returns a list of dicts:
      {label, target, months: [{month, actual, over_by, pct_of_target}],
       avg_actual, avg_over_by, avg_pct_of_target}
    """
    targets = config.get("spending_targets", {})
    if not targets:
        return []

    # Work only with expense transactions (negative amounts)
    expenses = df[df["amount"] < 0].copy()
    expenses["month"] = expenses["posted_at"].dt.to_period("M").astype(str)

    # Build list of the last N complete months
    today = pd.Timestamp.now()
    month_labels = []
    for i in range(months, 0, -1):
        m = (today - pd.DateOffset(months=i)).to_period("M").strftime("%Y-%m")
        month_labels.append(m)

    results = []
    for group_key, t_cfg in targets.items():
        label  = t_cfg.get("label", group_key)
        target = float(t_cfg.get("target", 0))
        matched = _match_transactions(expenses, t_cfg)

        monthly_rows = []
        for m in month_labels:
            month_df = matched[matched["month"] == m]
            actual = float(abs(month_df["amount"].sum()))
            over_by = actual - target
            pct = round(actual / target * 100, 1) if target else 0.0
            monthly_rows.append({
                "month": m,
                "actual": round(actual, 2),
                "target": target,
                "over_by": round(over_by, 2),
                "pct_of_target": pct,
            })

        actuals = [r["actual"] for r in monthly_rows]
        avg_actual  = round(sum(actuals) / len(actuals), 2) if actuals else 0.0
        avg_over_by = round(avg_actual - target, 2)
        avg_pct     = round(avg_actual / target * 100, 1) if target else 0.0

        results.append({
            "label":           label,
            "target":          target,
            "months":          monthly_rows,
            "avg_actual":      avg_actual,
            "avg_over_by":     avg_over_by,
            "avg_pct_of_target": avg_pct,
        })

    return results


# ── 2. Monthly Savings Progress ───────────────────────────────────────────────

def monthly_savings_progress(df: pd.DataFrame, config: dict, months: int = 6) -> dict:
    """
    Tracks how much is being "saved" each month vs. the $500/mo goal.

    Savings = combined target ceiling − actual spend across all tracked categories.
    Positive = under-budget (good); negative = over target (room to improve).

    Returns:
      {goal, months: [{month, total_target, total_actual, saved, vs_goal, cumulative}],
       cumulative_saved, cumulative_goal}
    """
    targets = config.get("spending_targets", {})
    goal    = float(config.get("monthly_savings_goal", 500))

    expenses = df[df["amount"] < 0].copy()
    expenses["month"] = expenses["posted_at"].dt.to_period("M").astype(str)

    today = pd.Timestamp.now()
    month_labels = []
    for i in range(months, 0, -1):
        m = (today - pd.DateOffset(months=i)).to_period("M").strftime("%Y-%m")
        month_labels.append(m)

    combined_target = sum(float(t.get("target", 0)) for t in targets.values())

    rows = []
    cumulative = 0.0
    for m in month_labels:
        total_actual = 0.0
        for t_cfg in targets.values():
            matched = _match_transactions(expenses[expenses["month"] == m], t_cfg)
            total_actual += float(abs(matched["amount"].sum()))

        saved   = round(combined_target - total_actual, 2)
        vs_goal = round(saved - goal, 2)
        cumulative += saved

        rows.append({
            "month":        m,
            "total_target": combined_target,
            "total_actual": round(total_actual, 2),
            "saved":        saved,
            "vs_goal":      vs_goal,
            "cumulative":   round(cumulative, 2),
        })

    cumulative_goal = goal * len(month_labels)

    return {
        "goal":             goal,
        "combined_target":  combined_target,
        "months":           rows,
        "cumulative_saved": round(cumulative, 2),
        "cumulative_goal":  round(cumulative_goal, 2),
        "on_track":         cumulative >= cumulative_goal * 0.8,  # within 20% = on track
    }


# ── 3. Milestone Tracker ──────────────────────────────────────────────────────

def milestone_status(config: dict) -> list:
    """
    Evaluates each milestone's status relative to today.

    Returns list of dicts:
      {id, label, target_date, days_away, status, pct_elapsed}

    status: "completed" | "imminent" (<30 days) | "upcoming" (<180 days) | "planned"
    pct_elapsed: % of time from tracking start to target_date that has passed
    """
    today      = date.today()
    start_str  = config.get("savings_tracking_start", str(today))
    try:
        track_start = date.fromisoformat(start_str)
    except ValueError:
        track_start = today

    results = []
    for ms in config.get("milestones", []):
        try:
            target_dt = date.fromisoformat(ms["target_date"])
        except (KeyError, ValueError):
            continue

        days_away = (target_dt - today).days

        if days_away < 0:
            status = "completed"
        elif days_away < 30:
            status = "imminent"
        elif days_away < 180:
            status = "upcoming"
        else:
            status = "planned"

        # % of the window from tracking_start → target_date that has elapsed
        total_window = (target_dt - track_start).days
        elapsed      = (today - track_start).days
        if total_window > 0:
            pct_elapsed = min(100, max(0, round(elapsed / total_window * 100, 1)))
        else:
            pct_elapsed = 100.0 if days_away <= 0 else 0.0

        results.append({
            "id":          ms.get("id", ""),
            "label":       ms.get("label", ""),
            "target_date": ms["target_date"],
            "days_away":   days_away,
            "status":      status,
            "pct_elapsed": pct_elapsed,
        })

    return results


# ── 4. DTI Readiness ──────────────────────────────────────────────────────────

def dti_readiness(accounts: list, config: dict) -> dict:
    """
    Calculates current and projected DTI (Debt-to-Income ratio).

    Current DTI  = (all credit card monthly payments + current mortgage) / gross income
    Projected DTI = (remaining balances after payoffs + new mortgage PITI) / gross income

    Lender thresholds: <36% ideal, <43% conventional max.

    Returns a dict with current_dti, projected_dti_low, projected_dti_high,
    threshold status, and a breakdown of monthly obligations.
    """
    gross_income = float(config.get("gross_monthly_income", 0))
    current_mortgage = float(config.get("current_mortgage_payment", 0))
    piti_low  = float(config.get("new_payment_piti_low", 0))
    piti_high = float(config.get("new_payment_piti_high", 0))

    # Load payment amounts from debts.yml
    debt_payments = {}
    if DEBTS_YML.exists():
        try:
            debts_cfg = yaml.safe_load(DEBTS_YML.read_text(encoding="utf-8"))
            for key, d in debts_cfg.get("debts", {}).items():
                debt_payments[key.lower()] = float(d.get("payment", 0))
        except Exception:
            pass

    # Match accounts to debt config for payment amounts
    obligations = []
    if accounts:
        for acc in accounts:
            acc_type    = acc.get("type", {})
            acc_subtype = acc.get("subtype", {})
            type_name   = acc_type.get("name", "") if isinstance(acc_type, dict) else ""
            sub_name    = acc_subtype.get("name", "") if isinstance(acc_subtype, dict) else ""

            if type_name != "credit" and sub_name != "credit_card":
                continue

            display_name = acc.get("displayName", acc.get("name", ""))
            balance = float(acc.get("displayBalance", acc.get("currentBalance", 0)) or 0)
            if balance <= 0:
                continue

            # Find matching payment amount from debts.yml
            payment = None
            for key, pmt in debt_payments.items():
                if key in display_name.lower():
                    payment = pmt
                    break
            if payment is None:
                payment = round(balance * 0.02, 2)  # Default: 2% minimum

            obligations.append({
                "name":    display_name,
                "balance": balance,
                "payment": payment,
            })

    total_cc_payments = sum(o["payment"] for o in obligations)

    # Current DTI: all CC payments + current mortgage
    current_total = total_cc_payments + current_mortgage
    current_dti   = round(current_total / gross_income * 100, 1) if gross_income else 0.0

    # Projected DTI: CC payments that remain + new mortgage PITI (assume debts being paid off
    # means balance will be lower; use current payments as conservative estimate for now)
    projected_total_low  = total_cc_payments + piti_low
    projected_total_high = total_cc_payments + piti_high
    proj_dti_low  = round(projected_total_low  / gross_income * 100, 1) if gross_income else 0.0
    proj_dti_high = round(projected_total_high / gross_income * 100, 1) if gross_income else 0.0

    return {
        "gross_monthly_income":   gross_income,
        "current_mortgage":       current_mortgage,
        "cc_obligations":         obligations,
        "total_cc_payments":      round(total_cc_payments, 2),
        "current_total_payments": round(current_total, 2),
        "current_dti":            current_dti,
        "piti_low":               piti_low,
        "piti_high":              piti_high,
        "projected_total_low":    round(projected_total_low, 2),
        "projected_total_high":   round(projected_total_high, 2),
        "projected_dti_low":      proj_dti_low,
        "projected_dti_high":     proj_dti_high,
        "threshold_ideal":        36.0,
        "threshold_max":          43.0,
        "current_ok":             current_dti < 43.0,
        "projected_ok":           proj_dti_high < 43.0,
    }
