"""
STARAPP STATIC LAUNCHER
Standard static HTTP file server using Python's built-in http.server.
(No backend framework, no database, no Flask/Django/FastAPI).
Serves index.html, CSS, and JS files to local browser.
"""

import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and shared array buffer headers if needed
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def copyfile(self, source, outputfile):
        """Silently handle browser client disconnects (WinError 10053 / BrokenPipe) without crashing."""
        try:
            super().copyfile(source, outputfile)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def handle_one_request(self):
        """Catch early socket resets from browser parallel connection pooling."""
        try:
            super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

class RobustThreadingServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        """Suppress benign client-abort errors from polluting terminal or blocking execution."""
        exc_type, exc_val = sys.exc_info()[:2]
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        super().handle_error(request, client_address)

def main():
    os.chdir(DIRECTORY)
    with RobustThreadingServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print(f"==================================================")
        print(f"STARAPP LOCAL STATIC PROTOTYPE SERVER (THREADED)")
        print(f"Serving at: {url}")
        print(f"Press Ctrl+C to stop.")
        print(f"==================================================")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    main()

