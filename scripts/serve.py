"""Servidor local da página (docs/) sem cache, para ver mudanças só recarregando.

Uso: python scripts/serve.py  →  http://localhost:8000
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
PORT = 8000


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", PORT), partial(NoCacheHandler, directory=str(DOCS)))
    print(f"Página em http://localhost:{PORT}  (Ctrl+C para parar)")
    server.serve_forever()
