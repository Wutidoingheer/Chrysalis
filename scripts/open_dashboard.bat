@echo off
REM Open the financial dashboard in browser
REM This can be called after the monthly report runs

cd /d "%~dp0\.."

REM Check if dashboard exists
if exist "data\outputs\dashboard.html" (
    echo Opening dashboard...
    start "" "data\outputs\dashboard.html"
) else (
    echo Dashboard not found. Generating...
    python scripts\create_dashboard.py
    if exist "data\outputs\dashboard.html" (
        start "" "data\outputs\dashboard.html"
    ) else (
        echo Error: Could not create dashboard
        pause
    )
)



