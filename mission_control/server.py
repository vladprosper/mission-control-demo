"""Local demonstration HTTP server; not a production deployment server."""
import json
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .store import ValidationError, report
from .portfolio import portfolio
from .story import Story

STATIC = Path(__file__).parent / "static"
ASSETS = {"/": ("story.html", "text/html; charset=utf-8"),
          "/technical": ("index.html", "text/html; charset=utf-8"),
          "/technical/": ("index.html", "text/html; charset=utf-8"),
          "/static/story.js": ("story.js", "text/javascript; charset=utf-8"),
          "/static/story.css": ("story.css", "text/css; charset=utf-8"),
          "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/static/style.css": ("style.css", "text/css; charset=utf-8")}
ASSETS.update({"/static/experience.js": ("experience.js", "text/javascript; charset=utf-8"),
               "/static/experience.css": ("experience.css", "text/css; charset=utf-8")})



def make_server(db_path, port=0, as_of=None, workbench=False):
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise ValidationError("Initialize and import a fictional database before serving")
    lab = None
    story = Story()
    if workbench:
        from .workbench import Workbench
        with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as baseline:
            baseline.row_factory = sqlite3.Row
            lab = Workbench(baseline, as_of)

    class Handler(BaseHTTPRequestHandler):
        def send_body(self, status, content, kind):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/health":
                self.send_body(200, b'{"ok":true,"fictional":true,"application":"mission-control-demo","version":3}', "application/json")
            elif path == "/api/story":
                self.send_json(200, {**story.state(), "interactive": bool(lab)})
            elif path == "/api/context":
                self.send_json(200, portfolio())
            elif path == "/api/workbench" and lab:
                self.send_json(200, lab.state())
            elif path == "/api/report":
                try:
                    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
                        db.row_factory = sqlite3.Row
                        payload = report(db, as_of)
                    self.send_body(200, json.dumps(payload, allow_nan=False).encode(), "application/json")
                except (sqlite3.Error, ValidationError):
                    self.send_body(503, b'{"error":"Report unavailable. Check database and reporting time."}', "application/json")
            elif path in ASSETS:
                file, kind = ASSETS[path]
                asset = STATIC / file
                if asset.is_file():
                    self.send_body(200, asset.read_bytes(), kind)
                else:
                    self.send_body(404, b"Artifact not available", "text/plain")
            else:
                self.send_body(404, b"Not found", "text/plain")

        def send_json(self, status, value):
            self.send_body(status, json.dumps(value, allow_nan=False).encode(), "application/json")

        def do_POST(self):
            if not lab:
                self.send_error(501, "Workbench is disabled")
                return
            path = urlsplit(self.path).path
            if path not in ("/api/story/advance", "/api/workbench/preview", "/api/workbench/apply", "/api/workbench/reset"):
                self.send_json(404, {"error": "Unknown workbench action"})
                return
            # Same-origin, bounded JSON actions over predefined synthetic fixtures only.
            host = self.headers.get("Host", "")
            origins = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if host not in origins or self.headers.get("Origin") != "http://" + host:
                self.send_json(403, {"error": "Workbench actions require the exact local page origin"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send_json(415, {"error": "JSON required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Request must be 1–4096 bytes")
                body = json.loads(self.rfile.read(length))
                if path == "/api/story/advance":
                    if not isinstance(body, dict) or set(body) != {"action", "revision"} or not isinstance(body["action"], str) or type(body["revision"]) is not int:
                        raise ValueError("Expected an action and integer revision")
                    try:
                        self.send_json(200, {**story.advance(body["action"], body["revision"]), "interactive": True})
                    except ValueError as exc:
                        self.send_json(409, {"error": str(exc)})
                    return
                fields = {"scenario", "preview_token"} if path.endswith("/apply") else set() if path.endswith("/reset") else {"scenario"}
                if not isinstance(body, dict) or set(body) != fields or any(not isinstance(v, str) for v in body.values()):
                    raise ValueError("Unexpected action fields")
                if path.endswith("/reset"):
                    result = lab.reset()
                elif path.endswith("/preview"):
                    result = lab.preview(body["scenario"])
                else:
                    result = lab.apply(body["scenario"], body["preview_token"])
                self.send_json(200, result)
            except (ValueError, UnicodeDecodeError) as exc:
                self.send_json(409 if isinstance(exc, ValidationError) else 400, {"error": str(exc)})

        def log_message(self, *_):
            pass

    class DemoServer(ThreadingHTTPServer):
        def server_close(self):
            super().server_close()
            if lab:
                lab.close()
            story.close()

    return DemoServer(("127.0.0.1", port), Handler)


def serve(db_path, port=0, as_of=None):
    with make_server(db_path, port, as_of) as server:
        print(f"Fictional demo: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
