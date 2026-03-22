"""
browser_helper_server.py — Run this on your HOST machine before starting Docker.

  python3 browser_helper_server.py

Listens on port 9876 for JSON POST requests from the container
and opens the URL in the host's default browser.
Works on macOS, Windows, and Linux — no dependencies beyond stdlib.
"""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            url = json.loads(self.rfile.read(length)).get("url", "")
            if url:
                print(f"[helper] Opening: {url}")
                webbrowser.open(url)
                self.send_response(200)
            else:
                self.send_response(400)
        except Exception as e:
            print(f"[helper] Error: {e}")
            self.send_response(500)
        self.end_headers()

    def log_message(self, *_):
        pass  # suppress access log


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9876), _Handler)
    print("[helper] Listening on port 9876 — waiting for container requests...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[helper] Stopped.")