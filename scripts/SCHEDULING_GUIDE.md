# Scheduling Monthly Financial Reports

This guide shows how to automatically run your financial report generation and ChatGPT analysis once per month.

## Option 1: Windows Task Scheduler (Recommended for Windows)

### Step 1: Create a Batch File

Create `chrysalis/scripts/run_monthly_report.bat`:

```batch
@echo off
cd /d "C:\path\to\chrysalis"
python scripts\generate_and_analyze.py >> logs\monthly_report.log 2>&1
```

### Step 2: Set Up Task Scheduler

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Click "Create Basic Task" in the right panel
   - Name: "Monthly Financial Report"
   - Description: "Generate and analyze financial report from Monarch Money"

3. **Set Trigger**:
   - Trigger: Monthly
   - Start date: First day of next month
   - Time: 9:00 AM (or your preferred time)
   - Recur every: 1 month
   - On day: 1 (first of the month)

4. **Set Action**:
   - Action: Start a program
   - Program/script: `C:\path\to\chrysalis\scripts\run_monthly_report.bat`
   - Start in: `C:\path\to\chrysalis`

5. **Finish**:
   - Check "Open the Properties dialog..." and click Finish
   - In Properties:
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges"
     - Configure for: Windows 10

### Step 3: Test

Right-click the task and select "Run" to test it.

---

## Option 2: Python Schedule Library (Runs while computer is on)

### Install schedule library:
```bash
pip install schedule
```

### Create `financeApi/scripts/scheduler.py`:

```python
import schedule
import time
import subprocess
import sys
from pathlib import Path

def run_monthly_report():
    """Run the monthly report generation."""
    base_dir = Path(__file__).parent.parent
    subprocess.run([sys.executable, str(base_dir / "scripts" / "generate_and_analyze.py")])

# Schedule for 1st of every month at 9 AM
schedule.every().month.do(run_monthly_report)

# Or schedule for specific day each month:
# schedule.every().month.at("09:00").do(run_monthly_report)

print("Scheduler started. Will run monthly report on the 1st of each month at 9 AM.")
print("Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

### Run the scheduler:
```bash
python scripts/scheduler.py
```

**Note**: This requires your computer to be on and the script running.

---

## Option 3: Cloud Scheduler (Always runs, even if computer is off)

### GitHub Actions (Free)

Create `.github/workflows/monthly-report.yml`:

```yaml
name: Monthly Financial Report

on:
  schedule:
    - cron: '0 9 1 * *'  # 9 AM on the 1st of every month
  workflow_dispatch:  # Allow manual trigger

jobs:
  generate-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e ../monarchmoney-fork
          pip install -r requirements.txt
          pip install openai
      
      - name: Configure environment
        env:
          MONARCH_AUTHORIZATION: ${{ secrets.MONARCH_AUTHORIZATION }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          echo "MONARCH_AUTHORIZATION=$MONARCH_AUTHORIZATION" >> .env
          echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
      
      - name: Generate and analyze report
        run: python scripts/generate_and_analyze.py
      
      - name: Upload report artifacts
        uses: actions/upload-artifact@v2
        with:
          name: financial-report
          path: data/outputs/
```

**Note**: Requires storing secrets in GitHub repository settings.

### AWS Lambda / Google Cloud Functions

For cloud-based scheduling, you can deploy the script to serverless functions that run on a schedule.

---

## Option 4: Cron (Linux/Mac)

If you have WSL or a Linux server:

```bash
# Edit crontab
crontab -e

# Add this line (runs 1st of every month at 9 AM):
0 9 1 * * cd /path/to/financeApi && python scripts/generate_and_analyze.py >> logs/monthly_report.log 2>&1
```

---

## Recommended: Windows Task Scheduler

For Windows users, **Option 1 (Task Scheduler)** is the best choice because:
- ✅ Runs automatically even if you're not logged in
- ✅ No need to keep scripts running
- ✅ Built into Windows
- ✅ Reliable and tested

---

## Setup Checklist

- [ ] Add `OPENAI_API_KEY` to `.env` file
- [ ] Test `python scripts/generate_and_analyze.py` manually
- [ ] Create batch file for Task Scheduler
- [ ] Set up Task Scheduler task
- [ ] Test the scheduled task
- [ ] Verify report and analysis are generated

---

## Troubleshooting

**Task doesn't run:**
- Check Task Scheduler history for errors
- Verify Python path is correct in batch file
- Check that `.env` file is accessible
- Ensure all dependencies are installed

**ChatGPT analysis fails:**
- Verify `OPENAI_API_KEY` is set correctly
- Check you have API credits
- Review error logs in `logs/monthly_report.log`

**Report is empty:**
- Check that session token is still valid
- Re-run `python scripts/monarch_use_token.py` if needed
- Verify Monarch Money API is accessible

