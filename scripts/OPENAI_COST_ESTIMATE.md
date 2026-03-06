# OpenAI API Cost Estimate for Financial Report Analysis

## Cost Breakdown

### Per Analysis (Monthly Report)

**Report Size**: ~5,600 characters (~1,400 tokens input)
**Analysis Response**: ~500-1,000 tokens output

#### Model Options & Costs:

1. **gpt-4o-mini** (Recommended - Best value)
   - Input: $0.15 per 1M tokens
   - Output: $0.60 per 1M tokens
   - **Cost per analysis**: ~$0.001 - $0.002 (less than 1 cent!)
   - **Monthly cost**: ~$0.01 - $0.02

2. **gpt-3.5-turbo** (Cheapest)
   - Input: $0.50 per 1M tokens
   - Output: $1.50 per 1M tokens
   - **Cost per analysis**: ~$0.001 - $0.003 (less than 1 cent!)
   - **Monthly cost**: ~$0.01 - $0.03

3. **gpt-4o** (Most capable, but more expensive)
   - Input: $2.50 per 1M tokens
   - Output: $10.00 per 1M tokens
   - **Cost per analysis**: ~$0.01 - $0.05
   - **Monthly cost**: ~$0.10 - $0.50

## Recommendation

**Use `gpt-4o-mini`** - It provides excellent analysis quality at the lowest cost:
- ✅ High quality financial analysis
- ✅ Very affordable (~$0.01/month)
- ✅ Fast response times
- ✅ Good for structured analysis tasks

## Setup Steps

1. **Go to OpenAI Billing**: https://platform.openai.com/account/billing
2. **Add Payment Method**: Credit card or PayPal
3. **Set Usage Limits** (optional but recommended):
   - Set a monthly spending limit (e.g., $5/month)
   - This prevents unexpected charges
4. **Add Credits** (if using prepaid):
   - Minimum is usually $5-10

## Cost Optimization Tips

1. **Use gpt-4o-mini** (already set as default in the script)
2. **Truncate long reports** (script already does this - limits to 8,000 chars)
3. **Reduce max_tokens** if needed (currently 2000, could go to 1500)
4. **Run monthly only** (not daily/weekly)

## Annual Cost Estimate

- **gpt-4o-mini**: ~$0.12 - $0.24/year (12 analyses)
- **gpt-3.5-turbo**: ~$0.12 - $0.36/year
- **gpt-4o**: ~$1.20 - $6.00/year

**Bottom line**: Even with the most expensive option, you're looking at **less than $6/year** for monthly financial analysis!

## Free Alternatives (If You Don't Want to Pay)

If you prefer not to use OpenAI, you could:

1. **Manual Review**: Just review the HTML report yourself
2. **Local LLM**: Use a local model like Ollama (free, but requires setup)
3. **Other Free APIs**: Some alternatives exist but may have limitations
4. **Skip Analysis**: Just use the report without ChatGPT analysis

## Current Script Configuration

The script is already optimized for cost:
- ✅ Uses `gpt-4o-mini` first (cheapest good option)
- ✅ Falls back to `gpt-3.5-turbo` if rate limited
- ✅ Truncates reports to 8,000 characters
- ✅ Limits response to 2,000 tokens
- ✅ Has retry logic to avoid wasted API calls

## Next Steps

1. Add billing to OpenAI: https://platform.openai.com/account/billing
2. Set a spending limit (recommended: $5/month)
3. Test the script: `python scripts/analyze_report_with_chatgpt.py`
4. Schedule monthly runs via Task Scheduler



