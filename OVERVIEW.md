# Finance API - Project Overview & Functionality Check

## Executive Summary

This project (`financeApi`) is a financial data management system that integrates with Monarch Money to fetch, transform, and analyze financial data, generating comprehensive HTML reports. The project uses a forked version of the `monarchmoney` library (`monarchmoney-fork`) for API interactions.

## Project Structure

```
financeApi/
├── config/              # Configuration files (accounts, categories, limits)
├── data/
│   ├── raw/            # Raw data from Monarch Money API
│   └── outputs/        # Generated reports (HTML)
├── scripts/            # Utility scripts (login helper)
├── src/
│   ├── analytics/      # Financial analysis modules
│   ├── api/            # (Empty - potential API endpoints)
│   ├── ingest/         # Data fetching from Monarch Money
│   ├── reports/        # Report generation
│   └── transform/      # Data normalization
└── tests/              # Test files
```

## Core Functionality

### 1. Data Ingestion (`src/ingest/`)

**`fetch_monarch_api.py`** - Primary data fetcher using the monarchmoney library
- ✅ Uses `MonarchMoney` client from monarchmoney-fork
- ✅ Supports session cookie or email/password authentication
- ✅ Fetches accounts and transactions
- ✅ Handles pagination for transactions
- ⚠️ **Issue**: Directly sets `mm.session` instead of using `load_session()` method
- ⚠️ **Issue**: Uses `asyncio.run()` multiple times (should reuse event loop)

**`fetch_monarch_graphql.py`** - Alternative GraphQL-based fetcher
- ✅ Direct GraphQL queries to Monarch Money API
- ✅ Requires manual token management
- ✅ Fallback option if library has issues

**`fetch_csv.py`** - CSV loader utility
- ✅ Loads transaction data from CSV files
- ✅ Normalizes column names

### 2. Data Transformation (`src/transform/`)

**`normalize_data.py`** - ⚠️ **EMPTY FILE**
- Should normalize data from different sources into common format
- **Action Required**: Implement normalization logic

### 3. Analytics (`src/analytics/`)

**`cashflow_summary.py`** - ⚠️ **EMPTY FILE**
- Should provide cash flow analysis
- **Action Required**: Implement cash flow calculations

**`debt_payoff.py`** - ⚠️ **EMPTY FILE**
- Should calculate debt payoff schedules
- **Action Required**: Implement debt payoff logic (currently in `generate_report.py`)

**`utilization.py`** - ✅ **IMPLEMENTED**
- Calculates credit utilization by account
- Computes overall utilization percentage
- Works correctly

### 4. Report Generation (`src/reports/`)

**`generate_report.py`** - ✅ **FULLY IMPLEMENTED**
- Generates comprehensive HTML financial reports
- Includes:
  - Monthly cash flow analysis
  - Category spending summary
  - Debt payoff calculations
  - Recent transactions
  - Credit utilization analysis
- Uses Jinja2 templates for HTML generation
- Loads data from JSON or CSV sources

## Integration with monarchmoney-fork

### Current Status

✅ **Working:**
- Import statement: `from monarchmoney import MonarchMoney` is correct
- Library provides all needed methods:
  - `get_accounts()` - ✅ Available
  - `get_transactions()` - ✅ Available with pagination support
  - `interactive_login()` - ✅ Available
  - `save_session()` / `load_session()` - ✅ Available

⚠️ **Issues Found:**

1. **Dependency Configuration**
   - `requirements.txt` points to: `monarchmoney @ git+https://github.com/keithah/monarchmoney.git`
   - You have a local fork at `../monarchmoney-fork/`
   - **Recommendation**: Use local path for development:
     ```
     monarchmoney @ file:///${PROJECT_ROOT}/../monarchmoney-fork
     ```
     Or install in editable mode: `pip install -e ../monarchmoney-fork`

2. **Session Handling in `fetch_monarch_api.py`**
   - Line 29: `mm.session = session_cookie` - This bypasses proper session loading
   - Should use: `mm.load_session()` method instead
   - The library has proper session management with encryption

3. **Async/Await Usage**
   - Multiple `asyncio.run()` calls can cause issues
   - Should wrap in single async function or use proper event loop management

## Configuration Files

### `config/limits.yml`
- ✅ Defines credit limits for accounts
- Used by utilization calculations

### `config/accounts.yml`
- ⚠️ **EMPTY FILE**
- Should contain account mappings/configuration

### `config/categories.yml`
- Exists but not reviewed (may contain category mappings)

## Missing Functionality

1. **Empty Implementation Files:**
   - `src/transform/normalize_data.py`
   - `src/analytics/cashflow_summary.py`
   - `src/analytics/debt_payoff.py`
   - `config/accounts.yml`

2. **API Endpoints (`src/api/`):**
   - Directory exists but is empty
   - Could implement REST API or CLI interface

3. **Error Handling:**
   - Limited error handling in fetch scripts
   - No retry logic for failed API calls
   - No validation of data before processing

4. **Testing:**
   - Only `test_transform.py` exists (appears empty)
   - No tests for ingestion, analytics, or reports

## Recommendations

### High Priority

1. **Fix Session Handling**
   ```python
   # In fetch_monarch_api.py, replace:
   if session_cookie:
       mm.session = session_cookie
   
   # With:
   if session_cookie:
       # Save session cookie to file first, then load
       session_file = Path("./data/.monarch_session.json")
       session_file.write_text(json.dumps({"session": session_cookie}))
       mm.load_session(str(session_file))
   ```

2. **Use Local Fork for Development**
   - Update `requirements.txt` to use local path
   - Or install fork in editable mode

3. **Improve Async Handling**
   - Wrap all async calls in single async function
   - Use proper event loop management

### Medium Priority

4. **Implement Missing Analytics**
   - Move debt payoff logic from `generate_report.py` to `debt_payoff.py`
   - Implement cash flow summary module
   - Create normalization module

5. **Add Error Handling**
   - Try/catch blocks around API calls
   - Retry logic with exponential backoff
   - Data validation before processing

6. **Create API/CLI Interface**
   - Add command-line interface for running reports
   - Or REST API endpoints for programmatic access

### Low Priority

7. **Add Tests**
   - Unit tests for analytics functions
   - Integration tests for data fetching
   - Report generation tests

8. **Documentation**
   - Add docstrings to all functions
   - Create usage examples
   - Document configuration options

## Testing the Integration

To verify everything works:

1. **Install Dependencies:**
   ```bash
   cd financeApi
   pip install -e ../monarchmoney-fork  # Install local fork
   pip install -r requirements.txt
   ```

2. **Set Up Authentication:**
   ```bash
   python scripts/monarch_login_once.py
   # This will prompt for credentials and save session
   ```

3. **Fetch Data:**
   ```bash
   python src/ingest/fetch_monarch_api.py
   # Or set environment variables:
   # MONARCH_EMAIL=your@email.com
   # MONARCH_PASSWORD=yourpassword
   # MONARCH_SINCE_DAYS=365
   ```

4. **Generate Report:**
   ```bash
   python src/reports/generate_report.py
   # Output: data/outputs/report.html
   ```

## Summary

**Status: 🟡 Partially Functional**

The project has a solid foundation with:
- ✅ Working report generation
- ✅ Credit utilization analytics
- ✅ Data ingestion from Monarch Money
- ✅ Integration with monarchmoney-fork library

However, several improvements are needed:
- ⚠️ Fix session handling
- ⚠️ Implement missing analytics modules
- ⚠️ Improve error handling
- ⚠️ Use local fork properly

The core functionality works, but the codebase needs completion and refinement for production use.


