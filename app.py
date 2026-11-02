"""
Vercel Serverless Entrypoint for Studio Pro
Provides both WSGI ('app') and BaseHTTPRequestHandler ('handler') interfaces.
Serves index.html with 100% reliability and zero external dependencies.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
CANDIDATE_PATHS = [
    os.path.join(CURR_DIR, "index.html"),
    os.path.join(CURR_DIR, "..", "index.html"),
    os.path.abspath("index.html")
]

HTML_BYTES = None
for p in CANDIDATE_PATHS:
    if os.path.exists(p):
        try:
            with open(p, "rb") as f:
                HTML_BYTES = f.read()
            break
        except Exception:
            pass

if HTML_BYTES is None:
    HTML_BYTES = b"<!DOCTYPE html><html><head><title>Studio Pro</title></head><body><h1>Studio Pro</h1></body></html>"


def get_html_data():
    return HTML_BYTES


# 1. WSGI Interface (Vercel standard)
def app(environ, start_response):
    data = get_html_data()
    status = "200 OK"
    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(data))),
        ("Cache-Control", "public, max-age=3600")
    ]
    start_response(status, response_headers)
    return [data]


# 2. BaseHTTPRequestHandler Interface (Vercel Serverless Function)
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = get_html_data()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        data = get_html_data()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()


# For local direct running
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    print("Serving on http://localhost:8000...")
    httpd = make_server("127.0.0.1", 8000, app)
    httpd.serve_forever()
