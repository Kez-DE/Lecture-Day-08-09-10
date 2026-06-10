#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from rag_agent import call_openrouter, retrieve

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length).decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "Day10Chat/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/chat"):
            self._serve_file(STATIC_DIR / "chat.html")
            return
        if path == "/api/status":
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "collection": os.environ.get("CHROMA_COLLECTION", "day10_kb_qwen3"),
                    "embedding_provider": os.environ.get("EMBEDDING_PROVIDER", "ollama"),
                    "embedding_model": os.environ.get("EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
                    "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "openrouter_model": os.environ.get("OPENROUTER_MODEL", "openrouter/owl-alpha"),
                    "openrouter_key_configured": bool(os.environ.get("OPENROUTER_API_KEY", "").strip()),
                },
            )
            return
        if path.startswith("/static/"):
            self._serve_file(STATIC_DIR / path.removeprefix("/static/"))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/chat", "/api/retrieve"):
            self.send_error(404)
            return
        try:
            payload = _read_json(self)
            question = (payload.get("question") or "").strip()
            top_k = int(payload.get("top_k") or 5)
            top_k = max(1, min(top_k, 10))
            if not question:
                _json_response(self, 400, {"ok": False, "error": "question is required"})
                return

            contexts = retrieve(question, top_k=top_k)
            if path == "/api/retrieve":
                _json_response(self, 200, {"ok": True, "contexts": contexts})
                return

            answer = call_openrouter(question, contexts)
            _json_response(self, 200, {"ok": True, "answer": answer, "contexts": contexts})
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            _json_response(self, 500, {"ok": False, "error": str(e)})

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _serve_file(self, path: Path) -> None:
        if not path.is_file() or STATIC_DIR not in path.resolve().parents and path.resolve() != STATIC_DIR:
            self.send_error(404)
            return
        suffix = path.suffix.lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local web chat UI for Day 10 RAG agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ChatHandler)
    print(f"Day 10 chat UI: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping chat server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
