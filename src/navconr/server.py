"""Loopback-only read bridge for the optional inspector."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, unquote, urlsplit

from .index import Index
from .models import NavconrError


def make_handler(database: Path, viewer: Path):
    viewer = viewer.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, body: bytes, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            port = cast(HTTPServer, self.server).server_port
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            origin = self.headers.get("Origin")
            if (
                self.headers.get("Host") not in hosts
                or (origin and origin not in {"http://" + h for h in hosts})
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                self.send(403, b'{"error":"loopback same-origin requests only"}')
                return
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)

            def arg(key, default=None):
                return query.get(key, [default])[0]

            try:
                if parsed.path.startswith("/api/"):
                    with Index(database) as index:
                        session = index.session(arg("revision"))
                        limit = int(arg("limit", "20"))
                        if not 1 <= limit <= 100:
                            raise NavconrError("limit must be 1..100")
                        kwargs = {"limit": limit, "cursor": arg("cursor")}
                        action = parsed.path[5:]
                        if action == "status":
                            value = {
                                "schema_version": 1,
                                "revision": session.data.revision,
                                "sources": len(session.data.sources),
                                "nodes": len(session.data.nodes),
                                "spans": len(session.data.spans),
                                "diagnostics": session.data.diagnostics[:20],
                            }
                        elif action == "overview":
                            value = session.overview(
                                view=arg("view", "physical"), **kwargs
                            ).model_dump()
                        elif action == "expand":
                            value = session.expand(arg("ids", "").split(","), **kwargs).model_dump()
                        elif action == "search":
                            value = session.search(arg("q", ""), **kwargs).model_dump()
                        elif action == "node":
                            value = session.card(arg("id", "")).model_dump()
                        elif action == "follow":
                            value = session.follow(
                                arg("id", ""),
                                relation=arg("relation", "reference"),
                                origin=arg("origin"),
                                **kwargs,
                            ).model_dump()
                        elif action == "read":
                            value = {
                                "items": [
                                    r.model_dump() for r in session.read(arg("ids", "").split(","))
                                ]
                            }
                        elif action == "runs":
                            offset = int(arg("offset", "0"))
                            if offset < 0:
                                raise NavconrError("offset must be nonnegative")
                            rows = index.store.db.execute(
                                "SELECT data FROM runs ORDER BY rowid DESC LIMIT ? OFFSET ?",
                                (limit + 1, offset),
                            ).fetchall()
                            value = {
                                "items": [
                                    {
                                        k: json.loads(row[0])[k]
                                        for k in [
                                            "run_id",
                                            "revision",
                                            "query",
                                            "policy",
                                            "stop_reason",
                                            "usage",
                                        ]
                                    }
                                    for row in rows[:limit]
                                ],
                                "next_offset": offset + limit if len(rows) > limit else None,
                            }
                        elif action == "run":
                            run = index.store.run(arg("id", ""))
                            offset = int(arg("offset", "0"))
                            if offset < 0:
                                raise NavconrError("offset must be nonnegative")
                            value = {
                                "schema_version": 1,
                                "run_id": run.run_id,
                                "query": run.query,
                                "revision": run.revision,
                                "usage": run.usage.model_dump(),
                                "stop_reason": run.stop_reason,
                                "trace": [
                                    e.model_dump() for e in run.trace[offset : offset + limit]
                                ],
                                "next_offset": offset + limit
                                if offset + limit < len(run.trace)
                                else None,
                                "evidence": [e.span.model_dump() for e in run.evidence],
                            }
                        else:
                            self.send(404, b'{"error":"unknown API route"}')
                            return
                    body = json.dumps(value, ensure_ascii=False).encode()
                    if len(body) > 2_000_000:
                        raise NavconrError("response exceeds inspector limit; use a smaller page")
                    self.send(200, body)
                else:
                    path = (viewer / unquote(parsed.path).lstrip("/")).resolve()
                    if not path.is_relative_to(viewer):
                        self.send(403, b"forbidden", "text/plain")
                        return
                    if path.is_dir():
                        path = path / "index.html"
                    if not path.is_file():
                        self.send(404, b"viewer file unavailable; build viewer first", "text/plain")
                        return
                    self.send(
                        200,
                        path.read_bytes(),
                        mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    )
            except (NavconrError, ValueError, OSError) as exc:
                self.send(400, json.dumps({"error": str(exc)}).encode())

    return Handler


def serve(index: Index, port: int, viewer: Path):
    server = HTTPServer(("127.0.0.1", port), make_handler(index.store.path.resolve(), viewer))
    print(f"Navconr inspector: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
