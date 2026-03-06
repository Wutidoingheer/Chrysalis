"""
Script to send the financial report to ChatGPT for analysis.

This script:
1. Reads the generated HTML report
2. Converts it to a readable format
3. Sends it to ChatGPT API for analysis
4. Saves the analysis to a file

Requirements:
- Set OPENAI_API_KEY in .env file
- Install openai package: pip install openai
"""
import os
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv
from html.parser import HTMLParser
import re

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI package not installed. Install with: pip install openai")

class HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style'}
        self.in_skip = False
        
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.in_skip = True
        elif tag == 'br':
            self.text.append('\n')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text.append('\n\n')
        elif tag in ('tr', 'td', 'th'):
            self.text.append(' | ')
        elif tag == 'table':
            self.text.append('\n')
            
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section'):
            self.text.append('\n')
        elif tag == 'tr':
            self.text.append('\n')
        elif tag == 'table':
            self.text.append('\n')
            
    def handle_data(self, data):
        if not self.in_skip:
            cleaned = data.strip()
            if cleaned:
                self.text.append(cleaned)
    
    def get_text(self):
        text = ''.join(self.text)
        # Clean up multiple spaces and newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

def extract_text_from_html(html_path: Path) -> str:
    """Extract readable text from HTML report."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    parser = HTMLTextExtractor()
    parser.feed(html_content)
    text = parser.get_text()
    
    # Add a header with report timestamp to help ChatGPT know it's fresh data
    report_mtime = os.path.getmtime(html_path)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report_mtime))
    
    header = f"=== FINANCIAL REPORT (Generated: {timestamp}) ===\n\n"
    return header + text

async def analyze_with_chatgpt(report_text: str, api_key: str) -> str:
    """Send report to ChatGPT for analysis with retry logic."""
    import time
    from openai import RateLimitError, APIError
    
    client = OpenAI(api_key=api_key)
    
    # Truncate report if too long (to avoid token limits and reduce costs)
    # Increased limit to capture more data, especially income and spending sections
    max_report_length = 15000  # characters (increased from 8000)
    original_length = len(report_text)
    if len(report_text) > max_report_length:
        print(f"[WARN] Report is {len(report_text)} characters, truncating to {max_report_length}...")
        # Try to keep important sections - prioritize income and spending data
        # Keep the first part (usually has summary) and try to keep income/spending sections
        if "USAA Bank Income" in report_text and "Spending by Card" in report_text:
            # Find key sections
            income_start = report_text.find("USAA Bank Income")
            spending_start = report_text.find("Spending by Card")
            
            # Keep beginning + income section + spending section
            if income_start > 0 and spending_start > income_start:
                # Keep first 3000 chars, then income section, then spending section
                beginning = report_text[:3000]
                income_section = report_text[income_start:spending_start + 5000]
                spending_section = report_text[spending_start:spending_start + 5000]
                report_text = beginning + "\n\n[... middle section truncated ...]\n\n" + income_section + "\n\n" + spending_section
                if len(report_text) > max_report_length:
                    report_text = report_text[:max_report_length] + "\n\n[... report truncated ...]"
            else:
                report_text = report_text[:max_report_length] + "\n\n[... report truncated ...]"
        else:
            report_text = report_text[:max_report_length] + "\n\n[... report truncated ...]"
        print(f"[INFO] Truncated from {original_length} to {len(report_text)} characters")
    
    prompt = """You are a pragmatic financial advisor analyzing a personal finance report. Your analysis must be deep, data-driven, and actionable.

**CRITICAL FOCUS AREAS:**

1. **Trend Analysis & Progress Evaluation**:
   - Analyze the USAA account summary: YTD income, expenses, net flow, previous month vs current month
   - Calculate the "Amount Paid Down" - is progress being made month-over-month?
   - Identify trends: Is spending increasing or decreasing? Is income consistent?
   - Evaluate effectiveness: "Your previous month total was $X, current month is $Y. This represents [progress/regression] of $Z."
   - Compare month-over-month changes: "You paid down $X more this month compared to last month" or "You're spending $Y more this month"
   - Look at cash flow trends over multiple months to identify patterns

2. **Debt Paydown Strategy & Effectiveness**:
   - Analyze current debt situation (balances, APRs, current payments, months to payoff)
   - Review recent payment history: Are minimum payments being made? Any extra payments?
   - Calculate actual progress: "Based on your current payment of $X/month, you're on track to pay off [debt] in Y months"
   - Evaluate strategy effectiveness: "Your current approach is [working/not working] because..."
   - Recommend specific adjustments: "To accelerate payoff, increase [debt] payment by $X/month"
   - Show impact of changes: "If you increase payment by $X, you'll save $Y in interest and pay off Z months faster"
   - Compare different strategies: Avalanche vs Snowball with actual numbers

3. **Income & Expense Deep Dive**:
   - Analyze YTD income: Is it consistent? Any patterns or anomalies?
   - Analyze YTD expenses: What percentage of income is going to expenses?
   - Calculate expense ratios: "Your expenses are X% of your income"
   - Identify expense trends: Which categories are growing? Which are shrinking?
   - Review upcoming income: Plan expenses around expected income
   - Calculate available funds: "With $X income and $Y expenses, you have $Z available for debt paydown"

4. **Actionable Recommendations Based on Trends**:
   - If progress is being made: "You're on the right track. To accelerate, consider..."
   - If progress is stalled: "Your spending increased $X this month. To get back on track..."
   - If regressing: "You're spending $X more than last month. Critical areas to address..."
   - Provide specific, measurable goals: "Aim to reduce [category] by $X/month to free up $Y for debt"

**TONE**: Be hard-nosed and direct about the numbers and consequences, but not Dave Ramsey-style extreme. Acknowledge that life happens, but emphasize the real cost of carrying debt and the opportunity cost of unnecessary spending. Use data-driven arguments with specific numbers from the report.

**OUTPUT FORMAT**:
1. **Progress Assessment**: Start with a clear evaluation of month-over-month progress
2. **Trend Analysis**: Show income/expense trends and what they mean
3. **Debt Strategy Evaluation**: Analyze current approach and recommend improvements
4. **Specific Action Plan**: End with concrete, measurable steps

Here is the financial report:

""" + report_text
    
    print("Sending report to ChatGPT for analysis...")
    
    # Retry logic for rate limits
    max_retries = 3
    retry_delay = 60  # Start with 60 seconds
    
    for attempt in range(max_retries):
        try:
            # Try more capable models first for deeper analysis
            # Cost: gpt-4o-mini ~$0.001, gpt-4o ~$0.01-0.03, gpt-4-turbo ~$0.03-0.06 per analysis
            models_to_try = ["gpt-4o", "gpt-4o-mini"]
            if attempt > 0:
                # On retry, fall back to cheaper models
                models_to_try = ["gpt-4o-mini", "gpt-3.5-turbo"]
            
            last_error = None
            for model in models_to_try:
                try:
                    print(f"  Trying model: {model}...")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a pragmatic, data-driven financial advisor. You focus on debt paydown strategies, expense optimization, and cash flow planning. You're direct and honest about the numbers and consequences, but not preachy or extreme. You acknowledge that people need some flexibility while emphasizing the real cost of debt and the opportunity cost of unnecessary spending. You provide specific, actionable recommendations with concrete numbers and timelines."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.7,
                        max_tokens=3000
                    )
                    
                    analysis = response.choices[0].message.content
                    print(f"[OK] Analysis received using {model}")
                    return analysis
                    
                except RateLimitError as e:
                    last_error = e
                    if "gpt-4" in model.lower():
                        # If gpt-4 is rate limited, try cheaper model
                        print(f"  [WARN] Rate limited on {model}, trying alternative...")
                        continue
                    else:
                        raise
                except APIError as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        last_error = e
                        if "gpt-4" in model.lower():
                            print(f"  [WARN] Rate limited on {model}, trying alternative...")
                            continue
                        else:
                            raise
                    else:
                        raise
            
            # If all models failed with rate limit, raise the last error
            if last_error:
                raise last_error
                
        except (RateLimitError, APIError) as e:
            error_str = str(e).lower()
            if "429" in str(e) or "rate limit" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    print(f"[WARN] Rate limit hit. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limit error after {max_retries} attempts. Please try again later or upgrade your OpenAI plan.")
            elif "quota" in error_str or "insufficient_quota" in error_str or "billing" in error_str:
                raise Exception(
                    "[ERROR] OpenAI API quota exceeded or no billing set up.\n"
                    "Please:\n"
                    "1. Go to https://platform.openai.com/account/billing\n"
                    "2. Add a payment method\n"
                    "3. Add credits to your account\n\n"
                    "Estimated cost: ~$0.01-0.05 per analysis (see script comments for details)"
                )
            else:
                raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")
    
    raise Exception("Failed to get analysis after all retries")

def main():
    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in .env file")
        print("\nTo use this script:")
        print("1. Get an API key from https://platform.openai.com/api-keys")
        print("2. Add to .env file:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        return
    
    if not OPENAI_AVAILABLE:
        print("\nPlease install OpenAI package:")
        print("  pip install openai")
        return
    
    # Find the report file
    report_path = Path(__file__).parent.parent / "data" / "outputs" / "report.html"
    
    if not report_path.exists():
        print(f"[ERROR] Report not found at {report_path}")
        print("\nPlease generate the report first:")
        print("  python src/reports/generate_report.py")
        return
    
    # Check report modification time to ensure it's fresh
    report_mtime = os.path.getmtime(report_path)
    report_age_seconds = time.time() - report_mtime
    report_age_minutes = report_age_seconds / 60
    
    print(f"Reading report from {report_path}...")
    print(f"Report last modified: {time.ctime(report_mtime)} ({report_age_minutes:.1f} minutes ago)")
    
    if report_age_minutes > 5:
        print(f"[WARN] Report is {report_age_minutes:.1f} minutes old.")
        print(f"[INFO] For best results, the report should be regenerated before analysis.")
        print(f"[INFO] Regenerating report now...")
        
        # Regenerate the report to ensure fresh data
        import subprocess
        import sys
        base_dir = Path(__file__).parent.parent
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(base_dir)
            result = subprocess.run(
                [sys.executable, str(base_dir / "src" / "reports" / "generate_report.py")],
                cwd=str(base_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                print("[OK] Report regenerated successfully")
                # Update report_mtime after regeneration
                report_mtime = os.path.getmtime(report_path)
                report_age_seconds = time.time() - report_mtime
                report_age_minutes = report_age_seconds / 60
                print(f"New report age: {report_age_minutes:.1f} minutes")
            else:
                print(f"[WARN] Report regeneration failed: {result.stderr}")
                print("[INFO] Continuing with existing report...")
        except Exception as e:
            print(f"[WARN] Could not regenerate report: {e}")
            print("[INFO] Continuing with existing report...")
    
    # Extract text from HTML
    print("Extracting text from HTML report...")
    report_text = extract_text_from_html(report_path)
    
    if not report_text:
        print("[ERROR] Could not extract text from report")
        return
    
    print(f"[OK] Extracted {len(report_text)} characters of text")
    
    # Show a preview of what we're sending (first 500 chars)
    # Use safe encoding for Windows console
    print(f"\nPreview of report text being analyzed:")
    print("-" * 60)
    try:
        preview = report_text[:500] + "..." if len(report_text) > 500 else report_text
        # Replace problematic Unicode characters for console display
        preview_safe = preview.encode('ascii', 'replace').decode('ascii')
        print(preview_safe)
    except:
        print("[Preview available but contains non-ASCII characters]")
    print("-" * 60)
    
    # Analyze with ChatGPT
    try:
        analysis = asyncio.run(analyze_with_chatgpt(report_text, api_key))
        
        # Save analysis
        analysis_path = Path(__file__).parent.parent / "data" / "outputs" / "chatgpt_analysis.txt"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("CHATGPT FINANCIAL ANALYSIS\n")
            f.write(f"Generated: {Path(__file__).parent.parent / 'data' / 'outputs' / 'report.html'}\n")
            f.write("=" * 60 + "\n\n")
            f.write(analysis)
        
        print(f"\n[OK] Analysis complete!")
        print(f"Analysis saved to: {analysis_path}")
        print("\n" + "=" * 60)
        print("ANALYSIS:")
        print("=" * 60)
        print(analysis)
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error analyzing with ChatGPT: {e}")
        raise

if __name__ == "__main__":
    main()

