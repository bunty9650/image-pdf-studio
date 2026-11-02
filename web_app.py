"""
Local Web Server for Studio Pro
Serves the modern, Vercel-ready index.html locally with zero external dependencies.
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_free_port(start_port: int = 3000) -> int:
    port = start_port
    while port < 4000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return 3000


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    port = find_free_port(3000)
    server_address = ("127.0.0.1", port)

    class CustomHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    httpd = HTTPServer(server_address, CustomHandler)
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("Studio Pro - Local Web Server")
    print(f"Running at: {url}")
    print("Opening your default browser...")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    main()
