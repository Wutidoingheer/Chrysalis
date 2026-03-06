"""
Start a local web server to host the financial reports.

This allows you to access all reports via http://localhost:8080
"""
import http.server
import socketserver
import webbrowser
import threading
from pathlib import Path
import sys

PORT = 8080
BASE_DIR = Path(__file__).parent.parent

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from the outputs directory."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR / "data" / "outputs"), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging, or customize it
        pass

def start_server(port=8080, open_browser=True):
    """Start the local web server."""
    handler = CustomHTTPRequestHandler
    
    # Try to bind to the port
    for attempt in range(5):
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                url = f"http://localhost:{port}"
                print(f"🌐 Local server started at {url}")
                print(f"📂 Serving files from: {BASE_DIR / 'data' / 'outputs'}")
                print(f"\n📊 Available reports:")
                print(f"   Dashboard: {url}/dashboard.html")
                print(f"   Report: {url}/report.html")
                print(f"   Analysis: {url}/analysis_visualization.html")
                print(f"\nPress Ctrl+C to stop the server")
                
                if open_browser:
                    # Open browser after a short delay
                    def open_browser_delayed():
                        import time
                        time.sleep(1)
                        webbrowser.open(f"{url}/dashboard.html")
                    
                    threading.Thread(target=open_browser_delayed, daemon=True).start()
                
                httpd.serve_forever()
        except OSError as e:
            if "Address already in use" in str(e) or "address is already in use" in str(e).lower():
                port += 1
                if attempt < 4:
                    print(f"⚠️  Port {port-1} in use, trying {port}...")
                    continue
            raise
        break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Start local web server for financial reports')
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on (default: 8080)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    args = parser.parse_args()
    
    try:
        start_server(port=args.port, open_browser=not args.no_browser)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)



