# PowerShell script to check Task Scheduler status
# Run this to verify your monthly financial report task

$separator = "=" * 60
Write-Host $separator
Write-Host "TASK SCHEDULER STATUS CHECK"
Write-Host $separator
Write-Host ""

# Find the task
$taskName = "Monthly Financial Report"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    Write-Host "Task Found: $taskName" -ForegroundColor Green
    Write-Host ""
    
    # Get task info
    $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
    Write-Host "Task Status: $($task.State)"
    Write-Host "Last Run Time: $($taskInfo.LastRunTime)"
    
    if ($taskInfo.LastTaskResult -eq 0) {
        Write-Host "Last Result: SUCCESS (0)" -ForegroundColor Green
    } else {
        Write-Host "Last Result: FAILED ($($taskInfo.LastTaskResult))" -ForegroundColor Red
    }
    
    Write-Host "Next Run Time: $($taskInfo.NextRunTime)"
    Write-Host ""
    
    # Check log file
    $logPath = "logs\monthly_report.log"
    if (Test-Path $logPath) {
        Write-Host "Recent Log Entries:" -ForegroundColor Cyan
        $logContent = Get-Content $logPath -Tail 30 -ErrorAction SilentlyContinue
        if ($logContent) {
            Write-Host $logContent
        } else {
            Write-Host "  (Log file is empty)"
        }
    } else {
        Write-Host "No log file found yet" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Output Files (sorted by date):" -ForegroundColor Cyan
    $outputFiles = Get-ChildItem "data\outputs\*.html" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($outputFiles) {
        foreach ($file in $outputFiles | Select-Object -First 5) {
            $age = (Get-Date) - $file.LastWriteTime
            if ($age.TotalHours -lt 24) {
                Write-Host "  $($file.Name) - $($file.LastWriteTime) (recent)" -ForegroundColor Green
            } else {
                Write-Host "  $($file.Name) - $($file.LastWriteTime) (old)" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  No output files found"
    }
    
    # Check for analysis file
    $analysisFile = "data\outputs\chatgpt_analysis.txt"
    if (Test-Path $analysisFile) {
        $analysisAge = (Get-Date) - (Get-Item $analysisFile).LastWriteTime
        if ($analysisAge.TotalHours -lt 24) {
            Write-Host ""
            Write-Host "  ChatGPT Analysis found (recent)" -ForegroundColor Green
        }
    }
    
} else {
    Write-Host "Task not found: $taskName" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available tasks with Financial or Report in name:"
    Get-ScheduledTask | Where-Object { $_.TaskName -like "*Financial*" -or $_.TaskName -like "*Report*" } | Select-Object TaskName, State
}

Write-Host ""
Write-Host $separator
Write-Host "To view detailed Task Scheduler history:"
Write-Host "1. Open Task Scheduler (Win+R, type taskschd.msc)"
Write-Host "2. Find Monthly Financial Report in the task list"
Write-Host "3. Click on History tab to see execution details"
Write-Host ""
Write-Host "To manually run the task:"
Write-Host "  Right-click the task and select Run"
Write-Host $separator
