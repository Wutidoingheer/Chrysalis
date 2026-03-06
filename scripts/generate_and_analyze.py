"""
Complete workflow: Generate report and analyze with ChatGPT.

This script:
1. Fetches fresh data from Monarch Money
2. Generates the financial report
3. Sends it to ChatGPT for analysis
4. Saves everything

Run this monthly via Task Scheduler.
"""
import subprocess
import sys
from pathlib import Path

def main():
    """Run the complete workflow."""
    base_dir = Path(__file__).parent.parent
    
    print("=" * 60)
    print("MONTHLY FINANCIAL REPORT GENERATION & ANALYSIS")
    print("=" * 60)
    
    # Step 1: Fetch data
    print("\n[Step 1] Fetching data from Monarch Money...")
    try:
        result = subprocess.run(
            [sys.executable, str(base_dir / "src" / "ingest" / "fetch_monarch_api.py")],
            cwd=str(base_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[ERROR] Error fetching data: {result.stderr}")
            return
        print("[OK] Data fetched successfully")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return
    
    # Step 2: Generate report
    print("\n[Step 2] Generating financial report...")
    try:
        import os
        env = os.environ.copy()
        env['PYTHONPATH'] = str(base_dir)
        result = subprocess.run(
            [sys.executable, str(base_dir / "src" / "reports" / "generate_report.py")],
            cwd=str(base_dir),
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[ERROR] Error generating report: {result.stderr}")
            return
        print("[OK] Report generated successfully")
        
        # Verify report was just created/updated
        report_path = base_dir / "data" / "outputs" / "report.html"
        if report_path.exists():
            import time
            report_age = time.time() - report_path.stat().st_mtime
            if report_age > 60:  # More than 1 minute old
                print(f"[WARN] Report appears to be {report_age:.1f} seconds old - may not be fresh")
            else:
                print(f"[OK] Report is fresh ({report_age:.1f} seconds old)")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return
    
    # Step 3: Export data for browser analysis
    print("\n[Step 3] Exporting data for browser analysis...")
    try:
        result = subprocess.run(
            [sys.executable, str(base_dir / "scripts" / "export_for_browser_analysis.py")],
            cwd=str(base_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[WARN] Export failed: {result.stderr}")
        else:
            print("[OK] Data exported for browser analysis")
            print(f"     Open browser_analysis/index.html and load the JSON file")
    except Exception as e:
        print(f"[WARN] Export error: {e}")
    
    # Step 4: Analyze with ChatGPT (optional - requires OPENAI_API_KEY)
    print("\n[Step 4] Analyzing report with ChatGPT...")
    import os
    if os.getenv("OPENAI_API_KEY"):
        try:
            # Small delay to ensure file system has updated
            import time
            time.sleep(1)
            
            result = subprocess.run(
                [sys.executable, str(base_dir / "scripts" / "analyze_report_with_chatgpt.py")],
                cwd=str(base_dir),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[WARN] ChatGPT analysis failed: {result.stderr}")
                print("Report generated but ChatGPT analysis skipped.")
            else:
                print("[OK] ChatGPT analysis complete")
                
                # Create visualization if analysis succeeded
                print("\n[Step 5] Creating HTML visualization...")
                try:
                    result = subprocess.run(
                        [sys.executable, str(base_dir / "scripts" / "visualize_analysis.py")],
                        cwd=str(base_dir),
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        print(f"[WARN] Visualization failed: {result.stderr}")
                    else:
                        print("[OK] Visualization created")
                except Exception as e:
                    print(f"[WARN] Visualization error: {e}")
        except Exception as e:
            print(f"[WARN] ChatGPT analysis error: {e}")
            print("Report generated but ChatGPT analysis skipped.")
    else:
        print("[INFO] OPENAI_API_KEY not set - skipping ChatGPT analysis")
        print("       Set OPENAI_API_KEY in .env to enable ChatGPT analysis")
    
    # Step 6: Create dashboard (always, even if analysis failed)
    print("\n[Step 6] Creating dashboard...")
    try:
        result = subprocess.run(
            [sys.executable, str(base_dir / "scripts" / "create_dashboard.py")],
            cwd=str(base_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[WARN] Dashboard creation failed: {result.stderr}")
        else:
            print("[OK] Dashboard created")
    except Exception as e:
        print(f"[WARN] Dashboard error: {e}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] MONTHLY REPORT COMPLETE")
    print("=" * 60)
    print(f"\nReport: {base_dir / 'data' / 'outputs' / 'report.html'}")
    print(f"Analysis: {base_dir / 'data' / 'outputs' / 'chatgpt_analysis.txt'}")
    print(f"Dashboard: {base_dir / 'data' / 'outputs' / 'dashboard.html'}")

if __name__ == "__main__":
    main()

