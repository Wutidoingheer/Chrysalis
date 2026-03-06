"""
Convert ChatGPT analysis to a beautiful HTML visualization.

This script:
1. Reads the ChatGPT analysis text file
2. Converts it to a nicely formatted HTML page
3. Optionally integrates it into the main report
"""
import re
from pathlib import Path
from jinja2 import Template

ANALYSIS_HTML_TEMPLATE = Template("""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Financial Analysis - ChatGPT Insights</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .content {
            padding: 40px;
        }
        
        .section {
            margin-bottom: 40px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .section h2 {
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .section h2::before {
            content: "📊";
            font-size: 1.2em;
        }
        
        .section.concerns h2::before {
            content: "⚠️";
        }
        
        .section.recommendations h2::before {
            content: "💡";
        }
        
        .section.strengths h2::before {
            content: "✅";
        }
        
        .section.budget h2::before {
            content: "💰";
        }
        
        .section ul, .section ol {
            margin-left: 20px;
            margin-top: 15px;
        }
        
        .section li {
            margin-bottom: 12px;
            line-height: 1.8;
        }
        
        .section p {
            margin-bottom: 15px;
            line-height: 1.8;
        }
        
        .highlight {
            background: #fff3cd;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 600;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .badge.positive {
            background: #d4edda;
            color: #155724;
        }
        
        .badge.negative {
            background: #f8d7da;
            color: #721c24;
        }
        
        .badge.warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }
        
        .footer a {
            color: #667eea;
            text-decoration: none;
        }
        
        .footer a:hover {
            text-decoration: underline;
        }
        
        .insight-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .insight-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #e9ecef;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .insight-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .insight-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 8px;
            }
            
            .header {
                padding: 30px 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .content {
                padding: 20px;
            }
            
            .section {
                padding: 20px;
            }
        }
    </style>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/20000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💰</text></svg>">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Financial Analysis</h1>
            <p>AI-Powered Insights from ChatGPT</p>
            <p style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;">Generated {{ timestamp }}</p>
        </div>
        
        <div class="content">
            {% for section in sections %}
            <div class="section {{ section.class }}">
                <h2>{{ section.title }}</h2>
                <div class="section-content">
                    {{ section.content|safe }}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Analysis generated by ChatGPT ({{ model }})</p>
            <p style="margin-top: 10px;">
                <a href="report.html">View Full Financial Report</a> | 
                <a href="chatgpt_analysis.txt">View Raw Analysis</a>
            </p>
        </div>
    </div>
</body>
</html>
""")

def parse_analysis_text(text: str) -> list:
    """Parse the ChatGPT analysis text into structured sections."""
    sections = []
    
    # Split by numbered sections or headers
    # Look for patterns like "### 1. Key Insights" or "**1. Key Insights**"
    patterns = [
        r'###?\s*(\d+)\.\s*\*\*([^*]+)\*\*',
        r'###?\s*(\d+)\.\s*([^\n]+)',
        r'\*\*(\d+)\.\s*([^*]+)\*\*',
    ]
    
    # Try to find sections
    current_section = None
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section header
        is_header = False
        section_title = None
        section_num = None
        
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                section_num = match.group(1)
                section_title = match.group(2).strip()
                is_header = True
                break
        
        # Also check for bold headers
        if not is_header:
            bold_match = re.match(r'\*\*([^*]+)\*\*', line)
            if bold_match and len(line) < 100:  # Likely a header
                section_title = bold_match.group(1).strip()
                is_header = True
        
        if is_header:
            # Save previous section
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content),
                    'class': get_section_class(current_section)
                })
            
            # Start new section
            current_section = section_title
            current_content = []
        else:
            if current_section:
                current_content.append(line)
            else:
                # Content before first section
                if not sections:
                    sections.append({
                        'title': 'Overview',
                        'content': line,
                        'class': 'overview'
                    })
                else:
                    sections[0]['content'] += '\n' + line
    
    # Add last section
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content),
            'class': get_section_class(current_section)
        })
    
    # If no sections found, treat entire text as one section
    if not sections:
        sections.append({
            'title': 'Analysis',
            'content': text,
            'class': 'analysis'
        })
    
    return sections

def get_section_class(title: str) -> str:
    """Get CSS class based on section title."""
    title_lower = title.lower()
    if 'concern' in title_lower or 'red flag' in title_lower:
        return 'concerns'
    elif 'recommendation' in title_lower or 'action' in title_lower:
        return 'recommendations'
    elif 'strength' in title_lower or 'positive' in title_lower:
        return 'strengths'
    elif 'budget' in title_lower or 'spending' in title_lower:
        return 'budget'
    elif 'insight' in title_lower:
        return 'insights'
    else:
        return 'general'

def format_content(content: str) -> str:
    """Format content with HTML tags."""
    # Convert markdown-style formatting to HTML
    content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)
    
    # Convert bullet points
    lines = content.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            continue
        
        # Check for bullet points
        if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
            if not in_list:
                formatted_lines.append('<ul>')
                in_list = True
            line = re.sub(r'^[-•*]\s+', '', line)
            line = re.sub(r'^\d+\.\s+', '', line)
            formatted_lines.append(f'<li>{line}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append(f'<p>{line}</p>')
    
    if in_list:
        formatted_lines.append('</ul>')
    
    return '\n'.join(formatted_lines)

def main():
    """Generate HTML visualization of ChatGPT analysis."""
    base_dir = Path(__file__).parent.parent
    analysis_path = base_dir / "data" / "outputs" / "chatgpt_analysis.txt"
    
    if not analysis_path.exists():
        print(f"[ERROR] Analysis file not found at {analysis_path}")
        print("\nPlease generate the analysis first:")
        print("  python scripts/analyze_report_with_chatgpt.py")
        return
    
    print(f"Reading analysis from {analysis_path}...")
    
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis_text = f.read()
    
    # Remove header if present
    if "=" * 60 in analysis_text:
        parts = analysis_text.split("=" * 60)
        if len(parts) > 2:
            analysis_text = "\n".join(parts[2:]).strip()
    
    # Parse into sections
    print("Parsing analysis into sections...")
    sections = parse_analysis_text(analysis_text)
    
    # Format sections
    formatted_sections = []
    for section in sections:
        formatted_sections.append({
            'title': section['title'],
            'content': format_content(section['content']),
            'class': section['class']
        })
    
    # Generate HTML
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = ANALYSIS_HTML_TEMPLATE.render(
        sections=formatted_sections,
        timestamp=timestamp,
        model="gpt-4o-mini"
    )
    
    # Save HTML
    output_path = base_dir / "data" / "outputs" / "analysis_visualization.html"
    output_path.write_text(html, encoding='utf-8')
    
    print(f"[OK] HTML visualization created: {output_path}")
    print(f"   Open it in your browser to view!")
    
    # Try to open it
    try:
        import webbrowser
        webbrowser.open(str(output_path))
        print("   (Opened in your default browser)")
    except:
        pass

if __name__ == "__main__":
    main()

