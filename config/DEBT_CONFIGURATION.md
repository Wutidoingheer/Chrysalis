# Debt Configuration Guide

## What's Pulled Live from Monarch Money

✅ **Balances** - Automatically pulled from `accounts.json` for all credit card accounts
✅ **Account Names** - Full display names from Monarch Money
✅ **Account Types** - Automatically identifies credit cards (type: "credit" or subtype: "credit_card")

## What Needs Configuration

⚠️ **APR (Annual Percentage Rate)** - Must be set in `config/debts.yml` or `generate_report.py`
⚠️ **Monthly Payment** - Must be set in `config/debts.yml` or `generate_report.py`

## How to Configure APR and Payments

### Option 1: Edit `config/debts.yml`

```yaml
debts:
  Amex:
    apr: 22.0
    payment: 2000.0
  
  Delta:
    apr: 20.0
    payment: 500.0
```

The system matches account names (case-insensitive partial match). For example:
- "Delta SkyMiles® Platinum Card" matches "Delta"
- "Costco Anywhere Visa Card by Citi" matches "Costco" or "Citi"

### Option 2: Edit `src/reports/generate_report.py`

Find the `DEBT_CONFIG` dictionary and add/update entries.

## Current Live Debts Found

The system automatically finds all credit card accounts from Monarch Money. Check the report to see which ones were detected.

## Defaults

If an account isn't found in the config:
- **APR**: Defaults to 20.0%
- **Payment**: Defaults to 2% of balance (minimum payment estimate)

## Verification

After running the report, check:
1. `data/outputs/report.html` - Debt Payoff section shows all detected debts
2. `data/outputs/financial_data_for_analysis.json` - Contains the same debt data for browser analysis



