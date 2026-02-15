#!/usr/bin/env python3
"""
Simple HTTP server for genealogical database
"""

import http.server
import socketserver
import os

PORT = 8000

# Change to project directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("Genealogical Database - Web Server")
print("=" * 70)
print()
print(f"Server starting on port {PORT}...")
print()
print("Open your browser and navigate to:")
print(f"  http://localhost:{PORT}/web/")
print()
print("Press Ctrl+C to stop the server")
print("=" * 70)
print()

# Create handler
Handler = http.server.SimpleHTTPRequestHandler

# Start server
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
