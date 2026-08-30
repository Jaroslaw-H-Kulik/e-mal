#!/usr/bin/env python3
"""
HTTP server for the genealogy editor: routes GET/POST requests, serves
static files from web/, and delegates genealogy data logic to
app.genealogy_repository.GenealogyRepository. The Geneteka proxy and
document management remain in this file for now.
"""

import base64
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from app.genealogy_repository import GenealogyRepository

# Ensure stdout/stderr use UTF-8 on Windows
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
except AttributeError:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

print("[SERVER] Starting server (utf-8 stdout/stderr configured)")

genealogy_repo = GenealogyRepository()


class GenealogyServerHandler(SimpleHTTPRequestHandler):
    """Extended HTTP handler with POST support for saving data"""

    def do_GET(self):
        """Handle GET requests (serve files and API endpoints)"""
        # Handle API endpoints
        if self.path.startswith('/api/geneteka-import'):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            first_name = params.get('first_name', [''])[0]
            last_name = params.get('last_name', [''])[0]
            record_type = params.get('type', ['birth'])[0]
            response_data = self.geneteka_import(first_name, last_name, record_type)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            return

        # Default to serving from web/ directory
        if self.path == '/':
            self.path = '/web/index.html'
        elif self.path.startswith('/person/') or self.path.startswith('/document/') or self.path == '/events':
            # SPA routing: serve index.html for clean entity URLs
            self.path = '/web/index.html'
        elif not self.path.startswith('/web/') and not self.path.startswith('/data/'):
            self.path = '/web' + self.path

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests (save data)"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'

        try:
            data = json.loads(post_data.decode('utf-8'))

            # Handle different endpoints
            if self.path == '/api/save-data':
                genealogy_repo.save_genealogy_data(data)
                response_data = {'status': 'success', 'message': 'Data saved successfully'}
            elif self.path == '/api/add-person':
                response_data = genealogy_repo.add_person(data)
            elif self.path == '/api/add-relationship':
                response_data = genealogy_repo.add_relationship(data)
            elif self.path == '/api/add-event':
                response_data = genealogy_repo.add_event(data)
            elif self.path == '/api/update-event':
                response_data = genealogy_repo.update_event(data)
            elif self.path == '/api/update-person':
                response_data = genealogy_repo.update_person(data)
            elif self.path == '/api/delete-person':
                response_data = genealogy_repo.delete_person(data)
            elif self.path == '/api/delete-event':
                response_data = genealogy_repo.delete_event(data)
            elif self.path == '/api/add-document':
                response_data = self.add_document(data)
            elif self.path == '/api/update-document':
                response_data = self.update_document(data)
            elif self.path == '/api/delete-document':
                response_data = self.delete_document(data)
            elif self.path == '/api/delete-document-page':
                response_data = self.delete_document_page(data)
            else:
                self.send_error(404, "Endpoint not found")
                return

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')
            try:
                with open(log_path, 'a', encoding='utf-8') as _log:
                    _log.write(f"=== do_POST exception ===\n")
                    _log.write(f"Type: {type(e).__name__}\n")
                    _log.write(f"Repr: {repr(e)}\n")
                    traceback.print_exc(file=_log)
                    _log.write("---\n")
            except Exception as log_err:
                pass
            # Use ascii-safe message for HTTP status line (latin-1 encoding required)
            safe_msg = repr(e).encode('ascii', errors='replace').decode('ascii')
            self.send_error(500, f"Error saving data: {safe_msg}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def geneteka_import(self, first_name, last_name, record_type='birth'):
        """Proxy request to Geneteka API and return parsed records (birth/marriage/death)"""
        import urllib.request
        import urllib.parse
        import re

        type_config = {
            'birth':    ('B', '3382'),
            'marriage': ('S', '3560'),
            'death':    ('D', '3384'),
        }
        bdm, rid = type_config.get(record_type, ('B', '3382'))

        def extract_uwagi(html):
            notes_parts = re.findall(r'<img[^>]+title="([^"]*)"', html)
            return ' | '.join(t.strip() for t in notes_parts if t.strip())

        def extract_links(html):
            return re.findall(r'href="(https?://[^"]+)"', html)

        def strip_html(text):
            return re.sub(r'<[^>]+>', '', text).strip()

        def parse_rodzice(rodzice):
            """Parse 'FatherName, MotherName MotherMaiden' into components"""
            if not rodzice or not rodzice.strip():
                return {'father_name': '', 'mother_name': '', 'mother_maiden': ''}
            parts = rodzice.split(',', 1)
            father_name = parts[0].strip()
            mother_part = parts[1].strip() if len(parts) > 1 else ''
            mother_parts = mother_part.split()
            mother_name = mother_parts[0] if mother_parts else ''
            mother_maiden = mother_parts[1] if len(mother_parts) > 1 else ''
            return {'father_name': father_name, 'mother_name': mother_name, 'mother_maiden': mother_maiden}

        try:
            import http.cookiejar
            encoded_last = urllib.parse.quote(last_name)
            encoded_first = urllib.parse.quote(first_name)

            # Build session using a cookie jar so the index page sets cookies
            # before we hit the API (Geneteka returns empty data without a session)
            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            common_headers = [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
                ('Accept-Language', 'pl,en;q=0.9'),
            ]
            # Step 1: visit the HTML search page to establish the session
            index_url = (
                f"https://geneteka.genealodzy.pl/index.php"
                f"?op=gt&lang=pol&bdm={bdm}&w=13sk&rid={rid}"
                f"&search_lastname={encoded_last}&search_name={encoded_first}"
                f"&search_lastname2=&search_name2=&from_date=&to_date="
            )
            index_req = urllib.request.Request(index_url, headers={
                'User-Agent': common_headers[0][1],
                'Accept': 'text/html',
                'Accept-Language': common_headers[1][1],
            })
            with opener.open(index_req, timeout=15) as _:
                pass  # just need the cookies

            # Step 2: call the JSON API with the session cookies
            url = (
                f"https://geneteka.genealodzy.pl/api/getAct.php"
                f"?op=gt&lang=pol&bdm={bdm}&w=13sk&rid={rid}"
                f"&search_lastname={encoded_last}&search_name={encoded_first}"
                f"&search_lastname2=&search_name2=&from_date=&to_date="
                f"&draw=1&start=0&length=100"
            )
            req = urllib.request.Request(url, headers={
                'User-Agent': common_headers[0][1],
                'Referer': index_url,
                'Accept': 'application/json',
                'Accept-Language': common_headers[1][1],
                'X-Requested-With': 'XMLHttpRequest',
            })

            with opener.open(req, timeout=15) as response:
                raw = response.read().decode('utf-8')

            data = json.loads(raw)
            records = []

            for row in data.get('data', []):
                if record_type == 'marriage':
                    # 10 columns: rok, akt, groom_name, groom_surname, groom_parents,
                    #              bride_name, bride_surname, bride_parents, place, uwagi
                    if len(row) < 9:
                        continue
                    uwagi_html = row[9] if len(row) > 9 else ''
                    records.append({
                        'rok': strip_html(row[0]).strip(),
                        'akt': strip_html(row[1]).strip(),
                        'imie_pana': strip_html(row[2]).strip(),
                        'nazwisko_pana': strip_html(row[3]).strip(),
                        'rodzice_pana': strip_html(row[4]).strip(),
                        'imie_pani': strip_html(row[5]).strip(),
                        'nazwisko_pani': strip_html(row[6]).strip(),
                        'rodzice_pani': strip_html(row[7]).strip(),
                        'miejscowosc': strip_html(row[8]).strip(),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                        'rodzice_pana_parsed': parse_rodzice(strip_html(row[4]).strip()),
                        'rodzice_pani_parsed': parse_rodzice(strip_html(row[7]).strip()),
                    })
                elif record_type == 'death':
                    # 9 columns: rok, akt, name, surname (may have HTML), father, mother, mother_maiden, place, uwagi
                    if len(row) < 8:
                        continue
                    uwagi_html = row[8] if len(row) > 8 else ''
                    records.append({
                        'rok': strip_html(row[0]).strip(),
                        'akt': strip_html(row[1]).strip(),
                        'imie': strip_html(row[2]).strip(),
                        'nazwisko': strip_html(row[3]).strip(),
                        'imie_ojca': strip_html(row[4]).strip(),
                        'imie_matki': strip_html(row[5]).strip(),
                        'nazwisko_matki': strip_html(row[6]).strip(),
                        'miejscowosc': strip_html(row[7]).strip(),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                    })
                else:
                    # birth: 10 columns: rok, akt, child_name, surname, father, mother, mother_maiden, parish, place, uwagi
                    # Some older/incomplete records have fewer columns; use empty string for missing fields.
                    if len(row) < 2:
                        continue
                    def col(i): return strip_html(row[i]).strip() if len(row) > i else ''
                    uwagi_html = row[9] if len(row) > 9 else ''
                    records.append({
                        'rok': col(0),
                        'akt': col(1),
                        'imie_dziecka': col(2),
                        'nazwisko': col(3),
                        'imie_ojca': col(4),
                        'imie_matki': col(5),
                        'nazwisko_matki': col(6),
                        'parafia': col(7),
                        'miejscowosc': col(8),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                    })

            return {
                'success': True,
                'records': records,
                'total': data.get('recordsTotal', len(records)),
            }

        except Exception as e:
            print(f"[ERR] Geneteka import error: {e}")
            return {'success': False, 'error': str(e), 'records': []}


    # ── Document management ──────────────────────────────────────────────────

    def _documents_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'documents.json')

    def _documents_dir(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'documents')
        os.makedirs(d, exist_ok=True)
        return d

    def load_documents(self):
        path = self._documents_path()
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_documents(self, documents):
        with open(self._documents_path(), 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

    def get_next_document_id(self, documents):
        existing = []
        for k in documents.keys():
            if k.startswith('D') and k[1:].isdigit():
                existing.append(int(k[1:]))
        next_num = max(existing, default=0) + 1
        return f'D{next_num:02d}'

    def add_document(self, data):
        try:
            documents = self.load_documents()
            doc_id = self.get_next_document_id(documents)
            docs_dir = self._documents_dir()

            pages = []
            for i, page_data in enumerate(data.get('pages', []), start=1):
                ext = page_data.get('ext', 'jpg').lower()
                filename = f'{doc_id}-{i}.{ext}'
                filepath = os.path.join(docs_dir, filename)
                file_bytes = base64.b64decode(page_data['data'])
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                pages.append({'filename': filename, 'transcription': ''})

            document = {
                'id': doc_id,
                'name': data.get('name', ''),
                'date': data.get('date'),
                'notes': data.get('notes', ''),
                'tags': data.get('tags', []),
                'link': data.get('link', ''),
                'events': data.get('events', []),
                'pages': pages,
            }
            documents[doc_id] = document
            self.save_documents(documents)
            print(f'[OK] Created document {doc_id}: {document["name"]} ({len(pages)} pages)')
            return {'success': True, 'document': document}
        except Exception as e:
            print(f'[ERR] add_document: {e}')
            return {'success': False, 'error': str(e)}

    def update_document(self, data):
        try:
            documents = self.load_documents()
            doc_id = data.get('id')
            if doc_id not in documents:
                return {'success': False, 'error': 'Document not found'}
            doc = documents[doc_id]
            for field in ('name', 'date', 'notes', 'tags', 'link', 'events', 'pages'):
                if field in data:
                    doc[field] = data[field]
            documents[doc_id] = doc
            self.save_documents(documents)
            print(f'[OK] Updated document {doc_id}')
            return {'success': True, 'document': doc}
        except Exception as e:
            print(f'[ERR] update_document: {e}')
            return {'success': False, 'error': str(e)}

    def delete_document(self, data):
        try:
            documents = self.load_documents()
            doc_id = data.get('id')
            if doc_id not in documents:
                return {'success': False, 'error': 'Document not found'}
            docs_dir = self._documents_dir()
            for page in documents[doc_id].get('pages', []):
                filepath = os.path.join(docs_dir, page['filename'])
                if os.path.exists(filepath):
                    os.remove(filepath)
            del documents[doc_id]
            self.save_documents(documents)
            print(f'[OK] Deleted document {doc_id}')
            return {'success': True}
        except Exception as e:
            print(f'[ERR] delete_document: {e}')
            return {'success': False, 'error': str(e)}

    def delete_document_page(self, data):
        try:
            documents = self.load_documents()
            doc_id = data.get('doc_id')
            filename = data.get('filename')
            if doc_id not in documents:
                return {'success': False, 'error': 'Document not found'}
            docs_dir = self._documents_dir()
            filepath = os.path.join(docs_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            doc = documents[doc_id]
            doc['pages'] = [p for p in doc.get('pages', []) if p['filename'] != filename]
            documents[doc_id] = doc
            self.save_documents(documents)
            print(f'[OK] Deleted page {filename} from {doc_id}')
            return {'success': True, 'document': doc}
        except Exception as e:
            print(f'[ERR] delete_document_page: {e}')
            return {'success': False, 'error': str(e)}


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
