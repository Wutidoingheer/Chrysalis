# Chrysalis

A personal finance reporting toolkit built on [Monarch Money](https://www.monarchmoney.com/). Fetches your accounts and transactions via the Monarch Money API, runs analytics, and generates HTML reports — including cash flow summaries, debt payoff projections, and credit utilization.

> Raw data goes in. Insight comes out.

## Features

- **Data ingestion** — pulls accounts and transactions from Monarch Money (API or GraphQL)
- **Debt payoff analysis** — tracks APR, payments, and payoff timelines per card
- **Credit utilization** — calculates utilization by account and overall
- **HTML reports** — Jinja2-templated monthly reports with spending breakdowns
- **OpenAI integration** — optional GPT analysis of monthly reports
- **Scheduling** — run automatically via Windows Task Scheduler or cron

## Requirements

- Python 3.10+
- A [Monarch Money](https://www.monarchmoney.com/) account
- [monarchmoney](https://github.com/Wutidoingheer/monarchmoney) library (see below)
- Optional: OpenAI API key for report analysis

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Wutidoingheer/Chrysalis.git
cd Chrysalis
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
MONARCH_EMAIL=your_email@example.com
MONARCH_PASSWORD=your_password_here
MONARCH_SINCE_DAYS=365
OPENAI_API_KEY=your_openai_api_key_here  # optional
```

### 3. Authenticate with Monarch Money

```bash
python scripts/monarch_login_once.py
```

This saves an encrypted session so you don't need to log in each run.

### 4. Fetch data and generate a report

```bash
python src/ingest/fetch_monarch_api.py
python src/reports/generate_report.py
```

Report output: `data/outputs/report.html`

## Configuration

| File | Purpose |
|---|---|
| `config/debts.yml` | Credit card APRs, limits, and monthly payments |
| `config/categories.yml` | Spending category mappings |
| `config/limits.yml` | Credit limit overrides |

## Scheduling

See [scripts/SCHEDULING_GUIDE.md](scripts/SCHEDULING_GUIDE.md) for instructions on automating monthly reports via Windows Task Scheduler, cron, or GitHub Actions.

## Project Structure

```
Chrysalis/
├── config/          # Account, category, and debt configuration
├── src/
│   ├── ingest/      # Monarch Money data fetching
│   ├── transform/   # Data normalization
│   ├── analytics/   # Cash flow, debt payoff, utilization
│   └── reports/     # HTML report generation
├── scripts/         # Login helpers, scheduling, analysis tools
├── browser_analysis/ # Client-side analysis tool
└── tests/
```

## Dependencies

This project uses a fork of the [`monarchmoney`](https://github.com/keithah/monarchmoney) Python library (originally by [@keithah](https://github.com/keithah)) with additional features and performance improvements:
[github.com/Wutidoingheer/monarchmoney](https://github.com/Wutidoingheer/monarchmoney)

## License

MIT
