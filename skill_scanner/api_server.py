"""
API Server for Skill Security Scanner.

Provides REST API for scanning skills programmatically.
"""

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from typing import Dict, Any
from skill_scanner.scanner import SkillScanner


class ScanHandler(BaseHTTPRequestHandler):
    """HTTP request handler for scan endpoints."""

    scanner: SkillScanner = None

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/scan":
            self.handle_scan()
        else:
            self.send_error(404, "Not Found")

    def handle_scan(self):
        """Handle scan request."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            path = data.get("path")
            if not path:
                self.send_error(400, "Missing 'path' parameter")
                return

            scanner = SkillScanner()
            findings = scanner.scan(path)

            response = {
                "status": "success",
                "findings": [
                    {
                        "severity": f.severity.name,
                        "detector": f.detector,
                        "description": f.description,
                        "file": f.file_path,
                        "line": f.line_number,
                    }
                    for f in findings
                ],
                "total": len(findings),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def serve(host: str = "0.0.0.0", port: int = 8080):
    """Start the API server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, ScanHandler)
    print(f"API Server running on http://{host}:{port}")
    print("Endpoints:")
    print("  POST /scan - Scan a skill directory")
    print("  Body: {\"path\": \"/path/to/skill\"}")
    httpd.serve_forever()


def main():
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(description="Skill Security Scanner API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    args = parser.parse_args()

    serve(args.host, args.port)


if __name__ == "__main__":
    main()
