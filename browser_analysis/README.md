# Browser-Based Financial Analysis

This is a standalone browser-based tool for granular transaction-level analysis and debt paydown planning.

## Features

- **Transaction-Level Analysis**: See every transaction and decide which ones to cut
- **Direct Debt Impact**: See exactly how cutting specific transactions affects your debt paydown
- **Avalanche Method**: Automatically calculates the best debt paydown strategy
- **Real-Time Calculations**: See interest savings and time saved as you adjust cuts
- **No API Required**: Runs entirely in your browser - no OpenAI API needed

## How to Use

1. **Generate the Data Export**:
   ```powershell
   python scripts/export_for_browser_analysis.py
   ```
   This creates `data/outputs/financial_data_for_analysis.json`

2. **Open the Analysis Tool**:
   - Open `browser_analysis/index.html` in your web browser
   - Or use the local server: `python scripts/start_local_server.py` and navigate to `browser_analysis/index.html`

3. **Load Your Data**:
   - Click "Choose File" and select `data/outputs/financial_data_for_analysis.json`

4. **Analyze Transactions**:
   - Review all current month credit card transactions
   - Click on transactions to select them
   - Enter how much you can cut from each transaction
   - See real-time impact on debt paydown

5. **View Impact**:
   - The "Debt Paydown Impact Preview" shows:
     - Total monthly cuts
     - Interest saved for each debt
     - Time saved (months)
     - Recommended strategy (Avalanche method)

## What It Shows

- **YTD Summary**: Income, expenses, and net flow
- **Debt Overview**: All debts with balances, APRs, payments, and payoff timelines
- **Current Month Transactions**: All credit card transactions with ability to mark cuts
- **Impact Preview**: Real-time calculation of how cuts affect debt paydown

## Granular Analysis

For each transaction, you can:
- See the exact amount
- Enter how much you can cut (up to the transaction amount)
- See immediate impact on:
  - Months to payoff
  - Total interest saved
  - Which debt benefits most (Avalanche method)

## Strategy

The tool uses the **Avalanche Method** by default:
- All cuts are applied to the highest APR debt first
- This maximizes interest savings
- Shows you exactly how much time and money you'll save

## Standalone Project

This is a completely standalone project:
- No dependencies
- No API keys required
- Works offline
- All calculations done in your browser
- Your data never leaves your computer



