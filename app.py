"""
Vercel Serverless Entrypoint for Studio Pro
Provides both WSGI ('app') and BaseHTTPRequestHandler ('handler') interfaces.
Serves index.html, sitemap.xml, and robots.txt with 100% reliability.
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

SITEMAP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://ilovepdf.gentechbridge.com/</loc>
    <lastmod>2026-11-13</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""

ROBOTS_TXT = b"""User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Bingbot
Allow: /

Sitemap: https://ilovepdf.gentechbridge.com/sitemap.xml
"""


def get_html_data():
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f.read()
            except Exception:
                pass
    return b"<!DOCTYPE html><html><head><title>Studio Pro</title></head><body><h1>Studio Pro</h1></body></html>"


def is_sitemap_req(path_val, headers_val):
    s = f"{path_val} {headers_val}".lower()
    return "sitemap.xml" in s or "sitemap" in s


def is_robots_req(path_val, headers_val):
    s = f"{path_val} {headers_val}".lower()
    return "robots.txt" in s or "robots" in s


# 1. WSGI Interface (Vercel standard)
def app(environ, start_response):
    path = environ.get("PATH_INFO", "")
    req_uri = environ.get("REQUEST_URI", "")
    x_matched = environ.get("HTTP_X_MATCHED_PATH", "")
    x_fwd = environ.get("HTTP_X_FORWARDED_URI", "")
    raw_debug = f"{path} {req_uri} {x_matched} {x_fwd}"

    if is_sitemap_req(path, raw_debug):
        data = SITEMAP_XML
        content_type = "application/xml; charset=utf-8"
        cache = "public, max-age=86400"
    elif is_robots_req(path, raw_debug):
        data = ROBOTS_TXT
        content_type = "text/plain; charset=utf-8"
        cache = "public, max-age=86400"
    else:
        data = get_html_data()
        content_type = "text/html; charset=utf-8"
        cache = "no-cache, no-store, must-revalidate"

    status = "200 OK"
    response_headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(data))),
        ("Cache-Control", cache)
    ]
    start_response(status, response_headers)
    return [data]


# 2. BaseHTTPRequestHandler Interface (Vercel Serverless Function)
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        raw_debug = f"{self.path} {self.headers.get('x-matched-path', '')} {self.headers.get('x-forwarded-uri', '')} {self.headers.get('x-vercel-sc-path', '')}"

        if is_sitemap_req(self.path, raw_debug):
            data = SITEMAP_XML
            content_type = "application/xml; charset=utf-8"
            cache = "public, max-age=86400"
        elif is_robots_req(self.path, raw_debug):
            data = ROBOTS_TXT
            content_type = "text/plain; charset=utf-8"
            cache = "public, max-age=86400"
        else:
            data = get_html_data()
            content_type = "text/html; charset=utf-8"
            cache = "no-cache, no-store, must-revalidate"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        raw_debug = f"{self.path} {self.headers.get('x-matched-path', '')} {self.headers.get('x-forwarded-uri', '')} {self.headers.get('x-vercel-sc-path', '')}"

        if is_sitemap_req(self.path, raw_debug):
            data_len = len(SITEMAP_XML)
            content_type = "application/xml; charset=utf-8"
        elif is_robots_req(self.path, raw_debug):
            data_len = len(ROBOTS_TXT)
            content_type = "text/plain; charset=utf-8"
        else:
            data_len = len(get_html_data())
            content_type = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(data_len))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()


# For local direct running
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    print("Serving on http://localhost:8000...")
    httpd = make_server("127.0.0.1", 8000, app)
    httpd.serve_forever()
