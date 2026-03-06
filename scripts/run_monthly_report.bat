@echo off
REM Monthly Financial Report Batch Script
REM This script runs the complete monthly report generation and analysis

cd /d "%~dp0\.."

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

python scripts\generate_and_analyze.py >> logs\monthly_report.log 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Monthly report completed successfully at %DATE% %TIME% >> logs\monthly_report.log
    echo.
    echo ========================================
    echo MONTHLY REPORT COMPLETE!
    echo ========================================
    echo.
    echo Dashboard available at: data\outputs\dashboard.html
    echo Browser analysis available at: browser_analysis\index.html
    echo Import file: data\outputs\financial_data_for_analysis.json
) else (
    echo Monthly report failed at %DATE% %TIME% >> logs\monthly_report.log
    echo.
    echo ========================================
    echo REPORT GENERATION FAILED
    echo ========================================
    echo Check logs\monthly_report.log for details
    pause
)

