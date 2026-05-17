"""
home_purchase_readiness.py

Analytics for the Home Purchase Readiness tracker.

Transaction-based functions (require Monarch data in data/raw/):
  spending_vs_targets(df, config)       — monthly actual vs. target for 3 cut categories
  monthly_savings_progress(df, config)  — running $500/mo savings discipline tracking

Config-only functions (no live data required):
  rsu_schedule(config)       — full vest schedule, net of withholding
  rsu_net_by_date(vests, dt) — cumulative net cash through a given date
  espp_summary(config)       — ESPP monthly drain and per-purchase gain
  income_summary(config)     — take-home, free cash, annual bonus (net)
  milestone_status(config)   — milestone timeline with countdown + status
  dti_readiness(accounts, config) — current & projected DTI indicator
"""

from pathlib import Path
from datetime import date
from math import log
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


# ── 5. RSU Schedule ───────────────────────────────────────────────────────────

# Static vest schedule. Quarterly vests use 38.5 (true average) so the running
# total reconciles exactly to 617 rather than rounding each vest independently.
_RSU_SCHEDULE_RAW = [
    ("2026-12-15", 155.0,  "Cliff Vest"),
    ("2027-03-15",  38.5,  "Quarterly"),
    ("2027-06-15",  38.5,  "Quarterly"),
    ("2027-09-15",  38.5,  "Quarterly"),
    ("2027-12-15",  38.5,  "Quarterly"),
    ("2028-03-15",  38.5,  "Quarterly"),
    ("2028-06-15",  38.5,  "Quarterly"),
    ("2028-09-15",  38.5,  "Quarterly"),
    ("2028-12-15",  38.5,  "Quarterly"),
    ("2029-03-15",  38.5,  "Quarterly"),
    ("2029-06-15",  38.5,  "Quarterly"),
    ("2029-09-15",  38.5,  "Quarterly"),
    ("2029-12-15",  38.5,  "Quarterly"),
]
# 155 + 12 * 38.5 = 617 — verified in tests/test_home_purchase_readiness.py


def rsu_schedule(config: dict) -> list[dict]:
    """
    Returns the full vest schedule with net-of-withholding calculations.

    Each entry:
      date, vest_type, gross_shares, withholding_rate, net_shares, price,
      net_cash (net_shares × price), cumulative_net_cash
    """
    price       = float(config.get("adbe_price_default", 247))
    withholding = float(config.get("rsu_withholding_default", 0.35))

    cumulative = 0.0
    results = []
    for vest_date, gross, vest_type in _RSU_SCHEDULE_RAW:
        net_shares = gross * (1 - withholding)
        net_cash   = net_shares * price
        cumulative += net_cash
        results.append({
            "date":               vest_date,
            "vest_type":          vest_type,
            "gross_shares":       gross,
            "withholding_rate":   withholding,
            "net_shares":         round(net_shares, 2),
            "price":              price,
            "net_cash":           round(net_cash, 2),
            "cumulative_net_cash": round(cumulative, 2),
        })
    return results


def rsu_net_by_date(vests: list[dict], cutoff: str) -> float:
    """Cumulative net RSU cash for all vests on or before cutoff (YYYY-MM-DD)."""
    return round(sum(v["net_cash"] for v in vests if v["date"] <= cutoff), 2)


# ── 6. ESPP Summary ───────────────────────────────────────────────────────────

def espp_summary(config: dict) -> dict:
    """
    Models ESPP as a continuous monthly cash drain with twice-yearly realized gain.

    Assumptions:
      - Contribution = espp_rate × base_salary / 12 per month (after-tax deduction)
      - 15% look-back discount: each $N invested purchases $N / 0.85 worth of stock
      - Realized gain per purchase = contribution_period × (discount / (1 - discount))
      - Two purchase dates per year (Jun 30, Dec 31)

    Returns monthly_drain, annual_drain, gain_per_purchase, annual_gain,
    and sensitivity: gain at 10%, 5%, 0% rates for comparison.
    """
    base    = float(config.get("base_salary", 150_000))
    rate    = float(config.get("espp_rate_default", 0.15))
    discount = float(config.get("espp_discount", 0.15))  # 15% look-back floor

    monthly_drain     = base * rate / 12
    annual_drain      = base * rate
    semi_annual_contribution = annual_drain / 2
    gain_per_purchase = semi_annual_contribution * (discount / (1 - discount))
    annual_gain       = gain_per_purchase * 2

    sensitivity = []
    for r in [0.15, 0.10, 0.05, 0.0]:
        d = base * r / 12
        g = (base * r / 2) * (discount / (1 - discount))
        sensitivity.append({
            "espp_rate":      r,
            "monthly_drain":  round(d, 2),
            "gain_per_purchase": round(g, 2),
            "annual_gain":    round(g * 2, 2),
            "annual_net_benefit": round(g * 2 - base * r, 2),
        })

    return {
        "espp_rate":          rate,
        "base_salary":        base,
        "monthly_drain":      round(monthly_drain, 2),
        "annual_drain":       round(annual_drain, 2),
        "gain_per_purchase":  round(gain_per_purchase, 2),
        "annual_gain":        round(annual_gain, 2),
        "sensitivity":        sensitivity,
        "note": (
            "ESPP drain is an after-tax payroll deduction. "
            "Gain is realized at each purchase date (Jun 30, Dec 31), "
            "not spread monthly — do not count as monthly income."
        ),
    }


# ── 7. Income Summary ─────────────────────────────────────────────────────────

def income_summary(config: dict) -> dict:
    """
    Computes take-home and free cash figures.

    Utah all-in effective rate at $150k is approximately 27–29%:
      Federal income tax: ~22% effective
      Utah state (flat):   4.85%
      FICA (employee):    ~1.4% above SS wage base, partial Medicare
    Default 28% is a reasonable conservative assumption; expose as a setting.

    Bonus withholding defaults to 35% (supplemental rate).
    """
    base        = float(config.get("base_salary", 150_000))
    tax_rate    = float(config.get("effective_tax_rate", 0.28))
    espp_rate   = float(config.get("espp_rate_default", 0.15))
    bonus_rate  = float(config.get("bonus_rate_default", 0.075))
    bonus_wh    = float(config.get("bonus_withholding", 0.35))

    gross_monthly     = base / 12
    takehome_monthly  = gross_monthly * (1 - tax_rate)
    espp_drain        = base * espp_rate / 12
    free_cash_monthly = takehome_monthly - espp_drain
    gross_bonus       = base * bonus_rate
    net_bonus         = gross_bonus * (1 - bonus_wh)

    return {
        "base_salary":        base,
        "gross_monthly":      round(gross_monthly, 2),
        "effective_tax_rate": tax_rate,
        "takehome_monthly":   round(takehome_monthly, 2),
        "espp_monthly_drain": round(espp_drain, 2),
        "free_cash_monthly":  round(free_cash_monthly, 2),
        "gross_annual_bonus": round(gross_bonus, 2),
        "net_annual_bonus":   round(net_bonus, 2),
        "utah_note": "Utah flat state tax: 4.85%. Default 28% all-in covers fed + UT + FICA.",
    }
