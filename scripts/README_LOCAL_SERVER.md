# Local Web Server for Financial Reports

This guide explains how to host your financial reports locally for easy access.

## Quick Start

### Option 1: Start Server Manually

Run the server script:
```powershell
python scripts\start_local_server.py
```

Or use the batch file:
```powershell
scripts\start_server.bat
```

The server will:
- Start on `http://localhost:8080`
- Automatically open the dashboard in your browser
- Serve all reports from `data/outputs/`

### Option 2: Auto-Open After Report Generation

The monthly report script (`run_monthly_report.bat`) automatically opens the dashboard after completion. No server needed - it just opens the HTML file directly.

## Accessing Reports

Once the server is running, you can access:

- **Dashboard**: http://localhost:8080/dashboard.html
- **Financial Report**: http://localhost:8080/report.html
- **AI Analysis Visualization**: http://localhost:8080/analysis_visualization.html
- **Raw Analysis Text**: http://localhost:8080/chatgpt_analysis.txt

## Server Features

- **Auto-opens browser**: Opens dashboard automatically when started
- **Port flexibility**: If port 8080 is busy, tries 8081, 8082, etc.
- **No caching**: Reports always show latest data
- **Easy to stop**: Press `Ctrl+C` to stop the server

## Scheduled Task Integration

When the scheduled task runs (`run_monthly_report.bat`), it will:
1. Generate all reports
2. Automatically open the dashboard in your browser
3. You can then start the server manually if you want to browse reports via URL

## Manual Server Start

If you want to start the server separately:

```powershell
# Start server (will open browser automatically)
python scripts\start_local_server.py

# Start server without opening browser
python scripts\start_local_server.py --no-browser

# Use a different port
python scripts\start_local_server.py --port 9000
```

## Troubleshooting

**Port already in use?**
- The server will automatically try the next port (8081, 8082, etc.)
- Or specify a different port: `python scripts\start_local_server.py --port 9000`

**Browser doesn't open?**
- Manually navigate to http://localhost:8080/dashboard.html
- Or open `data\outputs\dashboard.html` directly in your browser

**Reports not updating?**
- The server serves files directly from disk, so refresh your browser
- Make sure the report generation completed successfully



