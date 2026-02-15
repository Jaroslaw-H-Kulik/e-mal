#!/usr/bin/env python3
"""
Simple HTTP server with write capability for genealogy editor.
Serves static files and handles POST requests to save merge logs.
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class GenealogyServerHandler(SimpleHTTPRequestHandler):
    """Extended HTTP handler with POST support for saving data"""

    def do_GET(self):
        """Handle GET requests (serve files)"""
        # Default to serving from web/ directory
        if self.path == '/':
            self.path = '/web/index.html'
        elif not self.path.startswith('/web/') and not self.path.startswith('/data/'):
            self.path = '/web' + self.path

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests (save data)"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))

            # Handle different endpoints
            if self.path == '/api/save-merge-log':
                self.save_merge_log(data)
            elif self.path == '/api/save-data':
                self.save_genealogy_data(data)
            else:
                self.send_error(404, "Endpoint not found")
                return

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'status': 'success', 'message': 'Data saved successfully'}
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Error saving data: {str(e)}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def save_merge_log(self, data):
        """Save merge log to data/merge_log.json"""
        merge_log_path = 'data/merge_log.json'

        # Load existing merge log if it exists
        existing_merges = []
        if os.path.exists(merge_log_path):
            try:
                with open(merge_log_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_merges = existing_data.get('merges', [])
            except:
                pass  # If file is corrupted, start fresh

        # Append new merges (avoid duplicates)
        new_merges = data.get('merges', [])
        for new_merge in new_merges:
            # Check if this merge already exists
            is_duplicate = any(
                m['kept_name'] == new_merge['kept_name'] and
                m['merged_name'] == new_merge['merged_name']
                for m in existing_merges
            )
            if not is_duplicate:
                existing_merges.append(new_merge)

        # Save updated merge log
        merge_log = {
            'instructions': 'This file contains merge records. The parser will automatically apply these merges when processing base.md.',
            'merges': existing_merges,
            'total_merges': len(existing_merges),
            'last_updated': data.get('last_updated')
        }

        with open(merge_log_path, 'w', encoding='utf-8') as f:
            json.dump(merge_log, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved merge log: {len(existing_merges)} total merges")

    def save_genealogy_data(self, data):
        """Save complete genealogy data to data/genealogy_complete.json"""
        data_path = 'data/genealogy_complete.json'

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved genealogy data: {len(data.get('persons', {}))} persons")


def run_server(port=8001):
    """Start the genealogy server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, GenealogyServerHandler)

    print("=" * 70)
    print("Genealogy Editor Server")
    print("=" * 70)
    print(f"Server running at: http://localhost:{port}/")
    print(f"Web interface: http://localhost:{port}/web/")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")


if __name__ == '__main__':
    run_server(8001)
