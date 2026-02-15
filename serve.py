#!/usr/bin/env python3
"""
Simple HTTP server for the genealogical database web UI
Serves the web interface and data files
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8000
WEB_DIR = "web"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        # Serve files from web directory
        if self.path == '/' or self.path == '/index.html':
            self.path = '/web/index.html'
        elif self.path.startswith('/web/'):
            pass  # Already correct
        elif self.path.startswith('/data/'):
            pass  # Already correct
        else:
            # Default to web directory
            if not self.path.startswith('/'):
                self.path = '/' + self.path
            if not self.path.startswith('/web/') and not self.path.startswith('/data/'):
                self.path = '/web' + self.path

        return super().do_GET()

def main():
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Check if web directory exists
    if not os.path.exists(WEB_DIR):
        print(f"Error: {WEB_DIR} directory not found!")
        return

    # Check if data files exist
    if not os.path.exists('data/genealogy_complete.json'):
        print("Warning: data/genealogy_complete.json not found!")
        print("Please run: python3 process_genealogy.py")
        return

    print("=" * 70)
    print("Genealogical Database - Web Server")
    print("=" * 70)
    print()
    print(f"Starting server on http://localhost:{PORT}")
    print()
    print("Open your browser and navigate to:")
    print(f"  → http://localhost:{PORT}")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()

    # Start server
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        # Open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
            print("Thank you for using the Genealogical Database!")

if __name__ == "__main__":
    main()
