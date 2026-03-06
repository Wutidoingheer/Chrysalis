@echo off
REM Start local web server for financial reports
REM This allows easy access to all reports via http://localhost:8080

cd /d "%~dp0\.."
python scripts\start_local_server.py



