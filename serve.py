"""
STARAPP LOCAL FULL-STACK LAUNCHER
Launches the FastAPI backend with persistent SQLite3 storage, REST APIs,
server-side RBAC, and static frontend presentation serving.
"""

import sys
import os

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
if DIRECTORY not in sys.path:
    sys.path.insert(0, DIRECTORY)

try:
    import uvicorn
    HAVE_UVICORN = True
except ImportError:
    HAVE_UVICORN = False


def main():
    if HAVE_UVICORN:
        print("==================================================================")
        print("   STARAPP FULL-STACK PLATFORM — LOCAL PRODUCTION SERVER")
        print("==================================================================")
        print(" * Architecture: Modular FastAPI + SQLite3 + Native Frontend")
        print(" * Local URL:    http://127.0.0.1:8000")
        print(" * API Docs:     http://127.0.0.1:8000/docs")
        print(" * Health Check: http://127.0.0.1:8000/api/health")
        print("==================================================================")
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
    else:
        print("[WARN] uvicorn not installed. Falling back to static http.server...")
        import http.server
        import socketserver
        socketserver.TCPServer.allow_reuse_address = True
        handler = http.server.SimpleHTTPRequestHandler
        try:
            with socketserver.TCPServer(("127.0.0.1", 8000), handler) as httpd:
                print("Serving static StarApp at http://127.0.0.1:8000 (Ctrl+C to stop)...")
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStarApp server stopped gracefully.")


if __name__ == "__main__":
    main()
