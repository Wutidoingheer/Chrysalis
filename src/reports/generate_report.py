from pathlib import Path
import json
import pandas as pd
from jinja2 import Template
import yaml
from src.analytics.utilization import utilization_by_account
from src.analytics.home_purchase_readiness import (
    load_config as load_hp_config,
    spending_vs_targets,
    monthly_savings_progress,
    milestone_status,
    dti_readiness,
)
from src.ingest.fetch_csv import load_transactions as load_csv

# ---------- Config you can tweak ----------
CSV_PATH = Path("./data/raw/monarch_transactions.csv")  # optional if using JSON

SHOW_RECENT_N = 20

# Debt configuration - APR and payment can be set here or in config/debts.yml
# Balances are pulled live from accounts.json
DEBT_CONFIG = {
    # Map account names (or partial matches) to APR and payment
    # If not found here, will use defaults or try to load from config/debts.yml
    "Amex": {"apr": 22.0, "payment": 2000.0},
    "Citi": {"apr": 20.0, "payment": 500.0},
    "Delta": {"apr": 20.0, "payment": 500.0},
    "Costco": {"apr": 18.0, "payment": 300.0},
    "Amazon": {"apr": 25.0, "payment": 100.0},
    "Verizon": {"apr": 22.0, "payment": 50.0},
    "Quicksilver": {"apr": 24.0, "payment": 50.0},
}
# ------------------------------------------

HTML = Template("""
<!doctype html><meta charset="utf-8">
<title>Finance Snapshot</title>
<style>
  body {font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px;}
  h1 {margin-bottom: 0.25rem;}
  .muted {color:#666;margin-top:0}
  table {border-collapse: collapse; width: 100%; margin: 12px 0;}
  th,td {border:1px solid #ddd; padding:8px; text-align:left;}
  th {background:#f5f5f5;}
  .grid {display:grid; grid-template-columns: 1fr 1fr; gap: 24px;}
  .section{margin-top:24px;}
</style>

<h1>Finance Snapshot</h1>
<p class="muted">Generated {{ now }}</p>

<div class="section">
  <h2>USAA Account Summary (Year-To-Date {{ current_year }})</h2>
  <table>
    <tr><th>Metric</th><th>Amount</th></tr>
    <tr>
      <td><strong>Total Income (YTD)</strong></td>
      <td style="color: green; font-weight: bold;">{{ "${:,.2f}".format(usaa_total_income) }}</td>
    </tr>
    <tr>
      <td><strong>Total Expenses (YTD)</strong></td>
      <td style="color: red; font-weight: bold;">{{ "${:,.2f}".format(usaa_total_expenses) }}</td>
    </tr>
    <tr>
      <td><strong>Net Cash Flow (YTD)</strong></td>
      <td style="font-weight: bold; color: {{ 'green' if usaa_net_flow >= 0 else 'red' }};">{{ "${:,.2f}".format(usaa_net_flow) }}</td>
    </tr>
    <tr>
      <td><strong>Previous Month Total</strong></td>
      <td>{{ "${:,.2f}".format(previous_month_total) }}</td>
    </tr>
    <tr>
      <td><strong>Current Month Balance</strong></td>
      <td style="font-weight: bold; color: {{ 'green' if current_month_balance >= 0 else 'red' }};">{{ "${:,.2f}".format(current_month_balance) }}</td>
    </tr>
    <tr>
      <td><strong>Amount Paid Down (Progress)</strong></td>
      <td style="color: green; font-weight: bold;">{{ "${:,.2f}".format(amount_paid_down) }}</td>
    </tr>
  </table>
</div>

<div class="section">
  <h2>Debt Payoff (Illustrative)</h2>
  <table>
    <tr><th>Debt</th><th>Balance</th><th>APR</th><th>Payment</th><th>Months</th><th>Total Interest</th></tr>
    {% for d in debts %}
    <tr>
      <td>{{ d.name }}</td>
      <td>{{ "${:,.2f}".format(d.balance) }}</td>
      <td>{{ "{:.2f}%".format(d.apr) }}</td>
      <td>{{ "${:,.0f}".format(d.payment) }}</td>
      <td>{{ d.months if d.months is not none else "n/a" }}</td>
      <td>{{ "${:,.2f}".format(d.total_interest) if d.total_interest is not none else "n/a" }}</td>
    </tr>
    {% endfor %}
  </table>
  <p class="muted">Tip: try +$250/+500/+1000/mo to see how months and interest drop.</p>
</div>

<div class="section">
  <h2>Cash Flow by Month</h2>
  <table>
    <tr><th>Month</th><th>Net Flow</th></tr>
    {% for r in cashflow %}
    <tr><td>{{ r.month }}</td><td>{{ "{:,.2f}".format(r.net_flow) }}</td></tr>
    {% endfor %}
  </table>
</div>

<div class="section">
  <h2>USAA Bank Income (Year-To-Date {{ current_year }})</h2>
  {% if usaa_income %}
  <table>
    <tr><th>Date</th><th>Description</th><th>Amount</th><th>YTD Running Total</th></tr>
    {% for r in usaa_income %}
    <tr>
      <td>{{ r.posted_at }}</td>
      <td>{{ r.description_raw }}</td>
      <td style="color: green; font-weight: bold;">{{ "{:,.2f}".format(r.amount) }}</td>
      <td style="color: green; font-weight: bold;">{{ "${:,.2f}".format(r.running_total) }}</td>
    </tr>
    {% endfor %}
  </table>
  <p class="muted"><strong>YTD Total USAA Income: {{ "${:,.2f}".format(usaa_total_income) }}</strong></p>
  {% else %}
  <p class="muted">No income transactions found in USAA bank account for {{ current_year }}.</p>
  {% endif %}
</div>

<div class="section">
  <h2>Upcoming Income (Next 2 Weeks)</h2>
  {% if upcoming_income %}
  <table>
    <tr><th>Date</th><th>Account</th><th>Description</th><th>Amount</th></tr>
    {% for r in upcoming_income %}
    <tr>
      <td>{{ r.posted_at }}</td>
      <td>{{ r.account_name }}</td>
      <td>{{ r.description_raw }}</td>
      <td style="color: green; font-weight: bold;">{{ "{:,.2f}".format(r.amount) }}</td>
    </tr>
    {% endfor %}
  </table>
  <p class="muted"><strong>Total Upcoming Income: {{ "${:,.2f}".format(total_upcoming_income) }}</strong></p>
  {% else %}
  <p class="muted">No upcoming income transactions found in the next 2 weeks.</p>
  {% endif %}
</div>

<div class="section">
  <h2>Spending by Card/Account ({{ spending_period_label }})</h2>
  <table>
    <tr><th>Account</th><th>Total Spend</th><th>Transaction Count</th></tr>
    {% for r in spending_by_account %}
    <tr>
      <td>{{ r.account_name }}</td>
      <td style="color: red; font-weight: bold;">{{ "${:,.2f}".format(r.total_spend) }}</td>
      <td>{{ r.transaction_count }}</td>
    </tr>
    {% endfor %}
  </table>
</div>

<div class="section">
  <h2>Transactions by Card ({{ spending_period_label }})</h2>
  {% for card_data in transactions_by_card %}
  <h3>{{ card_data.account_name }} ({{ card_data.transaction_count }} transactions, Total: {{ "${:,.2f}".format(card_data.total_spend) }})</h3>
  <table>
    <tr><th>Date</th><th>Category</th><th>Description</th><th>Amount</th></tr>
    {% for txn in card_data.transactions %}
    <tr>
      <td>{{ txn.posted_at }}</td>
      <td>{{ txn.category or "" }}</td>
      <td>{{ txn.description_raw }}</td>
      <td>{{ "{:,.2f}".format(txn.amount) }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endfor %}
</div>

<div class="section">
  <h2>Recent {{ recent_n }} Transactions</h2>
  <table>
    <tr><th>Date</th><th>Account</th><th>Category</th><th>Description</th><th>Amount</th></tr>
    {% for r in recent %}
    <tr>
      <td>{{ r.posted_at }}</td>
      <td>{{ r.account_name }}</td>
      <td>{{ r.category or "" }}</td>
      <td>{{ r.description_raw }}</td>
      <td>{{ "{:,.2f}".format(r.amount) }}</td>
    </tr>
    {% endfor %}
  </table>
</div>
                
<div class="section">
  <h2>Credit Utilization</h2>
  <p class="muted">Overall utilization: {{ "{:.1f}%".format(overall_util*100) }}</p>
  <table>
    <tr><th>Account</th><th>Limit</th><th>Balance</th><th>Utilization</th></tr>
    {% for r in util_rows %}
    <tr>
      <td>{{ r.account_id }}</td>
      <td>{{ "${:,.0f}".format(r.limit) }}</td>
      <td>{{ "${:,.2f}".format(r.balance) }}</td>
      <td>{{ "{:.1f}%".format(r.utilization*100) }}</td>
    </tr>
    {% endfor %}
  </table>
  <p class="muted">Flags: try to keep per-card & overall under ~30%, ideally ~10–20% overall.</p>
</div>

{% if hp_enabled %}
<div class="section">
  <h2>🏡 Home Purchase Readiness</h2>
  <p class="muted">Target: ~$650k home by {{ hp_target_move_date }} &nbsp;|&nbsp; Est. proceeds: ${{ "{:,.0f}".format(hp_net_proceeds) }} &nbsp;|&nbsp; New PITI: ${{ "{:,.0f}".format(hp_piti_low) }}–${{ "{:,.0f}".format(hp_piti_high) }}/mo</p>

  <h3>1. Spending Category Targets</h3>
  <p class="muted">Monthly caps for the three cut areas. Goal: keep actual at or below target.</p>
  <table>
    <tr><th>Category</th><th>Monthly Target</th>
    {% for m in hp_spend_months %}<th>{{ m }}</th>{% endfor %}
    <th>Avg Actual</th><th>Avg vs Target</th></tr>
    {% for row in hp_spending %}
    <tr>
      <td><strong>{{ row.label }}</strong></td>
      <td>${{ "{:,.0f}".format(row.target) }}</td>
      {% for m in row.months %}
      <td style="color: {{ 'red' if m.over_by > 0 else 'green' }}; font-weight: bold;">
        ${{ "{:,.0f}".format(m.actual) }}
      </td>
      {% endfor %}
      <td style="font-weight: bold;">${{ "{:,.0f}".format(row.avg_actual) }}</td>
      <td style="color: {{ 'red' if row.avg_over_by > 0 else 'green' }}; font-weight: bold;">
        {{ ("+" if row.avg_over_by > 0 else "") + "${:,.0f}".format(row.avg_over_by) }}
      </td>
    </tr>
    {% endfor %}
  </table>

  <h3>2. Monthly Savings vs. ${{ "{:,.0f}".format(hp_savings_goal) }}/mo Goal</h3>
  <p class="muted">Savings = combined target ceiling (${{ "{:,.0f}".format(hp_combined_target) }}/mo) minus actual spend in tracked categories.</p>
  <table>
    <tr><th>Month</th><th>Target Ceiling</th><th>Actual Spend</th><th>Saved</th><th>vs. ${{ "{:,.0f}".format(hp_savings_goal) }} Goal</th><th>Cumulative Saved</th></tr>
    {% for r in hp_savings_months %}
    <tr>
      <td>{{ r.month }}</td>
      <td>${{ "{:,.0f}".format(r.total_target) }}</td>
      <td>${{ "{:,.0f}".format(r.total_actual) }}</td>
      <td style="color: {{ 'green' if r.saved >= 0 else 'red' }}; font-weight: bold;">${{ "{:,.0f}".format(r.saved) }}</td>
      <td style="color: {{ 'green' if r.vs_goal >= 0 else 'red' }}; font-weight: bold;">
        {{ ("+" if r.vs_goal >= 0 else "") + "${:,.0f}".format(r.vs_goal) }}
      </td>
      <td>${{ "{:,.0f}".format(r.cumulative) }}</td>
    </tr>
    {% endfor %}
    <tr style="background:#f5f5f5; font-weight: bold;">
      <td colspan="5">Cumulative Saved ({{ hp_savings_months|length }} months)</td>
      <td style="color: {{ 'green' if hp_cumulative_saved >= hp_cumulative_goal else 'red' }};">
        ${{ "{:,.0f}".format(hp_cumulative_saved) }} / ${{ "{:,.0f}".format(hp_cumulative_goal) }} goal
        ({{ "{:.0f}%".format(hp_cumulative_saved / hp_cumulative_goal * 100 if hp_cumulative_goal else 0) }})
      </td>
    </tr>
  </table>

  <h3>3. Milestone Tracker</h3>
  <table>
    <tr><th>Milestone</th><th>Target Date</th><th>Days Away</th><th>Progress</th><th>Status</th></tr>
    {% for ms in hp_milestones %}
    <tr>
      <td>{{ ms.label }}</td>
      <td>{{ ms.target_date }}</td>
      <td>{{ ms.days_away if ms.days_away >= 0 else "Passed" }}</td>
      <td>
        <div style="background:#eee; border-radius:4px; height:12px; width:120px; display:inline-block; vertical-align:middle;">
          <div style="background: {{ '#4caf50' if ms.status == 'completed' else '#2196f3' if ms.status == 'imminent' else '#ff9800' if ms.status == 'upcoming' else '#90caf9' }}; width:{{ ms.pct_elapsed }}%; height:100%; border-radius:4px;"></div>
        </div>
        <span style="font-size:0.85em; margin-left:6px;">{{ ms.pct_elapsed }}%</span>
      </td>
      <td style="font-weight: bold; color: {{ '#4caf50' if ms.status == 'completed' else '#e65100' if ms.status == 'imminent' else '#1976d2' if ms.status == 'upcoming' else '#666' }};">
        {{ ms.status | upper }}
      </td>
    </tr>
    {% endfor %}
  </table>

  <h3>4. DTI Readiness</h3>
  <p class="muted">Gross monthly income: ${{ "{:,.0f}".format(hp_dti.gross_monthly_income) }} &nbsp;|&nbsp; Thresholds: &lt;36% ideal, &lt;43% conventional max</p>
  <table>
    <tr><th>Scenario</th><th>Monthly Obligations</th><th>DTI</th><th>Status</th></tr>
    <tr>
      <td><strong>Current</strong> (CC payments + existing mortgage)</td>
      <td>${{ "{:,.0f}".format(hp_dti.current_total_payments) }}/mo</td>
      <td style="font-weight: bold; color: {{ 'green' if hp_dti.current_dti < 36 else 'orange' if hp_dti.current_dti < 43 else 'red' }};">{{ hp_dti.current_dti }}%</td>
      <td>{{ "OK" if hp_dti.current_dti < 43 else "HIGH" }}</td>
    </tr>
    <tr>
      <td><strong>Projected Low</strong> (CC payments + new PITI low)</td>
      <td>${{ "{:,.0f}".format(hp_dti.projected_total_low) }}/mo</td>
      <td style="font-weight: bold; color: {{ 'green' if hp_dti.projected_dti_low < 36 else 'orange' if hp_dti.projected_dti_low < 43 else 'red' }};">{{ hp_dti.projected_dti_low }}%</td>
      <td>{{ "OK" if hp_dti.projected_dti_low < 43 else "HIGH" }}</td>
    </tr>
    <tr>
      <td><strong>Projected High</strong> (CC payments + new PITI high)</td>
      <td>${{ "{:,.0f}".format(hp_dti.projected_total_high) }}/mo</td>
      <td style="font-weight: bold; color: {{ 'green' if hp_dti.projected_dti_high < 36 else 'orange' if hp_dti.projected_dti_high < 43 else 'red' }};">{{ hp_dti.projected_dti_high }}%</td>
      <td>{{ "OK" if hp_dti.projected_dti_high < 43 else "HIGH" }}</td>
    </tr>
  </table>
  <p class="muted">Note: paying down CC balances before closing will improve projected DTI. Update <code>config/home_purchase.yml</code> with your actual gross income.</p>
</div>
{% endif %}
""")

def load_any() -> pd.DataFrame:
    json_tx = Path("./data/raw/transactions.json")
    json_acc = Path("./data/raw/accounts.json")
    csv_p   = CSV_PATH

    if json_tx.exists():
        # Load JSON produced by fetch_monarch_api.py
        with open(json_tx, "r", encoding="utf-8") as f:
            tx = json.load(f)
        df = pd.DataFrame(tx)
        # normalize common fields -> posted_at, account_name, description_raw, category, amount
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

        for col in ["posted_at","account_name","description_raw","category","amount"]:
            if col not in df.columns:
                df[col] = None

        df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
        def to_num(x):
            try: return float(str(x).replace("$","").replace(",",""))
            except: return None
        df["amount"] = df["amount"].apply(to_num)
        
        # Extract category name from nested dict if needed
        if "category" in df.columns:
            def extract_category_name(cat):
                if pd.isna(cat) or cat is None:
                    return None
                if isinstance(cat, dict):
                    return cat.get("name", None)
                return str(cat)
            df["category"] = df["category"].apply(extract_category_name)
        
        # Extract account name from nested dict if needed
        if "account_name" in df.columns:
            def extract_account_name(acc):
                if pd.isna(acc) or acc is None:
                    return None
                if isinstance(acc, dict):
                    return acc.get("displayName", acc.get("name", None))
                return str(acc)
            df["account_name"] = df["account_name"].apply(extract_account_name)
        
        # Extract description from nested dict if needed (merchant field)
        if "description_raw" in df.columns:
            def extract_description(desc):
                if pd.isna(desc) or desc is None:
                    return None
                if isinstance(desc, dict):
                    return desc.get("name", desc.get("displayName", str(desc)))
                return str(desc)
            df["description_raw"] = df["description_raw"].apply(extract_description)
        
        return df.dropna(subset=["posted_at","amount"])

    elif csv_p.exists():
        return load_csv(csv_p)

    else:
        raise FileNotFoundError("No data: expected data/raw/transactions.json (API) or CSV at CSV_PATH")



def monthly_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["month"] = d["posted_at"].dt.to_period("M").astype(str)
    g = d.groupby("month")["amount"].sum().reset_index()
    g.rename(columns={"amount":"net_flow"}, inplace=True)
    return g.sort_values("month")

def by_category(df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    if months:
        cutoff = df["posted_at"].max() - pd.DateOffset(months=months)
        d = df[df["posted_at"] >= cutoff].copy()
        label = f"last {months} mo"
    else:
        d = df.copy()
        label = "all-time"
    g = d.groupby("category", dropna=False)["amount"].sum().reset_index()
    g.rename(columns={"amount":"net_amount"}, inplace=True)
    g = g.sort_values("net_amount")
    return g, label

def payoff_schedule(balance: float, apr: float, payment: float):
    r = apr / 12 / 100.0
    months, interest_sum, b = 0, 0.0, float(balance)
    if payment <= b * r:
        return None, None  # payment too low to cover interest
    while b > 0 and months < 600:
        i = b * r
        b = b + i - payment
        interest_sum += i
        months += 1
        if b < 0: b = 0
    return months, round(interest_sum, 2)

if __name__ == "__main__":
    OUT = Path("./data/outputs"); OUT.mkdir(parents=True, exist_ok=True)

    df = load_any()
    cf = monthly_cashflow(df).to_dict(orient="records")
    
    # Get USAA account data - Year-To-Date (current year only, resets Jan 1)
    current_year = pd.Timestamp.now().year
    year_start = pd.Timestamp(f"{current_year}-01-01")
    today = pd.Timestamp.now().normalize()
    month_start = today.replace(day=1).normalize()
    prev_month_end = month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1).normalize()
    
    # USAA income (positive amounts) - YTD
    usaa_income_df = df[
        (df["account_name"].str.contains("USAA", case=False, na=False)) & 
        (df["amount"] > 0) &
        (df["posted_at"] >= year_start)
    ].copy()
    usaa_income_df = usaa_income_df.sort_values("posted_at")
    usaa_income_df["running_total"] = usaa_income_df["amount"].cumsum()
    usaa_income_df["posted_at"] = usaa_income_df["posted_at"].dt.strftime("%Y-%m-%d")
    usaa_income_list = usaa_income_df[["posted_at","description_raw","amount","running_total"]].to_dict(orient="records")
    usaa_total_income = float(usaa_income_df["amount"].sum()) if len(usaa_income_df) > 0 else 0.0
    
    # USAA expenses (negative amounts) - YTD
    usaa_expenses_df = df[
        (df["account_name"].str.contains("USAA", case=False, na=False)) & 
        (df["amount"] < 0) &
        (df["posted_at"] >= year_start)
    ].copy()
    usaa_total_expenses = float(abs(usaa_expenses_df["amount"].sum())) if len(usaa_expenses_df) > 0 else 0.0
    usaa_net_flow = float(usaa_total_income - usaa_total_expenses)
    
    # Previous month USAA total
    prev_month_usaa = df[
        (df["account_name"].str.contains("USAA", case=False, na=False)) &
        (df["posted_at"] >= prev_month_start) &
        (df["posted_at"] < month_start)
    ]
    previous_month_total = float(prev_month_usaa["amount"].sum()) if len(prev_month_usaa) > 0 else 0.0
    
    # Current month USAA balance
    current_month_usaa = df[
        (df["account_name"].str.contains("USAA", case=False, na=False)) &
        (df["posted_at"] >= month_start) &
        (df["posted_at"] < (month_start + pd.DateOffset(months=1)))
    ]
    current_month_balance = float(current_month_usaa["amount"].sum()) if len(current_month_usaa) > 0 else 0.0
    
    # Amount paid down (progress) - difference between previous and current month
    # Positive means we're paying down debt/expenses, negative means we're spending more
    # If previous month was negative (expenses), and current is less negative, that's progress
    if previous_month_total < 0:
        amount_paid_down = float(abs(previous_month_total) - abs(current_month_balance)) if current_month_balance < 0 else float(abs(previous_month_total))
    else:
        amount_paid_down = 0.0
    
    # Get upcoming income (next 2 weeks, positive amounts)
    from datetime import datetime, timedelta
    today = pd.Timestamp.now().normalize()
    two_weeks = today + timedelta(days=14)
    future_df = df[(df["posted_at"] >= today) & (df["posted_at"] <= two_weeks) & (df["amount"] > 0)]
    upcoming_income = future_df.sort_values("posted_at").copy()
    upcoming_income["posted_at"] = upcoming_income["posted_at"].dt.strftime("%Y-%m-%d")
    upcoming_income_list = upcoming_income[["posted_at","account_name","description_raw","amount"]].to_dict(orient="records")
    total_upcoming_income = upcoming_income["amount"].sum() if len(upcoming_income) > 0 else 0
    
    # Spending by account - Monthly (current month)
    month_start = today.replace(day=1).normalize()
    next_month_start = (month_start + pd.DateOffset(months=1))
    
    # Filter for current month, negative amounts only (expenses), and credit card accounts
    # Credit cards typically have "card", "visa", "mastercard", "amex", "discover" in name
    spending_df = df[
        (df["posted_at"] >= month_start) & 
        (df["posted_at"] < next_month_start) &
        (df["amount"] < 0)
    ].copy()
    
    # Filter to credit cards (exclude checking/savings accounts)
    credit_card_keywords = ["card", "visa", "mastercard", "amex", "american express", "discover", "capital one", "citi", "chase"]
    is_credit_card = spending_df["account_name"].str.contains("|".join(credit_card_keywords), case=False, na=False)
    spending_df = spending_df[is_credit_card].copy()
    
    spending_by_account_df = spending_df.groupby("account_name").agg({
        "amount": ["sum", "count"]
    }).reset_index()
    spending_by_account_df.columns = ["account_name", "total_spend", "transaction_count"]
    spending_by_account_df["total_spend"] = spending_by_account_df["total_spend"].abs()  # Make positive for display
    spending_by_account_df = spending_by_account_df.sort_values("total_spend", ascending=False)
    spending_by_account_list = spending_by_account_df.to_dict(orient="records")
    
    # Transactions by card (grouped by account, monthly transactions only)
    transactions_by_card_list = []
    for account_name in spending_df["account_name"].unique():
        if pd.isna(account_name):
            continue
        account_txns = spending_df[spending_df["account_name"] == account_name].copy()
        account_txns = account_txns.sort_values("posted_at", ascending=False)
        account_txns["posted_at"] = account_txns["posted_at"].dt.strftime("%Y-%m-%d")
        transactions_by_card_list.append({
            "account_name": account_name,
            "transaction_count": len(account_txns),
            "total_spend": account_txns["amount"].sum(),
            "transactions": account_txns[["posted_at","category","description_raw","amount"]].to_dict(orient="records")
        })
    # Sort by total spend descending
    transactions_by_card_list.sort(key=lambda x: abs(x["total_spend"]), reverse=True)
    
    # Create period label for spending
    spending_period_label = month_start.strftime("%B %Y")
    
    rec = df.sort_values("posted_at", ascending=False).head(SHOW_RECENT_N)
    rec["posted_at"] = rec["posted_at"].dt.strftime("%Y-%m-%d")
    recent = rec[["posted_at","account_name","category","description_raw","amount"]].to_dict(orient="records")

    # Load live debt balances from accounts.json
    debts = []
    accounts = []
    json_acc = Path("./data/raw/accounts.json")
    if json_acc.exists():
        with open(json_acc, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        
        # Find credit card accounts (type.name == "credit" or subtype.name == "credit_card")
        for acc in accounts:
            acc_type = acc.get("type", {})
            acc_subtype = acc.get("subtype", {})
            type_name = acc_type.get("name", "") if isinstance(acc_type, dict) else ""
            subtype_name = acc_subtype.get("name", "") if isinstance(acc_subtype, dict) else ""
            
            # Check if it's a credit card
            is_credit_card = (type_name == "credit" or subtype_name == "credit_card")
            
            if is_credit_card:
                display_name = acc.get("displayName", acc.get("name", "Unknown"))
                current_balance = acc.get("currentBalance", 0.0)
                display_balance = acc.get("displayBalance", 0.0)
                
                # Use displayBalance if available, otherwise currentBalance
                # For credit cards, balance is typically positive (what you owe)
                balance = float(display_balance) if display_balance else float(current_balance)
                
                # Only include if there's an actual balance
                if balance > 0:
                    # Try to find APR and payment from config
                    apr = None
                    payment = None
                    
                    # Check DEBT_CONFIG for matches
                    for key, config in DEBT_CONFIG.items():
                        if key.lower() in display_name.lower():
                            apr = config.get("apr")
                            payment = config.get("payment")
                            break
                    
                    # Try to load from config/debts.yml if not found
                    if apr is None or payment is None:
                        debts_yml = Path("./config/debts.yml")
                        if debts_yml.exists():
                            try:
                                debts_config = yaml.safe_load(debts_yml.read_text(encoding="utf-8"))
                                for key, config in debts_config.get("debts", {}).items():
                                    if key.lower() in display_name.lower():
                                        apr = config.get("apr", apr)
                                        payment = config.get("payment", payment)
                                        break
                            except:
                                pass
                    
                    # Use defaults if still not found
                    if apr is None:
                        apr = 20.0  # Default APR
                    if payment is None:
                        payment = balance * 0.02  # Default 2% of balance as minimum payment
                    
                    debts.append({
                        "name": display_name,
                        "balance": balance,
                        "apr": apr,
                        "payment": payment
                    })
    
    # If no debts found from accounts, use fallback
    if not debts:
        print("[WARN] No credit card accounts found in accounts.json, using fallback debts")
        debts = [
            {"name": "Amex", "balance": 26000.0, "apr": 22.0, "payment": 2000.0},
            {"name": "Citi", "balance": 5000.0, "apr": 20.0, "payment": 500.0},
        ]
    
    # Calculate payoff schedules
    enriched = []
    for d in debts:
        m, ti = payoff_schedule(d["balance"], d["apr"], d["payment"])
        enriched.append({**d, "months": m, "total_interest": ti})

    # Approximate per-account balance: sum of amounts (for demo)
    by_acc = df.groupby("account_name")["amount"].sum().to_dict()

    # Map friendly account names to IDs (edit as you adopt real IDs)
    name_to_id = {
        "Amex Platinum": "acc_amex_cc",
        "Citi Rewards": "acc_citi_cc",
        "CapOne Venture": "acc_capone_cc",
    }
    balances_id = {name_to_id.get(k, k): v for k, v in by_acc.items()}

    limits = {}
    lp = Path("./config/limits.yml")
    if lp.exists():
        limits = yaml.safe_load(lp.read_text(encoding="utf-8")).get("credit_limits", {})

    util_df, overall_util = utilization_by_account(balances_id, limits)
    util_rows = util_df.to_dict(orient="records")

    # ── Home Purchase Readiness ────────────────────────────────────────────────
    hp_cfg = load_hp_config()
    hp_enabled = bool(hp_cfg)

    hp_spending_data   = spending_vs_targets(df, hp_cfg, months=3) if hp_enabled else []
    hp_savings_data    = monthly_savings_progress(df, hp_cfg, months=6) if hp_enabled else {}
    hp_milestones_data = milestone_status(hp_cfg) if hp_enabled else []

    # Load accounts list for DTI (already loaded above as `accounts`)
    raw_accounts = accounts if accounts else []
    hp_dti_data = dti_readiness(raw_accounts, hp_cfg) if hp_enabled else {}

    hp_spend_months = hp_spending_data[0]["months"] if hp_spending_data else []
    hp_spend_month_labels = [m["month"] for m in hp_spend_months]

    html = HTML.render(
        now=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        cashflow=cf,
        debts=enriched,
        current_year=current_year,
        usaa_total_income=usaa_total_income,
        usaa_total_expenses=usaa_total_expenses,
        usaa_net_flow=usaa_net_flow,
        previous_month_total=previous_month_total,
        current_month_balance=current_month_balance,
        amount_paid_down=amount_paid_down,
        usaa_income=usaa_income_list,
        upcoming_income=upcoming_income_list,
        total_upcoming_income=total_upcoming_income,
        spending_by_account=spending_by_account_list,
        spending_period_label=spending_period_label,
        transactions_by_card=transactions_by_card_list,
        recent=recent,
        recent_n=SHOW_RECENT_N,
        util_rows=util_rows,
        overall_util=overall_util,
        # Home Purchase Readiness
        hp_enabled=hp_enabled,
        hp_target_move_date=hp_cfg.get("target_move_date", ""),
        hp_net_proceeds=hp_cfg.get("estimated_net_proceeds", 0),
        hp_piti_low=hp_cfg.get("new_payment_piti_low", 0),
        hp_piti_high=hp_cfg.get("new_payment_piti_high", 0),
        hp_savings_goal=hp_savings_data.get("goal", 500),
        hp_combined_target=hp_savings_data.get("combined_target", 0),
        hp_spending=hp_spending_data,
        hp_spend_months=hp_spend_month_labels,
        hp_savings_months=hp_savings_data.get("months", []),
        hp_cumulative_saved=hp_savings_data.get("cumulative_saved", 0),
        hp_cumulative_goal=hp_savings_data.get("cumulative_goal", 0),
        hp_milestones=hp_milestones_data,
        hp_dti=type("DTI", (), hp_dti_data)() if hp_dti_data else None,
    )
    out = OUT / "report.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")
