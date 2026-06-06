from __future__ import annotations

import argparse
import json
import logging
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.collectors import collect_all
from app.sample_data import demo_markets
from app.scoring import dashboard_payload
from app.store import DEFAULT_DB_PATH, attach_history_changes, connect, latest_snapshots, save_snapshots

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT / "web"
LOGGER = logging.getLogger(__name__)


class SentimentHandler(BaseHTTPRequestHandler):
    db_path = DEFAULT_DB_PATH

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        self._handle_request(head_only=False)

    def do_HEAD(self) -> None:
        self._handle_request(head_only=True)

    def _handle_request(self, head_only: bool) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True}, head_only=head_only)
        elif parsed.path == "/api/refresh":
            limit = _int_query(parsed.query, "limit", 120)
            self._json(refresh_payload(self.db_path, limit=limit), head_only=head_only)
        elif parsed.path == "/api/dashboard":
            self._json(current_payload(self.db_path), head_only=head_only)
        else:
            self._static(parsed.path, head_only=head_only)

    def _json(self, payload: dict[str, object], status: int = HTTPStatus.OK, head_only: bool = False) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _static(self, request_path: str, head_only: bool = False) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        path = (WEB_ROOT / relative).resolve()
        if not path.is_file() or WEB_ROOT.resolve() not in path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)


def refresh_payload(db_path: Path, limit: int = 120) -> dict[str, object]:
    snapshots, errors = collect_all(limit=limit)
    with connect(db_path) as connection:
        if snapshots:
            save_snapshots(connection, snapshots)
            snapshots = attach_history_changes(connection, snapshots)
        else:
            snapshots = latest_snapshots(connection)
            errors.append("No live markets were collected; using latest local snapshots." if snapshots else "No live markets were collected; using demo dataset.")
            if snapshots:
                snapshots = attach_history_changes(connection, snapshots)
    if not snapshots:
        snapshots = demo_markets()
    payload = dashboard_payload(snapshots, errors=errors)
    payload["refreshed"] = True
    payload["savedSnapshots"] = len(snapshots) if payload["status"] == "live" else 0
    return payload


def current_payload(db_path: Path) -> dict[str, object]:
    with connect(db_path) as connection:
        snapshots = attach_history_changes(connection, latest_snapshots(connection))
    if not snapshots:
        snapshots = demo_markets()
    return dashboard_payload(snapshots)


def run(host: str, port: int, db_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    SentimentHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), SentimentHandler)
    LOGGER.info("Serving sentiment barometer at http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the investment sentiment barometer.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(args.host, args.port, args.db)


def _int_query(query: str, key: str, default: int) -> int:
    values = parse_qs(query).get(key)
    if not values:
        return default
    try:
        return max(1, min(500, int(values[0])))
    except ValueError:
        return default


if __name__ == "__main__":
    main()
