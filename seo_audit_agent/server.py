from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from . import nap, q1_onpage, q3_grounded_qa
from .ai_provider import AIProvider, _is_valid_key, deterministic_seo_summary


class APIHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: dict | list):
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.wfile.write(payload)

    def _parse_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/api/health", "/"):
            gemini_key = _is_valid_key(os.getenv("GEMINI_API_KEY"))
            groq_key = _is_valid_key(os.getenv("GROQ_API_KEY"))
            openai_key = _is_valid_key(os.getenv("OPENAI_API_KEY"))
            self._send_json(200, {
                "status": "healthy",
                "service": "SEO Audit Agent API",
                "version": "2.0.0",
                "available_providers": {
                    "gemini": gemini_key,
                    "groq": groq_key,
                    "openai": openai_key,
                    "manual": True,
                },
            })
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._parse_body()
        url = body.get("url", "").strip()

        if not url and parsed.path.startswith("/api/"):
            self._send_json(400, {"error": "Missing 'url' parameter in JSON payload"})
            return

        max_pages = int(body.get("max_pages", 25))
        timeout = float(body.get("timeout", 12.0))
        concurrency = int(body.get("concurrency", 5))
        ai_provider = body.get("ai_provider", "auto")
        ai_model = body.get("ai_model", None)

        try:
            if parsed.path == "/api/audit":
                # Question 1: On-page SEO Auditor
                findings = q1_onpage.run(
                    url=url,
                    output=os.devnull,
                    max_pages=max_pages,
                    timeout=timeout,
                    concurrency=concurrency,
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                )
                ai = AIProvider(provider=ai_provider, model=ai_model)
                summary = ai.generate_seo_summary(findings, url) if ai.is_available else None

                self._send_json(200, {
                    "task": "q1_onpage",
                    "url": url,
                    "summary": summary,
                    "findings_count": len(findings),
                    "findings": findings,
                })

            elif parsed.path == "/api/nap":
                # Question 2: NAP Consistency Checker (100% Rule-Based)
                report = nap.run(
                    url=url,
                    output=os.devnull,
                    max_pages=max_pages,
                    timeout=timeout,
                    concurrency=concurrency,
                )
                self._send_json(200, {
                    "task": "q2_nap",
                    "url": url,
                    "fields": report,
                })

            elif parsed.path == "/api/qa":
                # Question 3: Grounded Q&A Agent
                query = body.get("query", "").strip()
                if not query:
                    self._send_json(400, {"error": "Missing 'query' parameter for Q&A agent"})
                    return

                ans = q3_grounded_qa.run(
                    url=url,
                    query=query,
                    output=os.devnull,
                    max_pages=max_pages,
                    timeout=timeout,
                    concurrency=concurrency,
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                )
                self._send_json(200, {
                    "task": "q3_qa",
                    "url": url,
                    "query": query,
                    "answer": ans,
                })

            else:
                self._send_json(404, {"error": f"Unknown endpoint: {parsed.path}"})

        except Exception as e:
            self._send_json(500, {"error": str(e), "task": parsed.path})

    def log_message(self, format, *args):
        # Clean logging to stderr
        sys.stderr.write(f"[API Server] {self.address_string()} - {format % args}\n")


def run_server(host: str = "127.0.0.1", port: int = 8000):
    server = HTTPServer((host, port), APIHandler)
    print(f"[API Server] Listening on http://{host}:{port} ...", file=sys.stderr)
    print(f"[API Server] Endpoints available: /api/audit, /api/nap, /api/qa, /api/health", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[API Server] Shutting down.", file=sys.stderr)
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEO Audit Agent HTTP API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    args = parser.parse_args()
    run_server(args.host, args.port)
